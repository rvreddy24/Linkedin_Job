"""Interactive Discord Bot for Auto Bot LinkedIn Job.

Implements native Slash Commands (/hunt, /status, /hot, /draft, /help),
dual prefix commands (!hunt, !status...), and interactive UI buttons.
"""

import asyncio
from datetime import datetime, timezone
import discord
from discord.ext import commands
from typing import Optional, Dict, Any

from engine.config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
from engine.storage import storage
from engine.run_hunt import execute_hunt
from engine.drafter import check_cooldown, draft_outreach, generate_contact_url
from engine.discord_webhook import format_discord_embed

intents = discord.Intents.default()


class AutoBot(commands.Bot):
    async def setup_hook(self):
        try:
            guild = discord.Object(id=1518237534914875422)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Instantly synced {len(synced)} slash commands directly to Auto_Linkedin server: {[c.name for c in synced]}", flush=True)
        except Exception as e:
            print(f"Error syncing guild commands: {e}", flush=True)

    async def on_interaction(self, interaction: discord.Interaction):
        # Global persistent handler for Draft Outreach buttons (works across restarts and on old cards)
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("btn_draft:") or custom_id == "btn_draft":
                await interaction.response.defer(ephemeral=False)
                listing_id = None
                if custom_id.startswith("btn_draft:"):
                    listing_id = custom_id.split("btn_draft:", 1)[1]
                elif interaction.message and interaction.message.embeds:
                    footer = interaction.message.embeds[0].footer.text or ""
                    m = re.search(r"ID:\s*(\S+)", footer)
                    if m:
                        listing_id = m.group(1)

                if listing_id:
                    await execute_draft_response(interaction, listing_id)
                else:
                    await interaction.followup.send("⚠️ Could not detect listing ID from this card. Try using `/draft listing_id:...`.")
                return

        await super().on_interaction(interaction)


bot = AutoBot(command_prefix="!", intents=intents, application_id=1552147522351276153)


async def execute_draft_response(interaction: discord.Interaction, listing_id: str):
    """Generate and display copy-pasteable outreach note for a listing."""
    listing = storage.lookup_pipeline(listing_id)
    if not listing:
        await interaction.followup.send(f"❌ Error: Listing `{listing_id}` not found in Pipeline.")
        return

    company = listing.get("company", "Company")
    title = listing.get("title", "Role")

    # Generate draft asynchronously (using personal & professional prompt)
    draft = await asyncio.to_thread(draft_outreach, listing)
    storage.update_pipeline_touch(listing_id, status="drafted", draft=draft)
    storage.record_touch(company, listing_id, action="draft", preview=draft[:100])

    words = len(draft.split())
    reply_text = (
        f"📝 **Outreach Draft for {company} — {title}** ({words} words)\n"
        f"*(Ready to copy & paste into LinkedIn message, InMail, or email)*\n\n"
        f"```text\n{draft}\n```"
    )
    await interaction.followup.send(reply_text)


class HotCardActionView(discord.ui.View):
    """Interactive Button view for Discord hot opportunity cards."""

    def __init__(self, listing_id: str, company: str, job_url: str, contact_url: str):
        super().__init__(timeout=None)
        self.listing_id = listing_id
        self.company = company

        # Action Button 1: Draft Outreach (Persistent unique ID per card)
        draft_btn = discord.ui.Button(
            label="✍️ Draft Outreach",
            style=discord.ButtonStyle.primary,
            custom_id=f"btn_draft:{listing_id}",
        )
        self.add_item(draft_btn)

        # URL Button 2: Open Posting
        self.add_item(discord.ui.Button(label="🔗 Open Posting", url=job_url))

        # URL Button 3: Find Contact on LinkedIn
        self.add_item(discord.ui.Button(label="🔎 Find Contact", url=contact_url))


def create_hot_embed(item_data: dict, listing_id: str) -> discord.Embed:
    """Format single hot opportunity as a Discord embed."""
    title = str(item_data.get('title') or '')[:200]
    company = str(item_data.get('company') or '')[:100]
    fit = str(item_data.get('one_line_fit') or '')[:300]

    embed = discord.Embed(
        title=f"🎯 {title} @ {company}",
        url=item_data.get("url"),
        description=f"*{fit}*" if fit else None,
        color=0xF1C40F if item_data.get("type") == "BUY_SIGNAL" else 0x2ECC71,
    )
    embed.add_field(
        name="Signal & Score",
        value=f"**{item_data.get('type')}** — `{item_data.get('score')}/100` ({str(item_data.get('band', '')).upper()})",
        inline=True,
    )
    embed.add_field(
        name="Location & Source",
        value=f"{item_data.get('location') or 'US Remote'} • {item_data.get('source')}",
        inline=True,
    )
    embed.add_field(
        name="Target Role",
        value=f"`{item_data.get('approach_role') or 'VP of Engineering / Head of AI'}`",
        inline=True,
    )
    embed.add_field(
        name="Angle",
        value=str(item_data.get("angle") or "N/A")[:1000],
        inline=False,
    )
    embed.add_field(
        name="Asks For",
        value=str(item_data.get("asks_for") or "N/A")[:1000],
        inline=True,
    )
    embed.add_field(
        name="Concern",
        value=str(item_data.get("concern") or "N/A")[:1000],
        inline=True,
    )
    embed.set_footer(text=f"Auto Bot LinkedIn Job • ID: {listing_id}")
    return embed


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})", flush=True)
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Instantly synced {len(synced)} slash commands to guild: {guild.name} ({guild.id})", flush=True)
        except Exception as e:
            print(f"Error syncing guild {guild.id}: {e}", flush=True)
    try:
        await bot.tree.sync()
    except Exception as e:
        pass
    print("Auto Bot LinkedIn Job is online and listening! (On-demand mode: runs only when asked)", flush=True)


