"""
Pakistan zone grid generator — batch weather fetch + XGBoost predictions.

Flow:
  1. generate_pakistan_grid()  → ~1,168 (lat, lng) pairs at 0.25° spacing
  2. compute_all_zones(model)  → async batch: Open-Meteo → predict → collect
     - OPEN_METEO_BATCH_SIZE points run in parallel (asyncio.gather)
     - OPEN_METEO_BATCH_PAUSE_SEC pause between batches (rate-limit courtesy)
     - Points that fail Open-Meteo are skipped silently

Results are returned as plain dicts ready to INSERT into zone_grid_points.
This function is called by the background scheduler every 60 minutes;
users always read from cached DB rows — they never wait on this.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
import numpy as np

from app.core.config import settings
from app.hazards.flood.features import FEATURE_COLS
from app.hazards.flood.rules import classify_risk
from app.zones.open_meteo_adapter import RATE_LIMITED, fetch_weather_features, features_to_vector

logger = logging.getLogger(__name__)


# ── Grid generation ───────────────────────────────────────────────────────────

def generate_pakistan_grid() -> list[tuple[float, float]]:
    """
    Return all (lat, lng) pairs covering Pakistan at 0.25° spacing.

    Bbox from config: N=37.0 S=23.5 W=60.5 E=77.0  →  ~1,168 points.
    """
    points: list[tuple[float, float]] = []
    lat = settings.PAK_SOUTH
    while lat <= settings.PAK_NORTH + 1e-9:     # +epsilon avoids float edge-skip
        lng = settings.PAK_WEST
        while lng <= settings.PAK_EAST + 1e-9:
            points.append((round(lat, 4), round(lng, 4)))
            lng = round(lng + settings.GRID_STEP_DEGREES, 4)
        lat = round(lat + settings.GRID_STEP_DEGREES, 4)
    return points


# ── Single-point prediction ───────────────────────────────────────────────────

async def predict_single_point(
    lat: float,
    lng: float,
    client: httpx.AsyncClient,
    model,
    feature_importances: np.ndarray,
    feature_names: list[str],
) -> Optional[dict]:
    """
    Fetch weather → build vector → predict for one grid point.

    Returns a flat dict on success.
    Returns RATE_LIMITED sentinel when the 429 retry budget is exhausted
    (caller should add a longer cooldown before the next request).
    Returns None on any other transient failure (caller skips the point).
    """
    features = await fetch_weather_features(lat, lng, client)
    if features is RATE_LIMITED:
        return RATE_LIMITED   # propagate so the outer loop can cool down
    if features is None:
        return None

    vector     = features_to_vector(features).reshape(1, -1)
    flood_prob = float(model.predict_proba(vector)[0][1])
    confidence = float(2.0 * abs(flood_prob - 0.5))

    # Top-3 features by importance (descending)
    top_idx = np.argsort(feature_importances)[-3:][::-1]
    top = [
        {
            "name":       feature_names[i],
            "value":      float(vector[0][i]),
            "importance": float(feature_importances[i]),
        }
        for i in top_idx
    ]

    # Pad to 3 entries if model has fewer importances than expected
    while len(top) < 3:
        top.append({"name": "", "value": 0.0, "importance": 0.0})

    return {
        # Location
        "lat": lat,
        "lng": lng,

        # Prediction outputs
        "flood_prob": round(flood_prob, 4),
        "risk_level": classify_risk(flood_prob),
        "confidence": round(confidence, 4),

        # 14 input features (stored exactly as fed to the model)
        "precipitation":   features["precipitation"],
        "precip_3day_avg": features["precip_3day_avg"],
        "precip_7day_avg": features["precip_7day_avg"],
        "pressure":        features["pressure"],
        "temperature":     features["temperature"],
        "temp_3day_avg":   features["temp_3day_avg"],
        "soil_moisture":   features["soil_moisture"],
        "soil_3day_avg":   features["soil_3day_avg"],
        "wind_speed":      features["wind_speed"],
        "humidity":        features["humidity"],
        "evaporation":     features["evaporation"],
        "is_monsoon":      features["is_monsoon"],
        "month":           features["month"],
        "day_of_year":     features["day_of_year"],

        # Top-3 importances for the frontend explainer panel
        "top_feature_1_name":  top[0]["name"],
        "top_feature_1_value": top[0]["value"],
        "top_feature_1_imp":   top[0]["importance"],

        "top_feature_2_name":  top[1]["name"],
        "top_feature_2_value": top[1]["value"],
        "top_feature_2_imp":   top[1]["importance"],

        "top_feature_3_name":  top[2]["name"],
        "top_feature_3_value": top[2]["value"],
        "top_feature_3_imp":   top[2]["importance"],

        # Metadata
        "weather_source": "open-meteo",
        "computed_at":    datetime.now(timezone.utc).isoformat(),
    }


# ── Batch orchestrator ────────────────────────────────────────────────────────

async def compute_all_zones(model) -> list[dict]:
    """
    Run predictions for every Pakistan grid point.

    Processes points ONE AT A TIME.  Uses adaptive rate control:
      - Normal delay: OPEN_METEO_REQUEST_DELAY_SEC between each request.
      - After a 429 cascade (all retries exhausted): 3-minute cooldown,
        then doubles the per-request delay for subsequent points so we
        stay comfortably under the rate limit for the rest of the run.

    Args:
        model: FloodModel wrapper or raw XGBoost object — both accepted.
    """
    xgb = getattr(model, "_model", model)

    grid          = generate_pakistan_grid()
    total         = len(grid)
    base_delay    = settings.OPEN_METEO_REQUEST_DELAY_SEC
    current_delay = base_delay
    rate_cooldown = 180.0   # pause (s) after 429 exhaustion before next request
    log_every     = 200

    logger.info("Zone computation started: %d points, %.2fs base delay", total, base_delay)

    importances   = np.array(xgb.feature_importances_)
    feature_names = list(FEATURE_COLS)
    results:    list[dict] = []
    failed_cnt: int        = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, (lat, lng) in enumerate(grid):
            result = await predict_single_point(
                lat, lng, client, xgb, importances, feature_names
            )

            if result is RATE_LIMITED:
                failed_cnt += 1
                # All retries exhausted — rate window still open.
                # Wait for it to clear, then slow down permanently.
                new_delay = min(current_delay * 2, 3.0)
                logger.warning(
                    "Rate limit exhausted at point %d/%d — cooling down %.0fs, "
                    "then delay %.2fs→%.2fs for remaining points",
                    i + 1, total, rate_cooldown, current_delay, new_delay,
                )
                await asyncio.sleep(rate_cooldown)
                current_delay = new_delay
            elif result is not None:
                results.append(result)
            else:
                failed_cnt += 1

            if (i + 1) % log_every == 0 or (i + 1) == total:
                logger.info("Zone progress: %d/%d  (ok=%d failed=%d delay=%.2fs)",
                            i + 1, total, len(results), failed_cnt, current_delay)

            if i < total - 1:
                await asyncio.sleep(current_delay)

    logger.info("Zone computation complete: %d succeeded, %d failed, %d total",
                len(results), failed_cnt, total)
    return results
