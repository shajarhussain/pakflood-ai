"""
Fetch and save Pakistan's national boundary polygon to Supabase.

Usage (from backend/ directory):
    python scripts/fetch_pakistan_boundary.py

Downloads GADM 4.1 level-0 (country boundary) for Pakistan, applies RDP
simplification to reduce size, then upserts into the country_boundaries table.

Run this once to seed the DB. The zone scheduler will re-run it automatically
once the stored boundary is older than 1 year (next_refresh_at has passed).

DB table required (run in Supabase SQL editor first):

    CREATE TABLE IF NOT EXISTS country_boundaries (
        country_code    TEXT PRIMARY KEY,
        country_name    TEXT NOT NULL,
        geom_json       TEXT,
        source          TEXT,
        captured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        next_refresh_at TIMESTAMPTZ
    );
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.supabase import get_supabase  # noqa: E402

GADM_URL      = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PAK_0.json"
COUNTRY_CODE  = "PAK"
COUNTRY_NAME  = "Pakistan"
SOURCE        = "GADM 4.1 ADM0"
RDP_TOLERANCE = 0.02   # degrees — good balance for country-level boundary
REFRESH_YEARS = 1


# ── Pure-Python RDP simplification ───────────────────────────────────────────

def _perp_distance(point, start, end):
    if start == end:
        return ((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2) ** 0.5
    x0, y0 = point
    x1, y1 = start
    x2, y2 = end
    num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    den = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
    return num / den if den else 0.0


def _rdp(points, tolerance):
    if len(points) < 3:
        return points
    start, end = points[0], points[-1]
    max_dist, max_idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _perp_distance(points[i], start, end)
        if d > max_dist:
            max_dist, max_idx = d, i
    if max_dist > tolerance:
        left  = _rdp(points[:max_idx + 1], tolerance)
        right = _rdp(points[max_idx:], tolerance)
        return left[:-1] + right
    return [start, end]


def simplify_geometry(geom: dict, tolerance: float) -> dict:
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])

    if gtype == "Polygon":
        simplified = [_rdp(ring, tolerance) for ring in coords]
        return {"type": "Polygon", "coordinates": simplified}

    if gtype == "MultiPolygon":
        simplified = [
            [_rdp(ring, tolerance) for ring in poly]
            for poly in coords
        ]
        return {"type": "MultiPolygon", "coordinates": simplified}

    return geom


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Downloading Pakistan boundary from GADM 4.1…")
    print(f"  URL: {GADM_URL}")

    with httpx.Client(timeout=60.0) as client:
        resp = client.get(GADM_URL)
        resp.raise_for_status()

    data     = resp.json()
    features = data.get("features", [])

    if not features:
        print("ERROR: No features found in GADM response.")
        sys.exit(1)

    # GADM ADM0 for Pakistan is a single feature
    feature = features[0]
    geom    = feature.get("geometry", {})

    print(f"  Geometry type : {geom.get('type')}")

    # Count coordinates before simplification
    def count_coords(g):
        t = g.get("type")
        c = g.get("coordinates", [])
        if t == "Polygon":
            return sum(len(r) for r in c)
        if t == "MultiPolygon":
            return sum(len(r) for p in c for r in p)
        return 0

    before = count_coords(geom)
    geom_simplified = simplify_geometry(geom, RDP_TOLERANCE)
    after  = count_coords(geom_simplified)

    print(f"  Coordinates   : {before} -> {after} after RDP (tolerance={RDP_TOLERANCE} deg)")

    geom_str = json.dumps(geom_simplified)
    size_kb  = len(geom_str.encode()) / 1024
    print(f"  Stored size   : {size_kb:.1f} KB")

    now             = datetime.now(timezone.utc)
    next_refresh_at = (now + timedelta(days=365 * REFRESH_YEARS)).isoformat()

    db = get_supabase()
    db.table("country_boundaries").upsert({
        "country_code":    COUNTRY_CODE,
        "country_name":    COUNTRY_NAME,
        "geom_json":       geom_str,
        "source":          SOURCE,
        "captured_at":     now.isoformat(),
        "next_refresh_at": next_refresh_at,
    }, on_conflict="country_code").execute()

    print(f"\nSaved to country_boundaries table.")
    print(f"  country_code    : {COUNTRY_CODE}")
    print(f"  captured_at     : {now.isoformat()}")
    print(f"  next_refresh_at : {next_refresh_at}")
    print("\nDone.")


if __name__ == "__main__":
    main()
