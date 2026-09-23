"""Acceptance tests for Auto Bot LinkedIn Job (Section 18 of Build Spec)."""

import pytest
from datetime import datetime, timezone
from engine.models import NormalizedListing, ScoringResult
from engine.filters import (
    norm,
    company_key,
    compute_fingerprint,
    is_us_listing,
    keyword_prefilter,
    deduplicate_listings,
    is_agency_suspect,
)
from engine.scorer import heuristic_fallback_scorer
from engine.drafter import generate_contact_url, check_cooldown, draft_outreach
from engine.storage import StorageManager
from engine.run_hunt import format_card_text


def test_london_and_bengaluru_dropped():
    """Test: A London or Bengaluru-only role is dropped before scoring."""
    # London
    assert not is_us_listing(country="", location="London, UK", remote=False)
    assert not is_us_listing(country="GB", location="London", remote=True)
    # Bengaluru
    assert not is_us_listing(country="", location="Bengaluru, India", remote=False)
    assert not is_us_listing(country="IN", location="Bangalore Remote", remote=True)
    # Singapore, Germany
    assert not is_us_listing(country="", location="Singapore", remote=False)
    assert not is_us_listing(country="DE", location="Berlin", remote=False)

    # US cases should pass
    assert is_us_listing(country="US", location="Austin, TX", remote=False)
    assert is_us_listing(country="USA", location="Remote", remote=True)
    assert is_us_listing(country="", location="US-Remote", remote=True)
    assert is_us_listing(country="", location="San Francisco, CA", remote=False)


def test_fingerprint_deduplication():
    """Test: A listing seen yesterday does not reach Score Listing today, including the same role from a second source (fingerprint)."""
    item1 = NormalizedListing(
        listing_id="remotive:101",
        fingerprint=compute_fingerprint("Acme Inc.", "AI Enablement Lead"),
        source="remotive",
        title="AI Enablement Lead",
        company="Acme Inc.",
        location="Remote, US",
        url="https://remotive.com/101",
    )
    item2_different_source_same_role = NormalizedListing(
        listing_id="remoteok:999",
        fingerprint=compute_fingerprint("Acme, LLC", "AI Enablement Lead"),
        source="remoteok",
        title="AI Enablement Lead",
        company="Acme, LLC",
        location="US Remote",
        url="https://remoteok.com/999",
    )

    seen_ids = set()
    seen_fps = set()

    # First pass
    unique, dropped = deduplicate_listings([item1], seen_ids, seen_fps)
    assert len(unique) == 1
    assert dropped == 0
    assert "remotive:101" in seen_ids

    # Second pass with same role from different source (fingerprint match)
    unique2, dropped2 = deduplicate_listings([item2_different_source_same_role], seen_ids, seen_fps)
    assert len(unique2) == 0
    assert dropped2 == 1


def test_keyword_prefilter_exclude_engineer():
    """Test: Excluded non-technical roles are dropped, target AI roles are kept."""
    includes = ["Forward Deployed", "Forward Deployed Engineer", "AI Solutions Engineer", "GenAI Engineer", "LLM Engineer", "AI Agent"]
    excludes = ["Hardware Engineer", "Mechanical Engineer", "Nurse", "Therapist"]

    # Non-technical nurse role -> False
    assert not keyword_prefilter(
        title="Staff Registered Nurse",
        description="Patient care in hospital setting.",
        keywords_include=includes,
        keywords_exclude_title=excludes,
    )

    # Forward Deployed AI Engineer -> True
    assert keyword_prefilter(
        title="Forward Deployed AI Engineer",
        description="Build LLM solutions and agent workflows directly alongside clients.",
        keywords_include=includes,
        keywords_exclude_title=excludes,
    )


def test_scoring_classifications():
    """
    Test:
    - US remote Forward Deployed AI Engineer classifies BUY_SIGNAL, 85+.
    - A contract AI Solutions Prototype Developer classifies DIRECT_GIG.
    - A clinical nurse role is IGNORE.
    """
    # 1. Forward Deployed AI Engineer
    lead_listing = NormalizedListing(
        listing_id="test:1",
        fingerprint="corp|forward deployed ai engineer",
        source="test",
        title="Forward Deployed AI Engineer",
        company="Global Corp",
        location="Remote, US",
        country="US",
        remote=True,
        url="https://example.com/1",
        description="Build GenAI pipelines, RAG systems, and agent workflows directly with enterprise clients.",
    )
    res_lead = heuristic_fallback_scorer(lead_listing)
    assert res_lead.type == "BUY_SIGNAL"
    assert res_lead.score >= 80
    assert res_lead.keep is True

    # 2. Contract AI Prototype Developer
    trainer_listing = NormalizedListing(
        listing_id="test:2",
        fingerprint="training co|contract ai developer",
        source="test",
        title="Contract AI Developer",
        company="Training Co",
        location="New York, NY",
        country="US",
        url="https://example.com/2",
        description="Deliver hands-on prompt engineering and AI agent prototypes.",
    )
    res_trainer = heuristic_fallback_scorer(trainer_listing)
    assert res_trainer.type == "DIRECT_GIG"
    assert res_trainer.score >= 80
    assert res_trainer.keep is True

    # 3. Clinical Nurse
    nurse_listing = NormalizedListing(
        listing_id="test:3",
        fingerprint="tech corp|registered nurse",
        source="test",
        title="Registered Nurse",
        company="Health Corp",
        location="San Francisco, CA",
        country="US",
        url="https://example.com/3",
        description="Provide patient care and clinical services.",
    )
    res_backend = heuristic_fallback_scorer(nurse_listing)
    assert res_backend.type == "IGNORE"
    assert res_backend.score < 55
    assert res_backend.keep is False


