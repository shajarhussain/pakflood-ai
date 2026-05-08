"""Add feature_snapshot_json and source_status_json to risk_snapshots.

Revision ID: 003
Revises: 002
Create Date: 2026-05-06

Adds two nullable TEXT columns to risk_snapshots:
  - feature_snapshot_json: JSON dict of all feature values used in the model run
  - source_status_json: JSON dict of adapter statuses at inference time (imerg/chirps/glofas)

Safe to run on any PostgreSQL instance — uses ADD COLUMN IF NOT EXISTS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE risk_snapshots ADD COLUMN IF NOT EXISTS feature_snapshot_json TEXT"
    ))
    conn.execute(sa.text(
        "ALTER TABLE risk_snapshots ADD COLUMN IF NOT EXISTS source_status_json TEXT"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE risk_snapshots DROP COLUMN IF EXISTS feature_snapshot_json"
    ))
    conn.execute(sa.text(
        "ALTER TABLE risk_snapshots DROP COLUMN IF EXISTS source_status_json"
    ))
