"""
Single-point weather fetch for the prediction endpoint.

Wraps the zone adapter (which expects a shared client) with a one-shot
httpx.AsyncClient so callers don't need to manage connection lifecycle.
Raises HTTPException 503 when Open-Meteo is unreachable.
"""

from __future__ import annotations

from fastapi import HTTPException

import httpx

from app.zones.open_meteo_adapter import fetch_weather_features as _fetch


async def fetch_weather_features(lat: float, lng: float) -> dict[str, float]:
    """
    Return the 14 model features for a single lat/lng.

    Raises:
        HTTPException 503 — if Open-Meteo fails or returns no data.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        features = await _fetch(lat, lng, client)

    if features is None:
        raise HTTPException(
            status_code=503,
            detail="Weather API unavailable — could not fetch Open-Meteo data.",
        )

    return features
