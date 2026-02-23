import logging

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.agent.claude import GeminiAgent
from app.config import settings
from app.scheduler.jobs import run_morning_briefing, run_trending_scan, run_job_scan

logger = logging.getLogger(__name__)


def _cron_trigger(cron_expr: str) -> CronTrigger:
    parts = cron_expr.split()
    return CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=settings.timezone,
    )


def create_scheduler(
    agent: GeminiAgent,
    channels: dict[str, discord.TextChannel],
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    # Morning briefing — 9:00 AM
    briefings_ch = channels.get("briefings")
    if briefings_ch:
        scheduler.add_job(
            run_morning_briefing,
            trigger=_cron_trigger(settings.morning_brief_cron),
            args=[agent, briefings_ch],
            id="morning_briefing",
            name="Morning Briefing",
            replace_existing=True,
        )
        logger.info("Scheduled: morning briefing at %s → #%s", settings.morning_brief_cron, briefings_ch.name)

    # Trending AI/Tech — 8:30 AM (before the briefing)
    trending_ch = channels.get("trending")
    if trending_ch:
        scheduler.add_job(
            run_trending_scan,
            trigger=_cron_trigger("30 8 * * *"),
            args=[agent, trending_ch],
            id="trending_scan",
            name="Trending AI/Tech Scan",
            replace_existing=True,
        )
        logger.info("Scheduled: trending scan at 8:30 AM → #%s", trending_ch.name)

    # Job postings — every 12 hours (8 AM and 8 PM)
    jobs_ch = channels.get("jobs")
    if jobs_ch:
        scheduler.add_job(
            run_job_scan,
            trigger=_cron_trigger("0 8 * * *"),
            args=[agent, jobs_ch],
            id="job_scan_morning",
            name="Job Scan (Morning)",
            replace_existing=True,
        )
        scheduler.add_job(
            run_job_scan,
            trigger=_cron_trigger("0 20 * * *"),
            args=[agent, jobs_ch],
            id="job_scan_evening",
            name="Job Scan (Evening)",
            replace_existing=True,
        )
        logger.info("Scheduled: job scan every 12h (8AM + 8PM) → #%s", jobs_ch.name)

    return scheduler
