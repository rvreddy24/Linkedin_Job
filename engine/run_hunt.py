import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from engine.config import HUNT_CONFIG
from engine.models import NormalizedListing, ScoringResult, PipelineItem
from engine.sources import fetch_all_sources
from engine.filters import is_us_listing, keyword_prefilter, deduplicate_listings, is_posted_within_hours
from engine.scorer import score_listings_batch
from engine.storage import storage


def format_card_text(item: NormalizedListing, score: ScoringResult) -> str:
    """Format single Telegram alert card."""
    agency_flag = "POSTED VIA AGENCY - the real employer is hidden\n" if score.agency_post else ""
    return (
        f"{agency_flag}**{score.type}** — score {score.score} ({score.band})\n"
        f"**{item.title}**\n"
        f"{item.company} | {item.location or 'US Remote'} | {item.country or 'US'} | {item.source}\n\n"
        f"{score.one_line_fit}\n\n"
        f"**Angle:** {score.angle}\n"
        f"**Approach:** {score.approach_role}\n"
        f"**Asks for:** {score.asks_for}\n"
        f"**Concern:** {score.concern}"
    )


def execute_hunt() -> Dict[str, Any]:
    """Execute complete 5-stage hunt pipeline."""
    run_at = datetime.now(timezone.utc).isoformat()
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Stage 1: Fetch all sources
    raw_results = fetch_all_sources()
    raw_listings: List[NormalizedListing] = raw_results["listings"]
    source_counts = raw_results["source_counts"]
    credits_spent = raw_results["credits_spent"]
    total_matches = raw_results["total_matches"]
    raw_total = len(raw_listings)

    # Stage 2: 24h Recency, US Drop & Keyword Prefilter
    keywords_include = HUNT_CONFIG.get("keywords_include", [])
    keywords_exclude = HUNT_CONFIG.get("keywords_exclude_title", [])
    max_hours = HUNT_CONFIG.get("posted_within_hours", 24)

    us_survivors: List[NormalizedListing] = []
    raw_24h_count = 0
    for item in raw_listings:
        if is_posted_within_hours(item.posted_at, max_hours=max_hours):
            raw_24h_count += 1
            if is_us_listing(item.country, item.location, item.remote, title=item.title, description=item.description):
                if keyword_prefilter(item.title, item.description, keywords_include, keywords_exclude):
                    us_survivors.append(item)

    prefiltered_count = len(us_survivors)

    # Stage 3: Deduplication against Ledger (listing_id + fingerprint)
    seen_ids, seen_fps = storage.get_seen_identifiers()
    new_listings, dedup_dropped = deduplicate_listings(us_survivors, seen_ids, seen_fps)
    new_count = len(new_listings)

    # Stage 4: Scoring Batch (5)
    scored_pairs: List[Tuple[NormalizedListing, ScoringResult]] = []
    kept_items: List[PipelineItem] = []
    hot_cards: List[Dict[str, Any]] = []

    if new_listings:
        # Prioritize roles with core target keywords in title
        primary_kws = ["forward deployed", "ai solutions", "genai", "llm", "ai agent", "ai engineer", "rag", "founding ai"]
        new_listings.sort(key=lambda x: sum(2 for kw in primary_kws if kw in x.title.lower()), reverse=True)
        max_score = HUNT_CONFIG.get("max_score_per_run", 20)
        to_score = new_listings[:max_score] if max_score else new_listings
        scored_pairs = score_listings_batch(to_score, batch_size=5)

        # Log all scored rows to Ledger
        storage.log_to_ledger(run_at, scored_pairs)

        # Pipeline upsert (keep == True)
        for item, score in scored_pairs:
            if score.keep:
                p_item = PipelineItem(
                    listing_id=item.listing_id,
                    fingerprint=item.fingerprint,
                    run_at=run_at,
                    type=score.type,
                    score=score.score,
                    band=score.band,
                    company=item.company,
                    title=item.title,
                    location=item.location,
                    country=item.country,
                    source=item.source,
                    url=item.url,
                    one_line_fit=score.one_line_fit,
                    angle=score.angle,
                    approach_role=score.approach_role,
                    asks_for=score.asks_for,
                    concern=score.concern,
                    agency_post=score.agency_post,
                    status="new",
                )
                kept_items.append(p_item)

                if score.score >= HUNT_CONFIG.get("hot_score_min", 80):
                    card_text = format_card_text(item, score)
                    hot_cards.append({
                        "listing_id": item.listing_id,
                        "text": card_text,
                        "url": item.url,
                        "company": item.company,
                        "approach_role": score.approach_role,
                    })

        storage.upsert_pipeline(kept_items)

    kept_count = len(kept_items)
    hot_count = len(hot_cards)
    scored_count = len(scored_pairs)

    # Stage 5: Compile Run Report
    kw_str = ", ".join(keywords_include[:4]) + "..."
    types_str = ", ".join(HUNT_CONFIG.get("types", ["full-time", "contract"]))

    # Low-volume / zero-match chat notification
    if new_count == 0:
        ping_notice = f"🔔 **CHAT NOTICE:** 0 new matching jobs were posted in the last {max_hours} hours. (All fresh postings from today have already been analyzed)."
    elif hot_count == 0:
        ping_notice = f"🔔 **CHAT NOTICE:** Found {new_count} new job(s) in the last {max_hours} hours, but none reached hot score threshold (≥80)."
    elif hot_count < 3:
        ping_notice = f"🔔 **CHAT NOTICE:** Low volume — only {hot_count} hot opportunity found in the last {max_hours} hours."
    else:
        ping_notice = f"🎯 **CHAT NOTICE:** {hot_count} hot opportunities found in the last {max_hours} hours!"

    source_breakdown = " / ".join(f"{source_counts.get(s, 0)}" for s in ["linkedin", "remotive", "remoteok", "arbeitnow", "jobicy"])

    report_text = (
        f"**Auto Bot digest — {now_date}**\n"
        f"Keywords: {kw_str}\n"
        f"Countries: US | Posted within: Last {max_hours} hours\n\n"
        f"LinkedIn / Remotive / RemoteOK / Arbeitnow / Jobicy: {source_breakdown} rows\n"
        f"JobsPipe Search: {source_counts.get('jobspipe', 0)} rows\n"
        f"total matches available: {total_matches}\n"
        f"credits spent this run: {credits_spent}\n"
        f"Total raw rows: {raw_total} (within {max_hours}h: {raw_24h_count})\n"
        f"After US drop + prefilter: {prefiltered_count}   New after dedup: {new_count}\n"
        f"Scored: {scored_count}   Kept: {kept_count}   Hot: {hot_count}\n\n"
        f"{ping_notice}"
    )

    # Stage 6: Optional Discord Webhook Notification
    from engine.config import DISCORD_WEBHOOK_URL
    if DISCORD_WEBHOOK_URL:
        try:
            from engine.discord_webhook import post_run_report_webhook, format_discord_embed, send_discord_webhook
            post_run_report_webhook(report_text)
            embeds = []
            for item, score in scored_pairs:
                if score.score >= HUNT_CONFIG.get("hot_score_min", 80):
                    embeds.append(format_discord_embed(item, score))
            if embeds:
                send_discord_webhook(content="🎯 **New Hot Opportunities Identified (Score >= 80):**", embeds=embeds[:10])
        except Exception as e:
            print(f"[run_hunt] Discord notification error: {e}")

    return {
        "report_text": report_text,
        "ping_notice": ping_notice,
        "hot_cards": hot_cards,
        "raw_total": raw_total,
        "raw_24h_count": raw_24h_count,
        "prefiltered_count": prefiltered_count,
        "new_count": new_count,
        "scored_count": scored_count,
        "kept_count": kept_count,
        "hot_count": hot_count,
    }


if __name__ == "__main__":
    print("Running Auto Bot LinkedIn Job Hunt...")
    results = execute_hunt()
    print("\n" + "=" * 50)
    print(results["report_text"])
    print("=" * 50)
    if results["hot_cards"]:
        print(f"\nFound {len(results['hot_cards'])} hot opportunities (Score >= 80):")
        for card in results["hot_cards"]:
            print("-" * 40)
            print(card["text"])
