import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from typing import List, Tuple, Any, Dict
from engine.models import NormalizedListing, ScoringResult
from engine.config import GEMINI_API_KEY, GEMINI_MODEL, HUNT_CONFIG, POSITIONING_CONFIG
from engine.gemini_client import gemini_client


def _to_str(val: Any) -> str:
    """Safely convert Gemini output to string even if returned as list or dict."""
    if val is None:
        return ""
    if isinstance(val, list):
        return "; ".join(str(x) for x in val)
    return str(val).strip()


def build_positioning_pack() -> str:
    """Build system memory positioning pack string strictly from Hrishith's resume."""
    cfg = POSITIONING_CONFIG
    op_name = cfg.get("operator_name", "Hrishith Raj Reddy Malgireddy")
    offer = cfg.get("one_sentence_offer", "")
    summary = cfg.get("professional_summary", "")
    skills = cfg.get("technical_skills", {})
    languages = ", ".join(skills.get("languages", []))
    genai = ", ".join(skills.get("genai_llms_agents", []))
    cloud = ", ".join(skills.get("cloud_system_design", []))
    backend = ", ".join(skills.get("backend_databases", []))
    who_want = ", ".join(cfg.get("who_we_want", []))
    who_not = ", ".join(cfg.get("who_we_do_not_want", []))

    return f"""OPERATOR: {op_name}
SUMMARY: {summary}
CORE OFFER: {offer}
TECHNICAL STACK:
- Languages: {languages}
- GenAI & LLMs: {genai}
- Cloud & Architecture: {cloud}
- Backend & Databases: {backend}
TARGET ROLES: {who_want}
EXCLUDED: {who_not}
SIGNAL LOGIC:
  BUY_SIGNAL: Direct match roles in AI & software engineering: AI Intern, Software Engineer Intern, Machine Learning Intern, Junior / Entry-Level AI Engineer (0-1 years), Forward Deployed Engineer, AI Solutions Engineer, GenAI / LLM Engineer, AI Agent Engineer, Full Stack AI, Applied Machine Learning, RAG Engineer, Founding AI Engineer.
  DIRECT_GIG: Contract, freelance, or specialist engineering engagements building AI prototypes, agent workflows, or RAG architectures.
  IGNORE: Non-US roles, completely non-technical roles (sales, clinical healthcare, recruiting, HR, legal, accounting), or hardware/civil engineering.
AGENCY RULE: if employer is a recruiter and client is hidden, agency_post=true and prefix POSTED VIA AGENCY."""


SYSTEM_PROMPT = f"""You score job listings for Hrishith Raj Reddy Malgireddy based strictly on his engineering resume.
Use only the positioning pack and the listing. Do not invent employers, metrics, or proof points.

OPERATOR EXPERIENCE LEVEL & TARGETS:
- Education: Master of Science in Computer Science (Aug 2023 - Jul 2025), B.Tech in CSE (2019-2023).
- Professional Experience: Internships, 0–1 years (New Grad / Entry-Level / Beginner), and 1–3 years (Current Founding Software Developer @ Cure Culture actively shipping production AI agents, Research Assistant / TA @ Mizzou with PyTorch, MERN intern).
- TARGET SENIORITY: Intern, Internship, Entry-Level / New Grad (0-1 years), Junior, Associate, Mid-Level (1-3 years), Forward Deployed Engineer, AI Solutions Engineer, GenAI / LLM Engineer, AI Agent Engineer, Founding AI Developer.
- EXCLUDE SENIORITY: Do NOT target high-seniority executive or staff roles (Staff Engineer, Principal Engineer, Director, VP, CTO, or roles requiring 8+ years of experience). These must be scored IGNORE (< 45).
- LOCATION: MUST BE USA ONLY (or US-Remote). Any role located in Europe, UK, Germany, DACH (m/f/d), or requiring non-US residency must be scored IGNORE (0-10).

CLASSIFICATION:
BUY_SIGNAL (score 75-100) = Direct target roles matching Internships, 0-1 years (New Grad / Junior / Beginner), or 1-3 years: AI Intern, Software Engineer Intern, Machine Learning Intern, Junior AI Engineer, Entry-Level AI Developer, Forward Deployed Engineer, AI Solutions Engineer, GenAI Engineer, LLM Engineer, AI Agent Engineer, Full Stack AI, Applied Machine Learning, RAG Developer, Founding AI Developer.
DIRECT_GIG (score 70-85) = Contract, freelance, or specialist engagement delivering AI prototypes, agent workflows, or RAG architectures.
IGNORE (score 0-45) = Non-US roles, over-senior executive/staff roles (Staff/Principal/Director/VP/CTO), completely non-technical roles, or hardware/civil engineering.

keep = (type != IGNORE && score >= 55).
band: high >= 80, medium 55-79, low < 55.

Return JSON strictly matching the schema:
{{
  "type": "BUY_SIGNAL" | "DIRECT_GIG" | "IGNORE",
  "score": integer (0-100),
  "band": "high" | "medium" | "low",
  "one_line_fit": "1-2 sentences explaining why this role fits Hrishith's technical background and stack",
  "angle": "Technical pitch angle highlighting relevant experience (e.g., shipping production GenAI at Cure Culture, RAG systems, or agent workflows)",
  "approach_role": "Hiring manager title to approach (e.g. CTO, Head of AI, VP of Engineering, or Lead AI Architect)",
  "asks_for": "Core technical skills requested in listing",
  "concern": "Honest assessment of any gap or potential mismatch",
  "agency_post": boolean
}}

POSITIONING PACK:
{build_positioning_pack()}
"""


