"""Validate Phase 10 dataset files actually exist and are readable.

Writes ``data/real_dataset/reports/file_validation_report.json`` and exits
non-zero if fewer than 4 families pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="check_real_dataset_files")
    p.add_argument("--root", type=Path, default=Path("data/real_dataset/raw"))
    p.add_argument("--report", type=Path,
                   default=Path("data/real_dataset/reports/file_validation_report.json"))
    return p


def _inspect_vector(path: Path) -> dict:
    import geopandas as gpd
    gdf = gpd.read_file(path)
    b = [float(x) for x in gdf.total_bounds]
    in_pak_bbox = (60.0 <= b[0] <= 78.0 and 22.0 <= b[1] <= 38.0
                   and 60.0 <= b[2] <= 78.0 and 22.0 <= b[3] <= 38.0)
    return {
        "ok": True, "kind": "vector",
        "feature_count": int(len(gdf)),
        "crs": str(gdf.crs) if gdf.crs else None,
        "bounds": [round(v, 3) for v in b],
        "bounds_overlaps_pakistan": bool(60 <= b[2] and 60 <= 78 and b[0] <= 78 and b[1] <= 38 and 22 <= b[3]),
        "bounds_subset_of_pakistan": bool(in_pak_bbox),
    }


def _inspect_raster(path: Path) -> dict:
    import rasterio
    with rasterio.open(path) as src:
        b = [float(v) for v in src.bounds]
        return {
            "ok": True, "kind": "raster",
            "crs": str(src.crs) if src.crs else None,
            "width": int(src.width), "height": int(src.height),
            "band_count": int(src.count),
            "pixel_size": [round(float(src.res[0]), 5), round(float(src.res[1]), 5)],
            "bounds": [round(v, 3) for v in b],
            "size_mb": round(path.stat().st_size / 1e6, 2),
        }


def _inspect_raster_dir(path: Path) -> dict:
    files = sorted(path.glob("*.tif"))
    if not files:
        return {"ok": False, "kind": "raster_dir", "file_count": 0}
    sample = _inspect_raster(files[0])
    return {
        "ok": True, "kind": "raster_dir",
        "file_count": len(files),
        "total_size_mb": round(sum(f.stat().st_size for f in files) / 1e6, 2),
        "sample_file": files[0].name,
        "sample_crs": sample["crs"],
        "sample_shape": [sample["width"], sample["height"]],
    }


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.root.exists():
        print(f"ERROR: missing root {args.root}", file=sys.stderr); return 2

    families = [
        ("boundaries",  args.root / "boundaries" / "pakistan_districts.geojson",   "vector"),
        ("chirps_dir",  args.root / "rainfall_chirps",                              "raster_dir"),
        ("hydrorivers", args.root / "rivers" / "hydrorivers_pakistan.geojson",     "vector"),
        ("elevation",   args.root / "elevation" / "dem.tif",                       "raster"),
        ("population",  args.root / "population" / "worldpop_pakistan.tif",        "raster"),
        ("flood_extents", args.root / "flood_extents" / "unosat_flood_extents.geojson", "vector"),
        ("glofas",      args.root / "glofas" / "glofas_district_daily.csv",        "csv"),
        ("imerg_dir",   args.root / "rainfall_imerg",                              "raster_dir"),
    ]
    report = {"families": []}
    for key, path, kind in families:
        if not path.exists():
            report["families"].append({"family": key, "ok": False, "path": str(path),
                                       "reason": "missing"})
            continue
        try:
            if kind == "vector":     info = _inspect_vector(path)
            elif kind == "raster":   info = _inspect_raster(path)
            elif kind == "raster_dir": info = _inspect_raster_dir(path)
            else:                    info = {"ok": path.stat().st_size > 0, "kind": "csv"}
            report["families"].append({"family": key, "path": str(path), **info})
        except Exception as exc:  # noqa: BLE001
            report["families"].append({"family": key, "ok": False, "path": str(path),
                                       "reason": f"{type(exc).__name__}: {exc}"})

    valid = [f for f in report["families"] if f.get("ok")]
    report["summary"] = {
        "valid_count": len(valid),
        "valid_families": [f["family"] for f in valid],
        "meets_4_family_gate": len(valid) >= 4,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2))

    print(f"[check] {len(valid)} family(ies) valid: {report['summary']['valid_families']}")
    print(f"[check] report → {args.report}")
    return 0 if len(valid) >= 4 else 1


if __name__ == "__main__":
    raise SystemExit(run())
