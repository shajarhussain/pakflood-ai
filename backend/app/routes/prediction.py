import httpx
from fastapi import APIRouter, HTTPException, Query

from app.controllers.prediction_controller import run_prediction
from app.hazards.flood.model import get_flood_model
from app.hazards.flood.rules import DISCLAIMER, classify_risk
from app.hazards.flood.features import FEATURE_COLS
from app.models.prediction import PredictionResponse
from app.zones.open_meteo_adapter import fetch_weather_features, features_to_vector
from app.zones.zone_geojson import single_point_to_geojson

router = APIRouter()


@router.get("/predict", response_model=PredictionResponse)
async def predict_flood_risk(
    lat: float = Query(..., ge=-90,  le=90,  description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
) -> PredictionResponse:
    """
    Predict flood risk for any lat/lng.

    Fetches 7-day weather history from Open-Meteo, computes 14 model
    features, runs the XGBoost classifier, and persists the result to Supabase.
    """
    try:
        return await run_prediction(lat, lng)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prediction failed: {exc}") from exc


@router.get("/risk/by-location")
async def risk_by_location(
    lat: float = Query(..., ge=-90,  le=90,  description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
) -> dict:
    """
    Real-time flood risk for any coordinate as a GeoJSON Feature.

    Calls Open-Meteo live → runs XGBoost → returns a GeoJSON Feature
    so the frontend can drop it directly onto a Mapbox/Leaflet layer
    or pass it to Turf.js without any transformation.

    Use for: user GPS location, map click, district centre.
    """
    model = get_flood_model()
    if not model.is_ready:
        raise HTTPException(status_code=503, detail="Model artifact not loaded.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        features = await fetch_weather_features(lat, lng, client)

    if features is None:
        raise HTTPException(
            status_code=503,
            detail="Weather data unavailable for this location.",
        )

    xgb        = model._model
    vector     = features_to_vector(features).reshape(1, -1)
    flood_prob = float(xgb.predict_proba(vector)[0][1])
    risk_level = classify_risk(flood_prob)
    confidence = round(float(2.0 * abs(flood_prob - 0.5)), 4)

    import numpy as np
    imps    = np.array(xgb.feature_importances_)
    top_idx = np.argsort(imps)[-3:][::-1]
    top_factors = [
        {
            "name":       FEATURE_COLS[i],
            "value":      round(float(vector[0][i]), 4),
            "importance": round(float(imps[i]), 4),
        }
        for i in top_idx
    ]

    prediction = {
        "flood_prob":      round(flood_prob, 4),
        "risk_level":      risk_level,
        "confidence":      confidence,
        "top_factors":     top_factors,
        "disclaimer":      DISCLAIMER,
        "weather_features": features,
    }

    return single_point_to_geojson(lat, lng, prediction)


@router.get("/model/status")
def model_status() -> dict:
    """Report whether the XGBoost artifact is loaded."""
    model = get_flood_model()
    return {
        "model_version":  "flood_xgb_pakistan_v2",
        "artifact_ready": model.is_ready,
        "features":       14,
        "disclaimer":     DISCLAIMER,
    }
