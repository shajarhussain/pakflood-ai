"""Inspect downloaded Gate B raw datasets without training.

Reports per-file:
- existence
- vector: CRS, bounds, feature count, key property names
- raster: CRS, bounds, width × height, band count, pixel size, NoData
- raster directories: file count, parsed date range, sample CRS / shape
- CSV: required columns present, row count, date range

This script does NOT train, does NOT generate features, does NOT touch the
model artifact, does NOT call any pipeline step. It only reads files on disk
and prints a JSON-friendly summary. argparse and stdlib imports happen at
module top; heavy geospatial imports are deferred inside ``run()`` so
``--help`` works on a fresh environment.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Targets — kept in sync with REQUIRED_FILES in real_data_contract.py
# ---------------------------------------------------------------------------

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{8})")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check_raw_data_shapes",
        description=(
            "Inspect the 8 downloaded Gate B real-data targets and report "
            "their shape / CRS / counts / naming compliance. Read-only — "
            "no training, no synthetic data, no model artifact touched."
        ),
    )
    p.add_argument(
        "--data-root", type=Path, default=Path("data/real/raw"),
        help="Root directory containing the 8 raw subfolders. Default: data/real/raw",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Emit a machine-readable JSON report on stdout instead of pretty text.",
    )
    return p


# ---------------------------------------------------------------------------
# Inspectors — each returns a dict
# ---------------------------------------------------------------------------

def _inspect_vector(path: Path, expected_id_field: Optional[str] = None) -> dict[str, Any]:
    import geopandas as gpd  # deferred
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"read failed: {type(exc).__name__}: {exc}"}
    bounds = tuple(round(float(x), 4) for x in gdf.total_bounds)
    report = {
        "ok": True,
        "format": "vector",
        "feature_count": int(len(gdf)),
        "crs": str(gdf.crs) if gdf.crs is not None else None,
        "crs_is_geographic": bool(gdf.crs and gdf.crs.is_geographic),
        "bounds_minx_miny_maxx_maxy": list(bounds),
        "property_columns": [c for c in gdf.columns if c != "geometry"],
    }
    if expected_id_field:
        report["has_required_id_field"] = expected_id_field in gdf.columns
        report["required_id_field"] = expected_id_field
    return report


def _inspect_single_raster(path: Path) -> dict[str, Any]:
    import rasterio  # deferred
    try:
        with rasterio.open(path) as src:
            bounds = tuple(round(float(x), 4) for x in src.bounds)
            res = src.res
            return {
                "ok": True,
                "format": "raster",
                "crs": str(src.crs) if src.crs else None,
                "width": int(src.width),
                "height": int(src.height),
                "band_count": int(src.count),
                "pixel_size_x_y": [round(float(res[0]), 6), round(float(res[1]), 6)],
                "nodata": src.nodata,
                "bounds_minx_miny_maxx_maxy": list(bounds),
            }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"read failed: {type(exc).__name__}: {exc}"}


def _inspect_raster_dir(dir_path: Path, pattern: str = "*.tif") -> dict[str, Any]:
    files = sorted(dir_path.glob(pattern))
    if not files:
        return {
            "ok": False,
            "format": "raster_dir",
            "pattern": pattern,
            "file_count": 0,
            "error": f"no files matching {pattern} in {dir_path}",
        }

    dates_seen, naming_violations = [], []
    for f in files:
        m = DATE_RE.search(f.name)
        if m:
            raw = m.group(1)
            dates_seen.append(raw if "-" in raw else f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}")
        else:
            naming_violations.append(f.name)

    sample = _inspect_single_raster(files[0])
    return {
        "ok": True,
        "format": "raster_dir",
        "pattern": pattern,
        "file_count": len(files),
        "date_range": [min(dates_seen), max(dates_seen)] if dates_seen else None,
        "files_without_parseable_date": naming_violations[:5],
        "files_without_parseable_date_count": len(naming_violations),
        "sample_file": str(files[0].name),
        "sample_crs": sample.get("crs"),
        "sample_shape_w_h": [sample.get("width"), sample.get("height")] if sample.get("ok") else None,
        "sample_pixel_size": sample.get("pixel_size_x_y"),
    }


def _inspect_csv(path: Path, required_cols: list[str], date_col: Optional[str] = "date") -> dict[str, Any]:
    import pandas as pd  # deferred
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"read failed: {type(exc).__name__}: {exc}"}

    missing = [c for c in required_cols if c not in df.columns]
    report = {
        "ok": len(missing) == 0,
        "format": "csv",
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "missing_required_columns": missing,
        "required_columns": required_cols,
    }
    if date_col and date_col in df.columns:
        try:
            dt = pd.to_datetime(df[date_col], errors="coerce")
            if dt.notna().any():
                report["date_range"] = [str(dt.min().date()), str(dt.max().date())]
        except Exception:  # noqa: BLE001
            pass
    return report


# ---------------------------------------------------------------------------
# Per-target dispatcher
# ---------------------------------------------------------------------------

def inspect_target(key: str, root: Path) -> dict[str, Any]:
    """Inspect one of the 8 contract targets."""
    if key == "boundaries":
        path = root / "boundaries" / "pakistan_districts.geojson"
        if not path.exists():
            return {"key": key, "exists": False, "expected_path": str(path)}
        info = _inspect_vector(path, expected_id_field="district_id")
        return {"key": key, "exists": True, "path": str(path), **info}

    if key == "flood_extents":
        path = root / "flood_extents" / "unosat_flood_extents.geojson"
        if not path.exists():
            return {"key": key, "exists": False, "expected_path": str(path)}
        info = _inspect_vector(path)
        # Look for any plausible event-date property
        props = info.get("property_columns", [])
        candidates = [c for c in props if c.lower() in {"event_date", "observed_at", "date", "obs_date", "image_dat"}]
        info["plausible_event_date_columns"] = candidates
        return {"key": key, "exists": True, "path": str(path), **info}

    if key == "imerg_dir":
        d = root / "rainfall_imerg"
        info = _inspect_raster_dir(d, pattern="*.tif")
        return {"key": key, "exists": info["file_count"] > 0, "path": str(d), **info}

    if key == "chirps_dir":
        d = root / "rainfall_chirps"
        info = _inspect_raster_dir(d, pattern="*.tif")
        return {"key": key, "exists": info["file_count"] > 0, "path": str(d), **info}

    if key == "glofas":
        path = root / "glofas" / "glofas_district_daily.csv"
        if not path.exists():
            return {"key": key, "exists": False, "expected_path": str(path)}
        info = _inspect_csv(
            path,
            required_cols=["district_id", "date", "river_discharge_m3s", "source"],
            date_col="date",
        )
        return {"key": key, "exists": True, "path": str(path), **info}

    if key == "elevation":
        path = root / "elevation" / "dem.tif"
        if not path.exists():
            return {"key": key, "exists": False, "expected_path": str(path)}
        info = _inspect_single_raster(path)
        return {"key": key, "exists": True, "path": str(path), **info}

    if key == "rivers":
        path = root / "rivers" / "hydrorivers_pakistan.geojson"
        if not path.exists():
            return {"key": key, "exists": False, "expected_path": str(path)}
        info = _inspect_vector(path)
        # Cheap sanity check that the file was clipped to Pakistan
        b = info.get("bounds_minx_miny_maxx_maxy")
        if b:
            inside_pak = (60.0 <= b[0] <= 78.0 and 22.0 <= b[1] <= 38.0
                          and 60.0 <= b[2] <= 78.0 and 22.0 <= b[3] <= 38.0)
            info["bounds_look_like_pakistan_clip"] = bool(inside_pak)
        return {"key": key, "exists": True, "path": str(path), **info}

    if key == "population":
        raster = root / "population" / "worldpop_pakistan.tif"
        csv = root / "population" / "district_population_exposure.csv"
        if raster.exists():
            info = _inspect_single_raster(raster)
            return {"key": key, "exists": True, "path": str(raster), "variant": "raster", **info}
        if csv.exists():
            info = _inspect_csv(
                csv,
                required_cols=["district_id", "population_exposure_score", "source"],
                date_col=None,
            )
            return {"key": key, "exists": True, "path": str(csv), "variant": "csv", **info}
        return {
            "key": key, "exists": False,
            "expected_paths": [str(raster), str(csv)],
            "note": "either raster OR pre-aggregated district CSV is acceptable",
        }

    return {"key": key, "exists": False, "error": f"unknown key {key!r}"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ALL_KEYS = [
    "boundaries", "flood_extents", "imerg_dir", "chirps_dir",
    "glofas", "elevation", "rivers", "population",
]


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    # Deferred dep validation — exit cleanly if heavy libs are missing.
    try:
        from ml.training.real_data_contract import validate_dependencies, DependencyMissingError
        try:
            validate_dependencies()
        except DependencyMissingError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    except ModuleNotFoundError:
        # Running outside the project tree — let the imports below raise naturally.
        pass

    root = args.data_root
    if not root.exists():
        print(f"ERROR: --data-root does not exist: {root}", file=sys.stderr)
        return 3

    reports = [inspect_target(k, root) for k in ALL_KEYS]
    overall_ok = all(r.get("exists") and r.get("ok", True) for r in reports)

    if args.json:
        print(json.dumps({"overall_ok": overall_ok, "targets": reports}, indent=2, default=str))
        return 0 if overall_ok else 1

    # Pretty text
    print("PakFlood AI v3 — Gate B raw-data inspection")
    print("=" * 70)
    for r in reports:
        key = r["key"]
        status = "OK  " if r.get("exists") and r.get("ok", True) else "MISS"
        path = r.get("path") or r.get("expected_path") or r.get("expected_paths") or ""
        print(f"[{status}] {key:<14}  {path}")
        if not r.get("exists"):
            continue
        for field in (
            "crs", "crs_is_geographic", "feature_count", "property_columns",
            "has_required_id_field", "plausible_event_date_columns",
            "width", "height", "band_count", "pixel_size_x_y", "nodata",
            "file_count", "date_range", "files_without_parseable_date_count",
            "sample_crs", "sample_pixel_size",
            "row_count", "columns", "missing_required_columns",
            "bounds_minx_miny_maxx_maxy", "bounds_look_like_pakistan_clip",
            "variant",
        ):
            if field in r:
                val = r[field]
                # Keep long arrays compact
                if isinstance(val, list) and len(val) > 8:
                    val = val[:8] + ["…"]
                print(f"        {field:<35} {val}")
        if r.get("error"):
            print(f"        ERROR                               {r['error']}")
        print()

    print(f"OVERALL: {'OK' if overall_ok else 'INCOMPLETE — see above'}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
