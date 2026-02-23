import asyncio
import logging

import discord

from app.agent.claude import GeminiAgent
from app.bot.handlers import create_bot
from app.config import settings
from app.db.database import init_db
from app.memory.store import MemoryStore
from app.scheduler.runner import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Wall-E Agent starting up...")

    # 1. Initialize database
    await init_db()
    logger.info("Database initialized.")

    # 2. Memory store
    memory = MemoryStore()

    # 3. Agent
    agent = GeminiAgent(memory_store=memory)

    # 4. Discord bot
    bot = create_bot(agent, memory)

    # Start scheduler once bot is ready
    @bot.event
    async def on_ready():
        fallback = bot.get_channel(settings.discord_channel_id)
        sched_channels = {
            "briefings": bot.get_channel(settings.discord_briefings_channel_id) or fallback,
            "trending": bot.get_channel(settings.discord_trending_channel_id) or fallback,
            "jobs": bot.get_channel(settings.discord_jobs_channel_id) or fallback,
        }

        scheduler = create_scheduler(agent, sched_channels)
        scheduler.start()
        logger.info("Scheduler started with %d jobs.", len(scheduler.get_jobs()))
        logger.info("Wall-E is online! Listening on Discord...")

    # 5. Run the bot
    await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