# ==========================================
# SLASH COMMANDS (Type / in Discord)
# ==========================================

@bot.tree.command(name="hunt", description="Run a live US job hunt across all 5 boards right now")
async def slash_hunt(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        results = await asyncio.to_thread(execute_hunt)

        report_text = results.get("report_text", "")
        if len(report_text) > 3900:
            report_text = report_text[:3900] + "... (truncated)"

        report_embed = discord.Embed(
            title="📊 Auto Bot Daily Hunt Summary",
            description=f"```\n{report_text}\n```",
            color=0x2ECC71,
        )
        await interaction.followup.send(embed=report_embed)

        for card in results.get("hot_cards", [])[:10]:
            listing_id = card["listing_id"]
            item_data = storage.lookup_pipeline(listing_id)
            if not item_data:
                continue

            contact_url = generate_contact_url(card.get("approach_role", ""), card.get("company", ""))
            view = HotCardActionView(
                listing_id=listing_id,
                company=card.get("company", ""),
                job_url=card.get("url", ""),
                contact_url=contact_url,
            )
            embed = create_hot_embed(item_data, listing_id)
            await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"[slash_hunt] Error: {e}", flush=True)
        await interaction.followup.send(f"⚠️ Error executing hunt: {e}")


@bot.tree.command(name="status", description="Check how many listings have been scored and kept in pipeline")
async def slash_status(interaction: discord.Interaction):
    stats = storage.get_stats()
    embed = discord.Embed(
        title="📊 Auto Bot Pipeline Status",
        color=0x3498DB,
    )
    embed.add_field(name="Total Scored", value=f"`{stats['total_scored']}`", inline=True)
    embed.add_field(name="Kept in Pipeline", value=f"`{stats['total_kept']}`", inline=True)
    embed.add_field(name="Hot Opportunities (80+)", value=f"`{stats['total_hot']}`", inline=True)
    embed.set_footer(text="Auto Bot LinkedIn Job • US Only")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="hot", description="View all active hot opportunities (Score 80+) with action buttons")
