# 🚀 Auto Bot LinkedIn Job (Discord Edition)

An autonomous AI-powered US job research and signal hunter configured for Forward Deployed Engineer, GenAI, and LLM Developer roles. Listings are scraped across LinkedIn and top remote feeds, filtered strictly to the US within the last 24 hours, scored against operator experience using Google Gemini, and human-gated through Discord.

---

## ⚡ How to Run & Restart the Bot

If you close your computer, terminal, or IDE, you can restart the system anytime using either of the following methods:

### Method 1: Double-Click Launchers (Windows - Easiest)
Located directly in the project root:
- **`run_bot.bat`** *(Interactive Discord Bot)*:
  - Double-click to start the Discord bot service.
  - Keep the command prompt window open in the background.
  - The bot will stay online and respond to slash commands (`/hunt`, `/status`, etc.) and card buttons inside your Discord server.
- **`run_hunt.bat`** *(One-Off Instant Search)*:
  - Double-click to run an immediate job search across LinkedIn and all feeds.
  - Automatically posts the summary digest and any hot opportunities to your Discord webhook without needing Discord open.

---

### Method 2: Command Line (PowerShell / Terminal)
1. Open PowerShell or Terminal and navigate to the project directory:
   ```powershell
   cd "d:\Linkedin Job"
   ```
2. **Start the Discord bot**:
   ```powershell
   python -m engine.discord_bot
   ```
3. *(Alternative)* **Run an immediate hunt without running the bot daemon**:
   ```powershell
   python -m engine.run_hunt
   ```

---

## 💻 Setting Up on a New Machine

To run this project on a brand new computer:

### 1. Clone the Repository
```bash
git clone https://github.com/rvreddy24/Linkedin_Job.git
cd Linkedin_Job
```

### 2. Install Python Dependencies
Make sure Python 3.10+ is installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a file named `.env` in the root folder (you can copy `.env.example`):
```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key

# Discord Credentials
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_CHANNEL_ID=your_channel_id
```

> ⚠️ **Security Notice**: Never commit `.env` to Git. The `.gitignore` file is already preconfigured to protect `.env`, `ledger.db`, and local logs from being published.

### 4. Run the Bot
Double-click `run_bot.bat` or run:
```powershell
python -m engine.discord_bot
```

---

## 🎮 Discord Slash Commands & Card Buttons

The bot is strictly **on-demand**—it searches and drafts notes only when requested:

### Available Slash Commands
- **`/hunt`** — Scrapes fresh US postings from LinkedIn, RemoteOK, Remotive, Jobicy, and Arbeitnow from the past 24 hours, scores them with Gemini, and posts hot opportunities (score ≥ 80).
- **`/status`** — Displays the ledger scoreboard (total listings scanned, saved to pipeline, hot signal count).
- **`/hot`** — Lists your current top active hot opportunities with quick action buttons.
- **`/tailor <listing_id>`** — Generates an 80–130 word tailored outreach message for a specific job card using your resume background.
- **`/help`** — Displays a quick cheat-sheet of available commands and instructions.

### Interactive Buttons on Hot Cards
Every job card scoring ≥ 80 features one-click interactive buttons:
- **✍️ Draft Outreach**: Uses Gemini to generate a personalized outreach note referencing relevant projects and skills.
- **🔗 Open Posting**: Opens the direct application URL on LinkedIn or company career portal.
- **🔎 Find Contact**: Opens a pre-filled LinkedIn search for hiring managers and recruiters at the target company.

---

## 🧪 Testing & Verification

Run the automated test suite to verify feed parsers, location filters, deduplication, and score calculation:
```bash
python -m pytest tests/test_acceptance.py tests/test_feeds.py -v
```
