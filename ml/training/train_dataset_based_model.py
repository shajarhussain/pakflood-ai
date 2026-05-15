"""Phase 10 — train BalancedRandomForest + sigmoid calibration on the
dataset-based real-file CSV.

Artifacts:
  ml/artifacts/flood_prediction_dataset_based.pkl
  ml/artifacts/flood_prediction_dataset_based_metadata.json
  ml/evaluation/flood_prediction_dataset_based_metrics.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


EXCLUDED_COLS = {
    "district_id", "district_name", "province", "date",
    "observed_flood_today",
    "flood_next_24h", "flood_next_72h", "flood_next_7d",
    "label_source", "label_confidence", "feature_source_summary",
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="train_dataset_based_model")
    p.add_argument("--dataset", type=Path,
                   default=Path("data/real_dataset/training/pakistan_flood_prediction_dataset_based.csv"))
    p.add_argument("--target", default="flood_next_72h",
                   choices=["flood_next_24h", "flood_next_72h", "flood_next_7d"])
    p.add_argument("--output-dir",  type=Path, default=Path("ml/artifacts"))
    p.add_argument("--metrics-dir", type=Path, default=Path("ml/evaluation"))
    p.add_argument("--min-positive-samples", type=int, default=20)
    p.add_argument("--calibrate", default="sigmoid", choices=["sigmoid", "isotonic"])
    return p


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.dataset.exists():
        print(f"ERROR: dataset missing: {args.dataset}", file=sys.stderr); return 3

    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import (
        average_precision_score, f1_score, precision_score, recall_score,
        balanced_accuracy_score, brier_score_loss, roc_auc_score,
        accuracy_score, classification_report, confusion_matrix,
    )
    from sklearn.model_selection import StratifiedShuffleSplit
    try:
        from imblearn.ensemble import BalancedRandomForestClassifier
    except ImportError:
        print("ERROR: imbalanced-learn required (pip install imbalanced-learn>=0.12)", file=sys.stderr); return 4

    df = pd.read_csv(args.dataset, parse_dates=["date"])
    y = df[args.target].astype(int)
    pos = int(y.sum())
    pos_ratio = float(y.mean())
    print(f"[ds-train] rows={len(df):,}  positives={pos}  ratio={pos_ratio:.4f}")
    if pos < args.min_positive_samples:
        print(f"ERROR: only {pos} positives (< {args.min_positive_samples})", file=sys.stderr); return 5

    feature_cols = [c for c in df.columns if c not in EXCLUDED_COLS and c != args.target]
    X = df[feature_cols].copy()
    for c in feature_cols:
        if not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.loc[:, X.notna().any(axis=0)].fillna(0.0)
    feature_list = X.columns.tolist()
    for forbidden in ("observed_flood_today", "flood_next_24h", "flood_next_72h", "flood_next_7d"):
        if forbidden in feature_list:
            print(f"ERROR: leakage — '{forbidden}' must not be in features", file=sys.stderr); return 6

    # Time-holdout 60/20/20 — fall back to stratified if pos split == 0
    df_sorted = df.sort_values("date")
    idx = df_sorted.index.values
    n = len(idx)
    idx_fit  = idx[: int(n * 0.60)]
    idx_cal  = idx[int(n * 0.60): int(n * 0.80)]
    idx_test = idx[int(n * 0.80):]
    if y.loc[idx_fit].sum() == 0 or y.loc[idx_test].sum() == 0:
        print("[ds-train] zero-positive split — falling back to stratified")
        sss1 = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        pool, test_pos = next(sss1.split(X, y))
        sss2 = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        fit_pos, cal_pos = next(sss2.split(X.iloc[pool], y.iloc[pool]))
        idx_fit  = X.index[pool][fit_pos]
        idx_cal  = X.index[pool][cal_pos]
        idx_test = X.index[test_pos]

    X_fit,  y_fit  = X.loc[idx_fit],  y.loc[idx_fit]
    X_cal,  y_cal  = X.loc[idx_cal],  y.loc[idx_cal]
    X_test, y_test = X.loc[idx_test], y.loc[idx_test]
    print(f"[ds-train] split  fit={len(X_fit):,}  cal={len(X_cal):,}  test={len(X_test):,}  "
          f"pos_fit={int(y_fit.sum())} pos_cal={int(y_cal.sum())} pos_test={int(y_test.sum())}")

    base = BalancedRandomForestClassifier(n_estimators=400, max_depth=None, random_state=42, n_jobs=-1)
    base.fit(X_fit, y_fit)

    try:
        from sklearn.frozen import FrozenEstimator
        calibrated = CalibratedClassifierCV(FrozenEstimator(base), method=args.calibrate).fit(X_cal, y_cal)
        calibration_api = "FrozenEstimator"
    except ImportError:
        calibrated = CalibratedClassifierCV(base, method=args.calibrate, cv="prefit").fit(X_cal, y_cal)
        calibration_api = "cv_prefit_compatibility_fallback"

    def _eval(model, Xe, ye) -> dict:
        proba = model.predict_proba(Xe)[:, 1]
        pred = (proba >= 0.5).astype(int)
        return {
            "pr_auc": float(average_precision_score(ye, proba)),
            "f1": float(f1_score(ye, pred, zero_division=0)),
            "precision": float(precision_score(ye, pred, zero_division=0)),
            "recall": float(recall_score(ye, pred, zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(ye, pred)),
            "brier": float(brier_score_loss(ye, proba)),
            "roc_auc": float(roc_auc_score(ye, proba)) if ye.nunique() > 1 else None,
            "accuracy": float(accuracy_score(ye, pred)),
            "confusion_matrix": confusion_matrix(ye, pred).tolist(),
            "classification_report": classification_report(ye, pred, zero_division=0, output_dict=True),
        }

    metrics = {
        "primary":      _eval(calibrated, X_test, y_test),
        "uncalibrated": _eval(base,       X_test, y_test),
        "positive_class_ratio_test": float(y_test.mean()),
        "baseline_majority_class_accuracy": float((y_test == y_test.mode().iloc[0]).mean()),
        "calibration_api": calibration_api,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_dir.mkdir(parents=True, exist_ok=True)
    artifact_path  = args.output_dir / "flood_prediction_dataset_based.pkl"
    metadata_path  = args.output_dir / "flood_prediction_dataset_based_metadata.json"
    metrics_path   = args.metrics_dir / "flood_prediction_dataset_based_metrics.json"

    joblib.dump({
        "model": calibrated, "feature_list": feature_list,
        "calibration_method": args.calibrate, "calibration_api": calibration_api,
    }, artifact_path)
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str))

    # Try to read v3-lite metrics for a side-by-side comparison
    lite_metrics_path = args.metrics_dir / "flood_prediction_real_lite_metrics.json"
    lite_compare = None
    if lite_metrics_path.exists():
        try:
            lite_m = json.loads(lite_metrics_path.read_text())["primary"]
            lite_compare = {
                "pr_auc":   {"lite": lite_m["pr_auc"],   "dataset_based": metrics["primary"]["pr_auc"]},
                "f1":       {"lite": lite_m["f1"],       "dataset_based": metrics["primary"]["f1"]},
                "brier":    {"lite": lite_m["brier"],    "dataset_based": metrics["primary"]["brier"]},
                "recall":   {"lite": lite_m["recall"],   "dataset_based": metrics["primary"]["recall"]},
            }
        except Exception:  # noqa: BLE001
            lite_compare = None

    # Provenance — exact files used
    raw_root = Path("data/real_dataset/raw")
    files_used = {
        "boundaries":  str(raw_root / "boundaries" / "pakistan_districts.geojson"),
        "rivers":      str(raw_root / "rivers" / "hydrorivers_pakistan.geojson"),
        "dem":         str(raw_root / "elevation" / "dem.tif"),
        "worldpop":    str(raw_root / "population" / "worldpop_pakistan.tif"),
        "chirps_dir":  str(raw_root / "rainfall_chirps"),
        "chirps_file_count": len(list((raw_root / "rainfall_chirps").glob("chirps_*.tif"))),
        "weather_backbone": "data/real_lite/raw/weather/*.csv (NASA POWER Daily API)",
        "labels_source":    "NASA EONET v3 flood events (nearest-district match, ±3 day window)",
    }

    metadata = {
        "model_name": "flood_prediction_dataset_based",
        "model_type": "BalancedRandomForestClassifier + sigmoid CalibratedClassifierCV",
        "model_scope": "dataset-based real-data model (stronger than v3-lite, weaker than strict v3)",
        "is_prediction_model": True,
        "is_detection_model": False,
        "prediction_summary": (
            "Phase 10 dataset-based real-data flood probability prediction model. "
            "Features are computed from REAL downloaded raster/vector files "
            "(SRTMGL3 DEM, Natural Earth rivers proxy, WorldPop 2020, CHIRPS daily "
            "GeoTIFFs Aug-Sep 2022) combined with NASA POWER daily weather. "
            "Labels are weak — derived from NASA EONET v3 flood event-points via "
            "nearest-district matching with a ±3-day window. NOT the strict "
            "8-source research-grade v3 model."
        ),
        "data_sources_used": files_used,
        "data_sources_failed": ["unosat (no public direct GeoJSON URL succeeded)"],
        "data_sources_auth_required": [
            {"name": "glofas",  "env_vars": ["CDSAPI_URL", "CDSAPI_KEY"]},
            {"name": "imerg",   "env_vars": ["NASA_EARTHDATA_USERNAME", "NASA_EARTHDATA_PASSWORD"]},
        ],
        "target": args.target,
        "prediction_window": {
            "flood_next_24h": "T+1 day",
            "flood_next_72h": "T+1 to T+3 days",
            "flood_next_7d":  "T+1 to T+7 days",
        }[args.target],
        "feature_list": feature_list,
        "excluded_columns": sorted(EXCLUDED_COLS),
        "positive_class_ratio_full": pos_ratio,
        "imbalance_strategy": "BalancedRandomForestClassifier",
        "calibration_method": args.calibrate,
        "calibration_api": calibration_api,
        "calibration_fit_policy": "fit_train, calibration_train, and test are disjoint row sets",
        "dataset_rows": int(len(df)),
        "dataset_districts": int(df["district_id"].nunique()),
        "metrics_path": str(metrics_path),
        "artifact_path": str(artifact_path),
        "trained_at_iso": datetime.now(timezone.utc).isoformat(),
        "comparison_with_real_lite": lite_compare,
        "limitations": [
            "Weak labels: derived from EONET flood event-points, not satellite-flagged flood extents.",
            "Rivers feature uses Natural Earth as a proxy (Pakistan-clipped HydroRIVERS would be more accurate).",
            "Slope features not computed (would require gdaldem or richdem on the DEM).",
            "CHIRPS coverage is limited to Aug-Sep 2022 (46 daily files); other dates fall back to NASA POWER alone.",
            "Positive class is rare (~0.15%); recall/precision should be interpreted cautiously.",
            "This is NOT the research-grade v3 model — see docs/13_real_flood_prediction_pipeline_v3.md.",
        ],
        "next_step_to_research_grade_v3": (
            "Add UNOSAT/HDX flood extent vector files, full Pakistan-clipped HydroRIVERS, "
            "GloFAS CSV, IMERG GeoTIFFs (with credentials), then run the strict v3 pipeline."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f"[ds-train] PR-AUC={metrics['primary']['pr_auc']:.3f}  "
          f"F1={metrics['primary']['f1']:.3f}  Brier={metrics['primary']['brier']:.4f}")
    print(f"[ds-train] artifact → {artifact_path}")
    print(f"[ds-train] metadata → {metadata_path}")
    print(f"[ds-train] metrics  → {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
