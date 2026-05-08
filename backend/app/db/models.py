"""
Platform-level ORM models (shared across all hazard modules).

Geometry columns: Phase 2 stores raw GeoJSON in a Text column.
Phase 3 will add a proper PostGIS Geometry column via Alembic migration.
"""
import sqlalchemy as sa
from app.db.base import Base


class District(Base):
    """Administrative boundary record — one row per district."""
    __tablename__ = "districts"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    district_id = sa.Column(sa.String(20), unique=True, nullable=False, index=True)
    name = sa.Column(sa.String(100), nullable=False)
    province = sa.Column(sa.String(100), nullable=False)
    center_lat = sa.Column(sa.Float, nullable=False)
    center_lng = sa.Column(sa.Float, nullable=False)
    # Stores GeoJSON geometry object as JSON string; upgraded to PostGIS Geometry in Phase 3
    geom_json = sa.Column(sa.Text, nullable=True)


class DataSource(Base):
    """Registry of external data sources tracked by the platform."""
    __tablename__ = "data_sources"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    source_id = sa.Column(sa.String(50), unique=True, nullable=False, index=True)
    name = sa.Column(sa.String(200), nullable=False)
    status = sa.Column(sa.String(20), nullable=False, default="mock")  # fresh | stale | error | mock
    latency_hours = sa.Column(sa.Integer, nullable=True)
    description = sa.Column(sa.Text, nullable=True)
    features_created = sa.Column(sa.Text, nullable=True)  # JSON array stored as string
    last_updated = sa.Column(sa.DateTime(timezone=True), nullable=True)
