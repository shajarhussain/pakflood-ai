"""
Current weather endpoint — proxies OpenWeatherMap so the API key stays
server-side and results can be cached/rate-limited centrally.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_OWM_BASE = "https://api.openweathermap.org/data/2.5/weather"

_WIND_DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _compass(deg: float) -> str:
    return _WIND_DIRS[round(deg / 45) % 8]


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., ge=-90,  le=90),
    lng: float = Query(..., ge=-180, le=180),
) -> dict:
    """
    Fetch current weather for a lat/lng from OpenWeatherMap.

    Returns a flat dict ready for the frontend WeatherCard.
    Raises 503 if the key is not configured or OWM is unreachable.
    """
    if not settings.OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENWEATHER_API_KEY is not configured in backend/.env",
        )

    url = (
        f"{_OWM_BASE}"
        f"?lat={lat}&lon={lng}"
        f"&appid={settings.OPENWEATHER_API_KEY}"
        f"&units=metric"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
    except httpx.RequestError as exc:
        logger.error("OWM request failed: %s", exc)
        raise HTTPException(status_code=503, detail="Weather API unreachable")

    if res.status_code == 401:
        raise HTTPException(status_code=503, detail="Invalid OpenWeatherMap API key")
    if res.status_code == 429:
        raise HTTPException(status_code=429, detail="OpenWeatherMap rate limit exceeded")
    if not res.is_success:
        raise HTTPException(status_code=503, detail=f"Weather API error {res.status_code}")

    d = res.json()
    main   = d.get("main", {})
    wind   = d.get("wind", {})
    clouds = d.get("clouds", {})
    weather_list = d.get("weather", [{}])
    sys    = d.get("sys", {})

    wind_speed_ms  = wind.get("speed", 0)
    wind_deg       = wind.get("deg", 0)

    return {
        "location":    d.get("name") or "",
        "country":     sys.get("country") or "",
        "temp":        round(main.get("temp", 0), 1),
        "feels_like":  round(main.get("feels_like", 0), 1),
        "temp_min":    round(main.get("temp_min", 0), 1),
        "temp_max":    round(main.get("temp_max", 0), 1),
        "humidity":    main.get("humidity", 0),
        "pressure":    main.get("pressure", 0),
        "wind_speed":  round(wind_speed_ms * 3.6, 1),   # m/s → km/h
        "wind_deg":    wind_deg,
        "wind_dir":    _compass(wind_deg),
        "weather":     weather_list[0].get("main", ""),
        "description": weather_list[0].get("description", "").title(),
        "icon":        weather_list[0].get("icon", "01d"),
        "clouds":      clouds.get("all", 0),
        "visibility":  round(d.get("visibility", 10000) / 1000, 1),  # m → km
    }
