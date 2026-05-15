"""Gate B-Lite: download real public-API data for model training.

Sources (all public, no auth):
  - geoBoundaries: Pakistan ADM2 boundaries (GeoJSON)
  - NASA POWER Daily API: daily rainfall/T2M/RH2M/WS10M per district centroid
  - NASA EONET v3 events: geocoded flood events for weak labels
    (ReliefWeb's v1 API is now HTTP 410 Gone, v2 needs auth — EONET v3 is
    the live, no-auth public alternative).

Outputs:
  - data/real_lite/raw/boundaries/pakistan_districts.geojson
  - data/real_lite/raw/weather/{district_id}.csv  (one per district)
  - data/real_lite/raw/reports/eonet_floods.json

No synthetic data. No mock fallback. Fails loudly if a source is unreachable.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Optional


# 10 MVP district centroids (lat, lon) — keeps the API call count to 10
DISTRICT_CENTROIDS: dict[str, tuple[str, str, float, float]] = {
    "PK-SD-SKR": ("Sukkur",     "Sindh",        27.70, 68.85),
    "PK-SD-JCB": ("Jacobabad",  "Sindh",        28.45, 68.35),
    "PK-SD-LRK": ("Larkana",    "Sindh",        27.45, 67.90),
    "PK-PB-MUL": ("Multan",     "Punjab",       30.30, 71.55),
    "PK-PB-RWP": ("Rawalpindi", "Punjab",       33.65, 73.05),
    "PK-PB-LHR": ("Lahore",     "Punjab",       31.55, 74.40),
    "PK-KP-PSH": ("Peshawar",   "KPK",          34.10, 71.70),
    "PK-BL-QTA": ("Quetta",     "Balochistan",  30.20, 67.05),
    "PK-BL-NAS": ("Naseerabad", "Balochistan",  28.85, 68.15),
    "PK-GB-GIL": ("Gilgit",     "Gilgit-Baltistan", 36.00, 74.20),
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="download_real_lite_sources",
        description=(
            "Download real public-API data for Gate B-Lite training. "
            "geoBoundaries ADM2, NASA POWER daily, ReliefWeb Pakistan flood reports."
        ),
    )
    p.add_argument("--start-date", default="2015-01-01")
    p.add_argument("--end-date",   default="2024-12-31")
    p.add_argument("--out-root",   type=Path, default=Path("data/real_lite/raw"))
    p.add_argument("--max-reports", type=int, default=1000,
                   help="Max ReliefWeb reports to fetch (paginated, default 1000)")
    p.add_argument("--force", action="store_true",
                   help="Re-download even if target file exists")
    return p


def _http_get(url: str, accept: str = "application/json", timeout: int = 60) -> bytes:
    """Plain stdlib GET so the script runs anywhere with Python ≥ 3.11."""
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "pakflood-ai/v3-lite"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------------------
# 1. geoBoundaries — Pakistan ADM2
# ---------------------------------------------------------------------------

def fetch_boundaries(out_path: Path, force: bool) -> dict:
    if out_path.exists() and not force:
        return {"ok": True, "path": str(out_path), "cached": True}
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta_url = "https://www.geoboundaries.org/api/current/gbOpen/PAK/ADM2/"
    meta = json.loads(_http_get(meta_url))
    gj_url = meta.get("gjDownloadURL") or meta.get("downloadURL")
    if not gj_url:
        raise RuntimeError(f"geoBoundaries response missing gjDownloadURL: {meta}")
    raw = _http_get(gj_url)
    fc = json.loads(raw)
    if fc.get("type") != "FeatureCollection":
        raise RuntimeError(f"geoBoundaries returned non-FeatureCollection: {fc.get('type')}")

    # Normalise property names so downstream sees `district_id` and `name`
    for feat in fc.get("features", []):
        props = feat.setdefault("properties", {})
        if "district_id" not in props:
            props["district_id"] = (
                props.get("shapeID") or props.get("shapeISO")
                or props.get("ADM2_PCODE") or props.get("PCODE")
            )
        if "name" not in props:
            props["name"] = props.get("shapeName") or props.get("ADM2_EN")
        props.setdefault("province", props.get("shapeGroup") or "")

    out_path.write_text(json.dumps(fc))
    return {
        "ok": True, "path": str(out_path),
        "feature_count": len(fc.get("features", [])),
        "source_meta_url": meta_url,
        "source_geojson_url": gj_url,
    }


# ---------------------------------------------------------------------------
# 2. NASA POWER Daily API
# ---------------------------------------------------------------------------

POWER_PARAMS = "PRECTOTCORR,T2M,RH2M,WS10M"


def fetch_weather_for_district(
    district_id: str, name: str, province: str,
    lat: float, lon: float,
    start_date: str, end_date: str,
    out_dir: Path, force: bool,
) -> dict:
    csv_path = out_dir / f"{district_id}.csv"
    if csv_path.exists() and not force:
        return {"ok": True, "district_id": district_id, "path": str(csv_path), "cached": True}

    s = start_date.replace("-", "")
    e = end_date.replace("-", "")
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={POWER_PARAMS}&community=AG"
        f"&longitude={lon}&latitude={lat}"
        f"&start={s}&end={e}&format=JSON"
    )
    payload = json.loads(_http_get(url, timeout=120))
    params = payload.get("properties", {}).get("parameter", {})
    if not params:
        raise RuntimeError(f"NASA POWER returned no parameters for {district_id}: {payload}")

    precip = params.get("PRECTOTCORR", {})
    temp   = params.get("T2M", {})
    rh     = params.get("RH2M", {})
    wind   = params.get("WS10M", {})

    dates = sorted(precip.keys())
    rows = ["date,district_id,district_name,province,rainfall_mm,temperature_c,humidity_pct,wind_speed_ms"]
    for d in dates:
        iso = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
        rows.append(",".join([
            iso, district_id, name, province,
            str(precip.get(d, "")), str(temp.get(d, "")),
            str(rh.get(d, "")), str(wind.get(d, "")),
        ]))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {
        "ok": True, "district_id": district_id, "path": str(csv_path),
        "rows": len(dates), "source_url": url,
    }


# ---------------------------------------------------------------------------
# 3. ReliefWeb Pakistan flood reports
# ---------------------------------------------------------------------------

PAK_BBOX = (60.0, 22.0, 78.0, 38.0)  # (min_lon, min_lat, max_lon, max_lat)


def _point_in_pakistan(lon: float, lat: float) -> bool:
    return (PAK_BBOX[0] <= lon <= PAK_BBOX[2]
            and PAK_BBOX[1] <= lat <= PAK_BBOX[3])


def fetch_eonet_flood_events(
    _start_date: str, _end_date: str, out_path: Path, force: bool,
) -> dict:
    """Pull geocoded flood events from NASA EONET v3.

    Each event has 1..N geometry entries with (date, lat, lon). We keep only
    those that fall inside the Pakistan bounding box. The result is later
    matched to the nearest district centroid by the dataset builder.
    """
    if out_path.exists() and not force:
        return {"ok": True, "path": str(out_path), "cached": True}
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Pakistan flood coverage in EONET is concentrated in 2025-2026. Do NOT
    # apply a date filter — pull the full available history and let the
    # downstream bbox filter keep only Pakistan-area events.
    url = (
        "https://eonet.gsfc.nasa.gov/api/v3/events"
        "?category=floods"
        "&status=all"
        "&limit=2000"
    )
    payload = json.loads(_http_get(url, timeout=120))
    raw_events = payload.get("events", [])

    pak_events: list[dict] = []
    for ev in raw_events:
        kept_geoms = []
        for g in ev.get("geometry", []):
            coords = g.get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lon, lat = float(coords[0]), float(coords[1])
            if _point_in_pakistan(lon, lat):
                kept_geoms.append({
                    "date": g.get("date"),
                    "lon": lon,
                    "lat": lat,
                    "type": g.get("type"),
                    "magnitudeValue": g.get("magnitudeValue"),
                    "magnitudeUnit": g.get("magnitudeUnit"),
                })
        if kept_geoms:
            pak_events.append({
                "id": ev.get("id"),
                "title": ev.get("title"),
                "description": ev.get("description"),
                "closed": ev.get("closed"),
                "sources": [s.get("url") for s in (ev.get("sources") or [])],
                "geometry": kept_geoms,
            })

    out_path.write_text(json.dumps({
        "source": "NASA EONET v3",
        "source_url": url,
        "total_events_returned": len(raw_events),
        "pakistan_events": len(pak_events),
        "events": pak_events,
    }, indent=2))
    return {
        "ok": True, "path": str(out_path),
        "total_events_returned": len(raw_events),
        "pakistan_events": len(pak_events),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    args.out_root.mkdir(parents=True, exist_ok=True)
    boundaries_path = args.out_root / "boundaries" / "pakistan_districts.geojson"
    weather_dir     = args.out_root / "weather"
    reports_path    = args.out_root / "reports" / "eonet_floods.json"

    report = {"sources": {}}

    print(f"[lite-dl] geoBoundaries → {boundaries_path}", flush=True)
    try:
        report["sources"]["boundaries"] = fetch_boundaries(boundaries_path, args.force)
    except Exception as exc:
        print(f"  ! geoBoundaries failed: {exc}", file=sys.stderr)
        report["sources"]["boundaries"] = {"ok": False, "error": str(exc)}

    print(f"[lite-dl] NASA POWER weather for {len(DISTRICT_CENTROIDS)} districts "
          f"{args.start_date} → {args.end_date}", flush=True)
    weather_reports = []
    for district_id, (name, province, lat, lon) in DISTRICT_CENTROIDS.items():
        try:
            r = fetch_weather_for_district(
                district_id, name, province, lat, lon,
                args.start_date, args.end_date, weather_dir, args.force,
            )
            print(f"  ✓ {district_id} rows={r.get('rows', 'cached')}", flush=True)
            weather_reports.append(r)
        except Exception as exc:
            print(f"  ! {district_id} weather failed: {exc}", file=sys.stderr)
            weather_reports.append({"ok": False, "district_id": district_id, "error": str(exc)})
    report["sources"]["weather"] = weather_reports

    print(f"[lite-dl] NASA EONET v3 Pakistan flood events → {reports_path}", flush=True)
    try:
        report["sources"]["events"] = fetch_eonet_flood_events(
            args.start_date, args.end_date, reports_path, args.force,
        )
    except Exception as exc:
        print(f"  ! EONET failed: {exc}", file=sys.stderr)
        report["sources"]["events"] = {"ok": False, "error": str(exc)}

    # Persist a summary alongside the data
    (args.out_root / "_lite_download_summary.json").write_text(json.dumps(report, indent=2))

    ok = all(
        (s.get("ok") if isinstance(s, dict) else all(x.get("ok") for x in s))
        for s in report["sources"].values()
    )
    print(f"[lite-dl] OVERALL OK={ok}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
