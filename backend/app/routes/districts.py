"""
District endpoints.

GET /districts/search?q=lahore   — search + instant risk summary for each result
GET /districts/{district_id}     — full detail: boundary GeoJSON + zone points + summary
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.supabase import get_supabase
from app.zones.district_filter import district_zone_summary, filter_points_by_district
from app.zones.zone_geojson import points_to_geojson
from app.zones.zone_repository import ZoneRepository

router = APIRouter(prefix="/districts")
logger = logging.getLogger(__name__)

_BBOX_PAD = 0.5   # degrees padding around district bbox for zone queries


# ── Helpers ───────────────────────────────────────────────────────────────────

def _geom_bbox(geom_json: str) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lng, max_lng) from a GeoJSON geometry string."""
    geom   = json.loads(geom_json)
    coords = geom.get("coordinates", [])
    gtype  = geom.get("type")
    flat   = (
        [pt for poly in coords for ring in poly for pt in ring]
        if gtype == "MultiPolygon"
        else [pt for ring in coords for pt in ring]
    )
    lngs = [p[0] for p in flat]
    lats = [p[1] for p in flat]
    return min(lats), max(lats), min(lngs), max(lngs)


def _district_boundary_feature(district: dict) -> dict | None:
    """Wrap the stored geom_json as a GeoJSON Feature, or None if missing."""
    geom_json = district.get("geom_json")
    if not geom_json:
        return None
    return {
        "type":     "Feature",
        "geometry": json.loads(geom_json),
        "properties": {
            "district_id": district["district_id"],
            "name":        district["name"],
            "province":    district["province"],
        },
    }


async def _zone_summary_for_district(
    repo: ZoneRepository,
    district: dict,
) -> dict:
    """Fetch zone points inside a district and return the summary dict."""
    geom_json = district.get("geom_json")

    if geom_json:
        min_lat, max_lat, min_lng, max_lng = _geom_bbox(geom_json)
    else:
        clat    = district["center_lat"]
        clng    = district["center_lng"]
        min_lat = clat - _BBOX_PAD
        max_lat = clat + _BBOX_PAD
        min_lng = clng - _BBOX_PAD
        max_lng = clng + _BBOX_PAD

    candidates = await asyncio.to_thread(
        repo.get_zone_points_in_bbox,
        min_lat - _BBOX_PAD,
        max_lat + _BBOX_PAD,
        min_lng - _BBOX_PAD,
        max_lng + _BBOX_PAD,
    )

    points = (
        await asyncio.to_thread(filter_points_by_district, candidates, geom_json)
        if geom_json else candidates
    )
    return district_zone_summary(points), points


# ── GET /districts/search ─────────────────────────────────────────────────────

@router.get("/search")
async def search_districts(
    q: str = Query(..., min_length=2, description="District name (partial match)"),
) -> list[dict]:
    """
    Search districts by name.

    Each result includes:
      - district info (id, name, province, center)
      - boundary: GeoJSON Feature with the district polygon (null if not available)
      - summary: flood risk summary from cached zone data (null if no zones computed yet)
    """
    db = get_supabase()
    try:
        result = (
            db.table("districts")
            .select("district_id, name, province, center_lat, center_lng, geom_json")
            .ilike("name", f"%{q}%")
            .limit(10)
            .execute()
        )
    except Exception as exc:
        logger.error("District search failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    rows = result.data or []
    if not rows:
        return []

    repo = ZoneRepository()

    # Fetch risk summaries for all matched districts concurrently
    summaries = await asyncio.gather(
        *[_zone_summary_for_district(repo, r) for r in rows],
        return_exceptions=True,
    )

    output = []
    for district, result in zip(rows, summaries):
        summary, _ = result if not isinstance(result, Exception) else ({}, [])
        output.append({
            "district_id": district["district_id"],
            "name":        district["name"],
            "province":    district["province"],
            "center":      {"lat": district["center_lat"], "lng": district["center_lng"]},
            "boundary":    _district_boundary_feature(district),
            "summary":     summary if summary.get("total_points", 0) > 0 else None,
        })

    return output


# ── GET /districts/{district_id} ──────────────────────────────────────────────

@router.get("/{district_id}")
async def get_district_zones(district_id: str) -> dict:
    """
    Full flood risk data for a district.

    Response:
      district  — id, name, province, center, has_boundary
      boundary  — GeoJSON Feature (Polygon/MultiPolygon) for map highlight layer
      summary   — avg/max flood prob, dominant risk, breakdown by level, point count
      zones     — GeoJSON FeatureCollection of grid points inside the district
                  (all data from DB cache — no live API calls)
    """
    db = get_supabase()

    try:
        result = (
            db.table("districts")
            .select("*")
            .eq("district_id", district_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("District fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not result.data:
        raise HTTPException(status_code=404, detail=f"District '{district_id}' not found.")

    district  = result.data[0]
    geom_json = district.get("geom_json")

    repo  = ZoneRepository()
    batch = await asyncio.to_thread(repo.get_latest_batch)
    fresh = await asyncio.to_thread(repo.is_cache_fresh)

    # ── Bbox pre-filter → exact polygon filter ────────────────────────────────
    if geom_json:
        min_lat, max_lat, min_lng, max_lng = _geom_bbox(geom_json)
    else:
        clat    = district["center_lat"]
        clng    = district["center_lng"]
        min_lat = clat - _BBOX_PAD
        max_lat = clat + _BBOX_PAD
        min_lng = clng - _BBOX_PAD
        max_lng = clng + _BBOX_PAD

    candidates = await asyncio.to_thread(
        repo.get_zone_points_in_bbox,
        min_lat - _BBOX_PAD,
        max_lat + _BBOX_PAD,
        min_lng - _BBOX_PAD,
        max_lng + _BBOX_PAD,
    )

    if geom_json:
        district_points = await asyncio.to_thread(
            filter_points_by_district, candidates, geom_json
        )
    else:
        district_points = candidates
        logger.info(
            "District %s has no geometry — bbox fallback (%d points)",
            district_id, len(district_points),
        )

    summary       = district_zone_summary(district_points)
    computed_at   = batch.get("completed_at") if batch else None
    zones_geojson = points_to_geojson(district_points, computed_at, fresh)

    return {
        "district": {
            "district_id":  district["district_id"],
            "name":         district["name"],
            "province":     district["province"],
            "center":       {"lat": district["center_lat"], "lng": district["center_lng"]},
            "has_boundary": geom_json is not None,
        },
        "boundary": _district_boundary_feature(district),
        "summary":  summary,
        "zones":    zones_geojson,
    }
