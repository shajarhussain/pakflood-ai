from fastapi import APIRouter

from app.api.v1 import (
    admin, alerts, health, boundaries, risk, flood_events,
    data_sources, model_status,
)

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(boundaries.router, tags=["boundaries"])
router.include_router(risk.router, tags=["risk"])
router.include_router(flood_events.router, tags=["flood-events"])
router.include_router(data_sources.router, tags=["data-sources"])
router.include_router(admin.router, tags=["admin"])
router.include_router(alerts.router, tags=["alerts"])
router.include_router(model_status.router, tags=["model-status"])
