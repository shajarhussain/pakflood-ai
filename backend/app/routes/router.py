from fastapi import APIRouter

from app.routes import health, prediction, boundaries, flood_events, zones, districts, chat, weather, auth

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(prediction.router, tags=["prediction"])
router.include_router(boundaries.router, tags=["boundaries"])
router.include_router(flood_events.router, tags=["flood-events"])
router.include_router(zones.router, tags=["zones"])
router.include_router(districts.router, tags=["districts"])
router.include_router(chat.router,    tags=["chat"])
router.include_router(weather.router, tags=["weather"])
router.include_router(auth.router,    tags=["auth"])
