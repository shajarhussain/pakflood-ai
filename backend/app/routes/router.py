from fastapi import APIRouter

from app.routes import health, prediction, boundaries, flood_events, zones

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(prediction.router, tags=["prediction"])
router.include_router(boundaries.router, tags=["boundaries"])
router.include_router(flood_events.router, tags=["flood-events"])
router.include_router(zones.router, tags=["zones"])
