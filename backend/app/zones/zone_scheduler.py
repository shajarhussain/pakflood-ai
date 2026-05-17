"""
Hourly background scheduler for zone grid computation.

Uses APScheduler AsyncIOScheduler so it runs on FastAPI's own event loop
without blocking request handling.

Lifecycle:
  - start_zone_scheduler() is called once in the FastAPI startup event
  - First run fires immediately on startup (so zones exist from first request)
  - Subsequent runs every 60 minutes automatically
  - Concurrent runs are blocked by _is_computing flag
"""

from __future__ import annotations

import logging

import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.zones.grid_generator import compute_all_zones
from app.zones.zone_repository import ZoneRepository

logger = logging.getLogger(__name__)

_scheduler    = AsyncIOScheduler()
_is_computing = False


async def _startup_zone_job(model) -> None:
    """
    Startup-only wrapper: skip if the DB already has fresh data.
    This prevents hammering Open-Meteo when the server restarts mid-window.
    """
    repo = ZoneRepository()
    fresh = await asyncio.to_thread(repo.is_cache_fresh)
    if fresh:
        logger.info("Zone cache is fresh — skipping startup computation")
        return
    await _zone_job(model)


async def _zone_job(model) -> None:
    """Compute zones and persist to Supabase. Skipped if already running."""
    global _is_computing
    if _is_computing:
        logger.info("Zone job skipped — previous run still in progress")
        return

    _is_computing = True
    try:
        logger.info("Zone computation job started")
        points = await compute_all_zones(model)
        if points:
            repo     = ZoneRepository()
            batch_id = repo.save_zone_batch(points)
            logger.info("Zone job complete — batch %s, %d points", batch_id, len(points))
        else:
            logger.warning("Zone job produced no points — DB not updated")
    except asyncio.CancelledError:
        # Server is shutting down — log and swallow so APScheduler doesn't
        # emit a noisy "Job raised an exception" error on every restart.
        logger.info("Zone job cancelled (server shutdown)")
    except Exception as exc:
        logger.error("Zone computation job failed: %s", exc, exc_info=True)
    finally:
        _is_computing = False


def start_zone_scheduler(model) -> None:
    """
    Register the hourly job and start the scheduler.
    Call once from the FastAPI startup event.

    The first run is delayed by ZONE_STARTUP_DELAY_SEC (default 60s) so the
    server finishes initialising and any previous rate-limit window clears
    before we start hitting Open-Meteo.  Subsequent runs fire every 60 min.
    """
    delay_sec = settings.ZONE_STARTUP_DELAY_SEC
    now       = datetime.now(timezone.utc)
    first_run = now + timedelta(seconds=delay_sec)

    # Immediate one-shot: fires ~5s after startup.
    # Uses _startup_zone_job which skips if DB data is already fresh,
    # preventing Open-Meteo rate-limit hammering on repeated dev restarts.
    _scheduler.add_job(
        _startup_zone_job,
        trigger=DateTrigger(run_date=now + timedelta(seconds=5)),
        args=[model],
        id="zone_immediate",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Recurring job every 3 hours — ~952 points × 8 runs/day = 7,616 req/day
    # (safely under Open-Meteo free tier 10,000/day limit at 0.5° grid).
    _scheduler.add_job(
        _zone_job,
        trigger=IntervalTrigger(hours=3, start_date=first_run),
        args=[model],
        id="zone_hourly",
        replace_existing=True,
        misfire_grace_time=300,
    )

    _scheduler.start()
    logger.info(
        "Zone scheduler started — immediate run in 5s, then every 3h"
    )


def is_computing() -> bool:
    """Return True if a zone computation is currently running."""
    return _is_computing


def trigger_immediate(model) -> bool:
    """
    Queue a one-shot computation right now (non-blocking).
    Returns False if already running or scheduler not started.
    """
    if _is_computing or not _scheduler.running:
        return False
    _scheduler.add_job(
        _zone_job,
        args=[model],
        id="zone_on_demand",
        replace_existing=True,
    )
    logger.info("On-demand zone computation triggered")
    return True


def stop_zone_scheduler() -> None:
    """Gracefully shut down the scheduler. Call from FastAPI shutdown event."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Zone scheduler stopped")