def score_with_gemini(listing: NormalizedListing) -> ScoringResult:
    """Call Google Gemini API to score the listing with structured JSON output."""
    user_prompt = f"""LISTING
title: {listing.title}
company: {listing.company}
location: {listing.location} | {listing.country} | remote={listing.remote}
source: {listing.source}  url: {listing.url}  posted_at: {listing.posted_at}
agency_suspect: {listing.agency_suspect}
description:
{listing.description[:HUNT_CONFIG.get('description_max_chars', 6000)]}"""

    parsed = gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
    if parsed and isinstance(parsed, dict):
        try:
            score_val = int(parsed.get("score", 0))
            stype = str(parsed.get("type", "IGNORE")).upper()
            if stype not in {"DIRECT_GIG", "BUY_SIGNAL", "IGNORE"}:
                stype = "IGNORE"

            band_val = "high" if score_val >= 80 else ("medium" if score_val >= 55 else "low")
            keep_val = (stype != "IGNORE" and score_val >= 55)

            return ScoringResult(
                type=stype,
                score=score_val,
                band=band_val,
                one_line_fit=_to_str(parsed.get("one_line_fit", "")),
                angle=_to_str(parsed.get("angle", "")),
                approach_role=_to_str(parsed.get("approach_role", "VP of Engineering / Head of AI")),
                asks_for=_to_str(parsed.get("asks_for", "")),
                concern=_to_str(parsed.get("concern", "")),
                agency_post=bool(parsed.get("agency_post", listing.agency_suspect)),
                keep=keep_val,
            )
        except Exception as e:
            print(f"[scorer] Error constructing ScoringResult from Gemini response: {e}")

    return heuristic_fallback_scorer(listing)


