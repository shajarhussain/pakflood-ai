"""Gate B-Lite training — BalancedRandomForest + sigmoid calibration on
the public-API real-data CSV produced by build_real_lite_dataset.py.

This is a WEAK-LABEL PROTOTYPE. Labels come from EONET flood event-points
matched to nearest district centroids with a ±N-day window — not satellite
flood extent. It is NOT the strict v3 8-source research-grade model. The
metadata explicitly says so and ``model_name`` is ``flood_prediction_real_lite``.

Artifacts:
  - ml/artifacts/flood_prediction_real_lite.pkl
  - ml/artifacts/flood_prediction_real_lite_metadata.json
  - ml/evaluation/flood_prediction_real_lite_metrics.json
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
    p = argparse.ArgumentParser(
        prog="train_real_lite_model",
        description=(
            "Train BalancedRandomForestClassifier + sigmoid calibration on "
            "the Gate B-Lite real-data CSV. Weak-label public-API prototype."
        ),
    )
    p.add_argument("--dataset", type=Path,
                   default=Path("data/real_lite/training/pakistan_flood_prediction_real_lite.csv"))
    p.add_argument("--target",  default="flood_next_72h",
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
    try:
        from imblearn.ensemble import BalancedRandomForestClassifier
    except ImportError:
        print("ERROR: imbalanced-learn required (pip install imbalanced-learn>=0.12). "
              "No silent fallback.", file=sys.stderr)
        return 4

    df = pd.read_csv(args.dataset, parse_dates=["date"])
    y = df[args.target].astype(int)
    pos = int(y.sum())
    pos_ratio = float(y.mean())
    print(f"[lite-train] rows={len(df):,} positive={pos} ratio={pos_ratio:.4f}")
    if pos < args.min_positive_samples:
        print(f"ERROR: only {pos} positive samples (< --min-positive-samples)", file=sys.stderr)
        return 5

    # Feature matrix
    feature_cols = [c for c in df.columns if c not in EXCLUDED_COLS and c != args.target]
    X = df[feature_cols].copy()
    for c in feature_cols:
        if not pd.api.types.is_numeric_dtype(X[c]):
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.loc[:, X.notna().any(axis=0)].fillna(0.0)
    feature_list = X.columns.tolist()

    # Time-ordered 60/20/20 split
    order = df.sort_values("date").index
    n = len(order)
    idx_fit  = order[: int(n * 0.60)]
    idx_cal  = order[int(n * 0.60): int(n * 0.80)]
    idx_test = order[int(n * 0.80):]
    X_fit,  y_fit  = X.loc[idx_fit],  y.loc[idx_fit]
    X_cal,  y_cal  = X.loc[idx_cal],  y.loc[idx_cal]
    X_test, y_test = X.loc[idx_test], y.loc[idx_test]
    print(f"[lite-train] split  fit={len(X_fit):,}  cal={len(X_cal):,}  test={len(X_test):,}  "
          f"pos_fit={int(y_fit.sum())} pos_cal={int(y_cal.sum())} pos_test={int(y_test.sum())}")

    if y_fit.sum() == 0 or y_test.sum() == 0:
        # Time-holdout has no positives in one split — fall back to stratified.
        from sklearn.model_selection import StratifiedShuffleSplit
        print("[lite-train] time-holdout had a zero-positive split; falling back to stratified",
              flush=True)
        sss1 = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        pool_pos, test_pos = next(sss1.split(X, y))
        sss2 = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        fit_pos, cal_pos = next(sss2.split(X.iloc[pool_pos], y.iloc[pool_pos]))
        idx_fit  = X.index[pool_pos][fit_pos]
        idx_cal  = X.index[pool_pos][cal_pos]
        idx_test = X.index[test_pos]
        X_fit,  y_fit  = X.loc[idx_fit],  y.loc[idx_fit]
        X_cal,  y_cal  = X.loc[idx_cal],  y.loc[idx_cal]
        X_test, y_test = X.loc[idx_test], y.loc[idx_test]
        print(f"[lite-train] stratified split  fit={len(X_fit):,}  cal={len(X_cal):,}  test={len(X_test):,}  "
              f"pos_fit={int(y_fit.sum())} pos_cal={int(y_cal.sum())} pos_test={int(y_test.sum())}")

    base = BalancedRandomForestClassifier(
        n_estimators=400, max_depth=None, random_state=42, n_jobs=-1,
    )
    base.fit(X_fit, y_fit)

    try:
        from sklearn.frozen import FrozenEstimator
        calibrated = CalibratedClassifierCV(FrozenEstimator(base), method=args.calibrate).fit(X_cal, y_cal)
        calibration_api = "FrozenEstimator"
    except ImportError:
        calibrated = CalibratedClassifierCV(base, method=args.calibrate, cv="prefit").fit(X_cal, y_cal)
        calibration_api = "cv_prefit_compatibility_fallback"

    def _eval(model, X_eval, y_eval) -> dict:
        proba = model.predict_proba(X_eval)[:, 1]
        pred = (proba >= 0.5).astype(int)
        return {
            "pr_auc": float(average_precision_score(y_eval, proba)),
            "f1": float(f1_score(y_eval, pred, zero_division=0)),
            "precision": float(precision_score(y_eval, pred, zero_division=0)),
            "recall": float(recall_score(y_eval, pred, zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(y_eval, pred)),
            "brier": float(brier_score_loss(y_eval, proba)),
            "roc_auc": float(roc_auc_score(y_eval, proba)) if y_eval.nunique() > 1 else None,
            "accuracy": float(accuracy_score(y_eval, pred)),
            "confusion_matrix": confusion_matrix(y_eval, pred).tolist(),
            "classification_report": classification_report(y_eval, pred, zero_division=0, output_dict=True),
        }

    metrics = {
        "primary":      _eval(calibrated, X_test, y_test),
        "uncalibrated": _eval(base,       X_test, y_test),
        "positive_class_ratio_test": float(y_test.mean()),
        "baseline_majority_class_accuracy": float((y_test == y_test.mode().iloc[0]).mean()),
        "calibration_api": calibration_api,
        "calibration_method": args.calibrate,
    }

    # Reliability table
    proba = calibrated.predict_proba(X_test)[:, 1]
    bins = np.linspace(0, 1, 11)
    bin_idx = np.clip(np.digitize(proba, bins) - 1, 0, 9)
    reliability = []
    for b in range(10):
        mask = bin_idx == b
        if mask.sum() == 0:
            reliability.append({"bin": b, "count": 0})
        else:
            reliability.append({
                "bin": b,
                "count": int(mask.sum()),
                "mean_pred": float(proba[mask].mean()),
                "frac_positive": float(y_test.iloc[mask].mean()),
            })
    metrics["reliability_table"] = reliability

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_dir.mkdir(parents=True, exist_ok=True)
    artifact_path  = args.output_dir / "flood_prediction_real_lite.pkl"
    metadata_path  = args.output_dir / "flood_prediction_real_lite_metadata.json"
    metrics_path   = args.metrics_dir / "flood_prediction_real_lite_metrics.json"

    joblib.dump({
        "model": calibrated, "feature_list": feature_list,
        "calibration_method": args.calibrate,
        "calibration_api": calibration_api,
    }, artifact_path)
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str))

    metadata = {
        "model_name": "flood_prediction_real_lite",
        "model_type": "BalancedRandomForestClassifier + sigmoid CalibratedClassifierCV",
        "model_scope": "public API weak-label prototype",
        "is_prediction_model": True,
        "is_detection_model": False,
        "prediction_summary": (
            "Real prediction model v3-lite — public API / weak-label prototype. "
            "This model predicts flood probability for a future window using real "
            "NASA POWER daily weather and EONET flood event-points as weak labels. "
            "It is NOT the strict 8-source research-grade v3 model."
        ),
        "data_sources": {
            "boundaries": "geoBoundaries gbOpen PAK ADM2",
            "weather":    "NASA POWER Daily API (PRECTOTCORR, T2M, RH2M, WS10M)",
            "labels":     "NASA EONET v3 flood events, nearest-district matching",
        },
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
        "limitations": [
            "Weak labels: derived from EONET flood event-points, not satellite-flagged flood extents.",
            "Only 10 district centroids covered; full Pakistan coverage requires strict v3 8-source pipeline.",
            "Positive class is extremely rare (~0.15%); recall/precision should be interpreted cautiously.",
            "This is NOT the research-grade v3 model — see docs/13_real_flood_prediction_pipeline_v3.md.",
        ],
        "next_step_to_research_grade_v3": "Run the strict v3 Gate B (docs/13 + docs/14).",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f"[lite-train] PR-AUC(cal)={metrics['primary']['pr_auc']:.3f}  "
          f"F1={metrics['primary']['f1']:.3f}  "
          f"Brier={metrics['primary']['brier']:.4f}")
    print(f"[lite-train] artifact → {artifact_path}")
    print(f"[lite-train] metadata → {metadata_path}")
    print(f"[lite-train] metrics  → {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
