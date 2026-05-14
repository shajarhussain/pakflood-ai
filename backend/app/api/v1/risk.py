from fastapi import APIRouter, Depends, Path

from app.hazards.flood.explainer import get_flood_explainer
from app.hazards.flood.v3_guard import ensure_v3_ready
from app.schemas.risk import RiskExplanation, RiskResponse
from app.services.disaster_risk_service import DisasterRiskService, get_disaster_risk_service
from app.services.source_registry_service import SourceRegistryService, get_source_registry

router = APIRouter()


@router.get("/risk/by-boundary/{boundary_id}", response_model=RiskResponse)
def get_risk_by_boundary(
    boundary_id: str = Path(..., description="District ID, e.g. PK-SD-SKR"),
    service: DisasterRiskService = Depends(get_disaster_risk_service),
) -> RiskResponse:
    """Return the latest flood risk assessment for a single district.

    In ``MODEL_MODE=real_prediction`` and with the calibrated artifact
    missing, this route returns HTTP 503 with a structured remediation body —
    the legacy rule-based score is intentionally not served as v3 output.
    """
    ensure_v3_ready()  # raises ModelArtifactMissingError → HTTP 503
    return service.get_risk_by_boundary(boundary_id)


@router.get("/explain-risk/by-boundary/{boundary_id}", response_model=RiskExplanation)
def explain_risk_by_boundary(
    boundary_id: str = Path(..., description="District ID, e.g. PK-SD-SKR"),
    service: DisasterRiskService = Depends(get_disaster_risk_service),
    registry: SourceRegistryService = Depends(get_source_registry),
) -> RiskExplanation:
    """
    Return a 7-field source-backed flood risk explanation for a district.

    In ``MODEL_MODE=real_prediction`` and with the calibrated artifact missing,
    this route returns HTTP 503 with a structured remediation body — no
    legacy/mock explanation is served as v3 output.
    """
    ensure_v3_ready()  # raises ModelArtifactMissingError → HTTP 503
    risk = service.get_risk_by_boundary(boundary_id)  # raises 404 if missing
    flood_events = service.get_flood_events(risk.name)
    source_statuses = registry.to_data_source_responses()

    return get_flood_explainer().explain(
        district_id=boundary_id,
        district_name=risk.name,
        risk_level=risk.risk_level,
        confidence=risk.confidence,
        top_factors=risk.top_factors,
        model_version=risk.model_version,
        flood_events=flood_events,
        source_statuses=source_statuses,
    )
