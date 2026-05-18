"""
Prediction controller — serves from the zone grid DB cache.

Flow:
  1. Query zone_grid_points for the nearest cached point to (lat, lng)
  2. Build PredictionResponse from that cached row
  3. Return immediately — no live Open-Meteo call

The zone grid is recomputed every 3 hours by the background scheduler,
so cached data is always recent. This avoids hitting Open-Meteo on every
frontend prediction request and eliminates rate-limit failures.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from app.hazards.flood.rules import DISCLAIMER
from app.models.prediction import PredictionResponse, TopFactor
from app.zones.zone_repository import ZoneRepository

logger = logging.getLogger(__name__)

_WEATHER_FEATURE_KEYS = [
    "precipitation", "precip_3day_avg", "precip_7day_avg",
    "pressure", "temperature", "temp_3day_avg",
    "soil_moisture", "soil_3day_avg", "wind_speed",
    "humidity", "evaporation", "is_monsoon", "month", "day_of_year",
]


# ── Public entry point ────────────────────────────────────────────────────────

async def run_prediction(lat: float, lng: float) -> PredictionResponse:
    """
    Return a prediction for (lat, lng) from the nearest cached zone point.

    Raises HTTPException 503 if no zone data exists yet (first startup before
    the scheduler has run its first computation).
    """
    repo  = ZoneRepository()
    point = await asyncio.to_thread(repo.get_nearest_zone_point, lat, lng)

    if point is None:
        raise HTTPException(
            status_code=503,
            detail="No cached zone data yet — the background scheduler is still computing. Try again in ~10 minutes.",
        )

    weather_features = {
        k: float(point[k])
        for k in _WEATHER_FEATURE_KEYS
        if point.get(k) is not None
    }

    top_factors: list[TopFactor] = []
    for i in (1, 2, 3):
        name = point.get(f"top_feature_{i}_name")
        val  = point.get(f"top_feature_{i}_value")
        imp  = point.get(f"top_feature_{i}_imp")
        if name and val is not None and imp is not None:
            top_factors.append(TopFactor(name=name, value=float(val), importance=float(imp)))

    logger.info(
        "Prediction served from cache: lat=%.4f lng=%.4f → nearest=%.4f,%.4f risk=%s",
        lat, lng, point["lat"], point["lng"], point["risk_level"],
    )

    return PredictionResponse(
        latitude=lat,
        longitude=lng,
        nearest_grid_lat=float(point["lat"]),
        nearest_grid_lng=float(point["lng"]),
        flood_probability=float(point["flood_prob"]),
        risk_level=point["risk_level"],
        confidence=float(point["confidence"]),
        top_factors=top_factors,
        weather_features=weather_features,
        model_version="flood_xgb_pakistan_v2 (cached)",
        saved_to_db=True,
        disclaimer=DISCLAIMER,
    )

