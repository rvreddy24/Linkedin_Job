import requests

webhook_url = "https://discord.com/api/webhooks/1552144821379006484/Qqt6TET5ckMjZBMUlWNvbYh96S5awDTtW4GHJm4oxljC9OP6VcQqsQk9M2EyYDurJ7Jd?wait=true"

embed = {
    "title": "🧒 Auto Bot LinkedIn Job — Explained Simply for Anyone!",
    "description": (
        "**Imagine you have a super-smart robot helper who finds high-paying work for you while you sleep.**\n\n"
        "Here is the story of how this robot works, in simple steps that a 5th grader can understand:\n"
    ),
    "color": 0x2ECC71,  # Friendly Bright Green
    "fields": [
        {
            "name": "🕵️ What Does This Robot Do?",
            "value": (
                "Normally, people send 500 job applications into a black hole and get ignored.\n\n"
                "**Our robot does something way smarter:**\n"
                "It looks for big companies holding up a sign that says: *\"Help! We need someone to teach our team how to use AI tools!\"*\n\n"
                "When it spots that sign, it tells you who the boss is, so you can offer to help them right away!"
            ),
            "inline": False
        },
        {
            "name": "👣 The 5 Steps of the Robot",
            "value": (
                "**1️⃣ Step 1: The Morning Search**\n"
                "The robot visits 5 big websites every day and finds hundreds of new job posts.\n\n"
                "**2️⃣ Step 2: Throwing Away the Junk**\n"
                "It instantly throws away jobs outside America (like in London or India) and throws away coding jobs you do not care about.\n\n"
                "**3️⃣ Step 3: The Robot's Memory**\n"
                "The robot keeps a notebook. If it already saw a job yesterday, it skips it so you never see duplicates.\n\n"
                "**4️⃣ Step 4: The AI Teacher (Google Gemini)**\n"
                "Gemini gives each job a score from 0 to 100:\n"
                "• If a job gets a grade of **80 or higher (A+)**, it rings the alarm bell!\n\n"
                "**5️⃣ Step 5: Ding! A Card Arrives in Discord**\n"
                "The robot delivers a card right here into your Discord channel."
            ),
            "inline": False
        },
        {
            "name": "🎮 How You Use the Cards (Just Click 2 Buttons!)",
            "value": (
                "On every card that drops into Discord:\n"
                "• Click **🔗 Open Job Posting** ➔ See what the company needs.\n"
                "• Click **🔎 LinkedIn People Search** ➔ Takes you straight to the boss at that company on LinkedIn.\n"
                "• The robot even writes a friendly 100-word note for you to copy and paste to the boss!"
            ),
            "inline": False
        },
        {
            "name": "⚡ How to Start the Robot",
            "value": (
                "Whenever you want to find new jobs, open your computer terminal and type:\n"
                "```powershell\npython -m engine.run_hunt\n```\n"
                "Press Enter, and watch the robot do all the work!"
            ),
            "inline": False
        }
    ],
    "footer": {
        "text": "Auto Bot LinkedIn Job • Super Simple Guide • Pin this message!"
    }
}

resp = requests.post(webhook_url, json={"username": "Auto Bot (Simple Guide)", "embeds": [embed]}, timeout=15)
print("HTTP Status Code:", resp.status_code)
if resp.status_code in (200, 204):
    print("Delivered to Discord successfully!")
