import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.hazards.flood.model import get_flood_model
from app.routes.router import router
from app.zones.zone_scheduler import start_zone_scheduler, stop_zone_scheduler

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    model = get_flood_model()
    if model.is_ready:
        start_zone_scheduler(model)
    else:
        logger.warning(
            "Model artifact not found — zone scheduler NOT started. "
            "Place flood_xgb_pakistan_v2.pkl in backend/ml/artifacts/ and restart."
        )
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    stop_zone_scheduler()


app = FastAPI(
    title="PakFlood AI",
    description="Pakistan flood intelligence and early-risk visualization API.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
