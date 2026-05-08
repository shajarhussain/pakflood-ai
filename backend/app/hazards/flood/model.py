"""
FloodPredictionStrategy — implements the HazardModule Protocol.

Loads the trained RandomForest artifact from ml/artifacts/flood_baseline_v1.pkl.
Falls back to rule-based classification if the artifact is missing (e.g., before
the first training run). All sklearn/joblib imports are lazy so the backend
starts cleanly even without ML packages installed.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.hazards.base import (
    DataSourceSpec,
    FeatureFrame,
    HazardModule,
    ModelArtifact,
    RiskAssessment,
    RiskExplanation,
    RiskRequest,
    TrainingConfig,
)
from app.hazards.flood.features import (
    DISTRICT_STATIC_FEATURES,
    FEATURE_NAMES,
    build_feature_vector,
    get_stub_features,
)
from app.hazards.flood.rules import DISCLAIMER, classify_risk

# Resolve artifact path relative to this file (5 hops up to project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_ARTIFACT_PATH = _PROJECT_ROOT / "ml" / "artifacts" / "flood_baseline_v1.pkl"

# District center coordinates for lat/lon → district_id lookup
_DISTRICT_CENTERS: dict[str, tuple[float, float]] = {
    "PK-SD-SKR": (27.70, 68.85),
    "PK-SD-JCB": (28.45, 68.35),
    "PK-SD-LRK": (27.45, 67.90),
    "PK-PB-MUL": (30.30, 71.55),
    "PK-PB-RWP": (33.65, 73.05),
    "PK-PB-LHR": (31.55, 74.40),
    "PK-KP-PSH": (34.10, 71.70),
    "PK-BL-QTA": (30.20, 67.05),
    "PK-BL-NAS": (28.85, 68.15),
    "PK-GB-GIL": (36.00, 74.20),
}


@dataclass
class _ModelBundle:
    model: Any
    feature_names: list[str]
    label_to_level: dict[int, str]
    model_version: str
    top_features: list[str]
    feature_importances: dict[str, float]


def _load_bundle() -> _ModelBundle | None:
    """Attempt to load the trained model bundle. Returns None if unavailable."""
    if not _ARTIFACT_PATH.exists():
        return None
    try:
        import joblib
        raw = joblib.load(_ARTIFACT_PATH)
        return _ModelBundle(
            model=raw["model"],
            feature_names=raw["feature_names"],
            label_to_level={int(k): v for k, v in raw["label_to_level"].items()},
            model_version=raw["model_version"],
            top_features=raw["top_features"],
            feature_importances=raw["feature_importances"],
        )
    except Exception as exc:
        warnings.warn(f"Could not load flood model artifact: {exc}", stacklevel=2)
        return None


def _nearest_district(lat: float, lon: float) -> str:
    """Return the district_id whose center is nearest to (lat, lon)."""
    best_id = "PK-SD-SKR"
    best_dist = float("inf")
    for district_id, (dlat, dlon) in _DISTRICT_CENTERS.items():
        d = math.hypot(lat - dlat, lon - dlon)
        if d < best_dist:
            best_dist = d
            best_id = district_id
    return best_id


def _rule_based_score(features: dict[str, float]) -> float:
    """Simple deterministic score used when the model artifact is absent."""
    river_prox = max(0.0, 1.0 - features.get("distance_to_river_km", 10.0) / 30.0)
    elevation_risk = max(0.0, 1.0 - features.get("elevation_mean_m", 300.0) / 2000.0)
    flood_history = min(1.0, features.get("historical_flood_count", 3.0) / 10.0)
    rainfall_7d = min(1.0, features.get("rainfall_7d_mm", 0.0) / 400.0)
    return min(1.0, 0.30 * river_prox + 0.25 * elevation_risk + 0.25 * flood_history + 0.20 * rainfall_7d)


class FloodPredictionStrategy:
    """Flood risk prediction implementing the HazardModule Protocol."""

    hazard_name: str = "flood"

    def __init__(self) -> None:
        self._bundle: _ModelBundle | None = None
        self._bundle_loaded: bool = False

    # ── Protocol methods ──────────────────────────────────────────────────────

    def get_required_sources(self) -> list[DataSourceSpec]:
        return [
            DataSourceSpec(source_id="imerg", adapter_class="IMERGAdapter"),
            DataSourceSpec(source_id="glofas", adapter_class="GloFASAdapter"),
            DataSourceSpec(source_id="ffd", adapter_class="FFDAdapter"),
        ]

    def build_features(self, location: str, time_window: int) -> FeatureFrame:
        return FeatureFrame(
            features=get_stub_features(location),
            location_id=location,
            time_window_hours=time_window,
        )

    def train(self, config: TrainingConfig) -> ModelArtifact:
        raise NotImplementedError(
            "Run ml/training/train_baseline.py to train the model offline."
        )

    def infer(self, request: RiskRequest) -> RiskAssessment:
        district_id = _nearest_district(request.lat, request.lon)
        return self.infer_by_district_id(district_id)

    def explain(self, assessment: RiskAssessment) -> RiskExplanation:
        actions = {
            "Low": ["Monitor local advisories", "Keep emergency kit ready"],
            "Moderate": ["Prepare evacuation plan", "Monitor river levels", "Contact local PDMA"],
            "High": ["Evacuate low-lying areas", "Follow NDMA instructions", "Avoid river banks"],
            "Severe": ["Immediate evacuation required", "Call emergency services (1122)", "Seek high ground"],
        }
        return RiskExplanation(
            risk_level=assessment.risk_level,
            main_causes=assessment.top_factors,
            historical_evidence=[],
            suggested_actions=actions.get(assessment.risk_level, []),
            confidence=assessment.confidence,
            data_sources=list(assessment.source_status.keys()),
            disclaimer=DISCLAIMER,
        )

    # ── Public helper ─────────────────────────────────────────────────────────

    def infer_by_district_id(
        self,
        district_id: str,
        features: dict[str, float] | None = None,
    ) -> RiskAssessment:
        """Run inference for a specific district.

        features — pre-built complete feature dict (static + dynamic).
        If None, falls back to get_stub_features() (all synthetic).
        """
        bundle = self._get_bundle()
        effective_features = features if features is not None else get_stub_features(district_id)

        if bundle is not None:
            return self._ml_infer(district_id, effective_features, bundle)
        return self._rule_infer(district_id, effective_features)

    def model_version(self) -> str:
        bundle = self._get_bundle()
        return bundle.model_version if bundle else "rule-based-v0"

    def top_features(self) -> list[str]:
        bundle = self._get_bundle()
        return bundle.top_features if bundle else ["distance_to_river_km", "elevation_mean_m", "historical_flood_count"]

    # ── Private ───────────────────────────────────────────────────────────────

    def _get_bundle(self) -> _ModelBundle | None:
        if not self._bundle_loaded:
            self._bundle = _load_bundle()
            self._bundle_loaded = True
        return self._bundle

    def _ml_infer(
        self, district_id: str, features: dict[str, float], bundle: _ModelBundle
    ) -> RiskAssessment:
        import numpy as np

        vector = build_feature_vector(features)
        X = np.array([vector], dtype=np.float32)
        label_idx = int(bundle.model.predict(X)[0])
        probas = bundle.model.predict_proba(X)[0]
        confidence = round(float(probas[label_idx]), 3)
        risk_level = bundle.label_to_level.get(label_idx, "Unknown")
        risk_score = round(float(label_idx) / 3.0, 3)

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            top_factors=bundle.top_features[:3],
            model_version=bundle.model_version,
            source_status={s.source_id: "stale" for s in self.get_required_sources()},
        )

    def _rule_infer(self, district_id: str, features: dict[str, float]) -> RiskAssessment:
        score = _rule_based_score(features)
        risk_level = classify_risk(score)
        return RiskAssessment(
            risk_score=round(score, 3),
            risk_level=risk_level,
            confidence=0.50,
            top_factors=["distance_to_river_km", "elevation_mean_m", "historical_flood_count"],
            model_version="rule-based-v0",
            source_status={s.source_id: "stale" for s in self.get_required_sources()},
        )


# Module-level singleton — created lazily on first import use
_strategy_instance: FloodPredictionStrategy | None = None


def get_flood_strategy() -> FloodPredictionStrategy:
    global _strategy_instance
    if _strategy_instance is None:
        _strategy_instance = FloodPredictionStrategy()
    return _strategy_instance
