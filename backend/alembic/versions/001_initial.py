"""Initial schema — districts, data_sources, risk_snapshots, flood_events

Revision ID: 001
Revises:
Create Date: 2026-05-06

Note: geometry stored as Text (GeoJSON string) in Phase 2.
      Phase 3 will add PostGIS Geometry column via a follow-up migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "districts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("district_id", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("province", sa.String(100), nullable=False),
        sa.Column("center_lat", sa.Float, nullable=False),
        sa.Column("center_lng", sa.Float, nullable=False),
        # Phase 3: replace with sa.Column("geom", Geometry("GEOMETRY", srid=4326))
        sa.Column("geom_json", sa.Text, nullable=True),
    )
    op.create_index("ix_districts_district_id", "districts", ["district_id"])

    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="mock"),
        sa.Column("latency_hours", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("features_created", sa.Text, nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_data_sources_source_id", "data_sources", ["source_id"])

    op.create_table(
        "risk_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("district_id", sa.String(20), sa.ForeignKey("districts.district_id"), nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("top_factors", sa.Text, nullable=True),
        sa.Column("forecast_window_hours", sa.Integer, server_default="72"),
        sa.Column("model_version", sa.String(50), server_default="seed-v1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_risk_snapshots_district_id", "risk_snapshots", ["district_id"])

    op.create_table(
        "flood_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(100), unique=True, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("affected_provinces", sa.Text, nullable=True),
        sa.Column("affected_districts", sa.Text, nullable=True),
        sa.Column("peak_month", sa.String(20), nullable=True),
        sa.Column("estimated_affected", sa.BigInteger, nullable=True),
        sa.Column("damage_usd_billion", sa.Float, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
    )
    op.create_index("ix_flood_events_event_id", "flood_events", ["event_id"])
    op.create_index("ix_flood_events_year", "flood_events", ["year"])


def downgrade() -> None:
    op.drop_table("flood_events")
    op.drop_table("risk_snapshots")
    op.drop_table("data_sources")
    op.drop_table("districts")
