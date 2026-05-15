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
    # Three valid modes:
    #   "real_prediction"         — strict 8-source research-grade v3 model
    #   "real_lite_prediction"    — Gate B-Lite weak-label public-API prototype
    #   "dataset_based_prediction" — Phase 10 dataset-based real-file model
    # No synthetic / baseline fallback in any mode. If the configured
    # artifact is missing, /api/v1/model/status reports artifact_exists=false
    # and the frontend chrome shows the honest unavailable message.
    MODEL_MODE: str = "dataset_based_prediction"
    PREDICTION_MODEL_PATH: str = "ml/artifacts/flood_prediction_calibrated_v3.pkl"
    PREDICTION_METADATA_PATH: str = "ml/artifacts/flood_prediction_metadata_v3.json"
    REAL_LITE_MODEL_PATH: str = "ml/artifacts/flood_prediction_real_lite.pkl"
    REAL_LITE_METADATA_PATH: str = "ml/artifacts/flood_prediction_real_lite_metadata.json"
    DATASET_BASED_MODEL_PATH: str = "ml/artifacts/flood_prediction_dataset_based.pkl"
    DATASET_BASED_METADATA_PATH: str = "ml/artifacts/flood_prediction_dataset_based_metadata.json"

    def active_model_paths(self) -> tuple[str, str]:
        """Return (artifact_path, metadata_path) for the active MODEL_MODE."""
        if self.MODEL_MODE == "real_lite_prediction":
            return self.REAL_LITE_MODEL_PATH, self.REAL_LITE_METADATA_PATH
        if self.MODEL_MODE == "dataset_based_prediction":
            return self.DATASET_BASED_MODEL_PATH, self.DATASET_BASED_METADATA_PATH
        return self.PREDICTION_MODEL_PATH, self.PREDICTION_METADATA_PATH


settings = Settings()
