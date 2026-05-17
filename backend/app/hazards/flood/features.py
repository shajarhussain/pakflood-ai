"""14 feature columns expected by the XGBoost flood model — order is fixed."""

FEATURE_COLS: list[str] = [
    "precipitation",
    "precip_3day_avg",
    "precip_7day_avg",
    "pressure",
    "temperature",
    "temp_3day_avg",
    "soil_moisture",
    "soil_3day_avg",
    "wind_speed",
    "humidity",
    "evaporation",
    "is_monsoon",
    "month",
    "day_of_year",
]


def build_feature_vector(features: dict[str, float]) -> list[float]:
    """Return feature values in the stable FEATURE_COLS order."""
    return [float(features.get(f, 0.0)) for f in FEATURE_COLS]
