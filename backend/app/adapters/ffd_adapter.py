"""
Federal Flood Division (FFD) adapter.

Primary: attempts to scrape/call the FFD live discharge API.
Fallback: returns static data from backend/data/river_stations.json when
          the live source is unavailable or returns bad data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_STATIC_PATH = Path(__file__).parent.parent.parent / "data" / "river_stations.json"

# FFD does not publish a stable JSON API; this stub targets the most likely
# endpoint pattern. Update when FFD releases an official API.
_FFD_BASE = "https://ffd.gov.pk/api"
_TIMEOUT  = 6.0


def _load_static() -> list[dict[str, Any]]:
    try:
        return json.loads(_STATIC_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load static river stations fallback")
        return []


async def fetch_river_stations() -> list[dict[str, Any]]:
    """Return discharge data for all major river stations.

    Tries the FFD live API first; falls back to the bundled static snapshot
    if the request fails or the response is malformed.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_FFD_BASE}/discharge/current")
            resp.raise_for_status()
            data = resp.json()
            stations: list[dict[str, Any]] = data if isinstance(data, list) else data.get("stations", [])
            if stations:
                logger.info("FFD live data: %d stations", len(stations))
                return stations
    except Exception as exc:
        logger.warning("FFD live fetch failed (%s), using static fallback", exc)

    return _load_static()
