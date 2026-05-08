import json

from sqlalchemy.orm import Session

from app.hazards.flood.db_models import RiskSnapshot
from app.repositories.base import BaseRepository


class RiskRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_district_id(self, district_id: str) -> RiskSnapshot | None:
        return (
            self._db.query(RiskSnapshot)
            .filter(RiskSnapshot.district_id == district_id)
            .order_by(RiskSnapshot.created_at.desc())
            .first()
        )

    def get_all_latest(self) -> list[RiskSnapshot]:
        """Return the most recent snapshot per district."""
        from sqlalchemy import func
        subq = (
            self._db.query(
                RiskSnapshot.district_id,
                func.max(RiskSnapshot.created_at).label("max_ts"),
            )
            .group_by(RiskSnapshot.district_id)
            .subquery()
        )
        return (
            self._db.query(RiskSnapshot)
            .join(
                subq,
                (RiskSnapshot.district_id == subq.c.district_id)
                & (RiskSnapshot.created_at == subq.c.max_ts),
            )
            .all()
        )

    def get_top_factors(self, snapshot: RiskSnapshot) -> list[str]:
        try:
            return json.loads(snapshot.top_factors or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def insert_from_run(
        self,
        district_id: str,
        risk_score: float,
        risk_level: str,
        confidence: float,
        top_factors: list[str],
        model_version: str,
        feature_snapshot: dict | None = None,
        source_status: dict | None = None,
    ) -> RiskSnapshot:
        """Insert a new RiskSnapshot row from a model run result."""
        snapshot = RiskSnapshot(
            district_id=district_id,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            top_factors=json.dumps(top_factors),
            model_version=model_version,
            feature_snapshot_json=json.dumps(feature_snapshot or {}),
            source_status_json=json.dumps(source_status or {}),
        )
        self._db.add(snapshot)
        self._db.commit()
        return snapshot
