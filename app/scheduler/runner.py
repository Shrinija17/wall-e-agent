import logging

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.agent.claude import GeminiAgent
from app.config import settings
from app.scheduler.jobs import run_morning_briefing

logger = logging.getLogger(__name__)


def create_scheduler(agent: GeminiAgent, channel: discord.TextChannel) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    parts = settings.morning_brief_cron.split()
    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=settings.timezone,
    )

    scheduler.add_job(
        run_morning_briefing,
        trigger=trigger,
        args=[agent, channel],
        id="morning_briefing",
        name="Morning Briefing",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured: morning briefing at %s (%s)",
        settings.morning_brief_cron,
        settings.timezone,
    )

    return scheduler
