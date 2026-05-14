"""Build the v3 training dataset with continuous date index + lag/rolling/anomaly/interaction features.

Inputs: processed feature store, district labels, GloFAS CSV, river features
parquet, CHIRPS climatology parquet, optional population CSV.

For each district_id:
  1. sort by date
  2. reindex to complete daily date range from min..max date
  3. fill missing rainfall with 0; static features ffill/bfill; preserve missingness flags
  4. ONLY THEN compute trailing lag/rolling/antecedent/anomaly/interaction features
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


REQUIRED_CONTRACT_KEYS = ["glofas"]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_prediction_dataset",
        description=(
            "Merge processed features + labels + GloFAS + river features + "
            "CHIRPS climatology into the v3 training CSV with continuous date "
            "index and trailing-only lag/rolling features. No future leakage."
        ),
    )
    p.add_argument("--features", required=True, type=Path)
    p.add_argument("--labels", required=True, type=Path)
    p.add_argument("--glofas", required=True, type=Path)
    p.add_argument("--river-features", required=True, type=Path)
    p.add_argument("--chirps-climatology", required=True, type=Path)
    p.add_argument("--population", type=Path, default=None,
                   help="Optional district CSV (district_id, population_exposure_score) "
                        "if not already in --features")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--start-date", help="Optional ISO YYYY-MM-DD (default: min date in features)")
    p.add_argument("--end-date", help="Optional ISO YYYY-MM-DD (default: max date in features)")
    return p


def _enforce_glofas_schema(df) -> None:
    required = {"district_id", "date", "river_discharge_m3s", "source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"glofas CSV missing required columns: {sorted(missing)}")


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

    for path in (args.features, args.labels, args.river_features, args.chirps_climatology):
        if not path.exists():
            print(f"ERROR: required processed input missing: {path}", file=sys.stderr); return 4

    import numpy as np
    import pandas as pd

    features = pd.read_parquet(args.features)
    labels = pd.read_parquet(args.labels)
    rivers = pd.read_parquet(args.river_features)
    clim = pd.read_parquet(args.chirps_climatology)
    glofas = pd.read_csv(args.glofas)
    _enforce_glofas_schema(glofas)

    features["date"] = pd.to_datetime(features["date"])
    labels["date"] = pd.to_datetime(labels["date"])
    glofas["date"] = pd.to_datetime(glofas["date"])

    start_date = pd.to_datetime(args.start_date) if args.start_date else features["date"].min()
    end_date = pd.to_datetime(args.end_date) if args.end_date else features["date"].max()

    out_frames = []
    for district_id, g_feat in features.groupby("district_id"):
        g_feat = g_feat.sort_values("date").set_index("date")
        full_idx = pd.date_range(start_date, end_date, freq="D")
        g = g_feat.reindex(full_idx)
        g.index.name = "date"

        # Missingness flags
        g["imerg_missing_flag"] = g["imerg_rainfall_mean_mm"].isna().astype(int)
        g["chirps_missing_flag"] = g["chirps_rainfall_mean_mm"].isna().astype(int)

        # Fill rainfall with 0 (required before rolling)
        for col in ("imerg_rainfall_mean_mm", "imerg_rainfall_max_mm",
                    "chirps_rainfall_mean_mm", "chirps_rainfall_max_mm"):
            if col in g.columns:
                g[col] = g[col].fillna(0.0)

        # Static columns: forward/back fill
        for col in ("district_id", "district_name", "province",
                    "elevation_mean_m", "elevation_max_m",
                    "slope_mean_deg", "slope_max_deg",
                    "population_exposure_score"):
            if col in g.columns:
                g[col] = g[col].ffill().bfill()
        g["district_id"] = district_id

        # ---- Trailing rainfall rolling sums (never center=True) ----------
        r = g["imerg_rainfall_mean_mm"]
        g["rainfall_1d_mm"]  = r
        g["rainfall_3d_mm"]  = r.rolling(3,  min_periods=1).sum()
        g["rainfall_7d_mm"]  = r.rolling(7,  min_periods=1).sum()
        g["rainfall_14d_mm"] = r.rolling(14, min_periods=1).sum()
        g["rainfall_30d_mm"] = r.rolling(30, min_periods=1).sum()

        # Lag features
        g["precip_lag_1d"]  = r.shift(1)
        g["precip_lag_3d"]  = r.shift(3)
        g["precip_lag_7d"]  = r.shift(7)
        g["precip_lag_14d"] = r.shift(14)

        # Antecedent precipitation (excludes today)
        g["antecedent_precip_3d"]  = r.shift(1).rolling(3,  min_periods=1).sum()
        g["antecedent_precip_7d"]  = r.shift(1).rolling(7,  min_periods=1).sum()
        g["antecedent_precip_14d"] = r.shift(1).rolling(14, min_periods=1).sum()
        g["antecedent_precip_30d"] = r.shift(1).rolling(30, min_periods=1).sum()

        out_frames.append(g.reset_index())

    big = pd.concat(out_frames, ignore_index=True)
    big["date"] = pd.to_datetime(big["date"])

    # Merge CHIRPS climatology on (district_id, day_of_year) for anomaly calc
    big["day_of_year"] = big["date"].dt.dayofyear
    big = big.merge(clim, on=["district_id", "day_of_year"], how="left")

    safe_clim = big["chirps_climatology_mean_mm"].replace(0, np.nan)
    big["rainfall_anomaly_pct"] = (big["imerg_rainfall_mean_mm"] - safe_clim) / safe_clim * 100.0
    big["chirps_anomaly_pct"] = (big["chirps_rainfall_mean_mm"] - safe_clim) / safe_clim * 100.0

    # Merge GloFAS discharge
    big = big.merge(glofas[["district_id", "date", "river_discharge_m3s"]],
                    on=["district_id", "date"], how="left")
    big["glofas_missing_flag"] = big["river_discharge_m3s"].isna().astype(int)
    big["river_discharge_m3s"] = big["river_discharge_m3s"].fillna(0.0)
    big = big.sort_values(["district_id", "date"])
    big["discharge_lag_1d"] = big.groupby("district_id")["river_discharge_m3s"].shift(1)
    big["discharge_lag_3d"] = big.groupby("district_id")["river_discharge_m3s"].shift(3)
    big["discharge_lag_7d"] = big.groupby("district_id")["river_discharge_m3s"].shift(7)
    rolling_mean = big.groupby("district_id")["river_discharge_m3s"].transform(lambda s: s.rolling(30, min_periods=1).mean())
    big["discharge_anomaly_pct"] = (big["river_discharge_m3s"] - rolling_mean) / rolling_mean.replace(0, np.nan) * 100.0

    # Merge river features (static per district)
    big = big.merge(rivers[["district_id", "distance_to_river_km", "drainage_density", "total_river_length_km"]],
                    on="district_id", how="left")

    # Historical flood count from labels (sum of observed_flood_today up to but not including today)
    labels_sorted = labels.sort_values(["district_id", "date"])
    labels_sorted["historical_flood_count"] = (
        labels_sorted.groupby("district_id")["observed_flood_today"]
        .transform(lambda s: s.shift(1).fillna(0).cumsum())
    )
    big = big.merge(
        labels_sorted[["district_id", "date", "historical_flood_count",
                       "flood_next_24h", "flood_next_72h", "flood_next_7d"]],
        on=["district_id", "date"], how="left",
    )
    big["historical_flood_count"] = big["historical_flood_count"].fillna(0).astype(int)
    for lbl in ("flood_next_24h", "flood_next_72h", "flood_next_7d"):
        big[lbl] = big[lbl].fillna(0).astype(int)

    # Optional population CSV
    if args.population:
        pop = pd.read_csv(args.population)
        if "population_exposure_score" not in pop.columns:
            print("ERROR: --population CSV missing population_exposure_score", file=sys.stderr); return 4
        big = big.drop(columns=["population_exposure_score"], errors="ignore")
        big = big.merge(pop[["district_id", "population_exposure_score"]], on="district_id", how="left")

    # ---- Interaction features --------------------------------------------
    big["rainfall_7d_x_slope"] = big["rainfall_7d_mm"] * big.get("slope_mean_deg", 0)
    big["rainfall_7d_x_distance_to_river_inverse"] = (
        big["rainfall_7d_mm"] / (big.get("distance_to_river_km", 0).fillna(0) + 0.1)
    )
    big["rainfall_7d_x_historical_flood_count"] = big["rainfall_7d_mm"] * big["historical_flood_count"]
    big["discharge_x_rainfall_7d"] = big["river_discharge_m3s"] * big["rainfall_7d_mm"]
    big["anomaly_x_discharge"] = big["rainfall_anomaly_pct"].fillna(0) * big["river_discharge_m3s"]
    big["population_x_risk_exposure"] = big.get("population_exposure_score", 0) * big["historical_flood_count"]

    big["feature_source_summary"] = "IMERG+CHIRPS+GloFAS+HydroRIVERS+WorldPop+UNOSAT(labels)"
    big["label_source"] = "UNOSAT_HDX_v3"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    big.to_csv(args.output, index=False)
    print(f"[dataset] wrote {args.output} rows={len(big)} districts={big['district_id'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
