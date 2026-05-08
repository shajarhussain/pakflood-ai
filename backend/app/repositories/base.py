from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, db: Session) -> None:
        self._db = db
