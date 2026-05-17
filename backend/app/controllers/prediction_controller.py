"""
Prediction controller — orchestrates weather fetch → model inference → DB save.

Flow:
  1. fetch_weather_features(lat, lng)   → 14 features from Open-Meteo
  2. flood_model.predict(features)      → flood_prob, risk_level, confidence, top_factors
  3. _save_to_supabase(...)             → zone_batches + zone_grid_points rows
  4. return PredictionResponse
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.core.supabase import get_supabase
from app.hazards.flood.model import get_flood_model
from app.models.prediction import PredictionResponse, TopFactor
from app.models.zone import ZoneBatchRow, ZoneGridPointRow
from app.services.weather_service import fetch_weather_features

logger = logging.getLogger(__name__)


# ── Public entry point ────────────────────────────────────────────────────────

async def run_prediction(lat: float, lng: float) -> PredictionResponse:
    """Fetch weather, run model, persist to Supabase, return response."""

    features = await fetch_weather_features(lat, lng)
    result   = get_flood_model().predict(features)

    top_factors = [TopFactor(**f) for f in result["top_factors"]]

    saved = False
    try:
        saved = await asyncio.to_thread(_save_to_supabase, lat, lng, features, result)
    except Exception as exc:
        logger.error("Supabase save FAILED: %s", exc, exc_info=True)

    return PredictionResponse(
        latitude=lat,
        longitude=lng,
        flood_probability=result["flood_probability"],
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        top_factors=top_factors,
        weather_features=features,
        model_version=result["model_version"],
        saved_to_db=saved,
    )


# ── Private DB persistence ────────────────────────────────────────────────────

def _save_to_supabase(
    lat: float,
    lng: float,
    features: dict[str, float],
    result: dict,
) -> bool:
    """
    Insert one ZoneBatch + one ZoneGridPoint row into Supabase.
    Returns True on success, False on any error.
    Runs synchronously (called via asyncio.to_thread from the async controller).
    """
    db = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    batch_id = str(uuid.uuid4())

    # ── 1. Create batch ───────────────────────────────────────────────────────
    batch = ZoneBatchRow(
        id=batch_id,
        started_at=now,
        total_points=1,
        status="running",
    )
    db.table("zone_batches").insert(batch.model_dump(exclude_none=True)).execute()

    # ── 2. Build top-feature columns ──────────────────────────────────────────
    tops = result.get("top_factors", [])
    top_cols: dict = {}
    for i, factor in enumerate(tops[:3], start=1):
        top_cols[f"top_feature_{i}_name"]  = factor["name"]
        top_cols[f"top_feature_{i}_value"] = factor["value"]
        top_cols[f"top_feature_{i}_imp"]   = factor["importance"]

    # ── 3. Insert grid point ──────────────────────────────────────────────────
    point = ZoneGridPointRow(
        batch_id=batch_id,
        lat=lat,
        lng=lng,
        flood_prob=result["flood_probability"],
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        computed_at=now,
        **{k: features.get(k) for k in [
            "precipitation", "precip_3day_avg", "precip_7day_avg",
            "pressure", "temperature", "temp_3day_avg",
            "soil_moisture", "soil_3day_avg",
            "wind_speed", "humidity", "evaporation",
            "is_monsoon", "month", "day_of_year",
        ]},
        **top_cols,
    )
    db.table("zone_grid_points").insert(point.model_dump(exclude_none=True)).execute()

    # ── 4. Mark batch complete ────────────────────────────────────────────────
    db.table("zone_batches").update({
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", batch_id).execute()

    logger.info("Saved prediction batch=%s lat=%.4f lng=%.4f", batch_id, lat, lng)
    return True
