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
from app.zones.boundary_repository import BoundaryRepository
from app.zones.flood_events_sync import sync_flood_events

logger = logging.getLogger(__name__)

_scheduler    = AsyncIOScheduler()
_is_computing = False


async def _refresh_boundary_job() -> None:
    """
    Check if the Pakistan boundary is stale (older than 1 year) and refresh it.
    Downloads from GADM 4.1 and upserts into country_boundaries.
    Runs once on startup and then annually.
    """
    repo = BoundaryRepository()
    stale = await asyncio.to_thread(repo.is_stale, "PAK")
    if not stale:
        logger.info("Pakistan boundary is fresh — skipping refresh")
        return

    logger.info("Pakistan boundary is stale or missing — downloading from GADM…")
    try:
        import json
        import httpx
        from datetime import timedelta

        GADM_URL      = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PAK_0.json"
        RDP_TOLERANCE = 0.02

        def _perp(p, s, e):
            if s == e:
                return ((p[0]-s[0])**2 + (p[1]-s[1])**2) ** 0.5
            num = abs((e[1]-s[1])*p[0] - (e[0]-s[0])*p[1] + e[0]*s[1] - e[1]*s[0])
            den = ((e[1]-s[1])**2 + (e[0]-s[0])**2) ** 0.5
            return num / den if den else 0.0

        def _rdp(pts, tol):
            if len(pts) < 3: return pts
            s, e = pts[0], pts[-1]
            md, mi = 0.0, 0
            for i in range(1, len(pts)-1):
                d = _perp(pts[i], s, e)
                if d > md: md, mi = d, i
            if md > tol:
                return _rdp(pts[:mi+1], tol)[:-1] + _rdp(pts[mi:], tol)
            return [s, e]

        def simplify(geom, tol):
            t, c = geom.get("type"), geom.get("coordinates", [])
            if t == "Polygon":
                return {"type": "Polygon", "coordinates": [_rdp(r, tol) for r in c]}
            if t == "MultiPolygon":
                return {"type": "MultiPolygon", "coordinates": [[_rdp(r, tol) for r in p] for p in c]}
            return geom

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(GADM_URL)
            resp.raise_for_status()

        features = resp.json().get("features", [])
        if not features:
            logger.error("Boundary refresh: no features in GADM response")
            return

        geom_simplified = simplify(features[0]["geometry"], RDP_TOLERANCE)
        geom_str        = json.dumps(geom_simplified)

        await asyncio.to_thread(
            repo.save_boundary, "PAK", "Pakistan", geom_str, "GADM 4.1 ADM0"
        )
        logger.info("Pakistan boundary refreshed (%d chars)", len(geom_str))

    except Exception as exc:
        logger.error("Boundary refresh failed: %s", exc, exc_info=True)


async def _startup_zone_job(model) -> None:
    """
    Startup-only wrapper: refresh boundary if stale, sync flood events,
    then skip zone computation if the DB already has fresh zone data.
    """
    await _refresh_boundary_job()

    # Sync flood events on every startup (fast upsert, no-op if data is current)
    try:
        await asyncio.to_thread(sync_flood_events)
        logger.info("Flood events synced on startup")
    except Exception as exc:
        logger.warning("Flood events startup sync failed: %s", exc)

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

    # Yearly boundary refresh — checks next_refresh_at in DB, no-ops if fresh
    _scheduler.add_job(
        _refresh_boundary_job,
        trigger=IntervalTrigger(days=365),
        id="boundary_yearly",
        replace_existing=True,
        misfire_grace_time=86400,   # 1 day grace if server was down
    )

    # Weekly flood events sync — upserts GDACS RSS + historical baseline
    _scheduler.add_job(
        lambda: asyncio.to_thread(sync_flood_events),
        trigger=IntervalTrigger(weeks=1),
        id="flood_events_weekly",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(
        "Zone scheduler started — immediate run in 5s, then every 3h. "
        "Boundary refresh: on startup + yearly. "
        "Flood events sync: on startup + weekly."
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
