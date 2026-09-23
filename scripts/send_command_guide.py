import requests

webhook_url = "https://discord.com/api/webhooks/1552144821379006484/Qqt6TET5ckMjZBMUlWNvbYh96S5awDTtW4GHJm4oxljC9OP6VcQqsQk9M2EyYDurJ7Jd?wait=true"

embed = {
    "title": "⚡ Discord In-Chat Commands Menu",
    "description": (
        "**You do NOT need to type terminal commands!**\n"
        "You can control the entire system directly from inside Discord using these simple commands:\n"
    ),
    "color": 0x9B59B6,  # Royal Purple
    "fields": [
        {
            "name": "🚀 1. The Main Hunt Command",
            "value": (
                "Type: `/hunt` *(or `!hunt`)*\n"
                "• Starts a brand new hunt across all 5 job websites right now.\n"
                "• Gemini grades the jobs.\n"
                "• Pushes hot opportunity cards (Score 80+) right here with action buttons!"
            ),
            "inline": False
        },
        {
            "name": "📊 2. The Scoreboard Command",
            "value": (
                "Type: `/status` *(or `!status`)*\n"
                "• Shows your total scored jobs, kept opportunities, and hot alerts."
            ),
            "inline": False
        },
        {
            "name": "🎯 3. View Current Top Hot Leads",
            "value": (
                "Type: `/hot` *(or `!hot`)*\n"
                "• Pulls up the top active hot job cards with **Open Posting**, **LinkedIn Search**, and **Draft Outreach** buttons!"
            ),
            "inline": False
        },
        {
            "name": "✍️ 4. Generate a Pitch Note",
            "value": (
                "Type: `/draft [listing_id]` *(or click the 'Draft Outreach' button)*\n"
                "• Gemini writes a custom 80–130 word pitch tailored to that company.\n"
                "• Includes 21-day cooldown protection so you never contact the same company twice!"
            ),
            "inline": False
        },
        {
            "name": "⏰ 5. Automated Daily Hunting",
            "value": (
                "• The bot also runs **automatically once every 24 hours (at 13:30 UTC)**.\n"
                "• You do not even have to type anything—fresh opportunities will drop in daily!"
            ),
            "inline": False
        },
        {
            "name": "🔑 How to Activate the In-Chat Bot (1 Minute)",
            "value": (
                "1. Go to [Discord Developer Portal](https://discord.com/developers/applications) ➔ Click **New Application** ➔ Go to **Bot** tab ➔ Click **Reset Token**.\n"
                "2. Paste that token into your `.env` file as `DISCORD_BOT_TOKEN=...`\n"
                "3. Start the bot: `python -m engine.discord_bot` (it will stay running and listen for commands!)."
            ),
            "inline": False
        }
    ],
    "footer": {
        "text": "Auto Bot LinkedIn Job • Discord Commands Guide"
    }
}

resp = requests.post(webhook_url, json={"username": "Auto Bot Command Center", "embeds": [embed]}, timeout=15)
print("HTTP Status Code:", resp.status_code)
if resp.status_code in (200, 204):
    print("Delivered Command Menu to Discord successfully!")
