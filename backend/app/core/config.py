from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql://pakflood:pakflood@localhost:5432/pakflood"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # External data source API keys (optional for MVP)
    RELIEFWEB_API_KEY: str = ""
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_KEY_FILE: str = ""
    GEE_PROJECT: str = ""            # Google Earth Engine project ID

    # Rainfall data source (Phase 7A+)
    # ENABLE_LIVE_RAINFALL=false  →  always use stub data (safe default)
    # ENABLE_LIVE_RAINFALL=true   →  attempt live fetch; fall back to stub on failure
    ENABLE_LIVE_RAINFALL: bool = False
    RAINFALL_PROVIDER: str = "stub"  # stub | gee | earthdata

    # NASA Earthdata credentials (optional — only for RAINFALL_PROVIDER=earthdata)
    NASA_EARTHDATA_USERNAME: str = ""
    NASA_EARTHDATA_PASSWORD: str = ""

    # PakFlood AI v3 — Real Prediction Pipeline
    # MODEL_MODE="real_prediction" is the ONLY supported mode in v3. There is
    # no synthetic / baseline fallback. If the calibrated artifact is missing,
    # /api/v1/model/status reports artifact_exists=false and the frontend shows
    # "Real prediction model unavailable — run the real-data pipeline first."
    MODEL_MODE: str = "real_prediction"
    PREDICTION_MODEL_PATH: str = "ml/artifacts/flood_prediction_calibrated_v3.pkl"
    PREDICTION_METADATA_PATH: str = "ml/artifacts/flood_prediction_metadata_v3.json"


settings = Settings()
