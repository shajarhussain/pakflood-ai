"""
DisasterRiskService — Facade Pattern.

Single entry point for boundary, risk, and flood-event business logic.
Data-source status is delegated to SourceRegistryService (Phase 3+).
"""
import json
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.boundary_repository import BoundaryRepository
from app.repositories.risk_repository import RiskRepository
from app.repositories.flood_event_repository import FloodEventRepository
from app.schemas.boundary import LocationSearchResult
from app.schemas.risk import RiskResponse, DISCLAIMER
from app.schemas.flood_event import FloodEventResponse

logger = logging.getLogger(__name__)


class DisasterRiskService:
    """Facade coordinating repositories and hazard modules for API responses."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._boundary_repo = BoundaryRepository(db)
        self._risk_repo = RiskRepository(db)
        self._flood_event_repo = FloodEventRepository(db)

    # ------------------------------------------------------------------
    # Boundaries
    # ------------------------------------------------------------------

    def get_all_boundaries(self) -> dict:
        districts = self._boundary_repo.get_all()
        features = []
        for d in districts:
            geom = json.loads(d.geom_json) if d.geom_json else {"type": "Polygon", "coordinates": []}
            features.append({
                "type": "Feature",
                "properties": {"district_id": d.district_id, "name": d.name, "province": d.province},
                "geometry": geom,
            })
        return {"type": "FeatureCollection", "features": features}

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    def get_risk_by_boundary(self, boundary_id: str) -> RiskResponse:
        snapshot = self._risk_repo.get_by_district_id(boundary_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"No risk data found for district '{boundary_id}'")
        district = self._boundary_repo.get_by_id(boundary_id)

        # Use persisted source_status from model run if available; else safe default
        try:
            stored_status = json.loads(snapshot.source_status_json or "{}")
        except (json.JSONDecodeError, TypeError, AttributeError):
            stored_status = {}
        source_status = stored_status or {"imerg": "stale", "chirps": "stale", "glofas": "stale"}

        return RiskResponse(
            district_id=boundary_id,
            name=district.name if district else boundary_id,
            province=district.province if district else "",
            risk_score=snapshot.risk_score,
            risk_level=snapshot.risk_level,
            confidence=snapshot.confidence,
            top_factors=self._risk_repo.get_top_factors(snapshot),
            forecast_window_hours=snapshot.forecast_window_hours,
            model_version=snapshot.model_version,
            source_status=source_status,
            disclaimer=DISCLAIMER,
        )

    def persist_model_run(self, assessments: list) -> int:
        """Persist model-run assessments as new RiskSnapshot rows.

        Returns the count of successfully persisted rows.
        Swallows per-district errors so a single bad row doesn't abort the batch.
        """
        persisted = 0
        for a in assessments:
            try:
                self._risk_repo.insert_from_run(
                    district_id=a.district_id,
                    risk_score=a.risk_score,
                    risk_level=a.risk_level,
                    confidence=a.confidence,
                    top_factors=list(a.top_factors),
                    model_version=a.model_version,
                    feature_snapshot=dict(a.feature_snapshot),
                    source_status=dict(a.source_status),
                )
                persisted += 1
            except Exception as exc:
                logger.warning("Failed to persist snapshot for %s: %s", a.district_id, exc)
        return persisted

    # ------------------------------------------------------------------
    # Flood events
    # ------------------------------------------------------------------

    def get_flood_events(self, district_name: str | None = None) -> list[FloodEventResponse]:
        if district_name:
            events = self._flood_event_repo.get_by_district(district_name)
        else:
            events = self._flood_event_repo.get_all()
        return [self._event_to_schema(e) for e in events]

    def _event_to_schema(self, e) -> FloodEventResponse:
        return FloodEventResponse(
            id=e.event_id,
            year=e.year,
            title=e.title,
            affected_provinces=json.loads(e.affected_provinces or "[]"),
            affected_districts=json.loads(e.affected_districts or "[]"),
            peak_month=e.peak_month or "",
            estimated_affected=e.estimated_affected or 0,
            damage_usd_billion=e.damage_usd_billion,
            description=e.description or "",
        )

    # ------------------------------------------------------------------
    # Location search
    # ------------------------------------------------------------------

    def search_locations(self, q: str) -> list[LocationSearchResult]:
        if not q or len(q) < 2:
            return []
        districts = self._boundary_repo.search_by_name(q)
        results = []
        for d in districts:
            snapshot = self._risk_repo.get_by_district_id(d.district_id)
            results.append(LocationSearchResult(
                district_id=d.district_id,
                name=d.name,
                province=d.province,
                center=[d.center_lat, d.center_lng],
                risk_level=snapshot.risk_level if snapshot else "Unknown",
            ))
        return results


# ---------------------------------------------------------------------------
# FastAPI dependency — override this in tests via app.dependency_overrides
# ---------------------------------------------------------------------------

def get_disaster_risk_service(db: Session = Depends(get_db)) -> DisasterRiskService:
    return DisasterRiskService(db)
