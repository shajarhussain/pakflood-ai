from sqlalchemy.orm import Session

from app.db.models import District
from app.repositories.base import BaseRepository


class BoundaryRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_all(self) -> list[District]:
        return self._db.query(District).all()

    def get_by_id(self, district_id: str) -> District | None:
        return self._db.query(District).filter(District.district_id == district_id).first()

    def search_by_name(self, q: str) -> list[District]:
        pattern = f"%{q}%"
        return (
            self._db.query(District)
            .filter(District.name.ilike(pattern))
            .limit(10)
            .all()
        )
