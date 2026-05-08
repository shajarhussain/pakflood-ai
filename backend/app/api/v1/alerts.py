"""
Alert draft endpoint — Phase 5.

Generates a CAP-like draft alert from risk + explanation data.
This endpoint creates a draft ONLY. It does not send any notification,
SMS, email, WhatsApp, or push message to any system.
"""

from fastapi import APIRouter, Depends

from app.hazards.flood.explainer import get_flood_explainer
from app.schemas.risk import AlertDraftRequest, AlertDraftResponse
from app.services.disaster_risk_service import DisasterRiskService, get_disaster_risk_service
from app.services.source_registry_service import SourceRegistryService, get_source_registry

router = APIRouter(prefix="/alerts")

_SEVERITY_MAP = {
    "Low": "Minor",
    "Moderate": "Moderate",
    "High": "Severe",
    "Severe": "Extreme",
}

_DRAFT_DISCLAIMER = (
    "DRAFT ONLY — NOT SENT — NOT AN OFFICIAL WARNING. "
    "Educational prototype. For real emergencies follow PMD, FFD, NDMA, PDMA."
)


@router.post("/generate-draft", response_model=AlertDraftResponse)
def generate_alert_draft(
    request: AlertDraftRequest,
    service: DisasterRiskService = Depends(get_disaster_risk_service),
    registry: SourceRegistryService = Depends(get_source_registry),
) -> AlertDraftResponse:
    """
    Generate a CAP-like alert draft for a district.

    The draft is computed server-side and returned in the response body.
    It is never stored, queued, or transmitted to any external system.
    is_draft=True and is_official=False are always set.
    """
    risk = service.get_risk_by_boundary(request.boundary_id)
    flood_events = service.get_flood_events(risk.name)
    source_statuses = registry.to_data_source_responses()

    explanation = get_flood_explainer().explain(
        district_id=request.boundary_id,
        district_name=risk.name,
        risk_level=risk.risk_level,
        confidence=risk.confidence,
        top_factors=risk.top_factors,
        model_version=risk.model_version,
        flood_events=flood_events,
        source_statuses=source_statuses,
    )

    severity = _SEVERITY_MAP.get(risk.risk_level, "Moderate")
    causes_text = "; ".join(explanation.main_causes[:3])
    actions_text = " ".join(explanation.suggested_actions[:3])

    return AlertDraftResponse(
        headline=f"[DRAFT] Flood Risk Advisory — {risk.name}, {risk.province}",
        severity=severity,
        area=f"{risk.name}, {risk.province}, Pakistan",
        description=(
            f"PakFlood AI model (educational prototype) indicates {risk.risk_level} flood risk "
            f"for {risk.name} district (confidence: {risk.confidence:.0%}). "
            f"Key indicators: {causes_text}."
        ),
        instruction=actions_text,
        sources=explanation.data_sources,
        confidence=risk.confidence,
        disclaimer=_DRAFT_DISCLAIMER,
        is_draft=True,
        is_official=False,
    )
