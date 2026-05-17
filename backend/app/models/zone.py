from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ZoneBatchRow(BaseModel):
    id: str
    started_at: str          # ISO datetime string for Supabase
    completed_at: str | None = None
    total_points: int | None = None
    status: str = "running"


class ZoneGridPointRow(BaseModel):
    batch_id: str
    lat: float
    lng: float

    # Model output
    flood_prob: float
    risk_level: str
    confidence: float

    # Rainfall features
    precipitation: float | None = None
    precip_3day_avg: float | None = None
    precip_7day_avg: float | None = None

    # Atmospheric features
    pressure: float | None = None
    temperature: float | None = None
    temp_3day_avg: float | None = None

    # Soil features
    soil_moisture: float | None = None
    soil_3day_avg: float | None = None

    # Wind + humidity
    wind_speed: float | None = None
    humidity: float | None = None
    evaporation: float | None = None

    # Temporal features
    is_monsoon: float | None = None
    month: float | None = None
    day_of_year: float | None = None

    # Top-3 feature importances
    top_feature_1_name: str | None = None
    top_feature_1_value: float | None = None
    top_feature_1_imp: float | None = None

    top_feature_2_name: str | None = None
    top_feature_2_value: float | None = None
    top_feature_2_imp: float | None = None

    top_feature_3_name: str | None = None
    top_feature_3_value: float | None = None
    top_feature_3_imp: float | None = None

    # Metadata
    weather_source: str = "open-meteo"
    computed_at: str          # ISO datetime string
    data_age_hours: float | None = None
