"""
Pakistan boundary filter for zone grid points.

Uses the stored GADM country polygon to exclude grid points that fall
outside Pakistan's actual borders (ocean, neighbouring countries, etc.).

Reuses the same pure-Python ray-casting algorithm as district_filter.py.
The boundary is loaded once from the DB and cached in-process for the
duration of a zone computation run.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# In-process cache: loaded once per zone computation run
_cached_geom: Optional[dict] = None


# ── Ray-casting (identical to district_filter.py) ─────────────────────────────

def _point_in_ring(lat: float, lng: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]   # GeoJSON is [lng, lat]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(lat: float, lng: float, geom: dict) -> bool:
    gtype  = geom.get("type")
    coords = geom.get("coordinates", [])

    if gtype == "Polygon":
        return _point_in_ring(lat, lng, coords[0]) if coords else False

    if gtype == "MultiPolygon":
        return any(_point_in_ring(lat, lng, poly[0]) for poly in coords if poly)

    return False


# ── Public API ────────────────────────────────────────────────────────────────

def load_pakistan_boundary() -> Optional[dict]:
    """
    Load the Pakistan boundary geometry from Supabase and cache it in-process.
    Returns None if no boundary has been seeded yet.
    """
    global _cached_geom
    if _cached_geom is not None:
        return _cached_geom

    from app.zones.boundary_repository import BoundaryRepository
    geom_json = BoundaryRepository().get_boundary("PAK")

    if not geom_json:
        logger.warning(
            "Pakistan boundary not found in DB — "
            "run: python scripts/fetch_pakistan_boundary.py"
        )
        return None

    _cached_geom = json.loads(geom_json)
    logger.info("Pakistan boundary loaded from DB (%d chars)", len(geom_json))
    return _cached_geom


def clear_boundary_cache() -> None:
    """Clear the in-process cache so the next call re-reads from DB."""
    global _cached_geom
    _cached_geom = None


def is_inside_pakistan(lat: float, lng: float) -> bool:
    """
    Return True if (lat, lng) falls inside Pakistan's national boundary.

    Falls back to True (allow all points) if no boundary is stored in the DB
    — this preserves existing behaviour when the table is empty.
    """
    geom = load_pakistan_boundary()
    if geom is None:
        return True   # no boundary data → don't filter anything out

    return _point_in_geometry(lat, lng, geom)


def filter_grid_to_pakistan(
    grid: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Filter a list of (lat, lng) grid points to only those inside Pakistan.
    Logs how many points were removed.
    """
    geom = load_pakistan_boundary()
    if geom is None:
        logger.warning("No boundary available — returning full grid unfiltered")
        return grid

    inside = [pt for pt in grid if _point_in_geometry(pt[0], pt[1], geom)]
    removed = len(grid) - len(inside)
    logger.info(
        "Boundary filter: %d/%d grid points inside Pakistan (%d outside removed)",
        len(inside), len(grid), removed,
    )
    return inside
