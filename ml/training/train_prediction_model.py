"""Train the v3 BalancedRandomForestClassifier with disjoint fit/calibration/test splits.

STRICT POLICY
=============
- BalancedRandomForestClassifier from imbalanced-learn — no silent fallback to
  a plain RandomForest. If imblearn is missing, exit with explicit install hint.
- Three disjoint row sets:
    fit_train         → fit base BalancedRF
    calibration_train → fit CalibratedClassifierCV (sigmoid by default)
    test              → final unbiased evaluation
- Calibration API: FrozenEstimator path preferred (scikit-learn ≥ 1.6).
  Fallback to cv="prefit" with explicit compatibility comment for older versions.
- Refuse training if positive class count is too low or ratio is 0.
- Primary metrics: PR-AUC, F1, precision, recall, balanced accuracy, Brier.
  Accuracy is secondary, not the headline.

Artifacts written:
    ml/artifacts/flood_prediction_balanced_rf_v3.pkl       — base BalancedRF
    ml/artifacts/flood_prediction_calibrated_v3.pkl        — calibrated final
    ml/evaluation/flood_prediction_metrics_v3.json         — metrics + reliability table
    ml/artifacts/flood_prediction_metadata_v3.json         — model metadata
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


EXCLUDED_COLS = {
    "district_id", "district_name", "province", "date", "day_of_year",
    "observed_flood_today",
    "flood_next_24h", "flood_next_72h", "flood_next_7d",
    "label_source", "feature_source_summary", "metric_crs",
    "source_raster", "source_type",
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="train_prediction_model",
        description=(
            "Train BalancedRandomForestClassifier + probability calibration on "
            "the real v3 training CSV. No synthetic fallback."
        ),
    )
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--target", default="flood_next_72h",
                   choices=["flood_next_24h", "flood_next_72h", "flood_next_7d"])
    p.add_argument("--model", default="balanced_random_forest",
                   choices=["balanced_random_forest"])
    p.add_argument("--calibrate", default="sigmoid", choices=["sigmoid", "isotonic"])
    p.add_argument("--test-strategy", default="time_holdout",
                   choices=["time_holdout", "stratified"])
    p.add_argument("--output-dir", type=Path, default=Path("ml/artifacts"))
    p.add_argument("--metrics-dir", type=Path, default=Path("ml/evaluation"))
    p.add_argument("--min-positive-samples", type=int, default=20)
    return p


def _build_feature_matrix(df, target: str):
    feature_cols = [c for c in df.columns if c not in EXCLUDED_COLS and c != target]
    X = df[feature_cols].copy()
    # Coerce non-numeric columns to numeric via NaN; drop columns that are entirely null.
    import pandas as pd
    for c in feature_cols:
        if not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.loc[:, X.notna().any(axis=0)]
    X = X.fillna(0.0)
    return X, X.columns.tolist()


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    from ml.training.real_data_contract import (
        validate_dependencies, DependencyMissingError,
    )
    try:
        validate_dependencies()
    except DependencyMissingError as exc:
        print(str(exc), file=sys.stderr); return 2

    if not args.dataset.exists():
        print(f"ERROR: training dataset missing: {args.dataset}\n"
              f"Run build_prediction_dataset.py first.", file=sys.stderr); return 3

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
        print(
            "ERROR: imbalanced-learn is required (BalancedRandomForestClassifier).\n"
            "Install with: pip install imbalanced-learn>=0.12\n"
            "No silent fallback to a plain RandomForest is allowed.",
            file=sys.stderr,
        )
        return 4

    df = pd.read_csv(args.dataset, parse_dates=["date"])
    if args.target not in df.columns:
        print(f"ERROR: target {args.target} not in dataset", file=sys.stderr); return 5

    y = df[args.target].astype(int)
    pos = int(y.sum())
    pos_ratio = float(y.mean())
    print(f"[train] rows={len(df)} positive={pos} positive_ratio={pos_ratio:.4f}")
    if pos == 0:
        print("ERROR: positive class ratio is 0 — cannot train classifier.", file=sys.stderr); return 6
    if pos < args.min_positive_samples:
        print(f"ERROR: only {pos} positive samples (< --min-positive-samples={args.min_positive_samples}).",
              file=sys.stderr); return 6

    X, feature_list = _build_feature_matrix(df, args.target)
    # Hard leakage guard
    for forbidden in ("observed_flood_today", "flood_next_24h", "flood_next_72h", "flood_next_7d"):
        if forbidden in feature_list:
            print(f"ERROR: leakage — '{forbidden}' must not be in features", file=sys.stderr); return 7

    # ---- 3-way split (fit / calibration / test) ----------------------------
    if args.test_strategy == "time_holdout":
        df_sorted_idx = df.sort_values("date").index
        n = len(df_sorted_idx)
        i_fit_end = int(n * 0.60)
        i_cal_end = int(n * 0.80)
        idx_fit = df_sorted_idx[:i_fit_end]
        idx_cal = df_sorted_idx[i_fit_end:i_cal_end]
        idx_test = df_sorted_idx[i_cal_end:]
        split_method = "time_holdout"
        train_range = (df.loc[idx_fit, "date"].min().isoformat(), df.loc[idx_fit, "date"].max().isoformat())
        test_range = (df.loc[idx_test, "date"].min().isoformat(), df.loc[idx_test, "date"].max().isoformat())
    else:
        sss1 = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        pool_idx, idx_test = next(sss1.split(X, y))
        idx_pool = pd.Index(df.index[pool_idx])
        idx_test = pd.Index(df.index[idx_test])
        sss2 = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        fit_idx, cal_idx = next(sss2.split(X.loc[idx_pool], y.loc[idx_pool]))
        idx_fit = idx_pool[fit_idx]
        idx_cal = idx_pool[cal_idx]
        split_method = "stratified"
        train_range = test_range = (None, None)

    X_fit, y_fit = X.loc[idx_fit], y.loc[idx_fit]
    X_cal, y_cal = X.loc[idx_cal], y.loc[idx_cal]
    X_test, y_test = X.loc[idx_test], y.loc[idx_test]
    print(f"[train] split={split_method} fit={len(X_fit)} cal={len(X_cal)} test={len(X_test)}")

    base = BalancedRandomForestClassifier(
        n_estimators=400, max_depth=None, random_state=42, n_jobs=-1,
    )
    base.fit(X_fit, y_fit)

    # Calibration: FrozenEstimator if available, cv='prefit' fallback otherwise.
    try:
        from sklearn.frozen import FrozenEstimator  # scikit-learn >= 1.6
        calibrated = CalibratedClassifierCV(FrozenEstimator(base), method=args.calibrate)
        calibration_api = "FrozenEstimator"
    except ImportError:
        # COMPATIBILITY FALLBACK: cv='prefit' is deprecated in sklearn 1.6 but still
        # the only option for older versions. base must already be fit.
        calibrated = CalibratedClassifierCV(base, method=args.calibrate, cv="prefit")
        calibration_api = "cv_prefit_compatibility_fallback"
    calibrated.fit(X_cal, y_cal)

    def _metrics(model, X_eval, y_eval):
        proba = model.predict_proba(X_eval)[:, 1]
        pred = (proba >= 0.5).astype(int)
        return {
            "pr_auc": float(average_precision_score(y_eval, proba)),
            "f1": float(f1_score(y_eval, pred, zero_division=0)),
            "precision": float(precision_score(y_eval, pred, zero_division=0)),
            "recall": float(recall_score(y_eval, pred, zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(y_eval, pred)),
            "brier": float(brier_score_loss(y_eval, proba)),
            "roc_auc": float(roc_auc_score(y_eval, proba)),
            "accuracy": float(accuracy_score(y_eval, pred)),
            "classification_report": classification_report(y_eval, pred, zero_division=0, output_dict=True),
            "confusion_matrix": confusion_matrix(y_eval, pred).tolist(),
        }

    uncal = _metrics(base, X_test, y_test)
    cal = _metrics(calibrated, X_test, y_test)

    # Reliability table (10 bins)
    proba = calibrated.predict_proba(X_test)[:, 1]
    bins = np.linspace(0.0, 1.0, 11)
    bin_idx = np.clip(np.digitize(proba, bins) - 1, 0, 9)
    reliability = []
    for b in range(10):
        mask = bin_idx == b
        if mask.sum() == 0:
            reliability.append({"bin": b, "lower": float(bins[b]), "upper": float(bins[b + 1]),
                                "count": 0, "mean_pred": None, "frac_positive": None})
        else:
            reliability.append({
                "bin": b, "lower": float(bins[b]), "upper": float(bins[b + 1]),
                "count": int(mask.sum()),
                "mean_pred": float(proba[mask].mean()),
                "frac_positive": float(y_test.iloc[mask].mean()),
            })

    majority_class = int(y_test.mode().iloc[0])
    baseline_acc = float((y_test == majority_class).mean())

    metrics = {
        "primary": cal,
        "uncalibrated": uncal,
        "baseline_majority_class_accuracy": baseline_acc,
        "positive_class_ratio_train": float(y_fit.mean()),
        "positive_class_ratio_test": float(y_test.mean()),
        "reliability_table": reliability,
        "split_method": split_method,
        "calibration_api": calibration_api,
        "calibration_method": args.calibrate,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_dir.mkdir(parents=True, exist_ok=True)
    base_path = args.output_dir / "flood_prediction_balanced_rf_v3.pkl"
    cal_path = args.output_dir / "flood_prediction_calibrated_v3.pkl"
    metrics_path = args.metrics_dir / "flood_prediction_metrics_v3.json"
    metadata_path = args.output_dir / "flood_prediction_metadata_v3.json"

    joblib.dump({"model": base, "feature_list": feature_list}, base_path)
    joblib.dump({"model": calibrated, "feature_list": feature_list,
                 "calibration_method": args.calibrate,
                 "calibration_api": calibration_api}, cal_path)
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str))

    metadata = {
        "model_name": "flood_prediction_v3",
        "model_type": "BalancedRandomForestClassifier + sigmoid CalibratedClassifierCV",
        "is_prediction_model": True,
        "is_detection_model": False,
        "prediction_summary": (
            "This model predicts flood probability for a future window. "
            "It does not detect current flood water."
        ),
        "target": args.target,
        "prediction_window": {
            "flood_next_24h": "T+1 day",
            "flood_next_72h": "T+1 to T+3 days",
            "flood_next_7d":  "T+1 to T+7 days",
        }[args.target],
        "feature_list": feature_list,
        "excluded_columns": sorted(EXCLUDED_COLS),
        "label_definition": (
            "1 if any day in the future window has observed_flood_today=1 "
            "(flooded_area_pct_of_district >= --flood-area-threshold-pct)."
        ),
        "label_shift_description": (
            "Explicit forward shifts: shift(-h) for each horizon, then max. "
            "Never rolling+shift composition."
        ),
        "positive_class_ratio": pos_ratio,
        "imbalance_strategy": "BalancedRandomForestClassifier",
        "calibration_method": args.calibrate,
        "calibration_api": calibration_api,
        "calibration_fit_policy": "fit_train, calibration_train, and test are disjoint row sets",
        "train_date_range": train_range,
        "test_date_range": test_range,
        "dataset_rows": int(len(df)),
        "dataset_districts": int(df["district_id"].nunique()),
        "metrics_path": str(metrics_path),
        "base_artifact_path": str(base_path),
        "calibrated_artifact_path": str(cal_path),
        "data_sources": {
            "rainfall": "IMERG (NASA) + CHIRPS (UCSB)",
            "discharge": "GloFAS (Copernicus EMS)",
            "boundaries": "HDX COD-AB Pakistan",
            "labels": "UNOSAT / HDX flood extents",
            "elevation": "SRTM / Copernicus DEM",
            "rivers": "HydroRIVERS (HydroSHEDS)",
            "population": "WorldPop",
        },
        "zonal_stats_method": "rasterstats.zonal_stats parallelised via joblib.Parallel",
        "metric_crs": "EPSG:6933 (default, national equal-area; configurable via --metric-crs)",
        "continuous_date_index_policy": "Each district reindexed to a complete daily date range before lag/rolling features",
        "missing_day_fill_policy": "rainfall → 0; static → ffill+bfill; missingness flags preserved",
        "leakage_prevention_notes": [
            "Target columns (flood_next_24h/72h/7d) excluded from feature matrix",
            "observed_flood_today excluded from feature matrix",
            "Rolling windows are trailing-only (no center=True)",
            "Future-window labels generated by explicit forward shifts",
        ],
        "trained_at_iso": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Educational decision-support prototype. Not an authoritative emergency alert.",
            "Coverage limited to Pakistan districts; not extrapolatable to neighbouring countries.",
            "Performance depends on completeness of UNOSAT label coverage during the training period.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f"[train] PR-AUC(cal)={cal['pr_auc']:.3f}  F1(cal)={cal['f1']:.3f}  Brier(cal)={cal['brier']:.3f}")
    print(f"[train] artifacts → {base_path}, {cal_path}")
    print(f"[train] metrics   → {metrics_path}")
    print(f"[train] metadata  → {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
