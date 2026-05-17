from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from this file to find the backend/.env regardless of CWD
_HERE = Path(__file__).resolve().parent          # app/core/
_BACKEND_ROOT = _HERE.parent.parent              # backend/
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""   # anon/publishable key (add service role for writes)

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_API_KEY: str = ""  # set in .env — required to hit /admin/* endpoints

    # ── Zone grid computation ─────────────────────────────────────────────────
    GRID_STEP_DEGREES: float = 0.5
    ZONE_CACHE_TTL_MINUTES: int = 180
    OPEN_METEO_REQUEST_DELAY_SEC: float = 0.70  # delay between sequential requests
    OPEN_METEO_MAX_RETRIES: int = 4             # retries on 429 / transient errors
    OPEN_METEO_RETRY_BASE_SEC: float = 15.0     # backoff base: 15s, 30s, 60s, 120s
    ZONE_STARTUP_DELAY_SEC: int = 60            # wait before first computation on startup

    # ── Pakistan bounding box ─────────────────────────────────────────────────
    PAK_NORTH: float = 37.0
    PAK_SOUTH: float = 23.5
    PAK_EAST: float = 77.0
    PAK_WEST: float = 60.5


settings = Settings()
