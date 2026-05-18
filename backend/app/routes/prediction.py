import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.controllers.prediction_controller import run_prediction
from app.hazards.flood.model import get_flood_model
from app.hazards.flood.rules import DISCLAIMER
from app.models.prediction import PredictionResponse
from app.zones.zone_geojson import single_point_to_geojson
from app.zones.zone_repository import ZoneRepository

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
    Flood risk for any coordinate as a GeoJSON Feature, served from DB cache.

    Returns the nearest pre-computed zone grid point. The grid is refreshed
    every 3 hours by the background scheduler — no live Open-Meteo call is made.
    """
    repo  = ZoneRepository()
    point = await asyncio.to_thread(repo.get_nearest_zone_point, lat, lng)

    if point is None:
        raise HTTPException(
            status_code=503,
            detail="No cached zone data yet — the background scheduler is still computing. Try again in ~10 minutes.",
        )

    top_factors = []
    for i in (1, 2, 3):
        name = point.get(f"top_feature_{i}_name")
        val  = point.get(f"top_feature_{i}_value")
        imp  = point.get(f"top_feature_{i}_imp")
        if name and val is not None and imp is not None:
            top_factors.append({"name": name, "value": float(val), "importance": float(imp)})

    prediction = {
        "flood_prob":  round(float(point["flood_prob"]), 4),
        "risk_level":  point["risk_level"],
        "confidence":  round(float(point["confidence"]), 4),
        "top_factors": top_factors,
        "disclaimer":  DISCLAIMER,
        "cached_at":   point.get("computed_at"),
        "nearest_grid_point": {"lat": point["lat"], "lng": point["lng"]},
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
