from pydantic import BaseModel, Field

from app.hazards.flood.rules import DISCLAIMER


class TopFactor(BaseModel):
    name: str
    value: float
    importance: float


class PredictionResponse(BaseModel):
    latitude: float
    longitude: float
    flood_probability: float = Field(ge=0.0, le=1.0)
    risk_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_factors: list[TopFactor]
    weather_features: dict[str, float]
    model_version: str
    saved_to_db: bool = False
    disclaimer: str = DISCLAIMER
