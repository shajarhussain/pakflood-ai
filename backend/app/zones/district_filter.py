"""
Point-in-polygon filter for zone grid points.

Pure Python ray-casting — no shapely needed.
Handles both Polygon and MultiPolygon geom_json from the districts table.
"""

from __future__ import annotations

import json


def _point_in_ring(lat: float, lng: float, ring: list) -> bool:
    """Ray-casting algorithm for a single polygon ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]   # [lng, lat] per GeoJSON
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lat: float, lng: float, geom: dict) -> bool:
    """
    Test whether (lat, lng) falls inside a GeoJSON Polygon or MultiPolygon.
    Uses the outer ring only (ignores holes — good enough for district level).
    """
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])

    if gtype == "Polygon":
        return _point_in_ring(lat, lng, coords[0]) if coords else False

    if gtype == "MultiPolygon":
        return any(
            _point_in_ring(lat, lng, poly[0])
            for poly in coords
            if poly
        )

    return False


def filter_points_by_district(
    points: list[dict],
    geom_json: str | None,
) -> list[dict]:
    """
    Return only the zone points that fall inside the district polygon.

    Falls back to bounding-box pre-filter before the expensive ray-cast
    so large datasets stay fast.

    Args:
        points:    All zone_grid_points rows from ZoneRepository.
        geom_json: JSON string of the district's GeoJSON geometry (Polygon /
                   MultiPolygon).  Returns all points unchanged if None.
    """
    if not geom_json:
        return points

    geom = json.loads(geom_json)

    # ── Bounding-box pre-filter ───────────────────────────────────────────────
    coords = geom.get("coordinates", [])
    gtype  = geom.get("type")

    def _all_coords(c, depth=0):
        if depth == 0 and gtype == "Polygon":
            return [pt for ring in c for pt in ring]
        if depth == 0 and gtype == "MultiPolygon":
            return [pt for poly in c for ring in poly for pt in ring]
        return []

    flat = _all_coords(coords)
    if not flat:
        return points

    lngs = [p[0] for p in flat]
    lats = [p[1] for p in flat]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    # Add small buffer (0.05°≈5km) so points just outside bbox aren't missed
    buf = 0.05
    candidates = [
        p for p in points
        if (min_lat - buf) <= p["lat"] <= (max_lat + buf)
        and (min_lng - buf) <= p["lng"] <= (max_lng + buf)
    ]

    # ── Exact point-in-polygon ────────────────────────────────────────────────
    return [p for p in candidates if _point_in_polygon(p["lat"], p["lng"], geom)]


def district_zone_summary(points: list[dict]) -> dict:
    """Aggregate zone points into a district-level risk summary."""
    if not points:
        return {
            "total_points":    0,
            "avg_flood_prob":  None,
            "max_flood_prob":  None,
            "dominant_risk":   None,
            "risk_breakdown":  {"Low": 0, "Moderate": 0, "High": 0, "Severe": 0},
            "computed_at":     None,
        }

    probs     = [p["flood_prob"] for p in points if p.get("flood_prob") is not None]
    breakdown: dict[str, int] = {"Low": 0, "Moderate": 0, "High": 0, "Severe": 0}
    for p in points:
        lvl = p.get("risk_level", "Low")
        breakdown[lvl] = breakdown.get(lvl, 0) + 1

    # Dominant = highest-count level; tie-break by severity
    order    = ["Severe", "High", "Moderate", "Low"]
    dominant = max(order, key=lambda lvl: (breakdown.get(lvl, 0), -order.index(lvl)))

    computed_at = max(
        (p["computed_at"] for p in points if p.get("computed_at")),
        default=None,
    )

    return {
        "total_points":   len(points),
        "avg_flood_prob": round(sum(probs) / len(probs), 4) if probs else None,
        "max_flood_prob": round(max(probs), 4) if probs else None,
        "dominant_risk":  dominant,
        "risk_breakdown": breakdown,
        "computed_at":    str(computed_at) if computed_at else None,
    }
