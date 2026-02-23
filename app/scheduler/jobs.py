import json
import logging

import discord

from app.agent.claude import GeminiAgent
from app.agent.prompts import build_briefing_prompt
from app.bot.formatting import chunk_message
from app.db.database import async_session
from app.db.models import BriefingLog
from app.social.competitors import format_competitor_data, scan_all_competitors

logger = logging.getLogger(__name__)


async def run_morning_briefing(agent: GeminiAgent, channel: discord.TextChannel) -> str | None:
    try:
        logger.info("Starting morning briefing...")

        # 1. Scan competitors
        competitor_data = await scan_all_competitors()
        formatted = format_competitor_data(competitor_data)

        # 2. Feed to Claude
        prompt = build_briefing_prompt(formatted)
        briefing_text = await agent.run_briefing(prompt)

        # 3. Log it
        session_factory = async_session()
        async with session_factory() as session:
            log = BriefingLog(
                summary=briefing_text[:1000],
                competitor_data=json.dumps(competitor_data, default=str),
            )
            session.add(log)
            await session.commit()

        # 4. Send to Discord
        for chunk in chunk_message(briefing_text):
            await channel.send(chunk)

        logger.info("Morning briefing sent successfully.")
        return briefing_text

    except Exception as e:
        logger.exception("Morning briefing failed: %s", e)
        try:
            await channel.send(f"⚠️ Morning briefing failed: {e}\n\nUse `!briefing` to retry.")
        except Exception:
            pass
        return None
