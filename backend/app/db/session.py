from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Engine and session factory are created lazily — the driver (psycopg2) is only
# imported when get_db() is first called. Tests that override get_disaster_risk_service
# never reach get_db(), so no driver is needed in local test runs.
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        connect_args = {"connect_timeout": 5} if "postgresql" in settings.DATABASE_URL else {}
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def get_db():
    db = _get_session_factory()()
    try:
        yield db
    finally:
        db.close()
