"""Convert zone_grid_points rows into a GeoJSON FeatureCollection."""

from __future__ import annotations

from datetime import datetime

from app.core.config import settings

RISK_SCORE: dict[str, int] = {
    "Low":      1,
    "Moderate": 2,
    "High":     3,
    "Severe":   4,
}

_MODEL_FEATURES = [
    "precipitation", "precip_3day_avg", "precip_7day_avg",
    "pressure", "temperature", "temp_3day_avg",
    "soil_moisture", "soil_3day_avg", "wind_speed",
    "humidity", "evaporation", "is_monsoon",
    "month", "day_of_year",
]


def _iso(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def points_to_geojson(
    points: list[dict],
    computed_at,
    is_fresh: bool,
) -> dict:
    """
    Build a GeoJSON FeatureCollection from zone_grid_points rows.

    Each feature carries the full prediction output, all 14 model inputs,
    and the top-3 importance drivers so the frontend explainer panel can
    read everything from feature.properties without extra API calls.

    Args:
        points:      List of dicts from ZoneRepository.get_latest_zone_points()
        computed_at: datetime or ISO string of when the batch completed
        is_fresh:    Whether the cache is still within ZONE_CACHE_TTL_MINUTES
    """
    features = []
    for p in points:
        risk = p.get("risk_level", "Unknown")
        features.append({
            "type": "Feature",
            "geometry": {
                "type":        "Point",
                "coordinates": [p["lng"], p["lat"]],   # GeoJSON: [lng, lat]
            },
            "properties": {
                # ── Prediction outputs ────────────────────────────────────
                "flood_prob":  p.get("flood_prob"),
                "risk_level":  risk,
                "risk_score":  RISK_SCORE.get(risk, 0),
                "confidence":  p.get("confidence"),

                # ── 14 model input features ───────────────────────────────
                "precipitation":   _round(p.get("precipitation"), 3),
                "precip_3day_avg": _round(p.get("precip_3day_avg"), 3),
                "precip_7day_avg": _round(p.get("precip_7day_avg"), 3),
                "pressure":        _round(p.get("pressure"), 1),
                "temperature":     _round(p.get("temperature"), 1),
                "temp_3day_avg":   _round(p.get("temp_3day_avg"), 1),
                "soil_moisture":   _round(p.get("soil_moisture"), 4),
                "soil_3day_avg":   _round(p.get("soil_3day_avg"), 4),
                "wind_speed":      _round(p.get("wind_speed"), 2),
                "humidity":        _round(p.get("humidity"), 1),
                "evaporation":     _round(p.get("evaporation"), 4),
                "is_monsoon":      int(p.get("is_monsoon", 0)),
                "month":           int(p.get("month", 0)),
                "day_of_year":     int(p.get("day_of_year", 0)),

                # ── Top-3 importance drivers ──────────────────────────────
                "top_factors": [
                    {
                        "name":       p.get("top_feature_1_name", ""),
                        "value":      p.get("top_feature_1_value"),
                        "importance": p.get("top_feature_1_imp"),
                    },
                    {
                        "name":       p.get("top_feature_2_name", ""),
                        "value":      p.get("top_feature_2_value"),
                        "importance": p.get("top_feature_2_imp"),
                    },
                    {
                        "name":       p.get("top_feature_3_name", ""),
                        "value":      p.get("top_feature_3_value"),
                        "importance": p.get("top_feature_3_imp"),
                    },
                ],

                # ── Metadata ──────────────────────────────────────────────
                "computed_at":    _iso(p.get("computed_at", "")),
                "weather_source": p.get("weather_source", "open-meteo"),
            },
        })

    return {
        "type":     "FeatureCollection",
        "features": features,
        "metadata": {
            "computed_at":       _iso(computed_at),
            "is_fresh":          is_fresh,
            "total_points":      len(features),
            "grid_step_degrees": settings.GRID_STEP_DEGREES,
            "model_features":    _MODEL_FEATURES,
        },
    }


def single_point_to_geojson(lat: float, lng: float, prediction: dict) -> dict:
    """
    Wrap a single-point prediction as a GeoJSON Feature.

    prediction dict must have: risk_level, flood_prob (or risk_score),
    confidence, top_factors, disclaimer.
    Used by the /risk/by-location endpoint.
    """
    risk = prediction.get("risk_level", "Unknown")
    return {
        "type": "Feature",
        "geometry": {
            "type":        "Point",
            "coordinates": [lng, lat],
        },
        "properties": {
            "flood_prob":  prediction.get("flood_prob", prediction.get("risk_score")),
            "risk_level":  risk,
            "risk_score":  RISK_SCORE.get(risk, 0),
            "confidence":  prediction.get("confidence"),
            "top_factors": prediction.get("top_factors", []),
            "disclaimer":  prediction.get("disclaimer", ""),
            "weather_features": prediction.get("weather_features", {}),
        },
    }


def _round(value, ndigits: int):
    if value is None:
        return None
    return round(float(value), ndigits)
