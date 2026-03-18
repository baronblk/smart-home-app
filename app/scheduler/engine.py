"""
APScheduler engine — setup and lifecycle management.

The scheduler is registered in app/main.py's lifespan context manager.
It starts at application startup and shuts down cleanly on stop.

Background jobs registered here:
  - poll_all_devices: every 60 seconds
  - evaluate_all_rules: every 60 seconds
  - refresh_weather_cache: every 30 minutes (added in Phase 8)
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Module-level scheduler instance — shared across the application
scheduler = AsyncIOScheduler(timezone="UTC")


def setup_scheduler() -> AsyncIOScheduler:
    """
    Register all background jobs on the scheduler.

    Called during application startup (before scheduler.start()).
    Jobs are not added if the scheduler is already running to avoid
    duplicates on hot-reload.
    """
    from app.scheduler.tasks import evaluate_all_rules, poll_all_devices, refresh_weather_cache

    if not scheduler.get_job("poll_all_devices"):
        scheduler.add_job(
            poll_all_devices,
            trigger=IntervalTrigger(seconds=60),
            id="poll_all_devices",
            name="Poll all device states",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Registered job: poll_all_devices (every 60s)")

    if not scheduler.get_job("evaluate_all_rules"):
        scheduler.add_job(
            evaluate_all_rules,
            trigger=IntervalTrigger(seconds=60),
            id="evaluate_all_rules",
            name="Evaluate automation rules",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Registered job: evaluate_all_rules (every 60s)")

    if not scheduler.get_job("refresh_weather_cache"):
        scheduler.add_job(
            refresh_weather_cache,
            trigger=IntervalTrigger(minutes=30),
            id="refresh_weather_cache",
            name="Refresh weather cache",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Registered job: refresh_weather_cache (every 30min)")

    return scheduler


def start_scheduler() -> None:
    """Start the scheduler. Called from FastAPI lifespan."""
    setup_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started.")


def stop_scheduler() -> None:
    """Stop the scheduler gracefully. Called from FastAPI lifespan."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
