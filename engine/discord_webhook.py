"""Discord Webhook integration for Auto Bot LinkedIn Job.

Provides instant channel notifications with color-coded rich embeds and action links.
"""

import requests
from typing import Dict, Any, Optional, List
from engine.models import NormalizedListing, ScoringResult
from engine.config import DISCORD_WEBHOOK_URL
from engine.drafter import generate_contact_url


def format_discord_embed(item: NormalizedListing, score: ScoringResult) -> Dict[str, Any]:
    """Format single hot opportunity as a rich Discord embed."""
    # Color coding
    if score.agency_post:
        color = 0xE67E22  # Orange for agency notice
    elif score.type == "BUY_SIGNAL":
        color = 0xF1C40F  # Gold/Yellow for Buy Signal
    else:
        color = 0x2ECC71  # Green for Direct Gig

    contact_url = generate_contact_url(score.approach_role, item.company)

    prefix = "⚠️ [POSTED VIA AGENCY]\n" if score.agency_post else ""
    desc = f"{prefix}*{score.one_line_fit}*\n\n"
    desc += f"🔗 [Open Job Posting]({item.url})  |  🔎 [LinkedIn People Search]({contact_url})\n"
    desc += f"*(To draft outreach note via bot, use: `!draft {item.listing_id}`)*"

    fields = [
        {
            "name": "Signal & Score",
            "value": f"**{score.type}** — `{score.score}/100` ({score.band.upper()})",
            "inline": True,
        },
        {
            "name": "Location & Source",
            "value": f"{item.location or 'US Remote'} • {item.source.capitalize()}",
            "inline": True,
        },
        {
            "name": "Target Approach Role",
            "value": f"`{score.approach_role or 'VP of Engineering / Head of AI'}`",
            "inline": True,
        },
        {
            "name": "Strategic Angle",
            "value": score.angle or "Ship production GenAI pipelines and agent workflows.",
            "inline": False,
        },
        {
            "name": "Asks For",
            "value": score.asks_for or "Production GenAI architecture and API implementation.",
            "inline": True,
        },
        {
            "name": "Honest Concern",
            "value": score.concern or "Confirm architecture scale and team requirements.",
            "inline": True,
        },
    ]

    return {
        "title": f"🎯 {item.title} @ {item.company}",
        "url": item.url,
        "description": desc,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"Auto Bot LinkedIn Job • ID: {item.listing_id}",
        },
    }


def send_discord_webhook(
    content: Optional[str] = None,
    embeds: Optional[List[Dict[str, Any]]] = None,
    webhook_url: Optional[str] = None,
) -> bool:
    """Send payload to Discord webhook."""
    url = webhook_url or DISCORD_WEBHOOK_URL
    if not url or not url.startswith("https://discord.com/api/webhooks/"):
        print(f"[Discord Webhook Mock] Content: {content} | Embeds: {len(embeds or [])}")
        return True

    payload: Dict[str, Any] = {"username": "Auto Bot LinkedIn Job"}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code in {200, 204}:
            return True
        print(f"[Discord Webhook] Error HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Discord Webhook] Exception: {e}")

    return False


def post_hot_card_webhook(
    item: NormalizedListing,
    score: ScoringResult,
    webhook_url: Optional[str] = None,
) -> bool:
    """Post single hot card embed via Discord webhook."""
    embed = format_discord_embed(item, score)
    return send_discord_webhook(embeds=[embed], webhook_url=webhook_url)


def post_run_report_webhook(
    report_text: str,
    webhook_url: Optional[str] = None,
) -> bool:
    """Post hunt run summary report via Discord webhook."""
    embed = {
        "title": "📊 Auto Bot Daily Hunt Digest",
        "description": f"```\n{report_text}\n```",
        "color": 0x3498DB,  # Blue
        "footer": {"text": "Auto Bot LinkedIn Job • US Only"},
    }
    return send_discord_webhook(embeds=[embed], webhook_url=webhook_url)
