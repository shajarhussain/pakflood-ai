"""Phase 10 — combine real downloaded dataset files into a training table.

This script PRODUCES features from on-disk files (not API responses):

  Static per-district features (zonal-stat once, broadcast to all dates):
    - elevation_mean_m       ← SRTMGL3 DEM raster
    - distance_to_river_km   ← Natural Earth rivers (proxy), metric CRS EPSG:6933
    - population_exposure    ← WorldPop 2020 zonal SUM, normalised 0-1

  Daily per-district features:
    - chirps_rainfall_mean_mm ← CHIRPS GeoTIFFs zonal mean (Aug-Sep 2022 window)
    - rainfall_1d/3d/7d/14d/30d_mm  ← trailing rolling sums from NASA POWER
      (carried forward from data/real_lite/training/...csv so the training
      window extends to 2026 where the EONET labels live)
    - precip_lag_1d/3d/7d, antecedent_precip_3d/7d/14d, rainfall_anomaly_pct

  Labels (re-used from v3-lite — same EONET v3 event-point matching):
    - observed_flood_today
    - flood_next_24h, flood_next_72h, flood_next_7d  (explicit forward shifts)

Output:
    data/real_dataset/training/pakistan_flood_prediction_dataset_based.csv

No mock_risk.json, no synthetic data, no DB rows.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="build_dataset_based_prediction_table")
    p.add_argument("--root",          type=Path, default=Path("data/real_dataset/raw"))
    p.add_argument("--lite-csv",      type=Path,
                   default=Path("data/real_lite/training/pakistan_flood_prediction_real_lite.csv"),
                   help="Existing v3-lite weather+labels CSV used as the timeline backbone")
    p.add_argument("--output",        type=Path,
                   default=Path("data/real_dataset/training/pakistan_flood_prediction_dataset_based.csv"))
    p.add_argument("--metric-crs",    default="EPSG:6933")
    return p


def _bbox_intersects_pakistan(b: list[float]) -> bool:
    return 60.0 <= b[2] and b[0] <= 78.0 and 22.0 <= b[3] and b[1] <= 38.0


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    import geopandas as gpd
    import numpy as np
    import pandas as pd
    from pyproj import CRS
    import rasterio
    from rasterstats import zonal_stats
    from shapely.geometry import box

    boundaries_path = args.root / "boundaries" / "pakistan_districts.geojson"
    rivers_path     = args.root / "rivers" / "hydrorivers_pakistan.geojson"
    dem_path        = args.root / "elevation" / "dem.tif"
    pop_path        = args.root / "population" / "worldpop_pakistan.tif"
    chirps_dir      = args.root / "rainfall_chirps"

    for p, label in [
        (boundaries_path, "boundaries"), (rivers_path, "rivers"),
        (dem_path, "DEM"), (pop_path, "WorldPop"),
    ]:
        if not p.exists():
            print(f"ERROR: missing {label}: {p}", file=sys.stderr); return 2
    if not args.lite_csv.exists():
        print(f"ERROR: lite CSV missing: {args.lite_csv}", file=sys.stderr); return 2

    boundaries = gpd.read_file(boundaries_path)
    print(f"[build] boundaries: {len(boundaries)} features  crs={boundaries.crs}")

    # ── Resolve a district_id↔centroid map for the 10 MVP districts ───────
    # NASA POWER weather CSVs are keyed by our internal PK-XX-XXX scheme.
    # We match each district to the nearest gbOpen ADM2 polygon by centroid
    # so all 5 datasets share the same boundary geometry.
    DISTRICT_CENTROIDS = {
        "PK-SD-SKR": (27.70, 68.85), "PK-SD-JCB": (28.45, 68.35),
        "PK-SD-LRK": (27.45, 67.90), "PK-PB-MUL": (30.30, 71.55),
        "PK-PB-RWP": (33.65, 73.05), "PK-PB-LHR": (31.55, 74.40),
        "PK-KP-PSH": (34.10, 71.70), "PK-BL-QTA": (30.20, 67.05),
        "PK-BL-NAS": (28.85, 68.15), "PK-GB-GIL": (36.00, 74.20),
    }
    # Build a small GeoDataFrame from the centroid map and use the nearest
    # gbOpen polygon for each — that gives us 10 named polygons for zonal stats.
    from shapely.geometry import Point
    centroids_gdf = gpd.GeoDataFrame(
        [{"district_id": k} for k in DISTRICT_CENTROIDS],
        geometry=[Point(lon, lat) for (lat, lon) in DISTRICT_CENTROIDS.values()],
        crs="EPSG:4326",
    )
    # spatial-join nearest gbOpen polygon
    nearest = gpd.sjoin_nearest(centroids_gdf, boundaries.to_crs("EPSG:4326")[["geometry"]], how="left")
    district_polys = boundaries.iloc[nearest.index_right.values].copy()
    district_polys["district_id"] = list(DISTRICT_CENTROIDS.keys())
    district_polys = district_polys[["district_id", "geometry"]].reset_index(drop=True)
    print(f"[build] district polygons: {len(district_polys)} mapped to MVP IDs")

    # ── Static features ───────────────────────────────────────────────────
    # 1. Elevation (mean per district)
    elev_stats = zonal_stats(district_polys, str(dem_path), stats=["mean", "min", "max"])
    elev_df = pd.DataFrame({
        "district_id": district_polys["district_id"],
        "elevation_mean_m":  [s.get("mean") for s in elev_stats],
        "elevation_max_m":   [s.get("max")  for s in elev_stats],
    })
    print(f"[build] elevation_mean range: "
          f"{elev_df['elevation_mean_m'].min():.0f}–{elev_df['elevation_mean_m'].max():.0f} m")

    # 2. Distance to river (in metric CRS)
    rivers = gpd.read_file(rivers_path)
    target_crs = CRS.from_user_input(args.metric_crs)
    if target_crs.is_geographic:
        print("ERROR: --metric-crs is geographic; refusing", file=sys.stderr); return 3
    if rivers.crs is None:
        rivers = rivers.set_crs("EPSG:4326")
    rivers_m = rivers.to_crs(target_crs)
    poly_m   = district_polys.to_crs(target_crs)
    # Pakistan bbox in metric CRS for rivers clip
    pak_bbox_m = (gpd.GeoSeries([box(60, 22, 78, 38)], crs="EPSG:4326")
                  .to_crs(target_crs).iloc[0])
    rivers_m_pak = rivers_m.clip(pak_bbox_m)
    rivers_union = rivers_m_pak.geometry.unary_union if not rivers_m_pak.empty else None
    dist_km = []
    for geom in poly_m.geometry:
        if rivers_union is None:
            dist_km.append(None); continue
        dist_km.append(float(geom.distance(rivers_union)) / 1000.0)
    elev_df["distance_to_river_km"] = dist_km
    print(f"[build] distance_to_river_km range: "
          f"{min(d for d in dist_km if d is not None):.1f}–{max(d for d in dist_km if d is not None):.1f}")

    # 3. WorldPop zonal sum → normalised exposure
    pop_stats = zonal_stats(district_polys, str(pop_path), stats=["sum"])
    pop_sums = np.array([s.get("sum") or 0.0 for s in pop_stats], dtype=float)
    if pop_sums.max() > 0:
        pop_norm = pop_sums / pop_sums.max()
    else:
        pop_norm = pop_sums
    elev_df["population_exposure_score"] = pop_norm
    print(f"[build] population_exposure max: {pop_norm.max():.3f}  min: {pop_norm.min():.3f}")

    # ── CHIRPS daily zonal stats ──────────────────────────────────────────
    chirps_files = sorted(chirps_dir.glob("chirps_*.tif"))
    print(f"[build] CHIRPS files: {len(chirps_files)}")
    chirps_rows = []
    for f in chirps_files:
        date_iso = f.stem.split("_", 1)[1]  # chirps_YYYY-MM-DD
        stats = zonal_stats(district_polys, str(f), stats=["mean", "max"], nodata=-9999)
        for spec, s in zip(district_polys.itertuples(index=False), stats):
            chirps_rows.append({
                "district_id": spec.district_id,
                "date": pd.to_datetime(date_iso),
                "chirps_rainfall_mean_mm": s.get("mean") or 0.0,
                "chirps_rainfall_max_mm":  s.get("max")  or 0.0,
            })
    chirps_df = pd.DataFrame(chirps_rows)
    print(f"[build] CHIRPS zonal rows: {len(chirps_df)}  "
          f"date range: {chirps_df['date'].min().date()}…{chirps_df['date'].max().date()}")

    # ── Join with v3-lite timeline (NASA POWER weather + EONET labels) ────
    lite = pd.read_csv(args.lite_csv, parse_dates=["date"])
    print(f"[build] lite timeline: {len(lite):,} rows  "
          f"date range: {lite['date'].min().date()}…{lite['date'].max().date()}")

    merged = lite.merge(chirps_df, on=["district_id", "date"], how="left")
    merged["chirps_missing"] = merged["chirps_rainfall_mean_mm"].isna().astype(int)
    merged["chirps_rainfall_mean_mm"] = merged["chirps_rainfall_mean_mm"].fillna(0.0)
    merged["chirps_rainfall_max_mm"]  = merged["chirps_rainfall_max_mm"].fillna(0.0)

    merged = merged.merge(elev_df, on="district_id", how="left")

    # ── Provenance + source summary ──────────────────────────────────────
    merged["feature_source_summary"] = (
        "CHIRPS-zonal+NASA-POWER+SRTMGL3+NaturalEarth-rivers-proxy+WorldPop+EONET-labels"
    )

    # Keep only well-ordered columns
    cols = [c for c in (
        "district_id", "district_name", "province", "date",
        # NASA POWER daily + rollings already in lite CSV
        "rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm",
        "rainfall_14d_mm", "rainfall_30d_mm",
        "precip_lag_1d", "precip_lag_3d", "precip_lag_7d",
        "antecedent_precip_3d", "antecedent_precip_7d", "antecedent_precip_14d",
        "rainfall_anomaly_pct",
        "temperature_c", "humidity_pct", "wind_speed_ms",
        # New CHIRPS dataset features
        "chirps_rainfall_mean_mm", "chirps_rainfall_max_mm", "chirps_missing",
        # New static features from real rasters/vectors
        "elevation_mean_m", "elevation_max_m",
        "distance_to_river_km", "population_exposure_score",
        # Labels
        "observed_flood_today",
        "flood_next_24h", "flood_next_72h", "flood_next_7d",
        "label_source", "label_confidence", "feature_source_summary",
    ) if c in merged.columns]
    out = merged[cols].fillna(0.0)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)

    pos = int(out["flood_next_72h"].sum())
    print(f"[build] wrote {args.output} rows={len(out):,}  positives={pos}  "
          f"ratio={pos/max(len(out),1):.4f}")
    # Side-car provenance file
    (args.output.parent / "_dataset_provenance.json").write_text(json.dumps({
        "boundaries":    str(boundaries_path),
        "chirps_files":  [str(f) for f in chirps_files],
        "rivers":        str(rivers_path),
        "dem":           str(dem_path),
        "worldpop":      str(pop_path),
        "lite_backbone": str(args.lite_csv),
        "metric_crs":    args.metric_crs,
        "rows": int(len(out)),
        "positives_flood_next_72h": pos,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
