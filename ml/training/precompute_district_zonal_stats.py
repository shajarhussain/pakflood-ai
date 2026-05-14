"""Pre-aggregate raster data to a district-day feature store (PakFlood AI v3).

STRICT POLICY — real data only. Reads daily IMERG and CHIRPS GeoTIFFs plus a
single DEM (and optional WorldPop raster) and produces one parquet keyed by
(district_id, date) with mean/max/valid-pixel-count statistics. Slope is
either taken from --slope-raster or derived on-the-fly from the DEM.

Per the v3 universal CLI rule, argparse runs FIRST. Heavy geospatial imports
are deferred inside ``run()`` so ``--help`` works on a fresh environment with
no geopandas/rasterio/rasterstats installed.

Output schema:
    district_id, district_name, province, date,
    imerg_rainfall_mean_mm, imerg_rainfall_max_mm, imerg_valid_pixel_count,
    chirps_rainfall_mean_mm, chirps_rainfall_max_mm, chirps_valid_pixel_count,
    elevation_mean_m, elevation_max_m, slope_mean_deg, slope_max_deg,
    population_exposure_score, source_raster, source_type

Parallelism via joblib.Parallel(n_jobs=-1 by default). Each (raster, date) is
an independent job. Failures recorded to data/real/reports/zonal_stats_failures.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

# Module-top imports MUST be stdlib only so --help works on a fresh env.
# Heavy imports (geopandas, rasterio, rasterstats, joblib, numpy, pandas,
# pyarrow, shapely) happen inside run().


REQUIRED_CONTRACT_KEYS = ["boundaries", "imerg_dir", "chirps_dir", "elevation", "population"]
DATE_REGEX = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{8})")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="precompute_district_zonal_stats",
        description=(
            "Pre-aggregate raster IMERG/CHIRPS/DEM/population to a district-day "
            "parquet feature store via parallel zonal statistics. Real data only."
        ),
    )
    p.add_argument("--boundaries", required=True, type=Path, help="District polygons (GeoJSON)")
    p.add_argument("--imerg-dir", required=True, type=Path, help="Directory of daily IMERG GeoTIFFs")
    p.add_argument("--chirps-dir", required=True, type=Path, help="Directory of daily CHIRPS GeoTIFFs")
    p.add_argument("--elevation", required=True, type=Path, help="Single-file DEM GeoTIFF")
    p.add_argument("--slope-raster", type=Path, default=None,
                   help="Optional pre-computed slope raster (degrees). If absent, slope is derived from DEM via numpy gradient.")
    p.add_argument("--population", required=True, type=Path,
                   help="WorldPop raster OR pre-aggregated district CSV (district_id, population_exposure_score)")
    p.add_argument("--output", required=True, type=Path, help="Output parquet path")
    p.add_argument("--n-jobs", type=int, default=-1, help="joblib parallel workers (-1 = all cores)")
    p.add_argument("--allow-partial", action="store_true",
                   help="Continue even if some rasters fail (default: refuse).")
    p.add_argument("--cache-dir", type=Path, default=Path("data/real/processed/_cache_zonal"),
                   help="Per-raster cache directory")
    p.add_argument("--failure-report", type=Path,
                   default=Path("data/real/reports/zonal_stats_failures.json"))
    return p


def _parse_date_from_filename(name: str) -> Optional[str]:
    m = DATE_REGEX.search(name)
    if not m:
        return None
    raw = m.group(1)
    if "-" in raw:
        return raw
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def _file_hash(path: Path) -> str:
    return hashlib.sha1(f"{path.name}:{path.stat().st_size}".encode()).hexdigest()[:12]


def _process_one_raster(raster_path_str: str,
                        source_type: str,
                        boundaries_geojson_str: str,
                        cache_dir_str: str):
    """Worker — runs in a separate process. Imports heavy libs locally."""
    import geopandas as gpd  # noqa: F401  (validated upstream)
    import pandas as pd
    from rasterstats import zonal_stats

    raster_path = Path(raster_path_str)
    cache_dir = Path(cache_dir_str)
    cache_dir.mkdir(parents=True, exist_ok=True)

    date_str = _parse_date_from_filename(raster_path.name)
    if date_str is None:
        return {"ok": False, "raster": str(raster_path), "error": "unparseable date"}

    cache_key = f"{source_type}_{date_str}_{_file_hash(raster_path)}.parquet"
    cache_path = cache_dir / cache_key
    if cache_path.exists():
        return {"ok": True, "raster": str(raster_path), "cache": str(cache_path)}

    try:
        boundaries = gpd.read_file(boundaries_geojson_str)
        stats = zonal_stats(
            boundaries,
            str(raster_path),
            stats=["mean", "max", "count"],
            geojson_out=False,
            nodata=None,
        )
        rows = []
        for feat, s in zip(boundaries.itertuples(index=False), stats):
            rows.append({
                "district_id": getattr(feat, "district_id"),
                "district_name": getattr(feat, "name", None),
                "province": getattr(feat, "province", None),
                "date": date_str,
                "mean": s.get("mean"),
                "max": s.get("max"),
                "valid_pixel_count": s.get("count"),
                "source_raster": raster_path.name,
                "source_type": source_type,
            })
        df = pd.DataFrame(rows)
        df.to_parquet(cache_path, index=False)
        return {"ok": True, "raster": str(raster_path), "cache": str(cache_path)}
    except Exception as exc:  # noqa: BLE001 — record and continue per failure-report contract
        return {"ok": False, "raster": str(raster_path), "error": f"{type(exc).__name__}: {exc}"}


def _slope_from_dem(dem_path: Path):
    """Derive slope (degrees) from a DEM raster using numpy gradient.

    Returns (slope_mean, slope_max) per district by re-running zonal_stats with
    a temporary in-memory raster. Used when --slope-raster is not supplied.
    """
    import numpy as np
    import rasterio

    with rasterio.open(dem_path) as src:
        elev = src.read(1).astype("float32")
        pixel_size_y = abs(src.transform.e)
        pixel_size_x = abs(src.transform.a)
    # Numerical gradient — degrees.
    dy, dx = np.gradient(elev, pixel_size_y, pixel_size_x)
    slope_rad = np.arctan(np.sqrt(dx ** 2 + dy ** 2))
    slope_deg = np.degrees(slope_rad).astype("float32")
    return slope_deg


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    # ---- Preflight ---------------------------------------------------------
    from ml.training.real_data_contract import (  # deferred
        validate_dependencies, validate_real_data_contract,
        DataMissingError, DependencyMissingError,
    )
    try:
        validate_dependencies()
    except DependencyMissingError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        validate_real_data_contract(required_keys=REQUIRED_CONTRACT_KEYS)
    except DataMissingError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    # ---- Heavy imports (post-preflight) ------------------------------------
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    from joblib import Parallel, delayed
    import rasterio
    from rasterstats import zonal_stats
    from shapely.validation import make_valid

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    args.failure_report.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[zonal] loading boundaries: {args.boundaries}")
    boundaries = gpd.read_file(args.boundaries)
    if boundaries.crs is None:
        print("ERROR: boundaries file has no CRS set", file=sys.stderr)
        return 4
    boundaries["geometry"] = boundaries.geometry.apply(
        lambda g: g if g.is_valid else make_valid(g)
    )

    imerg_files = sorted(args.imerg_dir.glob("*.tif"))
    chirps_files = sorted(args.chirps_dir.glob("*.tif"))
    n_districts = len(boundaries)
    print(f"[zonal] districts={n_districts}  imerg={len(imerg_files)}  chirps={len(chirps_files)}  n_jobs={args.n_jobs}")

    jobs = (
        [(str(p), "imerg") for p in imerg_files]
        + [(str(p), "chirps") for p in chirps_files]
    )
    started = time.time()
    results = Parallel(n_jobs=args.n_jobs, verbose=5)(
        delayed(_process_one_raster)(rp, src, str(args.boundaries), str(args.cache_dir))
        for rp, src in jobs
    )

    failures = [r for r in results if not r["ok"]]
    successes = [r for r in results if r["ok"]]
    print(f"[zonal] success={len(successes)} failures={len(failures)} elapsed={time.time()-started:.1f}s")

    if failures:
        args.failure_report.write_text(json.dumps(failures, indent=2))
        if not args.allow_partial:
            print(f"ERROR: {len(failures)} rasters failed (see {args.failure_report}). "
                  f"Re-run with --allow-partial to ignore.", file=sys.stderr)
            return 5

    # ---- Aggregate per-raster cache parquets into long form ----------------
    cache_frames = []
    for r in successes:
        cache_frames.append(pd.read_parquet(r["cache"]))
    if not cache_frames:
        print("ERROR: no successful raster outputs to aggregate", file=sys.stderr)
        return 6
    long_df = pd.concat(cache_frames, ignore_index=True)

    # Pivot imerg vs chirps onto one row per (district_id, date)
    pivot_frames = []
    for src in ("imerg", "chirps"):
        sub = long_df[long_df["source_type"] == src].copy()
        sub = sub.rename(columns={
            "mean": f"{src}_rainfall_mean_mm",
            "max":  f"{src}_rainfall_max_mm",
            "valid_pixel_count": f"{src}_valid_pixel_count",
        })
        pivot_frames.append(sub.drop(columns=["source_raster", "source_type"]))
    out = pd.merge(
        pivot_frames[0],
        pivot_frames[1][["district_id", "date",
                         "chirps_rainfall_mean_mm",
                         "chirps_rainfall_max_mm",
                         "chirps_valid_pixel_count"]],
        on=["district_id", "date"],
        how="outer",
    )

    # ---- Static rasters: DEM + slope + population --------------------------
    print(f"[zonal] zonal-stats DEM: {args.elevation}")
    elev_stats = zonal_stats(boundaries, str(args.elevation), stats=["mean", "max"])
    out_elev = pd.DataFrame({
        "district_id": boundaries["district_id"].values,
        "elevation_mean_m": [s.get("mean") for s in elev_stats],
        "elevation_max_m":  [s.get("max")  for s in elev_stats],
    })

    if args.slope_raster:
        print(f"[zonal] zonal-stats slope raster: {args.slope_raster}")
        slope_stats = zonal_stats(boundaries, str(args.slope_raster), stats=["mean", "max"])
    else:
        print("[zonal] deriving slope from DEM (numpy gradient)")
        slope_array = _slope_from_dem(args.elevation)
        with rasterio.open(args.elevation) as src:
            affine = src.transform
        slope_stats = zonal_stats(
            boundaries, slope_array, affine=affine, stats=["mean", "max"], nodata=np.nan,
        )
    out_slope = pd.DataFrame({
        "district_id": boundaries["district_id"].values,
        "slope_mean_deg": [s.get("mean") for s in slope_stats],
        "slope_max_deg":  [s.get("max")  for s in slope_stats],
    })

    # Population: raster OR pre-aggregated CSV
    if args.population.suffix.lower() in {".tif", ".tiff"}:
        print(f"[zonal] zonal-stats WorldPop raster: {args.population}")
        pop_stats = zonal_stats(boundaries, str(args.population), stats=["sum", "mean"])
        pop_sums = np.array([s.get("sum") or 0 for s in pop_stats], dtype="float64")
        max_pop = float(pop_sums.max()) if pop_sums.size else 1.0
        scores = pop_sums / max_pop if max_pop > 0 else pop_sums
        out_pop = pd.DataFrame({
            "district_id": boundaries["district_id"].values,
            "population_exposure_score": scores,
        })
    else:
        print(f"[zonal] reading pre-aggregated population CSV: {args.population}")
        out_pop = pd.read_csv(args.population)[["district_id", "population_exposure_score"]]

    static_df = out_elev.merge(out_slope, on="district_id").merge(out_pop, on="district_id")
    final = out.merge(static_df, on="district_id", how="left")

    cols = [
        "district_id", "district_name", "province", "date",
        "imerg_rainfall_mean_mm", "imerg_rainfall_max_mm", "imerg_valid_pixel_count",
        "chirps_rainfall_mean_mm", "chirps_rainfall_max_mm", "chirps_valid_pixel_count",
        "elevation_mean_m", "elevation_max_m", "slope_mean_deg", "slope_max_deg",
        "population_exposure_score",
    ]
    for c in cols:
        if c not in final.columns:
            final[c] = None
    final["source_type"] = "v3_zonal_stats"
    final["source_raster"] = "aggregated"
    final = final[cols + ["source_raster", "source_type"]].sort_values(["district_id", "date"]).reset_index(drop=True)

    final.to_parquet(args.output, index=False)
    print(f"[zonal] wrote {args.output} rows={len(final)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
