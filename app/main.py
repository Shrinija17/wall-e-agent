import asyncio
import logging

from app.agent.claude import GeminiAgent
from app.bot.handlers import create_bot
from app.config import settings
from app.db.database import init_db
from app.memory.store import MemoryStore

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

    # 4. Discord bot (on_ready handles channel setup + scheduler)
    bot = create_bot(agent, memory)

    # 5. Run the bot
    await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