def heuristic_fallback_scorer(listing: NormalizedListing) -> ScoringResult:
    """Deterministic heuristic classification matching Hrishith's engineering resume."""
    title_lower = listing.title.lower()
    desc_lower = listing.description.lower()

    # Non-technical / excluded positions -> IGNORE
    non_tech_terms = [
        "nurse", "therapist", "psychotherapist", "dental", "accountant", "payroll",
        "customer service", "customer support", "sales representative", "retail",
        "legal counsel", "recruiter", "talent partner", "project scheduler",
        "hardware engineer", "mechanical engineer"
    ]
    if any(kw in title_lower for kw in non_tech_terms):
        return ScoringResult(
            type="IGNORE",
            score=10,
            band="low",
            one_line_fit="Non-technical or non-software role outside Hrishith's engineering focus.",
            angle="N/A",
            approach_role="",
            asks_for="",
            concern="Role is outside software and AI engineering domain",
            agency_post=listing.agency_suspect,
            keep=False,
        )

    # Over-senior / Executive roles exceeding 1-3 years experience -> IGNORE
    over_senior_terms = [
        "staff engineer", "principal engineer", "director of", "vp of",
        "vice president", "chief technology officer", "cto", "lead architect",
        "distinguished engineer", "chief executive", "head of engineering"
    ]
    if any(kw in title_lower for kw in over_senior_terms):
        return ScoringResult(
            type="IGNORE",
            score=35,
            band="low",
            one_line_fit="Role seniority exceeds Hrishith's 1-3 years experience level (targeted at Staff/Principal/Executive).",
            angle="N/A",
            approach_role="",
            asks_for="",
            concern="Over-seniority requirement (requires 8+ years experience)",
            agency_post=listing.agency_suspect,
            keep=False,
        )

    # Contract / Freelance technical engagements -> DIRECT_GIG (75-85)
    if (any(kw in title_lower for kw in ["contract", "freelance", "consultant"]) and "ai" in title_lower) or "contract ai" in desc_lower:
        return ScoringResult(
            type="DIRECT_GIG",
            score=85,
            band="high",
            one_line_fit=f"Contract technical engagement building AI/LLM solutions for {listing.company}.",
            angle="Propose rapid prototyping and deployment sprint for AI features and agent pipelines.",
            approach_role="Head of Product / Engineering Lead",
            asks_for="Hands-on AI prototyping and API deployment",
            concern="Scope boundaries and timeline delivery requirements",
            agency_post=listing.agency_suspect,
            keep=True,
        )

    # Prime Target Roles -> BUY_SIGNAL (High fit: 86-92)
    prime_targets = [
        "forward deployed", "ai solutions", "genai", "generative ai", "llm",
        "ai agent", "rag", "prompt engineer", "founding ai", "ai software engineer"
    ]
    if any(kw in title_lower for kw in prime_targets):
        score = 92 if any(t in title_lower for t in ["forward deployed", "ai solutions", "rag", "genai", "llm"]) else 86
        return ScoringResult(
            type="BUY_SIGNAL",
            score=score,
            band="high",
            one_line_fit=f"Strong technical alignment for {listing.title} at {listing.company} with Hrishith's experience in GenAI, RAG, agent workflows, and full-stack cloud systems.",
            angle="Position hands-on experience building production GenAI systems, RAG architectures, and autonomous AI agents with Python, GCP, and TypeScript.",
            approach_role="CTO" if "founding" in title_lower else "VP of Engineering / Head of AI",
            asks_for="GenAI/LLM system design, autonomous agents, RAG pipelines",
            concern="Confirm specific model architecture preferences and production scale expectations",
            agency_post=listing.agency_suspect,
            keep=True,
        )

    # General AI / ML / Full Stack AI -> BUY_SIGNAL (Medium/High fit: 78-84)
    ai_ml_targets = [
        "ai engineer", "machine learning", "ml engineer", "applied ai",
        "full stack ai", "ai developer", "python ai"
    ]
    if any(kw in title_lower for kw in ai_ml_targets) or ("ai" in title_lower and "engineer" in title_lower):
        return ScoringResult(
            type="BUY_SIGNAL",
            score=84,
            band="high",
            one_line_fit=f"Role for {listing.title} aligns with Hrishith's Master's in CS and applied ML / AI engineering background.",
            angle="Highlight PyTorch ML pipelines, vector databases, and enterprise system integrations.",
            approach_role="Director of Engineering / Head of Machine Learning",
            asks_for="Machine learning engineering and software system design",
            concern="Ensure role focus is production application rather than purely theoretical research",
            agency_post=listing.agency_suspect,
            keep=True,
        )

    # Software Engineer with AI in description -> BUY_SIGNAL (72)
    if ("ai" in desc_lower or "llm" in desc_lower or "rag" in desc_lower or "machine learning" in desc_lower) and "engineer" in title_lower:
        return ScoringResult(
            type="BUY_SIGNAL",
            score=72,
            band="medium",
            one_line_fit=f"Engineering role for {listing.title} at {listing.company} involving AI/LLM components.",
            angle="Leverage full-stack and backend engineering capabilities (Python, React, GCP) combined with GenAI tooling.",
            approach_role="Engineering Manager / Lead Architect",
            asks_for="Full-stack/backend engineering with AI integration",
            concern="Role may be heavier on general infrastructure than AI specialization",
            agency_post=listing.agency_suspect,
            keep=True,
        )

    # Default moderate fit -> IGNORE
    return ScoringResult(
        type="IGNORE",
        score=40,
        band="low",
        one_line_fit="Role does not strongly emphasize AI, GenAI, or Forward Deployed engineering capabilities.",
        angle="N/A",
        approach_role="",
        asks_for="",
        concern="Limited overlap with core GenAI/LLM target lane",
        agency_post=listing.agency_suspect,
        keep=False,
    )


def score_listings_batch(
    listings: List[NormalizedListing],
    batch_size: int = 5,
) -> List[Tuple[NormalizedListing, ScoringResult]]:
    """Score listings in batches of 5 to control rate limits."""
    results: List[Tuple[NormalizedListing, ScoringResult]] = []

    total = len(listings)
    for i in range(0, total, batch_size):
        batch = listings[i:i + batch_size]
        for idx_offset, item in enumerate(batch):
            idx = i + idx_offset
            if GEMINI_API_KEY and len(GEMINI_API_KEY.strip()) > 10:
                res = score_with_gemini(item)
            else:
                res = heuristic_fallback_scorer(item)
            title_safe = item.title.encode("ascii", errors="replace").decode("ascii")
            company_safe = item.company.encode("ascii", errors="replace").decode("ascii")
            print(f"[scorer] [{idx+1}/{total}] '{title_safe}' @ {company_safe} -> {res.type} ({res.score})", flush=True)
            results.append((item, res))

    return results
