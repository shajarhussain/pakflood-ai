from fastapi import APIRouter, Depends, Query

from app.services.disaster_risk_service import DisasterRiskService, get_disaster_risk_service
from app.schemas.boundary import LocationSearchResult

router = APIRouter()


@router.get("/admin-boundaries")
def get_admin_boundaries(
    level: str = Query(default="district", description="Boundary level (district only for Phase 2)"),
    service: DisasterRiskService = Depends(get_disaster_risk_service),
) -> dict:
    """Return GeoJSON FeatureCollection of all Pakistan districts."""
    return service.get_all_boundaries()


@router.get("/location/search", response_model=list[LocationSearchResult])
def search_location(
    q: str = Query(..., min_length=2, description="District name search string"),
    service: DisasterRiskService = Depends(get_disaster_risk_service),
) -> list[LocationSearchResult]:
    """Fuzzy-search districts by name — used by the map header search box."""
    return service.search_locations(q)
