"""Interactive Telegram Bot for Auto Bot LinkedIn Job.

Handles /hunt, /status, /help, and card callbacks (draft, open, contact).
"""

import time
import requests
from typing import Dict, Any, Optional

from engine.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from engine.storage import storage
from engine.run_hunt import execute_hunt
from engine.drafter import check_cooldown, draft_outreach, generate_contact_url

HELP_TEXT = """**Auto Bot LinkedIn Job**
`/hunt` — search and score US listings now
`/status` — today's keep / hot / credits
`/help` — this message

**On each card:**
• **Draft outreach** — write a note (blocked during company cooldown)
• **Open posting** — open the job URL
• **Find contact** — LinkedIn search for the approach role

_Nothing is sent to a company unless you paste the draft yourself._"""


class TelegramService:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, default_chat_id: str = TELEGRAM_CHAT_ID):
        self.token = token
        self.default_chat_id = default_chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        reply_markup: Optional[dict] = None,
        parse_mode: str = "Markdown",
    ) -> bool:
        if not self.token:
            print(f"[Telegram Mock] To {chat_id or self.default_chat_id}:\n{text}")
            return True

        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            print("[Telegram] No chat_id provided.")
            return False

        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Telegram] send_message error: {e}")
            return False

    def answer_callback(self, callback_query_id: str, text: Optional[str] = None):
        if not self.token:
            return
        url = f"{self.api_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"[Telegram] answer_callback error: {e}")

    def send_hot_card(self, card_data: dict, chat_id: Optional[str] = None):
        listing_id = card_data["listing_id"]
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✍️ Draft outreach", "callback_data": f"draft::{listing_id}"},
                    {"text": "🔗 Open posting", "callback_data": f"open::{listing_id}"},
                ],
                [
                    {"text": "🔎 Find contact", "callback_data": f"contact::{listing_id}"}
                ]
            ]
        }
        self.send_message(card_data["text"], chat_id=chat_id, reply_markup=keyboard)

    def handle_command(self, text: str, chat_id: str):
        cmd = text.strip().split()[0].lower()
        if cmd == "/help":
            self.send_message(HELP_TEXT, chat_id=chat_id)
        elif cmd == "/status":
            stats = storage.get_stats()
            status_msg = (
                f"📊 **Auto Bot Status**\n\n"
                f"• Total Listings Scored: `{stats['total_scored']}`\n"
                f"• Kept in Pipeline: `{stats['total_kept']}`\n"
                f"• Hot Opportunities (80+): `{stats['total_hot']}`"
            )
            self.send_message(status_msg, chat_id=chat_id)
        elif cmd == "/hunt":
            self.send_message("🔍 Starting US job-signal hunt across all feeds...", chat_id=chat_id)
            results = execute_hunt()

            if results["new_count"] == 0:
                self.send_message(
                    "✅ **Quiet success** — no new US listings matched today.\n"
                    "All matching listings have already been reviewed and logged to Ledger.",
                    chat_id=chat_id
                )

            # Send Hot Cards (Score >= 80)
            for card in results["hot_cards"]:
                self.send_hot_card(card, chat_id=chat_id)

            # Send Run Report
            self.send_message(results["report_text"], chat_id=chat_id)
        else:
            self.send_message("Unknown command. Type /help for available options.", chat_id=chat_id)

    def handle_callback(self, callback_id: str, data: str, chat_id: str):
        self.answer_callback(callback_id)

        parts = data.split("::", 1)
        if len(parts) != 2:
            return

        action, listing_id = parts[0], parts[1]
        listing = storage.lookup_pipeline(listing_id)
        if not listing:
            self.send_message(f"❌ Error: Listing `{listing_id}` not found in Pipeline.", chat_id=chat_id)
            return

        company = listing.get("company", "")
        url = listing.get("url", "")
        role = listing.get("approach_role", "VP of Engineering / Head of AI")

        if action == "open":
            storage.update_pipeline_touch(listing_id, status="opened")
            storage.record_touch(company, listing_id, action="open", preview=url)
            self.send_message(f"🔗 **Job Posting URL:**\n<{url}>", chat_id=chat_id)

        elif action == "contact":
            contact_url = generate_contact_url(role, company)
            storage.update_pipeline_touch(listing_id, status="contact_sent")
            storage.record_touch(company, listing_id, action="contact", preview=contact_url)
            self.send_message(
                f"🔎 **LinkedIn Contact Search for {company}:**\n"
                f"Target Role: `{role}`\n\n"
                f"<{contact_url}>",
                chat_id=chat_id
            )

        elif action == "draft":
            # Cooldown check
            is_blocked, notice = check_cooldown(company)
            if is_blocked:
                storage.update_pipeline_touch(listing_id, status="cooldown")
                self.send_message(notice, chat_id=chat_id)
                return

            self.send_message(f"⏳ Generating outreach draft for {company}...", chat_id=chat_id)
            draft = draft_outreach(listing)

            storage.update_pipeline_touch(listing_id, status="drafted", draft=draft)
            storage.record_touch(company, listing_id, action="draft", preview=draft[:100])

            word_count = len(draft.split())
            msg = (
                f"📝 **Outreach Draft for {company}** ({word_count} words)\n"
                f"_Copy and paste into LinkedIn or email:_\n\n"
                f"```text\n{draft}\n```"
            )
            self.send_message(msg, chat_id=chat_id)

    def poll_updates(self):
        """Long-polling update loop for local execution."""
        if not self.token:
            print("Telegram token not set. Running in headless / CLI mode.")
            return

        print("Telegram bot polling started. Waiting for /hunt, /status, or button taps...")
        offset = 0
        while True:
            try:
                url = f"{self.api_url}/getUpdates?offset={offset}&timeout=20"
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1

                        if "message" in update and "text" in update["message"]:
                            msg = update["message"]
                            chat_id = str(msg["chat"]["id"])
                            self.handle_command(msg["text"], chat_id=chat_id)

                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            cb_id = cb["id"]
                            cb_data = cb.get("data", "")
                            chat_id = str(cb["message"]["chat"]["id"])
                            self.handle_callback(cb_id, cb_data, chat_id=chat_id)
                time.sleep(1)
            except KeyboardInterrupt:
                print("Stopping bot polling.")
                break
            except Exception as e:
                print(f"[Telegram Poller] Error: {e}")
                time.sleep(3)


bot_service = TelegramService()

if __name__ == "__main__":
    bot_service.poll_updates()
