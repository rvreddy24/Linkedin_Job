# Auto Bot LinkedIn Job (Discord Edition)

US job-signal hunter. Scores listings against operator positioning.
Outreach is human-gated via Discord.

## Overview
Auto Bot LinkedIn Job is a research engine, not an auto-applier. It pulls US job listings across 5 job sources, drops non-US roles, filters by keywords, deduplicates against an append-only ledger, scores survivors against the operator's positioning memory, logs opportunities to storage, and pushes actionable hot cards directly to **Discord**.

No application or message is ever sent to a company without the operator manually reviewing and copy-pasting the draft note.

---

## Discord Setup Options

You can connect Discord using either of the following methods:

### Option 1: Instant Discord Webhook (30-Second Setup)
*Zero bot hosting needed. Pushes color-coded rich embeds with direct links for job postings and LinkedIn searches.*
1. In your Discord server, open **Channel Settings** (gear icon) $\rightarrow$ **Integrations** $\rightarrow$ **Webhooks** $\rightarrow$ **New Webhook**.
2. Click **Copy Webhook URL**.
3. In your `.env` file, paste:
   ```env
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef...
   ```
4. Run a hunt:
   ```bash
   python -m engine.run_hunt
   ```
   Hot opportunities and daily digests will immediately appear in your Discord channel!

### Option 2: Interactive Discord Bot (Full Bot with Commands & Buttons)
*Enables `!hunt`, `!status`, `!help`, and interactive buttons directly inside Discord.*
1. Visit the [Discord Developer Portal](https://discord.com/developers/applications) and create a New Application.
2. Under the **Bot** tab:
   - Click **Reset Token** to get your `DISCORD_BOT_TOKEN`.
   - Enable **Message Content Intent** under Privileged Gateway Intents.
3. Under **OAuth2** $\rightarrow$ **URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`, `View Channels`
   - Copy the generated URL and open it in your browser to invite the bot to your server.
4. Add credentials to your `.env`:
   ```env
   DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN
   ```
5. Start the bot:
   ```bash
   python -m engine.discord_bot
   ```

---

## Discord Commands & Card Buttons (100% On-Demand)
The bot operates strictly **on-demand**—it will never search or message unless you explicitly ask it to.

### Slash Commands
- `/hunt` — Launch a search and score US listings across all 5 feeds right now.
- `/status` — View your scoreboard (total scored, kept in pipeline, hot alerts).
- `/hot` — View active top hot opportunities with action buttons.
- `/draft <listing_id>` — Generate a tailored outreach note for a specific listing.
- `/help` — Display bot commands and instructions.

### Interactive Card Buttons (Score >= 80)
- **✍️ Draft Outreach**: Gated by a 21-day company cooldown. Generates an 80–130 word plain-text note using Gemini and at most one proof point, ready to copy-paste.
- **🔗 Open Posting**: One-click direct link to the live job posting.
- **🔎 Find Contact**: One-click direct link to a pre-filled LinkedIn People Search for the hiring lead (e.g. `VP Revenue Enablement + Company`).

---

## Deploy to n8n (Discord Edition)
1. Open n8n (Cloud or self-hosted).
2. Click **Import from File** and select `n8n/auto_bot_linkedin_job_discord.json`.
3. Set your `DISCORD_WEBHOOK_URL` in n8n environment variables or directly inside the Discord HTTP nodes.
4. Connect your Google Gemini credential (`gemini_cred`).
5. Activate the workflow!

---

## Required Credentials Checklist
- **Discord**: `DISCORD_WEBHOOK_URL` (Option 1) or `DISCORD_BOT_TOKEN` (Option 2).
- **Google Gemini**: `GEMINI_API_KEY` (Sole AI engine: used for both structured listing scoring and outreach drafting).
- **JobsPipe** *(Optional)*: `JOBSPIPE_API_KEY` (`jp_live_...`).
- **Google Sheets** *(Optional)*: Local SQLite ledger is active by default.

---

## Testing
Run the acceptance test suite to verify US filtering, deduplication, cooldown gates, and Discord embed formatting:
```bash
python -m pytest tests/test_acceptance.py tests/test_feeds.py -v
```