async def slash_hot(interaction: discord.Interaction):
    await interaction.response.defer()
    import sqlite3

    conn = sqlite3.connect(storage.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, company, title, location, country, source, url, type, score, band,
               one_line_fit, angle, approach_role, asks_for, concern, agency_post
        FROM pipeline WHERE score >= 80 ORDER BY score DESC LIMIT 10
    """)
    rows = cursor.fetchall()

    if not rows:
        await interaction.followup.send("No hot opportunities in pipeline yet. Run `/hunt` to search!")
        return

    await interaction.followup.send(f"🎯 **Showing Top {len(rows)} Hot Opportunities:**")

    for r in rows:
        listing_id, company, title, location, country, source, url, stype, score, band, fit, angle, approach, asks_for, concern, agency_post = r
        item_data = {
            "title": title, "company": company, "location": location, "source": source,
            "url": url, "type": stype, "score": score, "band": band, "one_line_fit": fit,
            "angle": angle, "approach_role": approach, "asks_for": asks_for, "concern": concern,
        }
        contact_url = generate_contact_url(approach, company)
        view = HotCardActionView(
            listing_id=listing_id,
            company=company,
            job_url=url,
            contact_url=contact_url,
        )
        embed = create_hot_embed(item_data, listing_id)
        await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="draft", description="Generate a tailored outreach note for a job listing")
async def slash_draft(interaction: discord.Interaction, listing_id: str):
    await interaction.response.defer(thinking=True)
    try:
        await execute_draft_response(interaction, listing_id)
    except Exception as e:
        print(f"[slash_draft] Error: {e}", flush=True)
        await interaction.followup.send(f"⚠️ Error drafting outreach: {e}")


@bot.tree.command(name="help", description="How to use Auto Bot LinkedIn Job commands and buttons")
async def slash_help(interaction: discord.Interaction):
    help_text = (
        "🤖 **Auto Bot LinkedIn Job — Command Guide**\n\n"
        "**Available Slash Commands (type `/` in chat):**\n"
        "• `/hunt` — Launch a live US job hunt across all 5 feeds\n"
        "• `/status` — View your ledger statistics (scored, kept, hot)\n"
        "• `/hot` — List current top hot opportunities with 1-click buttons\n"
        "• `/draft <listing_id>` — Generate a Gemini pitch note for any job\n"
        "• `/help` — Display this guide\n\n"
        "**Card Action Buttons:**\n"
        "• **✍️ Draft Outreach** — Uses Gemini to draft an 80–130 word pitch (checks 21-day cooldown)\n"
        "• **🔗 Open Posting** — Opens the live job description in your browser\n"
        "• **🔎 Find Contact** — Pre-fills a LinkedIn People Search for the department head"
    )
    await interaction.response.send_message(help_text)


# ==========================================
# TEXT PREFIX COMMANDS (Type ! in Discord)
# ==========================================

@bot.command(name="hunt")
async def cmd_hunt(ctx: commands.Context):
    """Run hunt via !hunt prefix."""
    msg = await ctx.send("🔍 **Starting US job hunt across all 5 feeds...**")
    results = execute_hunt()

    report_embed = discord.Embed(
        title="📊 Auto Bot Daily Hunt Summary",
        description=f"```\n{results['report_text']}\n```",
        color=0x2ECC71,
    )
    await msg.edit(content="", embed=report_embed)

    if results["new_count"] == 0:
        await ctx.send("✅ **Quiet success** — no new US listings matched today.")
        return

    for card in results["hot_cards"]:
        listing_id = card["listing_id"]
        item_data = storage.lookup_pipeline(listing_id)
        if not item_data:
            continue

        contact_url = generate_contact_url(card.get("approach_role", ""), card.get("company", ""))
        view = HotCardActionView(
            listing_id=listing_id,
            company=card.get("company", ""),
            job_url=card.get("url", ""),
            contact_url=contact_url,
        )
        embed = create_hot_embed(item_data, listing_id)
        await ctx.send(embed=embed, view=view)


@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    stats = storage.get_stats()
    embed = discord.Embed(title="📊 Auto Bot Pipeline Status", color=0x3498DB)
    embed.add_field(name="Total Scored", value=f"`{stats['total_scored']}`", inline=True)
    embed.add_field(name="Kept in Pipeline", value=f"`{stats['total_kept']}`", inline=True)
    embed.add_field(name="Hot Opportunities (80+)", value=f"`{stats['total_hot']}`", inline=True)
    embed.set_footer(text="Auto Bot LinkedIn Job • US Only")
    await ctx.send(embed=embed)


@bot.command(name="hot")
async def cmd_hot(ctx: commands.Context):
    import sqlite3
    conn = sqlite3.connect(storage.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, company, title, location, country, source, url, type, score, band,
               one_line_fit, angle, approach_role, asks_for, concern, agency_post
        FROM pipeline WHERE score >= 80 ORDER BY score DESC LIMIT 5
    """)
    rows = cursor.fetchall()
    if not rows:
        await ctx.send("No hot opportunities in pipeline yet. Type `!hunt` to search!")
        return

    await ctx.send(f"🎯 **Showing Top {len(rows)} Hot Opportunities:**")
    for r in rows:
        listing_id, company, title, location, country, source, url, stype, score, band, fit, angle, approach, asks_for, concern, agency_post = r
        item_data = {
            "title": title, "company": company, "location": location, "source": source,
            "url": url, "type": stype, "score": score, "band": band, "one_line_fit": fit,
            "angle": angle, "approach_role": approach, "asks_for": asks_for, "concern": concern,
        }
        contact_url = generate_contact_url(approach, company)
        view = HotCardActionView(
            listing_id=listing_id,
            company=company,
            job_url=url,
            contact_url=contact_url,
        )
        embed = create_hot_embed(item_data, listing_id)
        await ctx.send(embed=embed, view=view)


@bot.command(name="draft")
async def cmd_draft(ctx: commands.Context, listing_id: str):
    listing = storage.lookup_pipeline(listing_id)
    if not listing:
        await ctx.send(f"❌ Error: Listing `{listing_id}` not found in Pipeline.")
        return

    company = listing.get("company", "")
    is_blocked, notice = check_cooldown(company)
    if is_blocked:
        await ctx.send(notice or f"Cooldown active for {company}.")
        return

    draft = draft_outreach(listing)
    storage.update_pipeline_touch(listing_id, status="drafted", draft=draft)
    storage.record_touch(company, listing_id, action="draft", preview=draft[:100])

    words = len(draft.split())
    await ctx.send(
        f"📝 **Outreach Draft for {company}** ({words} words)\n```text\n{draft}\n```"
    )


def start_discord_bot():
    if not DISCORD_BOT_TOKEN:
        print("[Discord Bot] DISCORD_BOT_TOKEN not configured in .env.")
        print("To enable slash commands, add DISCORD_BOT_TOKEN to .env and run:")
        print("  python -m engine.discord_bot")
        return
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    start_discord_bot()