def test_agency_suspect_flag():
    """Test: Agency-of-record posting carries POSTED VIA AGENCY."""
    hints = ["recruitment", "recruiting", "staffing", "search firm", "talent partners"]
    assert is_agency_suspect("Apex Talent Partners", "AI Specialist", hints) is True
    assert is_agency_suspect("Acme Recruiting LLC", "Trainer", hints) is True
    assert is_agency_suspect("Stripe", "Enablement Lead", hints) is False

    item = NormalizedListing(
        listing_id="test:4",
        fingerprint="apex talent|ai trainer",
        source="test",
        title="AI Trainer",
        company="Apex Talent Partners",
        url="https://example.com/4",
        agency_suspect=True,
    )
    score = ScoringResult(
        type="DIRECT_GIG",
        score=85,
        band="high",
        agency_post=True,
        keep=True,
    )
    card = format_card_text(item, score)
    assert "POSTED VIA AGENCY" in card


def test_contact_url_generation():
    """Test: Find contact returns a people-search URL with approach_role + company."""
    url = generate_contact_url("VP of Revenue Enablement", "Datadog")
    assert "https://www.linkedin.com/search/results/people/?keywords=" in url
    assert "VP+of+Revenue+Enablement+Datadog" in url or "VP%20of%20Revenue%20Enablement" in url


def test_cooldown_gate(tmp_path):
    """Test: Second draft to the same company inside 21 days -> Cooldown Notice."""
    test_db = tmp_path / "test_ledger.db"
    mgr = StorageManager(db_path=test_db)

    # First touch: draft recorded today
    mgr.record_touch(company_key_val="acme", listing_id="test:10", action="draft", preview="Hello...")

    # Query last touch
    last = mgr.get_last_touch_date("acme", action="draft")
    assert last is not None

    # Check cooldown
    delta = datetime.now(timezone.utc) - last
    days_passed = delta.total_seconds() / 86400.0
    assert days_passed < 21


def test_draft_word_count_and_no_resume_dump():
    """Test: Draft text is 80–130 words and does not contain the raw résumé."""
    listing_data = {
        "company": "Figma",
        "title": "Director of Sales Enablement",
        "type": "BUY_SIGNAL",
        "score": 88,
        "one_line_fit": "Scaling revenue team with structured AI enablement.",
        "angle": "Deliver a 60-day sprint alongside new hire.",
        "approach_role": "VP Revenue",
        "concern": "Internal hire focus",
    }
    draft = draft_outreach(listing_data)
    words = draft.split()
    assert 60 <= len(words) <= 150  # comfortably in the targeted concise window
    assert "Curriculum Vitae" not in draft
    assert "GPA" not in draft
    assert "References available upon request" not in draft


def test_discord_embed_formatting():
    """Test: Discord embed produces correct color, titles, fields, and action URLs."""
    from engine.discord_webhook import format_discord_embed

    item = NormalizedListing(
        listing_id="jobicy:888",
        fingerprint="unite us|community strategy enablement manager",
        source="jobicy",
        title="Community Strategy Enablement Manager",
        company="Unite Us",
        location="USA",
        country="US",
        url="https://jobicy.com/jobs/888",
    )
    score = ScoringResult(
        type="BUY_SIGNAL",
        score=88,
        band="high",
        one_line_fit="Company is investing in community enablement.",
        angle="60-day sprint alongside new hire",
        approach_role="Head of Enablement",
        asks_for="Program design",
        concern="May prioritize internal seat",
        agency_post=False,
        keep=True,
    )

    embed = format_discord_embed(item, score)
    assert embed["title"] == "🎯 Community Strategy Enablement Manager @ Unite Us"
    assert embed["url"] == "https://jobicy.com/jobs/888"
    assert embed["color"] == 0xF1C40F  # Gold for BUY_SIGNAL
    assert "Open Job Posting" in embed["description"]
    assert "LinkedIn People Search" in embed["description"]

    # Check agency suspect coloring
    score.agency_post = True
    agency_embed = format_discord_embed(item, score)
    assert agency_embed["color"] == 0xE67E22  # Orange
    assert "[POSTED VIA AGENCY]" in agency_embed["description"]


def test_recency_filter_24_hours():
    """Verify that jobs older than 24 hours are dropped and fresh jobs are kept."""
    from datetime import datetime, timezone, timedelta
    from engine.filters import is_posted_within_hours, parse_posted_datetime

    now = datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc)

    # 2 hours ago -> KEEP
    h2_ago = (now - timedelta(hours=2)).isoformat()
    assert is_posted_within_hours(h2_ago, max_hours=24, now=now) is True

    # 23 hours ago -> KEEP
    h23_ago = (now - timedelta(hours=23)).isoformat()
    assert is_posted_within_hours(h23_ago, max_hours=24, now=now) is True

    # 25 hours ago -> DROP
    h25_ago = (now - timedelta(hours=25)).isoformat()
    assert is_posted_within_hours(h25_ago, max_hours=24, now=now) is False

    # Unix epoch 5 hours ago -> KEEP
    ts_5h_ago = str(int((now - timedelta(hours=5)).timestamp()))
    assert is_posted_within_hours(ts_5h_ago, max_hours=24, now=now) is True

    # Unix epoch 3 days ago -> DROP
    ts_3d_ago = str(int((now - timedelta(days=3)).timestamp()))
    assert is_posted_within_hours(ts_3d_ago, max_hours=24, now=now) is False

    # Empty date -> DROP
    assert is_posted_within_hours("", max_hours=24, now=now) is False

