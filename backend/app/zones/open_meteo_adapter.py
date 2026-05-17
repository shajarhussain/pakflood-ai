"""
Open-Meteo weather adapter for any lat/lng → 14 model features.

Designed for batch zone computation: caller creates ONE httpx.AsyncClient
and passes it in so connections are reused across hundreds of points.

Open-Meteo variable notes (verified against API):
  Daily available  : precipitation_sum, temperature_2m_max,
                     wind_speed_10m_max, et0_fao_evapotranspiration
  Hourly only      : relative_humidity_2m, surface_pressure,
                     soil_moisture_0_to_1cm
                     (soil_moisture_0_to_7cm and *_mean daily variants
                      do not exist — we aggregate hourly ourselves)

Unit conversions applied (model trained on ERA5 SI units):
  pressure   : hPa  × 100   → Pa
  wind_speed : km/h ÷ 3.6   → m/s
  evaporation: mm   / -1000 → negative metres (ERA5 convention)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Sentinel returned (not raised) when all 429 retries are exhausted.
# Callers should treat this as a signal to add a longer cooldown before
# the next request, rather than just skipping the point silently.
class _RateLimited:
    pass

RATE_LIMITED: _RateLimited = _RateLimited()

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

_DAILY_VARS = ",".join([
    "precipitation_sum",
    "temperature_2m_max",
    "wind_speed_10m_max",
    "et0_fao_evapotranspiration",
])

_HOURLY_VARS = ",".join([
    "relative_humidity_2m",
    "surface_pressure",
    "soil_moisture_0_to_1cm",
])

FEATURE_ORDER = [
    "precipitation", "precip_3day_avg", "precip_7day_avg",
    "pressure", "temperature", "temp_3day_avg",
    "soil_moisture", "soil_3day_avg", "wind_speed",
    "humidity", "evaporation", "is_monsoon", "month", "day_of_year",
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _last(values: list, default: float = 0.0) -> float:
    for v in reversed(values):
        if v is not None:
            return float(v)
    return default


def _mean_tail(values: list, n: int, default: float = 0.0) -> float:
    tail = [v for v in values[-n:] if v is not None]
    return float(sum(tail) / len(tail)) if tail else default


def _hourly_to_daily(hourly: list, n_days: int) -> list[float]:
    """Average each 24-hour block into one daily value."""
    result = []
    for d in range(n_days):
        block = [v for v in hourly[d * 24: (d + 1) * 24] if v is not None]
        result.append(float(sum(block) / len(block)) if block else 0.0)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_weather_features(
    lat: float,
    lng: float,
    client: httpx.AsyncClient,
) -> dict[str, float] | None:
    """
    Fetch 7-day weather history + today from Open-Meteo.

    Retries up to OPEN_METEO_MAX_RETRIES times on 429 with exponential
    backoff (2s, 4s, 8s). Returns None on any unrecoverable failure so
    the caller can skip this grid point gracefully.

    Args:
        lat:    Latitude (-90 … 90)
        lng:    Longitude (-180 … 180)
        client: Shared httpx.AsyncClient — reuse across batch for speed.
    """
    params = {
        "latitude":      lat,
        "longitude":     lng,
        "daily":         _DAILY_VARS,
        "hourly":        _HOURLY_VARS,
        "past_days":     7,
        "forecast_days": 1,
        "timezone":      "Asia/Karachi",
    }

    max_retries    = settings.OPEN_METEO_MAX_RETRIES
    rate_base      = settings.OPEN_METEO_RETRY_BASE_SEC  # 15s for 429
    transient_base = 3.0                                  # 3s for 502/503/504

    data = None
    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(_OPEN_METEO_URL, params=params)

            if resp.status_code == 429:
                if attempt < max_retries:
                    wait = rate_base * (2 ** attempt)   # 15s → 30s → 60s → 120s
                    logger.warning(
                        "429 rate-limited lat=%.4f lng=%.4f — retry %d/%d in %.0fs",
                        lat, lng, attempt + 1, max_retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                logger.warning("429 retries exhausted lat=%.4f lng=%.4f", lat, lng)
                return RATE_LIMITED

            if resp.status_code in (502, 503, 504):
                if attempt < max_retries:
                    wait = transient_base * (2 ** attempt)  # 3s → 6s → 12s → 24s
                    logger.warning(
                        "%d transient error lat=%.4f lng=%.4f — retry %d/%d in %.0fs",
                        resp.status_code, lat, lng, attempt + 1, max_retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                logger.warning("%d retries exhausted lat=%.4f lng=%.4f", resp.status_code, lat, lng)
                return None

            resp.raise_for_status()
            data = resp.json()
            break

        except Exception as exc:
            if attempt < max_retries:
                wait = transient_base * (2 ** attempt)
                logger.warning(
                    "fetch error lat=%.4f lng=%.4f — retry %d/%d in %.0fs: %s",
                    lat, lng, attempt + 1, max_retries, wait, exc,
                )
                await asyncio.sleep(wait)
            else:
                logger.warning("fetch_weather_features failed lat=%.4f lng=%.4f: %s", lat, lng, exc)
                return None

    if data is None:
        return None

    try:
        # ── Daily arrays (8 values: 7 past days + today) ──────────────────────
        daily = data["daily"]
        prec  = daily["precipitation_sum"]           # mm/day
        temp  = daily["temperature_2m_max"]           # °C
        wind  = daily["wind_speed_10m_max"]           # km/h  → m/s
        evap  = daily["et0_fao_evapotranspiration"]  # mm/day → negative m

        # ── Hourly arrays → daily means ───────────────────────────────────────
        hourly = data["hourly"]
        n_days = len(prec)
        hum  = _hourly_to_daily(hourly["relative_humidity_2m"],  n_days)  # %
        pres = _hourly_to_daily(hourly["surface_pressure"],       n_days)  # hPa → Pa
        soil = _hourly_to_daily(hourly["soil_moisture_0_to_1cm"], n_days)  # m³/m³

        # ── Date-derived features ─────────────────────────────────────────────
        now       = datetime.now()
        month     = now.month
        day_of_yr = now.timetuple().tm_yday

        return {
            "precipitation":   _last(prec),
            "precip_3day_avg": _mean_tail(prec, 3),
            "precip_7day_avg": _mean_tail(prec, 7),
            "pressure":        _last(pres) * 100.0,   # hPa → Pa
            "temperature":     _last(temp),
            "temp_3day_avg":   _mean_tail(temp, 3),
            "soil_moisture":   _last(soil),
            "soil_3day_avg":   _mean_tail(soil, 3),
            "wind_speed":      _last(wind) / 3.6,     # km/h → m/s
            "humidity":        _last(hum),
            "evaporation":     -abs(_last(evap)) / 1000.0,  # mm → negative m
            "is_monsoon":      float(month in (6, 7, 8, 9, 10)),
            "month":           float(month),
            "day_of_year":     float(day_of_yr),
        }

    except Exception as exc:
        logger.warning("Feature parse failed lat=%.4f lng=%.4f: %s", lat, lng, exc)
        return None


def features_to_vector(features: dict[str, float]) -> np.ndarray:
    """
    Convert features dict → 1-D numpy array in the exact model training order.

    Must match FEATURE_COLS from the training notebook exactly.
    Raises KeyError if any required feature is missing.
    """
    return np.array([features[f] for f in FEATURE_ORDER], dtype=np.float32)
