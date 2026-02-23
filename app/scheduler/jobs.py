import json
import logging

import discord

from app.agent.claude import GeminiAgent
from app.agent.prompts import build_briefing_prompt, build_trending_prompt, build_jobs_prompt
from app.bot.formatting import chunk_message
from app.db.database import async_session
from app.db.models import BriefingLog
from app.social.competitors import format_competitor_data, scan_all_competitors
from app.social.trending import format_trending_data, scan_trending_ai
from app.jobs.scanner import format_job_results, scan_jobs

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


async def run_trending_scan(agent: GeminiAgent, channel: discord.TextChannel) -> str | None:
    try:
        logger.info("Starting trending AI/Tech scan...")

        # 1. Scan trending topics
        results = await scan_trending_ai()
        formatted = format_trending_data(results)

        # 2. Feed to agent for analysis + tweet drafts
        prompt = build_trending_prompt(formatted)
        trending_text = await agent.run_briefing(prompt)

        # 3. Send to Discord
        header = "🔥 **Trending AI/Tech — Today's Scan**\n\n"
        for chunk in chunk_message(header + trending_text):
            await channel.send(chunk)

        logger.info("Trending scan sent successfully.")
        return trending_text

    except Exception as e:
        logger.exception("Trending scan failed: %s", e)
        try:
            await channel.send(f"⚠️ Trending scan failed: {e}\n\nUse `!trending` to retry.")
        except Exception:
            pass
        return None


async def run_job_scan(agent: GeminiAgent, channel: discord.TextChannel) -> str | None:
    try:
        logger.info("Starting job postings scan...")

        # 1. Scan job postings
        results = await scan_jobs()
        formatted = format_job_results(results)

        # 2. Feed to agent for analysis
        prompt = build_jobs_prompt(formatted)
        jobs_text = await agent.run_briefing(prompt)

        # 3. Send to Discord
        header = "💼 **Daily Job Scan**\n\n"
        for chunk in chunk_message(header + jobs_text):
            await channel.send(chunk)

        logger.info("Job scan sent successfully.")
        return jobs_text

    except Exception as e:
        logger.exception("Job scan failed: %s", e)
        try:
            await channel.send(f"⚠️ Job scan failed: {e}\n\nUse `!jobs` to retry.")
        except Exception:
            pass
        return None
