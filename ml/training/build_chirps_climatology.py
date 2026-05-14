"""CHIRPS day-of-year climatology per Pakistan district (PakFlood AI v3).

Reads the processed district-day feature store and aggregates CHIRPS daily
rainfall by (district_id, day_of_year) to produce a multi-year climatology
used downstream for anomaly calculations. Fails loudly if not enough years
of CHIRPS coverage exist for the requested districts.

Output schema:
    district_id, day_of_year, chirps_climatology_mean_mm, chirps_climatology_std_mm
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_chirps_climatology",
        description=(
            "Build CHIRPS day-of-year × district climatology from the processed "
            "feature store. No synthetic fallback — refuses to run with too few years."
        ),
    )
    p.add_argument("--features", required=True, type=Path,
                   help="Processed district-day feature store parquet (from precompute_district_zonal_stats.py)")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--min-years", type=int, default=10,
                   help="Minimum distinct years of CHIRPS coverage required. Default 10.")
    return p


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    from ml.training.real_data_contract import (
        validate_dependencies, DependencyMissingError,
    )
    try:
        validate_dependencies()
    except DependencyMissingError as exc:
        print(str(exc), file=sys.stderr); return 2

    if not args.features.exists():
        print(f"ERROR: features parquet not found: {args.features}\n"
              f"Run precompute_district_zonal_stats.py first.", file=sys.stderr); return 3

    import pandas as pd

    df = pd.read_parquet(args.features)
    if "chirps_rainfall_mean_mm" not in df.columns:
        print("ERROR: features parquet has no chirps_rainfall_mean_mm column", file=sys.stderr); return 4

    df["date"] = pd.to_datetime(df["date"])
    df["day_of_year"] = df["date"].dt.dayofyear
    df["year"] = df["date"].dt.year

    distinct_years = df["year"].nunique()
    if distinct_years < args.min_years:
        print(f"ERROR: CHIRPS coverage spans only {distinct_years} year(s); "
              f"--min-years={args.min_years} required. No synthetic backfill.",
              file=sys.stderr); return 5

    clim = (
        df.groupby(["district_id", "day_of_year"])["chirps_rainfall_mean_mm"]
          .agg(["mean", "std"])
          .reset_index()
          .rename(columns={
              "mean": "chirps_climatology_mean_mm",
              "std":  "chirps_climatology_std_mm",
          })
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    clim.to_parquet(args.output, index=False)
    print(f"[chirps-clim] wrote {args.output} rows={len(clim)} years={distinct_years}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
