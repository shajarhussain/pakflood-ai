"""XGBoost flood prediction model — lazy singleton loader."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from app.hazards.flood.features import FEATURE_COLS
from app.hazards.flood.rules import DISCLAIMER, classify_risk

MODEL_VERSION = "flood_xgb_pakistan_v2"


def _find_artifact() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / "ml" / "artifacts" / f"{MODEL_VERSION}.pkl"
        if candidate.exists():
            return candidate
    return Path.cwd() / "ml" / "artifacts" / f"{MODEL_VERSION}.pkl"


class FloodModel:
    def __init__(self) -> None:
        self._model = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        path = _find_artifact()
        if not path.exists():
            warnings.warn(
                f"Flood model artifact not found at {path}. "
                "Predictions will return risk_level='Unknown'. "
                "Place flood_xgb_pakistan_v2.pkl in ml/artifacts/.",
                stacklevel=2,
            )
            return
        try:
            import joblib
            self._model = joblib.load(path)
        except Exception as exc:
            warnings.warn(f"Failed to load flood model: {exc}", stacklevel=2)

    def predict(self, features: dict[str, float]) -> dict:
        self._load()

        vec = np.array(
            [[features.get(f, 0.0) for f in FEATURE_COLS]], dtype=np.float32
        )

        if self._model is None:
            return {
                "flood_probability": 0.5,
                "risk_level": "Unknown",
                "confidence": 0.0,
                "top_factors": [],
                "model_version": f"{MODEL_VERSION} (unavailable)",
                "disclaimer": DISCLAIMER,
            }

        prob = float(self._model.predict_proba(vec)[0][1])
        risk_level = classify_risk(prob)
        confidence = round(2.0 * abs(prob - 0.5), 4)

        importances = self._model.feature_importances_
        top_idx = np.argsort(importances)[-3:][::-1]
        top_factors = [
            {
                "name": FEATURE_COLS[i],
                "value": round(float(vec[0][i]), 4),
                "importance": round(float(importances[i]), 4),
            }
            for i in top_idx
        ]

        return {
            "flood_probability": round(prob, 4),
            "risk_level": risk_level,
            "confidence": confidence,
            "top_factors": top_factors,
            "model_version": MODEL_VERSION,
            "disclaimer": DISCLAIMER,
        }

    @property
    def is_ready(self) -> bool:
        self._load()
        return self._model is not None


_instance: FloodModel | None = None


def get_flood_model() -> FloodModel:
    global _instance
    if _instance is None:
        _instance = FloodModel()
    return _instance
