from pydantic import BaseModel, Field

from app.hazards.flood.rules import DISCLAIMER


class TopFactor(BaseModel):
    name: str
    value: float
    importance: float


class PredictionResponse(BaseModel):
    latitude: float
    longitude: float
    nearest_grid_lat: float   # actual grid point used for prediction
    nearest_grid_lng: float   # snap the map pin to this, not the raw input
    flood_probability: float = Field(ge=0.0, le=1.0)
    risk_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_factors: list[TopFactor]
    weather_features: dict[str, float]
    model_version: str
    saved_to_db: bool = False
    disclaimer: str = DISCLAIMER
