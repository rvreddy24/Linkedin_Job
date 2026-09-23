"""Gemini-powered outreach drafter with 21-day cooldown gate and contact URL generator."""

import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import requests

from engine.config import GEMINI_API_KEY, GEMINI_MODEL, HUNT_CONFIG, POSITIONING_CONFIG
from engine.filters import company_key
from engine.storage import storage
from engine.scorer import build_positioning_pack
from engine.gemini_client import gemini_client


def generate_contact_url(approach_role: str, company: str) -> str:
    """Generate targeted LinkedIn people search query URL."""
    role = approach_role.strip() if approach_role else "VP of Engineering / Head of AI"
    query = f"{role} {company}".strip()
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}"


def check_cooldown(company_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if company had a draft generated within cooldown_days (21 days).
    Returns (is_blocked, notice_message).
    """
    ckey = company_key(company_name)
    last_touch = storage.get_last_touch_date(ckey, action="draft")
    cooldown_days = HUNT_CONFIG.get("cooldown_days", 21)

    if last_touch:
        delta = datetime.now(timezone.utc) - last_touch
        days_passed = delta.total_seconds() / 86400.0
        if days_passed < cooldown_days:
            remaining = int(cooldown_days - days_passed)
            notice = (
                f"⏸️ **Cooldown Notice for {company_name}**\n\n"
                f"A draft was already created for this company {int(days_passed)} day(s) ago.\n"
                f"Cooldown period is {cooldown_days} days ({remaining} days remaining).\n"
                f"Touch blocked to prevent duplicate outreach."
            )
            return True, notice

    return False, None


def draft_outreach(listing_data: Dict[str, Any]) -> str:
    """
    Draft an 80-130 word outreach note using Gemini (or fallback template).
    Uses at most ONE proof point.
    """
    company = listing_data.get("company", "")
    title = listing_data.get("title", "")
    stype = listing_data.get("type", "BUY_SIGNAL")
    score = listing_data.get("score", 80)
    fit = listing_data.get("one_line_fit", "")
    angle = listing_data.get("angle", "")
    concern = listing_data.get("concern", "")
    role = listing_data.get("approach_role") or "VP of Engineering / Head of AI"

    proof_points = POSITIONING_CONFIG.get("proof_points", [])
    # Pick at most 1 proof point
    selected_pp = proof_points[0] if proof_points else {}
    pp_str = (
        f"Problem: {selected_pp.get('problem')}\n"
        f"Action: {selected_pp.get('what_you_did')}\n"
        f"Outcome: {selected_pp.get('outcome')}"
    ) if selected_pp else "None"

    draft_sig = POSITIONING_CONFIG.get("draft_signature", "Best regards,\n[Your Name]")

    system_instruction = f"""Write a short outreach note from Hrishith Raj Reddy Malgireddy regarding {title} at {company}.
Position Hrishith as an AI-focused Forward Deployed Engineer with experience designing, building, and deploying production GenAI/LLM systems, AI agent workflows, and RAG architectures in Python, TypeScript, React, and GCP.
Do not invent metrics or companies not in the proof point.
Use at most ONE proof point from the candidate memory pack.
Tone: Technical, direct, engineer-to-engineer / founder-to-engineer.
80-120 words. Plain text only. End with Hrishith's signature and links.

CANDIDATE POSITIONING:
{build_positioning_pack()}

RELEVANT PROOF POINT:
{pp_str}

OPPORTUNITY:
Role: {title} @ {company} ({stype} - score {score})
Fit: {fit}
Angle: {angle}
"""

    user_prompt = f"Draft note to {role} at {company} regarding {title}. Plain text only, 80-120 words."

    if gemini_client.is_configured:
        generated = gemini_client.generate_text(system_instruction, user_prompt, timeout=25)
        if generated:
            return generated

    # Deterministic fallback draft template (80-120 words) matching Hrishith's resume
    if stype == "BUY_SIGNAL":
        draft = (
            f"Hi {role},\n\n"
            f"I saw {company} is hiring for a {title}. As an AI-focused Forward Deployed Engineer, I specialize "
            f"in designing, developing, and deploying production GenAI systems, autonomous agent workflows, and RAG architectures "
            f"in Python, TypeScript, React, and GCP.\n\n"
            f"In my recent work, I built and shipped production AI agent workflows and prompt pipelines using Claude Code, Cursor, "
            f"and GCP directly alongside startup leadership for a healthcare-adjacent platform.\n\n"
            f"I'd love to bring this hands-on engineering execution to your team at {company}. Open to a brief technical chat this week?\n\n"
            f"{draft_sig}"
        )
    else:
        draft = (
            f"Hi {role},\n\n"
            f"I came across the {title} opening at {company}. With a Master's in Computer Science and hands-on experience "
            f"deploying production GenAI systems, vector search RAG architectures, and autonomous AI agents, I'd love to connect.\n\n"
            f"I specialize in bridging the gap between cutting-edge LLMs and reliable production software using Python, Django, React, and GCP.\n\n"
            f"Would you be open to a brief conversation regarding how I can contribute to your engineering team at {company}?\n\n"
            f"{draft_sig}"
        )

    return draft
