"""
Patch district geom_json from GADM 4.1 Pakistan level-2 GeoJSON.

Usage (from backend/ directory):
    python scripts/patch_district_geom.py

Downloads ~200-300 KB from GADM, matches features to our district rows by
name, simplifies geometries, then upserts geom_json into Supabase.
Safe to re-run — uses upsert on district_id.
"""

import json
import sys
from difflib import get_close_matches
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.supabase import get_supabase  # noqa: E402

GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PAK_3.json"

# Manual overrides for names that differ between GADM and our seed data
NAME_OVERRIDES: dict[str, str] = {
    # GADM name -> our district name
    "Dera Ghazi Khan":        "Dera Ghazi Khan",
    "Rahim Yar Khan":         "Rahim Yar Khan",
    "Toba Tek Singh":         "Toba Tek Singh",
    "Mandi Bahauddin":        "Mandi Bahauddin",
    "Nankana Sahib":          "Nankana Sahib",
    "Kambar Shahdadkot":      "Kambar Shahdadkot",
    "Qambar Shahdadkot":      "Kambar Shahdadkot",
    "Shaheed Benazirabad":    "Shaheed Benazirabad",
    "NawabShah":              "Shaheed Benazirabad",
    "Nawab Shah":             "Shaheed Benazirabad",
    "Naushahro Feroze":       "Naushahro Feroze",
    "Tando Allahyar":         "Tando Allahyar",
    "Tando Muhammad Khan":    "Tando Muhammad Khan",
    "TandoM.Khan":            "Tando Muhammad Khan",
    "Mithi":                  "Tharparkar",
    "Dera Ismail Khan":       "Dera Ismail Khan",
    "Lakki Marwat":           "Lakki Marwat",
    "North Waziristan":       "North Waziristan",
    "South Waziristan":       "South Waziristan",
    "Lower Dir":              "Lower Dir",
    "Upper Dir":              "Upper Dir",
    "Killa Abdullah":         "Killa Abdullah",
    "Killa Saifullah":        "Killa Saifullah",
    "Dera Bugti":             "Dera Bugti",
    "Jhal Magsi":             "Jhal Magsi",
    "Bolan":                  "Kachhi",
    "LarghaShirani":          "Sherani",
    "Largha Shirani":         "Sherani",
    "Chilas":                 "Diamer",
    "Muzaffarabad":           "Muzaffarabad",
    "Hattian Bala":           "Hattian Bala",
    "Bagh":                   "Bagh",
    "Karachi":                "Karachi",
    "KarachiCentral":         "Karachi",
    "KarachiSouth":           "Karachi",
    "Islamabad":              "Islamabad",
    "Astore":                 "Astore",
    "Ghanche":                "Ghanche",
    "Ghizer":                 "Ghizer",
    "Gilgit":                 "Gilgit",
    "Hunza":                  "Hunza",
    "Nagar":                  "Nagar",
    "Skardu":                 "Skardu",
    "Sujawal":                "Sujawal",
    "Chiniot":                "Chiniot",
    "Harnai":                 "Harnai",
    "Nushki":                 "Nushki",
    "Washuk":                 "Washuk",
    "Sohbatpur":              "Sohbatpur",
    "Lehri":                  "Lehri",
    "Haveli":                 "Haveli",
}


def simplify_geometry(geom: dict, tolerance: float = 0.01) -> dict:
    """
    Reduce coordinate count by removing points closer than `tolerance` degrees.
    Pure Python — no shapely required.
    Tolerance 0.01° ≈ 1 km, good enough for district-level map display.
    """
    def rdp(points: list, eps: float) -> list:
        if len(points) <= 2:
            return points
        # Find point with max distance from line start→end
        start, end = points[0], points[-1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
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
            left  = rdp(points[:max_idx + 1], eps)
            right = rdp(points[max_idx:], eps)
            return left[:-1] + right
        return [start, end]

    def simplify_ring(ring: list) -> list:
        simplified = rdp(ring, tolerance)
        if len(simplified) < 4:
            return ring  # keep original if too small after simplification
        return simplified

    def simplify_polygon(coords: list) -> list:
        return [simplify_ring(ring) for ring in coords]

    def simplify_multipolygon(coords: list) -> list:
        return [simplify_polygon(poly) for poly in coords]

    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": simplify_polygon(geom["coordinates"])}
    if geom["type"] == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": simplify_multipolygon(geom["coordinates"])}
    return geom


def match_name(gadm_name: str, our_names: list[str]) -> str | None:
    """Return the best matching district name from our seed data."""
    # Check manual overrides first
    if gadm_name in NAME_OVERRIDES:
        candidate = NAME_OVERRIDES[gadm_name]
        if candidate in our_names:
            return candidate

    # Exact match
    if gadm_name in our_names:
        return gadm_name

    # Fuzzy match (cutoff 0.75)
    matches = get_close_matches(gadm_name, our_names, n=1, cutoff=0.75)
    return matches[0] if matches else None


def main() -> None:
    db = get_supabase()

    # ── 1. Load existing districts from DB (only those missing geometry) ────────
    print("Loading districts from Supabase...")
    all_result   = db.table("districts").select("district_id, name").execute()
    null_result  = db.table("districts").select("district_id, name").is_("geom_json", "null").execute()
    all_rows     = all_result.data or []
    null_rows    = null_result.data or []
    name_to_id: dict[str, str] = {row["name"]: row["district_id"] for row in all_rows}
    # Only try to fill the ones still missing geometry
    missing_ids  = {row["district_id"] for row in null_rows}
    our_names    = list(name_to_id.keys())
    print(f"  Total districts: {len(all_rows)}  |  Missing geometry: {len(null_rows)}")

    # ── 2. Download GADM GeoJSON ──────────────────────────────────────────────
    print(f"Downloading GADM GeoJSON from {GADM_URL} ...")
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(GADM_URL)
        resp.raise_for_status()
    gadm = resp.json()
    features = gadm.get("features", [])
    print(f"  Downloaded {len(features)} GADM features")

    # ── 3. Match and collect updates ──────────────────────────────────────────
    updates:   list[dict] = []
    unmatched: list[str]  = []

    for feat in features:
        props     = feat.get("properties", {})
        gadm_name = props.get("NAME_3", "") or props.get("NAME_2", "")
        geom      = feat.get("geometry")

        if not gadm_name or not geom:
            continue

        matched = match_name(gadm_name, our_names)
        if matched is None:
            unmatched.append(gadm_name)
            continue

        district_id  = name_to_id[matched]

        # Skip if already has geometry
        if district_id not in missing_ids:
            continue
        simple_geom  = simplify_geometry(geom, tolerance=0.01)
        geom_json_str = json.dumps(simple_geom)

        updates.append({
            "district_id": district_id,
            "geom_json":   geom_json_str,
        })

    print(f"  Matched: {len(updates)}  |  Unmatched: {len(unmatched)}")
    if unmatched:
        print(f"  Unmatched GADM names: {unmatched}")

    # ── 4. Update each row individually (rows already exist from seed) ─────────
    print("Patching geom_json in Supabase...")
    patched = 0
    for row in updates:
        db.table("districts").update({"geom_json": row["geom_json"]}).eq("district_id", row["district_id"]).execute()
        patched += 1
        if patched % 20 == 0 or patched == len(updates):
            print(f"  {patched}/{len(updates)} patched")

    print(f"Done — {patched} district geometries updated.")


if __name__ == "__main__":
    main()
