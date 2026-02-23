import logging

import discord
from discord.ext import commands

from app.agent.claude import GeminiAgent
from app.bot.approvals import get_pending_drafts, send_approval_message
from app.bot.formatting import chunk_message
from app.config import settings
from app.memory.store import MemoryStore

logger = logging.getLogger(__name__)


def create_bot(agent: GeminiAgent, memory: MemoryStore) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    channel: discord.TextChannel | None = None

    # Wire up the approval callback so the agent can send drafts to Discord
    async def _send_approval(draft_id: int, platform: str, content: str):
        if channel:
            await send_approval_message(draft_id, platform, content, channel)

    agent.send_approval_fn = _send_approval

    @bot.event
    async def on_ready():
        nonlocal channel
        channel = bot.get_channel(settings.discord_channel_id)
        if channel:
            logger.info("Wall-E connected to #%s", channel.name)
        else:
            logger.warning("Could not find channel %s", settings.discord_channel_id)
        logger.info("Wall-E is online as %s", bot.user)

    @bot.command(name="start")
    async def start(ctx: commands.Context):
        await ctx.send(
            "👋 Hey Shrinija! Wall-E is online.\n\n"
            "I can help with competitor intel, social post drafts, and anything JustPaid.\n\n"
            "**Commands:**\n"
            "`!briefing` — Get your morning briefing\n"
            "`!draft <platform> <topic>` — Draft a post\n"
            "`!pending` — See posts awaiting approval\n"
            "`!new` — Clear conversation history\n"
        )

    @bot.command(name="new")
    async def new_conversation(ctx: commands.Context):
        await memory.clear_conversation()
        await ctx.send("🔄 Conversation cleared. Fresh start!")

    @bot.command(name="briefing")
    async def briefing(ctx: commands.Context):
        await ctx.send("☕ Running your morning briefing... hang tight.")
        async with ctx.typing():
            from app.scheduler.jobs import run_morning_briefing
            result = await run_morning_briefing(agent, ctx.channel)
            if result:
                for chunk in chunk_message(result):
                    await ctx.send(chunk)

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
        for d in drafts[:10]:
            await send_approval_message(d.id, d.platform, d.content, ctx.channel)

    @bot.event
    async def on_message(message: discord.Message):
        # Process commands first
        await bot.process_commands(message)

        # Ignore bots, commands, and messages outside the configured channel
        if message.author.bot:
            return
        if message.content.startswith("!"):
            return
        if message.channel.id != settings.discord_channel_id:
            return

        async with message.channel.typing():
            response = await agent.chat(message.content)
            for chunk in chunk_message(response):
                await message.channel.send(chunk)

    return bot
