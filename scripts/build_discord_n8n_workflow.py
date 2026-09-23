"""Generator for Auto Bot LinkedIn Job Discord n8n Workflow JSON."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "n8n" / "auto_bot_linkedin_job_discord.json"

# Load the base workflow
with open(BASE_DIR / "n8n" / "auto_bot_linkedin_job.json", "r", encoding="utf-8") as f:
    wf = json.load(f)

# Update workflow name
wf["name"] = "Auto Bot LinkedIn Job (Discord Edition)"

# Replace Telegram Hot Alert with Discord Webhook Hot Alert
for node in wf["nodes"]:
    if node["name"] == "Telegram Hot Alert":
        node["name"] = "Discord Hot Alert"
        node["type"] = "n8n-nodes-base.httpRequest"
        node["typeVersion"] = 4.2
        node["parameters"] = {
            "method": "POST",
            "url": "={{ $env.DISCORD_WEBHOOK_URL || 'https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN' }}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={
  "username": "Auto Bot LinkedIn Job",
  "embeds": [
    {
      "title": "🎯 " + $json.title + " @ " + $json.company,
      "url": $json.url,
      "description": "*" + $json.one_line_fit + "*\\n\\n🔗 [Open Posting](" + $json.url + ") | 🔎 [LinkedIn Contact Search](https://www.linkedin.com/search/results/people/?keywords=" + encodeURIComponent(($json.approach_role || "VP of Engineering / Head of AI") + " " + $json.company) + ")",
      "color": ($json.type === "BUY_SIGNAL" ? 15844367 : 3066993),
      "fields": [
        {"name": "Signal & Score", "value": "**" + $json.type + "** — `" + $json.score + "/100` (" + $json.band + ")", "inline": true},
        {"name": "Location & Source", "value": ($json.location || "US Remote") + " • " + $json.source, "inline": true},
        {"name": "Target Approach Role", "value": "`" + ($json.approach_role || "VP of Engineering / Head of AI") + "`", "inline": true},
        {"name": "Strategic Angle", "value": $json.angle || "N/A", "inline": false},
        {"name": "Asks For", "value": $json.asks_for || "N/A", "inline": true},
        {"name": "Concern", "value": $json.concern || "N/A", "inline": true}
      ],
      "footer": {"text": "Auto Bot LinkedIn Job • ID: " + $json.listing_id}
    }
  ]
}""",
            "options": {"timeout": 15000}
        }
        if "credentials" in node:
            del node["credentials"]

    elif node["name"] == "Send Run Report":
        node["name"] = "Discord Run Report"
        node["type"] = "n8n-nodes-base.httpRequest"
        node["typeVersion"] = 4.2
        node["parameters"] = {
            "method": "POST",
            "url": "={{ $env.DISCORD_WEBHOOK_URL || 'https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN' }}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={
  "username": "Auto Bot LinkedIn Job",
  "embeds": [
    {
      "title": "📊 Auto Bot Hunt Digest",
      "description": "```\\n" + $json.digest_text + "\\n```",
      "color": 3447003,
      "footer": {"text": "Auto Bot LinkedIn Job • US Only"}
    }
  ]
}""",
            "options": {"timeout": 15000}
        }
        if "credentials" in node:
            del node["credentials"]

    elif node["name"] == "Nothing New Notice":
        node["name"] = "Discord Nothing New Notice"
        node["type"] = "n8n-nodes-base.httpRequest"
        node["typeVersion"] = 4.2
        node["parameters"] = {
            "method": "POST",
            "url": "={{ $env.DISCORD_WEBHOOK_URL || 'https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN' }}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={
  "username": "Auto Bot LinkedIn Job",
  "content": "✅ **Quiet success**: No new US listings found today. All matching listings have already been reviewed and logged."
}""",
            "options": {"timeout": 15000}
        }
        if "credentials" in node:
            del node["credentials"]

# Update connections references
conn_str = json.dumps(wf["connections"])
conn_str = conn_str.replace("Telegram Hot Alert", "Discord Hot Alert")
conn_str = conn_str.replace("Send Run Report", "Discord Run Report")
conn_str = conn_str.replace("Nothing New Notice", "Discord Nothing New Notice")
wf["connections"] = json.loads(conn_str)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2)

print(f"Generated Discord n8n workflow at {OUTPUT_FILE}")
