"""
DB access layer for country_boundaries table.

Provides:
  - get_boundary(country_code)   → geom_json string or None
  - is_boundary_stale(country_code) → True if next_refresh_at has passed
  - save_boundary(...)           → upsert a new boundary
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

REFRESH_YEARS = 1


class BoundaryRepository:

    def __init__(self) -> None:
        self._db = get_supabase()

    def get_boundary(self, country_code: str = "PAK") -> Optional[str]:
        """Return the stored geom_json string, or None if not seeded yet."""
        result = (
            self._db.table("country_boundaries")
            .select("geom_json")
            .eq("country_code", country_code)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows or not rows[0].get("geom_json"):
            return None
        return rows[0]["geom_json"]

    def get_row(self, country_code: str = "PAK") -> Optional[dict]:
        """Return the full boundary row, or None."""
        result = (
            self._db.table("country_boundaries")
            .select("*")
            .eq("country_code", country_code)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def is_stale(self, country_code: str = "PAK") -> bool:
        """
        True if the stored boundary has passed its next_refresh_at date,
        or if no boundary exists yet.
        """
        row = self.get_row(country_code)
        if not row:
            return True

        refresh_str = row.get("next_refresh_at")
        if not refresh_str:
            return True

        next_refresh = datetime.fromisoformat(refresh_str.replace("Z", "+00:00"))
        if next_refresh.tzinfo is None:
            next_refresh = next_refresh.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) >= next_refresh

    def save_boundary(
        self,
        country_code: str,
        country_name: str,
        geom_json: str,
        source: str,
    ) -> None:
        """Upsert a boundary row and set next_refresh_at to 1 year from now."""
        now             = datetime.now(timezone.utc)
        next_refresh_at = (now + timedelta(days=365 * REFRESH_YEARS)).isoformat()

        self._db.table("country_boundaries").upsert({
            "country_code":    country_code,
            "country_name":    country_name,
            "geom_json":       geom_json,
            "source":          source,
            "captured_at":     now.isoformat(),
            "next_refresh_at": next_refresh_at,
        }, on_conflict="country_code").execute()

        logger.info(
            "Boundary saved: %s — next refresh at %s", country_code, next_refresh_at
        )
