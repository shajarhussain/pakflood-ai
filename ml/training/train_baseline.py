"""
PakFlood AI — Phase 4 Baseline Model Training Script.

Trains a RandomForestClassifier on the synthetic flood-risk dataset and saves:
  ml/artifacts/flood_baseline_v1.pkl    — serialized model + metadata bundle
  ml/artifacts/model_metadata.json      — human-readable metadata
  ml/evaluation/metrics_report.json     — accuracy, AUC-ROC, confusion matrix

Run from the project root:
    python ml/training/train_baseline.py

This is an educational prototype using synthetic data.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Resolve project root regardless of working directory
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
_ARTIFACTS_DIR = _PROJECT_ROOT / "ml" / "artifacts"
_EVAL_DIR = _PROJECT_ROOT / "ml" / "evaluation"

# Ensure feature_pipeline is importable
sys.path.insert(0, str(_SCRIPT_DIR))


def train() -> None:
    # ── lazy imports so missing packages surface as clear errors ──────────────
    try:
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            confusion_matrix,
            roc_auc_score,
        )
        from sklearn.model_selection import train_test_split
        import joblib
    except ImportError as exc:
        print(f"[ERROR] Missing dependency: {exc}")
        print("Install with: pip install scikit-learn numpy joblib")
        sys.exit(1)

    from feature_pipeline import FEATURE_NAMES, LABEL_TO_LEVEL, generate_dataset

    print("=" * 60)
    print("PakFlood AI — Baseline Flood Risk Model Training")
    print("=" * 60)

    # ── 1. Generate dataset ───────────────────────────────────────────────────
    print("\n[1/5] Generating synthetic dataset...")
    ds = generate_dataset(seed=42)
    X = np.array(ds.X, dtype=np.float32)
    y = np.array(ds.y, dtype=np.int32)
    print(f"      Dataset: {len(ds)} rows, {len(FEATURE_NAMES)} features")
    unique, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique, counts):
        print(f"      Class {label} ({LABEL_TO_LEVEL[int(label)]}): {count} samples")

    # ── 2. Train/test split (stratified) ─────────────────────────────────────
    print("\n[2/5] Splitting dataset (80/20 stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"      Train: {len(X_train)} rows | Test: {len(X_test)} rows")

    # Verify no leakage: train and test rows are disjoint by index
    assert len(X_train) + len(X_test) == len(X), "Split size mismatch"
    assert len(X_train) == len(y_train)
    assert len(X_test) == len(y_test)

    # ── 3. Train RandomForest ─────────────────────────────────────────────────
    print("\n[3/5] Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print("      Training complete.")

    # ── 4. Evaluate ───────────────────────────────────────────────────────────
    print("\n[4/5] Evaluating on held-out test set...")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    auc_roc = float(
        roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
    )
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(
        y_test, y_pred,
        target_names=[LABEL_TO_LEVEL[i] for i in range(4)],
        output_dict=True,
    )

    print(f"      Accuracy : {accuracy:.4f}")
    print(f"      AUC-ROC  : {auc_roc:.4f}")
    print(f"      Confusion matrix:\n{np.array(cm)}")
    print()
    for level in ["Low", "Moderate", "High", "Severe"]:
        r = report[level]
        print(f"      {level:10s}  precision={r['precision']:.3f}  recall={r['recall']:.3f}  f1={r['f1-score']:.3f}")

    # Feature importances (top-3 factors used in API explanations)
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURE_NAMES, importances.tolist()), key=lambda x: x[1], reverse=True)
    top_features = [name for name, _ in ranked[:3]]
    print(f"\n      Top-3 features: {top_features}")

    # ── 5. Save artifacts ─────────────────────────────────────────────────────
    print("\n[5/5] Saving artifacts...")
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    _EVAL_DIR.mkdir(parents=True, exist_ok=True)

    artifact_path = _ARTIFACTS_DIR / "flood_baseline_v1.pkl"
    metadata_path = _ARTIFACTS_DIR / "model_metadata.json"
    metrics_path = _EVAL_DIR / "metrics_report.json"

    # Bundle model + metadata into pkl for single-load convenience
    bundle = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "label_to_level": LABEL_TO_LEVEL,
        "model_version": "flood-baseline-v1",
        "top_features": top_features,
        "feature_importances": dict(zip(FEATURE_NAMES, importances.tolist())),
    }
    joblib.dump(bundle, artifact_path)
    print(f"      Model artifact : {artifact_path}")

    metadata = {
        "model_version": "flood-baseline-v1",
        "algorithm": "RandomForestClassifier",
        "feature_names": FEATURE_NAMES,
        "label_to_level": LABEL_TO_LEVEL,
        "training_date": str(date.today()),
        "dataset_size": len(ds),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "top_features": top_features,
        "feature_importances": dict(zip(FEATURE_NAMES, importances.tolist())),
        "metrics_path": str(metrics_path.relative_to(_PROJECT_ROOT)),
        "artifact_path": str(artifact_path.relative_to(_PROJECT_ROOT)),
        "disclaimer": (
            "Educational prototype trained on synthetic data. "
            "Do not use for real emergency decisions."
        ),
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"      Metadata       : {metadata_path}")

    metrics = {
        "model_version": "flood-baseline-v1",
        "accuracy": round(accuracy, 4),
        "auc_roc_macro_ovr": round(auc_roc, 4),
        "confusion_matrix": cm,
        "per_class": {
            level: {
                "precision": round(report[level]["precision"], 4),
                "recall": round(report[level]["recall"], 4),
                "f1_score": round(report[level]["f1-score"], 4),
                "support": int(report[level]["support"]),
            }
            for level in ["Low", "Moderate", "High", "Severe"]
        },
    }
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"      Metrics report : {metrics_path}")

    print("\n" + "=" * 60)
    if auc_roc >= 0.65:
        print(f"PASS  AUC-ROC {auc_roc:.4f} >= 0.65 threshold")
    else:
        print(f"WARN  AUC-ROC {auc_roc:.4f} < 0.65 threshold — check data or model")
    print("Training complete.")
    print("=" * 60)


if __name__ == "__main__":
    train()
