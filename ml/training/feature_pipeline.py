"""
Synthetic feature pipeline for Phase 4 baseline model training.

Generates a 300-row dataset (30 samples per district × 10 districts) with
realistic static and dynamic features. Labels are deterministic from a risk
formula, with 15% random noise injected to make the task non-trivial.

This is educational synthetic data — not real sensor readings.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# Mirrors backend/app/hazards/flood/features.py — must stay in sync
FEATURE_NAMES: list[str] = [
    "elevation_mean_m",
    "slope_mean_deg",
    "distance_to_river_km",
    "historical_flood_count",
    "population_exposure_score",
    "rainfall_1d_mm",
    "rainfall_3d_mm",
    "rainfall_7d_mm",
    "rainfall_anomaly_pct",
    "river_discharge_m3s",
    "source_freshness_score",
]

# Static geographic baseline per district (same as backend features.py)
_DISTRICT_STATIC: dict[str, dict[str, float]] = {
    "PK-SD-SKR": {"elevation_mean_m": 60.0,   "slope_mean_deg": 0.3, "distance_to_river_km": 1.2,  "historical_flood_count": 8, "population_exposure_score": 0.82},
    "PK-SD-JCB": {"elevation_mean_m": 56.0,   "slope_mean_deg": 0.2, "distance_to_river_km": 3.5,  "historical_flood_count": 7, "population_exposure_score": 0.75},
    "PK-SD-LRK": {"elevation_mean_m": 45.0,   "slope_mean_deg": 0.2, "distance_to_river_km": 2.0,  "historical_flood_count": 9, "population_exposure_score": 0.80},
    "PK-PB-MUL": {"elevation_mean_m": 110.0,  "slope_mean_deg": 0.8, "distance_to_river_km": 4.5,  "historical_flood_count": 6, "population_exposure_score": 0.88},
    "PK-PB-RWP": {"elevation_mean_m": 508.0,  "slope_mean_deg": 4.2, "distance_to_river_km": 6.0,  "historical_flood_count": 3, "population_exposure_score": 0.90},
    "PK-PB-LHR": {"elevation_mean_m": 217.0,  "slope_mean_deg": 0.5, "distance_to_river_km": 5.5,  "historical_flood_count": 4, "population_exposure_score": 0.95},
    "PK-KP-PSH": {"elevation_mean_m": 350.0,  "slope_mean_deg": 2.1, "distance_to_river_km": 3.0,  "historical_flood_count": 5, "population_exposure_score": 0.85},
    "PK-BL-QTA": {"elevation_mean_m": 1680.0, "slope_mean_deg": 3.5, "distance_to_river_km": 25.0, "historical_flood_count": 1, "population_exposure_score": 0.60},
    "PK-BL-NAS": {"elevation_mean_m": 65.0,   "slope_mean_deg": 0.4, "distance_to_river_km": 4.0,  "historical_flood_count": 6, "population_exposure_score": 0.55},
    "PK-GB-GIL": {"elevation_mean_m": 1500.0, "slope_mean_deg": 8.0, "distance_to_river_km": 0.8,  "historical_flood_count": 4, "population_exposure_score": 0.40},
}

DISTRICT_IDS = list(_DISTRICT_STATIC.keys())
SAMPLES_PER_DISTRICT = 30
NOISE_RATE = 0.15  # 15% label flip rate

# Risk label encoding (matches rules.py thresholds)
LABEL_TO_LEVEL = {0: "Low", 1: "Moderate", 2: "High", 3: "Severe"}


@dataclass
class FloodDataset:
    X: list[list[float]] = field(default_factory=list)
    y: list[int] = field(default_factory=list)
    district_ids: list[str] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=lambda: list(FEATURE_NAMES))

    def __len__(self) -> int:
        return len(self.y)


def _sample_dynamic(rng: random.Random, rainfall_intensity: float) -> dict[str, float]:
    """Generate dynamic features given a rainfall intensity multiplier [0, 1]."""
    r1 = max(0.0, rainfall_intensity * 80 + rng.gauss(0, 8))
    r3 = max(0.0, r1 * 2.5 + rng.gauss(0, 15))
    r7 = max(0.0, r3 * 2.0 + rng.gauss(0, 25))
    anomaly = (rainfall_intensity - 0.5) * 200 + rng.gauss(0, 20)
    discharge = max(50.0, rainfall_intensity * 8000 + rng.gauss(0, 500))
    freshness = max(0.0, min(1.0, 0.6 + rng.gauss(0, 0.15)))
    return {
        "rainfall_1d_mm": round(r1, 2),
        "rainfall_3d_mm": round(r3, 2),
        "rainfall_7d_mm": round(r7, 2),
        "rainfall_anomaly_pct": round(anomaly, 2),
        "river_discharge_m3s": round(discharge, 2),
        "source_freshness_score": round(freshness, 3),
    }


def _compute_risk_score(static: dict[str, float], dynamic: dict[str, float]) -> float:
    """
    Deterministic risk score in [0, 1] from features.

    Higher score → more severe risk. Formula weights:
      - Proximity to river: 25% (lower km → higher risk)
      - Rainfall (7d):      20%
      - Historical count:   20%
      - Elevation:          15% (lower → higher risk for plains)
      - Rainfall anomaly:   10%
      - River discharge:    10%
    """
    river_prox = max(0.0, 1.0 - static["distance_to_river_km"] / 30.0)  # 30 km ceiling
    elevation_risk = max(0.0, 1.0 - static["elevation_mean_m"] / 2000.0)
    flood_history = min(1.0, static["historical_flood_count"] / 10.0)
    rainfall_7d = min(1.0, dynamic["rainfall_7d_mm"] / 400.0)
    anomaly = min(1.0, max(0.0, (dynamic["rainfall_anomaly_pct"] + 100) / 300.0))
    discharge = min(1.0, dynamic["river_discharge_m3s"] / 12000.0)

    score = (
        0.25 * river_prox
        + 0.20 * rainfall_7d
        + 0.20 * flood_history
        + 0.15 * elevation_risk
        + 0.10 * anomaly
        + 0.10 * discharge
    )
    return min(1.0, max(0.0, score))


def _score_to_label(score: float) -> int:
    if score < 0.30:
        return 0  # Low
    if score < 0.55:
        return 1  # Moderate
    if score < 0.75:
        return 2  # High
    return 3  # Severe


def generate_dataset(
    seed: int = 42,
    inject_rainfall: dict[str, dict[str, float]] | None = None,
) -> FloodDataset:
    """
    Generate the full 300-row synthetic training dataset.

    Reproducible with a fixed seed. Each district contributes 30 samples
    across a range of rainfall intensities to ensure class diversity.

    inject_rainfall — optional mapping of district_id → dynamic feature dict
    from a real adapter (e.g. IMERGAdapter normalized output). When provided,
    one additional row per district is appended using the real observation
    values instead of synthetic sampling. No label noise is applied to real rows.
    All other rows remain synthetic.
    """
    rng = random.Random(seed)
    dataset = FloodDataset()

    for district_id in DISTRICT_IDS:
        static = _DISTRICT_STATIC[district_id]

        # Vary rainfall intensity across samples to produce all 4 risk classes
        intensities = [rng.uniform(0.0, 1.0) for _ in range(SAMPLES_PER_DISTRICT)]

        for intensity in intensities:
            dynamic = _sample_dynamic(rng, intensity)
            score = _compute_risk_score(static, dynamic)
            label = _score_to_label(score)

            # Inject 15% label noise (flip to adjacent class)
            if rng.random() < NOISE_RATE:
                label = max(0, min(3, label + rng.choice([-1, 1])))

            row: dict[str, float] = {**static, **dynamic}
            vector = [row[f] for f in FEATURE_NAMES]

            dataset.X.append(vector)
            dataset.y.append(label)
            dataset.district_ids.append(district_id)

        # Append one real-observation row if adapter data is available for this district
        if inject_rainfall and district_id in inject_rainfall:
            real_dynamic = inject_rainfall[district_id]
            real_row: dict[str, float] = {**static, **real_dynamic}
            if all(f in real_row for f in FEATURE_NAMES):
                real_vector = [real_row[f] for f in FEATURE_NAMES]
                real_label = _score_to_label(_compute_risk_score(static, real_dynamic))
                dataset.X.append(real_vector)
                dataset.y.append(real_label)
                dataset.district_ids.append(district_id)

    return dataset
