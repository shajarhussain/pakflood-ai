from fastapi import APIRouter
from typing import Any

from app.adapters.ffd_adapter import fetch_river_stations

router = APIRouter(prefix="/rivers")


@router.get("", summary="Major Pakistan river discharge stations")
async def get_river_stations() -> list[dict[str, Any]]:
    """Return discharge readings for major FFD monitoring stations.

    Falls back to a static snapshot when the FFD live API is unavailable.
    """
    return await fetch_river_stations()
