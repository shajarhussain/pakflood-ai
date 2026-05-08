"""Admin endpoints — Phase 4+: run-risk-model with IMERG+CHIRPS+GloFAS wiring (Phase 8+9)."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from app.adapters.chirps_adapter import CHIRPSAdapter
from app.adapters.glofas_adapter import GloFASAdapter
from app.adapters.imerg_adapter import IMERGAdapter
from app.hazards.flood.features import (
    DISTRICT_STATIC_FEATURES,
    build_chirps_anomaly,
    build_glofas_discharge,
    build_rainfall_features,
)
from app.hazards.flood.model import get_flood_strategy
from app.schemas.risk import DISCLAIMER, DistrictRiskAssessment, RunModelResponse
from app.services.disaster_risk_service import DisasterRiskService, get_disaster_risk_service

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_ARTIFACT_PATH = _PROJECT_ROOT / "ml" / "artifacts" / "flood_baseline_v1.pkl"
_METRICS_PATH = _PROJECT_ROOT / "ml" / "evaluation" / "metrics_report.json"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


def _combined_source_label(imerg_status: str, chirps_status: str, glofas_status: str) -> str:
    """Summarise which adapters contributed usable data into a single label."""
    parts = [
        name for name, status in (
            ("imerg", imerg_status),
            ("chirps", chirps_status),
            ("glofas", glofas_status),
        )
        if status in ("fresh", "stale")
    ]
    return ("adapter-" + "-".join(parts)) if parts else "synthetic"


@router.post("/run-risk-model", response_model=RunModelResponse)
def run_risk_model(
    service: DisasterRiskService = Depends(get_disaster_risk_service),
) -> RunModelResponse:
    """
    Trigger inference on all known districts using the trained baseline model.

    Data responsibility (Phase 8):
      IMERG  → rainfall_1d_mm, rainfall_3d_mm, rainfall_7d_mm
      CHIRPS → rainfall_anomaly_pct (historical baseline / anomaly signal)
      GloFAS → river_discharge_m3s (upstream hydrological pressure)
      Static → elevation, slope, river proximity, historical flood count, population
      Stub   → source_freshness_score (not yet adapter-sourced)

    Any adapter failure falls back gracefully — the endpoint never raises.
    Results are persisted to RiskSnapshot via the service layer when a DB is available.
    """
    strategy = get_flood_strategy()

    # Fetch all three adapters once per batch.
    # fetch() is circuit-breaker protected and never raises.
    imerg_result = IMERGAdapter().fetch()
    chirps_result = CHIRPSAdapter().fetch()
    glofas_result = GloFASAdapter().fetch()

    imerg_status = imerg_result.status
    chirps_status = chirps_result.status
    glofas_status = glofas_result.status
    source_label = _combined_source_label(imerg_status, chirps_status, glofas_status)

    assessments: list[DistrictRiskAssessment] = []

    for district_id in DISTRICT_STATIC_FEATURES:
        static = DISTRICT_STATIC_FEATURES[district_id]

        # Each builder returns {} on failure — safe layered override
        imerg_features = build_rainfall_features(district_id, imerg_result)
        chirps_anomaly = build_chirps_anomaly(district_id, chirps_result)
        glofas_discharge = build_glofas_discharge(district_id, glofas_result)

        # Merge order: static < IMERG < CHIRPS < GloFAS
        merged_features = {**static, **imerg_features, **chirps_anomaly, **glofas_discharge}

        assessment = strategy.infer_by_district_id(district_id, features=merged_features)

        source_status = {
            **assessment.source_status,
            "imerg": imerg_status,
            "chirps": chirps_status,
            "glofas": glofas_status,
        }

        assessments.append(
            DistrictRiskAssessment(
                district_id=district_id,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                confidence=assessment.confidence,
                top_factors=assessment.top_factors,
                model_version=assessment.model_version,
                source_status=source_status,
                feature_snapshot=merged_features,
                rainfall_source=source_label,
            )
        )

    # Persist to DB when available — swallow failures so response is always returned
    persisted_count = 0
    persistence_failed_count = 0
    persistence_status = "skipped"
    try:
        persisted_count = service.persist_model_run(assessments)
        persistence_failed_count = len(assessments) - persisted_count
        persistence_status = "ok" if persistence_failed_count == 0 else "partial"
        logger.info("Persisted %d/%d district snapshots", persisted_count, len(assessments))
    except Exception as exc:
        persistence_failed_count = len(assessments)
        persistence_status = "failed_non_blocking"
        logger.warning("RiskSnapshot persistence skipped: %s", exc)

    return RunModelResponse(
        model_version=strategy.model_version(),
        districts_updated=len(assessments),
        assessments=assessments,
        persisted_count=persisted_count,
        persistence_failed_count=persistence_failed_count,
        persistence_status=persistence_status,
    )


@router.get("/model-status")
def model_status() -> dict:
    """
    Returns current model readiness and artifact availability.
    Useful for demo health checks — no DB or adapter calls made.
    """
    strategy = get_flood_strategy()
    artifact_available = _ARTIFACT_PATH.exists()
    metrics_available = _METRICS_PATH.exists()

    source_status_summary: dict[str, str] = {}
    try:
        imerg_state = IMERGAdapter().circuit_state
        chirps_state = CHIRPSAdapter().circuit_state
        glofas_state = GloFASAdapter().circuit_state
        source_status_summary = {
            "imerg_circuit": imerg_state,
            "chirps_circuit": chirps_state,
            "glofas_circuit": glofas_state,
        }
    except Exception:
        pass

    return {
        "model_version": strategy.model_version(),
        "artifact_available": artifact_available,
        "metrics_available": metrics_available,
        "district_count": len(DISTRICT_STATIC_FEATURES),
        "source_status_summary": source_status_summary,
        "disclaimer": DISCLAIMER,
    }
