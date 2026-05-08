import json

from sqlalchemy.orm import Session

from app.hazards.flood.db_models import FloodEvent
from app.repositories.base import BaseRepository


class FloodEventRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_all(self) -> list[FloodEvent]:
        return self._db.query(FloodEvent).order_by(FloodEvent.year).all()

    def get_by_district(self, district_name: str) -> list[FloodEvent]:
        """Filter events that affected the given district name."""
        events = self.get_all()
        return [e for e in events if district_name in self._parse_json(e.affected_districts)]

    def _parse_json(self, text: str | None) -> list[str]:
        try:
            return json.loads(text or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
