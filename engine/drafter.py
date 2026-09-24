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


def draft_outreach(listing_data: Dict[str, Any], recipient_name: Optional[str] = None) -> str:
    """
    Draft an 75-105 word outreach note using Gemini (or fallback template).
    Addresses the recipient directly by name if provided or discovered in description.
    """
    import re
    company = listing_data.get("company", "")
    title = listing_data.get("title", "")
    stype = listing_data.get("type", "BUY_SIGNAL")
    score = listing_data.get("score", 80)
    fit = listing_data.get("one_line_fit", "")
    angle = listing_data.get("angle", "")
    concern = listing_data.get("concern", "")
    role = listing_data.get("approach_role") or "VP of Engineering / Head of AI"

    # Determine recipient name
    target_name = (recipient_name or "").strip()
    if not target_name:
        desc = listing_data.get("description", "")
        m = re.search(r'\b(?:reach out to|contact|report(?:ing)? to|hiring manager:?|recruiter:?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', desc, re.I)
        if m:
            target_name = m.group(1).split()[0]

    if target_name:
        salutation_start = f"Hi {target_name},"
        target_entity = target_name
        salutation_guide = (
            f'ALWAYS begin the message with: "{salutation_start}" and write this message directly to {target_name} '
            f'({role} at {company}). Address {target_name} directly as a peer engineer.'
        )
    else:
        team_name = f"{company} Hiring Team" if company else "Hiring Team"
        salutation_start = f"Hi {team_name},"
        target_entity = team_name
        salutation_guide = (
            f'No specific poster name is provided, so ALWAYS begin the message with: "{salutation_start}". '
            f'NEVER use placeholders like "[Name]" or brackets. Address the note directly to the {team_name}.'
        )

    proof_points = POSITIONING_CONFIG.get("proof_points", [])
    # Pick at most 1 proof point
    selected_pp = proof_points[0] if proof_points else {}
    pp_str = (
        f"Problem: {selected_pp.get('problem')}\n"
        f"Action: {selected_pp.get('what_you_did')}\n"
        f"Outcome: {selected_pp.get('outcome')}"
    ) if selected_pp else "None"

    draft_sig = POSITIONING_CONFIG.get("draft_signature", "Best regards,\n[Your Name]")

    system_instruction = f"""You write personal, professional, engineer-to-engineer direct outreach notes for Hrishith Raj Reddy Malgireddy to send on LinkedIn and email regarding the {title} role at {company}.

CRITICAL STYLE & TONE GUIDELINES:
- Write like a real, competent peer engineer reaching out directly (1-on-1 direct message), NOT an automated bot or generic cover letter.
- NEVER start with robotic phrases like "As an AI-focused engineer...", "I am writing to express my interest in...", or "Recently, at an AI-enabled mental health platform...".
- {salutation_guide}
- ZERO PLACEHOLDERS: Never output placeholders like "[Name]", "[Company]", or brackets. Every name and company must be concrete and 100% copy-paste ready.
- CURRENT ROLE AT CURE CULTURE: Hrishith is CURRENTLY the Founding Software Developer at Cure Culture (Nov 2025 – Present). He is actively working and building there right now. ALWAYS write about this role in the present tense (e.g. "As Founding Software Developer at Cure Culture, I build and ship production AI agent workflows...", "In my current role at Cure Culture, I work directly with founders to..."). NEVER say "I served as", "I worked at", "I was", or use past tense for Cure Culture.
- Connect specifically to {company}'s domain and {angle}.
- Show immediate value: explain how he can step in, build, and deploy production AI solutions rapidly without onboarding overhead.
- End with a low-friction call to action: "Would you be open to a quick 10-minute technical chat sometime this week?"
- Keep the body concise: 75–105 words. Clean paragraphs.

MANDATORY SIGNATURE: You must conclude the note with this exact signature block:
{draft_sig}

CANDIDATE POSITIONING:
{build_positioning_pack()}

RELEVANT PROOF POINT:
{pp_str}

OPPORTUNITY:
Role: {title} @ {company} ({stype} - score {score})
Fit: {fit}
Angle: {angle}
Approach Role: {role}
Target Recipient: {target_entity}
"""

    def clean_draft(text: str) -> str:
        # Fix any duplicated protocols
        text = re.sub(r'https?://https?://', 'https://', text)
        # Strictly enforce Hrishith's true GitHub profile: https://github.com/hrishith30
        text = re.sub(r'https?://github\.com/[A-Za-z0-9_.-]+', 'https://github.com/hrishith30', text)
        text = re.sub(r'(?<!https://)(?<!http://)\bgithub\.com/[A-Za-z0-9_.-]+', 'https://github.com/hrishith30', text)
        text = re.sub(r'https?://https?://', 'https://', text)
        # Clean any accidental placeholders
        team_name = f"{company} Hiring Team" if company else "Hiring Team"
        fallback_salutation = target_name if target_name else team_name
        text = re.sub(r'\[Name\]', fallback_salutation, text)
        text = re.sub(r'Hi \[Hiring Manager\]', f"Hi {team_name}", text, flags=re.I)
        # Enforce present tense for current role at Cure Culture (he is currently working there)
        text = re.sub(r'\b(?:At Cure Culture, )?I served as (?:the |a )?Founding Software Developer\b', 'As Founding Software Developer at Cure Culture, I', text, flags=re.I)
        text = re.sub(r'\bI served as\b', 'I work as', text, flags=re.I)
        text = re.sub(r'\bI worked at Cure Culture\b', 'In my current role at Cure Culture, I work', text, flags=re.I)
        text = re.sub(r'\bAt Cure Culture, I worked\b', 'At Cure Culture, I work', text, flags=re.I)
        text = re.sub(r'\bAt Cure Culture, I translated\b', 'At Cure Culture, I translate', text, flags=re.I)
        return text

    user_prompt = f"Draft personal and professional outreach note to {target_entity} regarding {title} at {company}. Plain text, 75-105 words, starting with '{salutation_start}'"

    if gemini_client.is_configured:
        generated = gemini_client.generate_text(system_instruction, user_prompt, timeout=25)
        if generated:
            return clean_draft(generated)

    # Deterministic fallback draft template (75-105 words) matching Hrishith's resume
    if stype == "BUY_SIGNAL":
        draft = (
            f"{salutation_start}\n\n"
            f"I saw the {title} opening at {company} and wanted to reach out directly. "
            f"As Founding Software Developer at Cure Culture, I currently build and ship production AI agent workflows, "
            f"RAG systems, and full-stack backend services in Python, TypeScript, and GCP directly alongside our founders.\n\n"
            f"Given {company}'s focus on {title.lower()} and rapid deployment, I'd love to help your team build and scale reliable AI systems "
            f"without onboarding ramp-up.\n\n"
            f"Would you be open to a quick 10-minute technical chat sometime this week?\n\n"
            f"{draft_sig}"
        )
    else:
        draft = (
            f"{salutation_start}\n\n"
            f"I noticed {company} is hiring for a {title} and wanted to connect directly. "
            f"As Founding Software Developer at Cure Culture, I actively build and deploy production GenAI systems, autonomous AI agents, and RAG architectures "
            f"using Python, Django, and GCP, bridging cutting-edge LLMs with dependable backend systems.\n\n"
            f"I'd love to contribute to your engineering goals at {company}. Would you have 10 minutes for a brief chat this week?\n\n"
            f"{draft_sig}"
        )

    return clean_draft(draft)
