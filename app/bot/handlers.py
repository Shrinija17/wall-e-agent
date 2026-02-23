import logging

import discord
from discord.ext import commands

from app.agent.claude import GeminiAgent
from app.bot.approvals import get_pending_drafts, send_approval_message
from app.bot.formatting import chunk_message
from app.config import settings
from app.memory.store import MemoryStore
from app.scheduler.runner import create_scheduler

logger = logging.getLogger(__name__)


def create_bot(agent: GeminiAgent, memory: MemoryStore) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    channels: dict[str, discord.TextChannel | None] = {
        "chat": None,
        "briefings": None,
        "drafts": None,
        "trending": None,
        "jobs": None,
    }

    # Wire up the approval callback so the agent can send drafts to #drafts
    async def _send_approval(draft_id: int, platform: str, content: str):
        ch = channels["drafts"] or channels["chat"]
        if ch:
            await send_approval_message(draft_id, platform, content, ch)

    agent.send_approval_fn = _send_approval

    @bot.event
    async def on_ready():
        # Populate all channel references
        channels["chat"] = bot.get_channel(settings.discord_channel_id)
        channels["briefings"] = bot.get_channel(settings.discord_briefings_channel_id)
        channels["drafts"] = bot.get_channel(settings.discord_drafts_channel_id)
        channels["trending"] = bot.get_channel(settings.discord_trending_channel_id)
        channels["jobs"] = bot.get_channel(settings.discord_jobs_channel_id)

        found = [name for name, ch in channels.items() if ch]
        missing = [name for name, ch in channels.items() if not ch]
        if found:
            logger.info("Wall-E connected to: %s", ", ".join(f"#{c}" for c in found))
        if missing:
            logger.warning("Channels not found: %s", ", ".join(missing))

        # Start scheduler with channel routing
        fallback = channels["chat"]
        sched_channels = {
            "briefings": channels["briefings"] or fallback,
            "trending": channels["trending"] or fallback,
            "jobs": channels["jobs"] or fallback,
        }
        scheduler = create_scheduler(agent, sched_channels)
        scheduler.start()
        logger.info("Scheduler started with %d jobs.", len(scheduler.get_jobs()))

        logger.info("Wall-E is online as %s", bot.user)

    @bot.command(name="start")
    async def start(ctx: commands.Context):
        await ctx.send(
            "👋 Hey Shrinija! Wall-E is online.\n\n"
            "I can help with competitor intel, trending topics, job hunting, social posts, and anything JustPaid.\n\n"
            "**Channels:**\n"
            f"<#{settings.discord_channel_id}> — Chat with me\n"
            f"<#{settings.discord_briefings_channel_id}> — Morning briefings\n"
            f"<#{settings.discord_drafts_channel_id}> — Post drafts & approvals\n"
            f"<#{settings.discord_trending_channel_id}> — Trending AI/Tech + X posts\n"
            f"<#{settings.discord_jobs_channel_id}> — Job postings\n\n"
            "**Commands:**\n"
            "`!briefing` — Competitor intel briefing\n"
            "`!trending` — Trending AI/Tech + tweet drafts\n"
            "`!jobs` — Latest job postings for you\n"
            "`!draft <x|linkedin> <topic>` — Draft a post\n"
            "`!pending` — Posts awaiting approval\n"
            "`!new` — Clear conversation history\n"
        )

    @bot.command(name="new")
    async def new_conversation(ctx: commands.Context):
        await memory.clear_conversation()
        await ctx.send("🔄 Conversation cleared. Fresh start!")

    @bot.command(name="briefing")
    async def briefing(ctx: commands.Context):
        target = channels["briefings"] or ctx.channel
        if target.id != ctx.channel.id:
            await ctx.send(f"☕ Running briefing... check <#{target.id}>")
        else:
            await ctx.send("☕ Running your morning briefing... hang tight.")
        async with target.typing():
            from app.scheduler.jobs import run_morning_briefing
            await run_morning_briefing(agent, target)

    @bot.command(name="trending")
    async def trending(ctx: commands.Context):
        target = channels["trending"] or ctx.channel
        if target.id != ctx.channel.id:
            await ctx.send(f"🔥 Scanning trends... check <#{target.id}>")
        else:
            await ctx.send("🔥 Scanning trending AI/Tech topics... hang tight.")
        async with target.typing():
            from app.scheduler.jobs import run_trending_scan
            await run_trending_scan(agent, target)

    @bot.command(name="jobs")
    async def jobs(ctx: commands.Context):
        target = channels["jobs"] or ctx.channel
        if target.id != ctx.channel.id:
            await ctx.send(f"💼 Scanning jobs... check <#{target.id}>")
        else:
            await ctx.send("💼 Scanning job postings... hang tight.")
        async with target.typing():
            from app.scheduler.jobs import run_job_scan
            await run_job_scan(agent, target)

    @bot.command(name="draft")
    async def draft(ctx: commands.Context, platform: str = None, *, topic: str = None):
        if not platform or not topic:
            await ctx.send(
                "Usage: `!draft <x|linkedin> <topic>`\n"
                "Example: `!draft x AI agents in finance`"
            )
            return

        platform = platform.lower()
        if platform not in ("x", "linkedin"):
            await ctx.send("Platform must be `x` or `linkedin`.")
            return

        drafts_ch = channels["drafts"]
        if drafts_ch and ctx.channel.id != drafts_ch.id:
            await ctx.send(f"✍️ Drafting... I'll post it in <#{drafts_ch.id}> for approval.")

        async with ctx.typing():
            response = await agent.chat(f"Draft a {platform} post about: {topic}")
            for chunk in chunk_message(response):
                await ctx.send(chunk)

    @bot.command(name="pending")
    async def pending(ctx: commands.Context):
        drafts = await get_pending_drafts()
        if not drafts:
            await ctx.send("No pending drafts. All clear! ✨")
            return
        target = channels["drafts"] or ctx.channel
        for d in drafts[:10]:
            await send_approval_message(d.id, d.platform, d.content, target)
        if target.id != ctx.channel.id:
            await ctx.send(f"📝 Sent {len(drafts[:10])} draft(s) to <#{target.id}>")

    @bot.event
    async def on_message(message: discord.Message):
        # Process commands first
        await bot.process_commands(message)

        # Ignore bots, commands
        if message.author.bot:
            return
        if message.content.startswith("!"):
            return

        # Only respond in the #wall-e chat channel
        if message.channel.id != settings.discord_channel_id:
            return

        async with message.channel.typing():
            response = await agent.chat(message.content)
            for chunk in chunk_message(response):
                await message.channel.send(chunk)

    return bot
