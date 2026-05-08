from fastapi import APIRouter, Depends, Query

from app.services.disaster_risk_service import DisasterRiskService, get_disaster_risk_service
from app.schemas.flood_event import FloodEventResponse

router = APIRouter()


@router.get("/flood-events", response_model=list[FloodEventResponse])
def get_flood_events(
    district_name: str | None = Query(default=None, description="Filter by district name"),
    service: DisasterRiskService = Depends(get_disaster_risk_service),
) -> list[FloodEventResponse]:
    """Return historical flood events, optionally filtered by district name."""
    return service.get_flood_events(district_name)
