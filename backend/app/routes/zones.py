"""
Zone grid endpoints.

GET  /zones/geojson  — latest cached zone GeoJSON (always instant)
                       stale-while-revalidate: if cache is old, returns
                       old data immediately AND triggers a background refresh
GET  /zones/status   — batch age, freshness, point count, next-refresh ETA
POST /zones/compute  — manually trigger a recomputation
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.hazards.flood.model import get_flood_model
from app.zones.zone_geojson import points_to_geojson
from app.zones.zone_repository import ZoneRepository
from app.zones.zone_scheduler import is_computing, trigger_immediate

router = APIRouter(prefix="/zones")
logger = logging.getLogger(__name__)


# ── GET /zones/geojson ────────────────────────────────────────────────────────

@router.get("/geojson")
async def get_zone_geojson() -> dict:
    """
    Return the latest complete zone GeoJSON from the DB cache.

    Stale-while-revalidate: if cache is older than ZONE_CACHE_TTL_MINUTES,
    returns the existing data immediately AND quietly triggers a background
    refresh so the next request gets fresh data.

    Returns an empty FeatureCollection (metadata.total_points=0) when no
    computation has run yet.
    """
    repo    = ZoneRepository()
    points  = await asyncio.to_thread(repo.get_latest_zone_points)
    batch   = await asyncio.to_thread(repo.get_latest_batch)
    fresh   = await asyncio.to_thread(repo.is_cache_fresh)

    # Stale-while-revalidate: kick off background refresh if needed
    if not fresh and not is_computing():
        model = get_flood_model()
        if model.is_ready:
            trigger_immediate(model)
            logger.info("Stale cache detected — background refresh triggered")

    if not points:
        return {
            "type":     "FeatureCollection",
            "features": [],
            "metadata": {
                "computed_at":       None,
                "is_fresh":          False,
                "total_points":      0,
                "grid_step_degrees": 0.25,
                "model_features":    [],
                "message":           "No zone data yet — computation queued, retry in ~10 min.",
            },
        }

    completed = batch.get("completed_at") if batch else None
    return points_to_geojson(points, completed, fresh)


# ── GET /zones/status ─────────────────────────────────────────────────────────

@router.get("/status")
async def get_zone_status() -> dict:
    """
    Report cache age, freshness, and when the next refresh will happen.
    Frontend polls this to show a loading indicator.
    """
    from app.core.config import settings

    repo    = ZoneRepository()
    batch   = await asyncio.to_thread(repo.get_latest_batch)
    minutes = await asyncio.to_thread(repo.get_minutes_since_last_computation)
    fresh   = await asyncio.to_thread(repo.is_cache_fresh)

    ttl            = settings.ZONE_CACHE_TTL_MINUTES
    next_refresh   = round(max(0.0, ttl - minutes), 1) if minutes is not None else ttl

    return {
        "status":              batch.get("status") if batch else "never_computed",
        "has_data":            batch is not None,
        "is_fresh":            fresh,
        "is_computing":        is_computing(),
        "computed_at":         batch.get("completed_at") if batch else None,
        "age_minutes":         round(minutes, 1) if minutes is not None else None,
        "next_refresh_in_min": next_refresh,
        "total_points":        batch.get("total_points") if batch else 0,
        "last_batch_id":       batch.get("id") if batch else None,
    }


# ── POST /zones/compute ───────────────────────────────────────────────────────

@router.post("/compute")
async def trigger_zone_computation() -> dict:
    """
    Manually trigger a zone recomputation in the background.
    Returns immediately — poll /zones/status to track progress.
    No-op if a computation is already running.
    """
    if is_computing():
        return {"started": False, "reason": "Computation already running."}

    model = get_flood_model()
    if not model.is_ready:
        raise HTTPException(status_code=503, detail="Model artifact not loaded.")

    started = trigger_immediate(model)
    if started:
        return {"started": True, "message": "Zone computation started — poll /zones/status."}
    return {"started": False, "reason": "Scheduler not running — restart the server."}


# ── POST /admin/refresh-zones ─────────────────────────────────────────────────

@router.post("/admin/refresh-zones")
async def admin_refresh_zones(
    x_api_key: str | None = Header(default=None),
) -> dict:
    """
    Force a full zone recomputation immediately, bypassing the 60-min cache.

    Protected by ADMIN_API_KEY (set in backend/.env).
    Pass the key as the request header:  X-Api-Key: <your-key>

    Use when: model artifact updated, major weather event, debugging.
    Returns immediately — computation runs in background.
    Poll GET /zones/status to track progress.
    """
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY not configured on server.")

    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    if is_computing():
        return {"status": "already_computing", "message": "A computation is already running."}

    model = get_flood_model()
    if not model.is_ready:
        raise HTTPException(status_code=503, detail="Model artifact not loaded.")

    started = trigger_immediate(model)
    if started:
        return {"status": "triggered", "message": "Zone recomputation started in background."}
    return {"status": "error", "message": "Scheduler not running — restart the server."}
