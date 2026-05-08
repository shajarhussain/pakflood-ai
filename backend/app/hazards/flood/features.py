"""Flood risk feature schema, district static data, and feature utilities."""

from __future__ import annotations

# Ordered feature list — position must stay stable (model artifact depends on this order)
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

# Static geographic/historical features per district (values from HDX, USGS, PMD records)
DISTRICT_STATIC_FEATURES: dict[str, dict[str, float]] = {
    "PK-SD-SKR": {  # Sukkur, Sindh — Indus crossing, flood-prone floodplain
        "elevation_mean_m": 60.0,
        "slope_mean_deg": 0.3,
        "distance_to_river_km": 1.2,
        "historical_flood_count": 8,
        "population_exposure_score": 0.82,
    },
    "PK-SD-JCB": {  # Jacobabad, Sindh — extremely flat, near Indus
        "elevation_mean_m": 56.0,
        "slope_mean_deg": 0.2,
        "distance_to_river_km": 3.5,
        "historical_flood_count": 7,
        "population_exposure_score": 0.75,
    },
    "PK-SD-LRK": {  # Larkana, Sindh — Indus floodplain, major 2010 inundation
        "elevation_mean_m": 45.0,
        "slope_mean_deg": 0.2,
        "distance_to_river_km": 2.0,
        "historical_flood_count": 9,
        "population_exposure_score": 0.80,
    },
    "PK-PB-MUL": {  # Multan, Punjab — Chenab + Indus confluence zone
        "elevation_mean_m": 110.0,
        "slope_mean_deg": 0.8,
        "distance_to_river_km": 4.5,
        "historical_flood_count": 6,
        "population_exposure_score": 0.88,
    },
    "PK-PB-RWP": {  # Rawalpindi, Punjab — sub-mountain, flash flood risk
        "elevation_mean_m": 508.0,
        "slope_mean_deg": 4.2,
        "distance_to_river_km": 6.0,
        "historical_flood_count": 3,
        "population_exposure_score": 0.90,
    },
    "PK-PB-LHR": {  # Lahore, Punjab — Ravi river floodplain
        "elevation_mean_m": 217.0,
        "slope_mean_deg": 0.5,
        "distance_to_river_km": 5.5,
        "historical_flood_count": 4,
        "population_exposure_score": 0.95,
    },
    "PK-KP-PSH": {  # Peshawar, KPK — Kabul river valley
        "elevation_mean_m": 350.0,
        "slope_mean_deg": 2.1,
        "distance_to_river_km": 3.0,
        "historical_flood_count": 5,
        "population_exposure_score": 0.85,
    },
    "PK-BL-QTA": {  # Quetta, Balochistan — high plateau, low flood risk
        "elevation_mean_m": 1680.0,
        "slope_mean_deg": 3.5,
        "distance_to_river_km": 25.0,
        "historical_flood_count": 1,
        "population_exposure_score": 0.60,
    },
    "PK-BL-NAS": {  # Naseerabad, Balochistan — flat, prone to flash floods
        "elevation_mean_m": 65.0,
        "slope_mean_deg": 0.4,
        "distance_to_river_km": 4.0,
        "historical_flood_count": 6,
        "population_exposure_score": 0.55,
    },
    "PK-GB-GIL": {  # Gilgit, GB — mountain valley, GLOF risk
        "elevation_mean_m": 1500.0,
        "slope_mean_deg": 8.0,
        "distance_to_river_km": 0.8,
        "historical_flood_count": 4,
        "population_exposure_score": 0.40,
    },
}

# Default stub dynamic features — used when live adapters are unavailable
_STUB_DYNAMIC: dict[str, float] = {
    "rainfall_1d_mm": 0.0,
    "rainfall_3d_mm": 5.0,
    "rainfall_7d_mm": 12.0,
    "rainfall_anomaly_pct": 0.0,
    "river_discharge_m3s": 500.0,
    "source_freshness_score": 0.3,
}


def get_stub_features(district_id: str) -> dict[str, float]:
    """Return a complete feature dict for a district using static + stub dynamic values."""
    static = DISTRICT_STATIC_FEATURES.get(district_id, _default_static())
    return {**static, **_STUB_DYNAMIC}


