"""HydroRIVERS-derived river features per district (PakFlood AI v3).

Computes distance_to_river_km, drainage_density and total_river_length_km for
each Pakistan district. All length/distance calculations are performed in a
projected metric CRS (default EPSG:6933). Geographic CRS for area/distance is
refused with a hard runtime guard.

Performance: builds a spatial index on the river network and clips candidate
rivers to each district's envelope before exact intersection — never runs a
global unfiltered intersection over the full HydroRIVERS layer.

Output schema:
    district_id, distance_to_river_km, drainage_density, total_river_length_km, metric_crs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


REQUIRED_CONTRACT_KEYS = ["boundaries", "rivers"]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="precompute_river_features",
        description=(
            "Compute distance-to-river, drainage density and total river length "
            "per Pakistan district from HydroRIVERS in a projected metric CRS."
        ),
    )
    p.add_argument("--boundaries", required=True, type=Path)
    p.add_argument("--rivers", required=True, type=Path, help="HydroRIVERS GeoJSON clipped to Pakistan")
    p.add_argument("--output", required=True, type=Path, help="Output parquet path")
    p.add_argument("--metric-crs", default="EPSG:6933",
                   help="Projected CRS for distance/length. Default EPSG:6933 (national equal-area).")
    return p


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    from ml.training.real_data_contract import (
        validate_dependencies, validate_real_data_contract,
        DataMissingError, DependencyMissingError,
    )
    try:
        validate_dependencies()
    except DependencyMissingError as exc:
        print(str(exc), file=sys.stderr); return 2
    try:
        validate_real_data_contract(required_keys=REQUIRED_CONTRACT_KEYS)
    except DataMissingError as exc:
        print(str(exc), file=sys.stderr); return 3

    import geopandas as gpd
    import pandas as pd
    from pyproj import CRS

    boundaries = gpd.read_file(args.boundaries)
    rivers = gpd.read_file(args.rivers)
    if boundaries.crs is None or rivers.crs is None:
        print("ERROR: both boundaries and rivers must have CRS set", file=sys.stderr); return 4

    target_crs = CRS.from_user_input(args.metric_crs)
    if target_crs.is_geographic:
        print(f"ERROR: --metric-crs {args.metric_crs} is geographic. Refusing distance/length "
              f"calculation in a geographic CRS.", file=sys.stderr); return 4

    boundaries_m = boundaries.to_crs(target_crs)
    rivers_m = rivers.to_crs(target_crs)

    # Spatial index for fast candidate selection.
    sindex = rivers_m.sindex

    rows = []
    for feat in boundaries_m.itertuples(index=False):
        geom = feat.geometry
        district_id = getattr(feat, "district_id")
        district_area_m2 = float(geom.area)
        district_area_km2 = district_area_m2 / 1e6

        # Candidates = bbox intersection
        candidate_idx = list(sindex.intersection(geom.bounds))
        if not candidate_idx:
            rows.append({
                "district_id": district_id,
                "distance_to_river_km": None,
                "drainage_density": 0.0,
                "total_river_length_km": 0.0,
                "metric_crs": str(target_crs),
            })
            continue
        candidates = rivers_m.iloc[candidate_idx]

        # Distance to nearest river: use unary_union of candidates (small set)
        try:
            union = candidates.geometry.unary_union
            distance_m = float(geom.distance(union))
        except Exception:  # noqa: BLE001
            distance_m = None

        # Total length inside this district
        try:
            intersected = candidates.geometry.intersection(geom)
            total_length_m = float(intersected.length.sum())
        except Exception:  # noqa: BLE001
            total_length_m = 0.0

        total_length_km = total_length_m / 1000.0
        drainage_density = total_length_km / district_area_km2 if district_area_km2 > 0 else 0.0

        rows.append({
            "district_id": district_id,
            "distance_to_river_km": (distance_m / 1000.0) if distance_m is not None else None,
            "drainage_density": drainage_density,
            "total_river_length_km": total_length_km,
            "metric_crs": str(target_crs),
        })

    out = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)
    print(f"[rivers] wrote {args.output} rows={len(out)} metric_crs={target_crs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
