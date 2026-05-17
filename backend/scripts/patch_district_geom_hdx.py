"""
Patch remaining districts that have no geom_json using geoBoundaries PAK ADM3.

Usage (from backend/ directory):
    python scripts/patch_district_geom_hdx.py

Only updates districts where geom_json IS NULL — safe to re-run.
"""

import json
import sys
from difflib import get_close_matches
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.supabase import get_supabase  # noqa: E402

GEOBOUNDARIES_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/"
    "releaseData/gbOpen/PAK/ADM2/geoBoundaries-PAK-ADM2.geojson"
)

# geoBoundaries ADM2 shapeName (case-insensitive) -> our district name
NAME_OVERRIDES: dict[str, str] = {
    "mandi bahauddin":    "Mandi Bahauddin",
    "lower dir":          "Lower Dir",
    "upper dir":          "Upper Dir",
    "nushki":             "Nushki",
    "astore":             "Astore",
    "ghanche":            "Ghanche",
    "ghizer":             "Ghizer",
    "hunza":              "Hunza",
    "kharmang":           "Kharmang",
    "nagar":              "Nagar",
    "shigar":             "Shigar",
    "skardu":             "Skardu",
    "qambar shahdadkot":  "Kambar Shahdadkot",
    "kambar shahdadkot":  "Kambar Shahdadkot",
    "chiniot":            "Chiniot",
    "sujawal":            "Sujawal",
    "harnai":             "Harnai",
    "sohbatpur":          "Sohbatpur",
    "washuk":             "Washuk",
    "haveli":             "Haveli",
    "hattian bala":       "Hattian Bala",
    "hattian":            "Hattian Bala",
    "lehri":              "Lehri",
    "diamer":             "Diamer",
}


def simplify_geometry(geom: dict, tolerance: float = 0.01) -> dict:
    def rdp(points: list, eps: float) -> list:
        if len(points) <= 2:
            return points
        start, end = points[0], points[-1]
        dx, dy = end[0] - start[0], end[1] - start[1]
        dist_sq = dx * dx + dy * dy
        max_dist, max_idx = 0.0, 0
        for i in range(1, len(points) - 1):
            px, py = points[i]
            if dist_sq == 0:
                d = ((px - start[0]) ** 2 + (py - start[1]) ** 2) ** 0.5
            else:
                t = max(0, min(1, ((px - start[0]) * dx + (py - start[1]) * dy) / dist_sq))
                d = ((px - (start[0] + t * dx)) ** 2 + (py - (start[1] + t * dy)) ** 2) ** 0.5
            if d > max_dist:
                max_dist, max_idx = d, i
        if max_dist > eps:
            return rdp(points[:max_idx + 1], eps)[:-1] + rdp(points[max_idx:], eps)
        return [start, end]

    def simplify_ring(ring):
        s = rdp(ring, tolerance)
        return ring if len(s) < 4 else s

    def simplify_polygon(coords):
        return [simplify_ring(r) for r in coords]

    def simplify_multipolygon(coords):
        return [simplify_polygon(p) for p in coords]

    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": simplify_polygon(geom["coordinates"])}
    if geom["type"] == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": simplify_multipolygon(geom["coordinates"])}
    return geom


def match_name(gb_name: str, our_names: list[str]) -> str | None:
    key = gb_name.lower().strip()
    # Override map (case-insensitive keys)
    if key in NAME_OVERRIDES:
        candidate = NAME_OVERRIDES[key]
        if candidate in our_names:
            return candidate
    # Exact match (case-insensitive)
    our_lower = {n.lower(): n for n in our_names}
    if key in our_lower:
        return our_lower[key]
    # Fuzzy match
    matches = get_close_matches(key, our_lower.keys(), n=1, cutoff=0.80)
    return our_lower[matches[0]] if matches else None


def main() -> None:
    db = get_supabase()

    # ── 1. Find districts still missing geometry ──────────────────────────────
    print("Loading districts missing geometry...")
    all_result  = db.table("districts").select("district_id, name").execute()
    null_result = db.table("districts").select("district_id, name").is_("geom_json", "null").execute()
    name_to_id  = {row["name"]: row["district_id"] for row in (all_result.data or [])}
    missing_ids = {row["district_id"] for row in (null_result.data or [])}
    our_names   = list(name_to_id.keys())
    print(f"  Missing geometry: {len(missing_ids)}")

    if not missing_ids:
        print("All districts already have geometry — nothing to do.")
        return

    # ── 2. Download geoBoundaries PAK ADM3 ───────────────────────────────────
    print(f"Downloading geoBoundaries PAK ADM3...")
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        resp = client.get(GEOBOUNDARIES_URL)
        resp.raise_for_status()
    features = resp.json().get("features", [])
    print(f"  Downloaded {len(features)} features")

    # ── 3. Match to our missing districts ────────────────────────────────────
    updates:   list[dict] = []
    unmatched: list[str]  = []
    seen_ids:  set[str]   = set()

    for feat in features:
        props   = feat.get("properties", {})
        gb_name = props.get("shapeName", "") or props.get("NAME_2", "")
        geom    = feat.get("geometry")

        if not gb_name or not geom:
            continue

        matched = match_name(gb_name, our_names)
        if matched is None:
            continue

        district_id = name_to_id[matched]

        # Only process missing ones; skip duplicates (multiple features → same district)
        if district_id not in missing_ids or district_id in seen_ids:
            continue

        seen_ids.add(district_id)
        simple_geom = simplify_geometry(geom, tolerance=0.01)
        updates.append({
            "district_id": district_id,
            "name":        matched,
            "geom_json":   json.dumps(simple_geom),
        })

    # Report what's still unmatched after processing
    still_missing = missing_ids - seen_ids
    print(f"  Matched: {len(updates)}  |  Still unmatched: {len(still_missing)}")
    if still_missing:
        missing_names = [
            next(n for n, did in name_to_id.items() if did == did_val)
            for did_val in still_missing
        ]
        print(f"  Still missing: {missing_names}")

    # ── 4. Update Supabase ────────────────────────────────────────────────────
    if not updates:
        print("No new matches found.")
        return

    print(f"Patching {len(updates)} districts...")
    for i, row in enumerate(updates, 1):
        db.table("districts").update({"geom_json": row["geom_json"]}).eq("district_id", row["district_id"]).execute()
        if i % 10 == 0 or i == len(updates):
            print(f"  {i}/{len(updates)} patched")

    print(f"Done — {len(updates)} more districts now have geometry.")


if __name__ == "__main__":
    main()
