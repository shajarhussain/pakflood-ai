"""
Flood-specific ORM models.
All flood logic must live inside backend/app/hazards/flood/ — never leak to platform layer.
"""
import sqlalchemy as sa
from app.db.base import Base


class RiskSnapshot(Base):
    """Latest flood risk assessment for a district."""
    __tablename__ = "risk_snapshots"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    district_id = sa.Column(sa.String(20), sa.ForeignKey("districts.district_id"), nullable=False, index=True)
    risk_score = sa.Column(sa.Float, nullable=False)
    risk_level = sa.Column(sa.String(20), nullable=False)   # Low | Moderate | High | Severe
    confidence = sa.Column(sa.Float, nullable=False)
    top_factors = sa.Column(sa.Text, nullable=True)         # JSON array stored as string
    forecast_window_hours = sa.Column(sa.Integer, default=72)
    model_version = sa.Column(sa.String(50), default="seed-v1.0")
    feature_snapshot_json = sa.Column(sa.Text, nullable=True)   # JSON dict of feature values
    source_status_json = sa.Column(sa.Text, nullable=True)      # JSON dict of source statuses
    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())


class FloodEvent(Base):
    """Historical flood event record."""
    __tablename__ = "flood_events"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    event_id = sa.Column(sa.String(100), unique=True, nullable=False, index=True)
    year = sa.Column(sa.Integer, nullable=False)
    title = sa.Column(sa.String(200), nullable=False)
    affected_provinces = sa.Column(sa.Text, nullable=True)   # JSON array
    affected_districts = sa.Column(sa.Text, nullable=True)   # JSON array
    peak_month = sa.Column(sa.String(20), nullable=True)
    estimated_affected = sa.Column(sa.BigInteger, nullable=True)
    damage_usd_billion = sa.Column(sa.Float, nullable=True)
    description = sa.Column(sa.Text, nullable=True)
