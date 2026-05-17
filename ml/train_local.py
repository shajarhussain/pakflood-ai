"""
Run this once from the project root to build flood_xgb_pakistan_v2.pkl.
  python ml/train_local.py
"""
import json
import os
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    precision_score, recall_score,
)

warnings.filterwarnings("ignore")

ROOT      = Path(__file__).resolve().parent.parent   # pakflood-ai/
DATA_PATH = ROOT / "ml" / "notebooks" / "pakistan_flood_complete_dataset.csv"
# Output inside backend/ so the artifact is included in Render deployments
OUT_DIR   = ROOT / "backend" / "ml" / "artifacts"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = OUT_DIR / "flood_xgb_pakistan_v2.pkl"
META_PATH  = OUT_DIR / "model_metadata.json"

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"Loaded: {df.shape[0]} rows × {df.shape[1]} columns")

FEATURE_COLS = [
    "precipitation", "precip_3day_avg", "precip_7day_avg",
    "pressure", "temperature", "temp_3day_avg",
    "soil_moisture", "soil_3day_avg", "wind_speed",
    "humidity", "evaporation", "is_monsoon", "month", "day_of_year",
]
TARGET_COL = "flood_event"

X = df[FEATURE_COLS].fillna(df[FEATURE_COLS].median()).values
y = df[TARGET_COL].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale_pos_w = neg / pos
print(f"Train {X_train.shape[0]} rows | scale_pos_weight={scale_pos_w:.2f}")

# ── Train ─────────────────────────────────────────────────────────────────────
model = XGBClassifier(
    n_estimators=500, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.7,
    min_child_weight=5, gamma=0.2, reg_alpha=0.5, reg_lambda=2.0,
    objective="binary:logistic", eval_metric="auc",
    scale_pos_weight=scale_pos_w,
    tree_method="hist", n_jobs=-1, random_state=42,
    early_stopping_rounds=40, verbosity=0,
)
print("Training XGBoost ...")
model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    verbose=False,
)
print(f"Done. Best iteration: {model.best_iteration}")

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy  = accuracy_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred, average="macro")
auc       = roc_auc_score(y_test, y_prob)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)

print(f"Accuracy: {accuracy*100:.1f}%  AUC: {auc:.4f}  F1: {f1:.4f}")

cv_model = XGBClassifier(
    n_estimators=300, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.7,
    min_child_weight=5, gamma=0.2, reg_alpha=0.5, reg_lambda=2.0,
    objective="binary:logistic",
    scale_pos_weight=scale_pos_w,
    tree_method="hist", n_jobs=-1, random_state=42, verbosity=0,
)
cv_acc = cross_val_score(
    cv_model, X, y,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    scoring="accuracy",
)
print(f"CV Accuracy: {cv_acc.mean()*100:.1f}% ± {cv_acc.std()*100:.1f}%")

# ── Save model ────────────────────────────────────────────────────────────────
joblib.dump(model, MODEL_PATH)
print(f"Model saved: {MODEL_PATH}  ({MODEL_PATH.stat().st_size/1024:.1f} KB)")

# ── Save metadata ─────────────────────────────────────────────────────────────
top3 = sorted(
    zip(FEATURE_COLS, model.feature_importances_),
    key=lambda x: x[1], reverse=True,
)[:3]

metadata = {
    "model_version":  "v2",
    "model_type":     "XGBClassifier_binary",
    "training_date":  datetime.now().strftime("%Y-%m-%d"),
    "feature_names":  FEATURE_COLS,
    "n_features":     len(FEATURE_COLS),
    "training_data": {
        "total_rows": int(len(df)),
        "train_rows": int(X_train.shape[0]),
        "test_rows":  int(X_test.shape[0]),
    },
    "evaluation": {
        "test_accuracy":  round(float(accuracy), 4),
        "test_f1_macro":  round(float(f1), 4),
        "test_auc_roc":   round(float(auc), 4),
        "test_precision": round(float(precision), 4),
        "test_recall":    round(float(recall), 4),
        "cv_accuracy":    round(float(cv_acc.mean()), 4),
        "cv_std":         round(float(cv_acc.std()), 4),
    },
    "top_3_features": [f for f, _ in top3],
    "feature_importances": {
        f: round(float(imp), 6)
        for f, imp in zip(FEATURE_COLS, model.feature_importances_)
    },
}

with open(META_PATH, "w") as fh:
    json.dump(metadata, fh, indent=2)
print(f"Metadata saved: {META_PATH}")
print("Done — place flood_xgb_pakistan_v2.pkl in ml/artifacts/ (already there).")