def validate_features(features: dict[str, float]) -> None:
    """Raise ValueError if any required feature is missing."""
    missing = [f for f in FEATURE_NAMES if f not in features]
    if missing:
        raise ValueError(f"Missing required features: {missing}")


def build_feature_vector(features: dict[str, float]) -> list[float]:
    """Return feature values in the stable FEATURE_NAMES order."""
    validate_features(features)
    return [float(features[f]) for f in FEATURE_NAMES]


def _default_static() -> dict[str, float]:
    """Fallback static features for unknown districts (Pakistan average)."""
    return {
        "elevation_mean_m": 300.0,
        "slope_mean_deg": 1.5,
        "distance_to_river_km": 10.0,
        "historical_flood_count": 3,
        "population_exposure_score": 0.5,
    }


def build_chirps_anomaly(
    district_id: str,
    chirps_result: object | None = None,
) -> dict[str, float]:
    """Extract rainfall_anomaly_pct from a CHIRPS AdapterResult for one district.

    Returns {"rainfall_anomaly_pct": <value>} when the adapter has usable data,
    or an empty dict on any failure/missing condition — the empty dict is intentional
    so callers can safely apply it as an override without erasing other features.

    CHIRPS field is anomaly_pct; this function maps it to the feature name rainfall_anomaly_pct.
    """
    if chirps_result is None:
        return {}

    status = getattr(chirps_result, "status", "stale")
    data: list[dict] = getattr(chirps_result, "data", []) or []

    record: dict | None = next(
        (row for row in data if row.get("district_id") == district_id), None
    )

    if record is None or status not in ("fresh", "stale"):
        return {}

    anomaly = record.get("anomaly_pct")
    if anomaly is None:
        return {}

    return {"rainfall_anomaly_pct": float(anomaly)}


def build_glofas_discharge(
    district_id: str,
    glofas_result: object | None = None,
) -> dict[str, float]:
    """Extract river_discharge_m3s from a GloFAS AdapterResult for one district.

    Returns {"river_discharge_m3s": float} when the adapter has usable data,
    or an empty dict on any failure — empty dict preserves IMERG/CHIRPS features intact.

    GloFAS field is river_discharge_m3s (matches feature name directly).
    """
    if glofas_result is None:
        return {}

    status = getattr(glofas_result, "status", "stale")
    data: list[dict] = getattr(glofas_result, "data", []) or []

    record: dict | None = next(
        (row for row in data if row.get("district_id") == district_id), None
    )

    if record is None or status not in ("fresh", "stale"):
        return {}

    discharge = record.get("river_discharge_m3s")
    if discharge is None:
        return {}

    return {"river_discharge_m3s": float(discharge)}


def build_rainfall_features(
    district_id: str,
    imerg_result: object | None = None,
) -> dict[str, float]:
    """Extract rainfall features from an IMERG AdapterResult for one district.

    Falls back to _STUB_DYNAMIC values when imerg_result is None, stale/error,
    or the district is not present in the payload.
    river_discharge_m3s and source_freshness_score are always from _STUB_DYNAMIC
    because IMERG does not carry those fields.
    """
    _RAINFALL_KEYS = ("rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_anomaly_pct")

    if imerg_result is None:
        return dict(_STUB_DYNAMIC)

    # Duck-type access: AdapterResult has .status and .data (list[dict])
    status = getattr(imerg_result, "status", "stale")
    data: list[dict] = getattr(imerg_result, "data", []) or []

    record: dict | None = next(
        (row for row in data if row.get("district_id") == district_id), None
    )

    if record is None or status not in ("fresh", "stale"):
        return dict(_STUB_DYNAMIC)

    rainfall = {k: float(record.get(k, _STUB_DYNAMIC[k])) for k in _RAINFALL_KEYS}
    # Derive freshness from adapter confidence; fall back to stub default
    confidence = float(record.get("confidence", 0.0))
    return {
        **rainfall,
        "river_discharge_m3s": _STUB_DYNAMIC["river_discharge_m3s"],
        "source_freshness_score": confidence if confidence > 0.0 else _STUB_DYNAMIC["source_freshness_score"],
    }
