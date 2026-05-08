"""Add PostGIS geometry columns to districts and flood_events.

Revision ID: 002
Revises: 001
Create Date: 2026-05-06

Upgrades geom_json (Text) storage to proper PostGIS Geometry columns.
Migration is safe to run on PostgreSQL without PostGIS — the outer try/except
logs a warning and marks the migration complete without adding the columns.
The geom_json fallback columns are kept for backward compatibility.
"""
from typing import Sequence, Union
import warnings

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    try:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(sa.text(
            "ALTER TABLE districts ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326)"
        ))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS idx_districts_geom ON districts USING GIST (geom)"
        ))
        conn.execute(sa.text(
            "ALTER TABLE flood_events ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326)"
        ))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS idx_flood_events_geom ON flood_events USING GIST (geom)"
        ))
        # Populate geom from geom_json where available
        conn.execute(sa.text(
            "UPDATE districts SET geom = ST_SetSRID(ST_GeomFromGeoJSON(geom_json), 4326) "
            "WHERE geom_json IS NOT NULL AND geom_json != ''"
        ))
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"PostGIS extension not available; geometry columns skipped. ({exc})",
            stacklevel=2,
        )


def downgrade() -> None:
    conn = op.get_bind()
    try:
        conn.execute(sa.text("DROP INDEX IF EXISTS idx_districts_geom"))
        conn.execute(sa.text("DROP INDEX IF EXISTS idx_flood_events_geom"))
        conn.execute(sa.text("ALTER TABLE districts DROP COLUMN IF EXISTS geom"))
        conn.execute(sa.text("ALTER TABLE flood_events DROP COLUMN IF EXISTS geom"))
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"Downgrade skipped (PostGIS not available): {exc}", stacklevel=2)
