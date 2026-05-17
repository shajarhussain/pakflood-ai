"""
Supabase access layer for zone batch data.

Never delete an old batch until the new one is confirmed complete —
the frontend always reads from the last complete batch, so users
always have data even while a recomputation is running.

Supabase row-limit note: the client defaults to 1 000 rows per query.
We pass .limit(_MAX_ROWS) on any query that may exceed that.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

_MAX_ROWS   = 10_000   # well above the ~3 685 grid points
_CHUNK_SIZE = 200      # rows per bulk-insert call (Supabase limit is ~1 MB/call)


class ZoneRepository:
    """All DB operations for zone_batches and zone_grid_points tables."""

    def __init__(self) -> None:
        self._db = get_supabase()

    # ── Read helpers ──────────────────────────────────────────────────────────

    def get_latest_batch(self) -> Optional[dict]:
        """Return the most recent complete batch row, or None."""
        result = (
            self._db.table("zone_batches")
            .select("*")
            .eq("status", "complete")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_latest_zone_points(self) -> list[dict]:
        """
        Return all grid-point rows from the latest complete batch.
        Paginates in _CHUNK_SIZE pages to work around Supabase's 1 000-row cap.
        Returns [] if no complete batch exists.
        """
        batch = self.get_latest_batch()
        if batch is None:
            return []
        return self._fetch_all_points(batch["id"])

    def get_zone_points_in_bbox(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
    ) -> list[dict]:
        """
        Return zone points from the latest batch within a lat/lng bounding box.
        Used by the district endpoint to avoid fetching all ~3 000+ points.
        """
        batch = self.get_latest_batch()
        if batch is None:
            return []

        result = (
            self._db.table("zone_grid_points")
            .select("*")
            .eq("batch_id", batch["id"])
            .gte("lat", min_lat)
            .lte("lat", max_lat)
            .gte("lng", min_lng)
            .lte("lng", max_lng)
            .limit(_MAX_ROWS)
            .execute()
        )
        return result.data or []

    def _fetch_all_points(self, batch_id: str) -> list[dict]:
        """Paginate through zone_grid_points in pages of 1 000 rows."""
        rows: list[dict] = []
        page_size = 1000
        offset    = 0
        while True:
            result = (
                self._db.table("zone_grid_points")
                .select("*")
                .eq("batch_id", batch_id)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            page = result.data or []
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def is_cache_fresh(self) -> bool:
        """True if the latest complete batch is younger than ZONE_CACHE_TTL_MINUTES."""
        minutes = self.get_minutes_since_last_computation()
        if minutes is None:
            return False
        return minutes < settings.ZONE_CACHE_TTL_MINUTES

    def get_minutes_since_last_computation(self) -> Optional[float]:
        """Age of the latest complete batch in minutes, or None if never computed."""
        batch = self.get_latest_batch()
        if batch is None:
            return None

        completed_at_str = batch.get("completed_at")
        if not completed_at_str:
            return None

        completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
        # Ensure both datetimes are timezone-aware before subtracting
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - completed_at).total_seconds() / 60.0

    # ── Write helpers ─────────────────────────────────────────────────────────

    def save_zone_batch(self, points: list[dict]) -> str:
        """
        Persist a full zone computation run.

        Steps:
          1. Insert zone_batches row with status='running'
          2. Bulk-insert all zone_grid_points in chunks of _CHUNK_SIZE
          3. Mark the batch status='complete'
          4. Delete all previous complete batches (and their grid points)

        Returns the new batch_id (UUID string).
        """
        batch_id = str(uuid.uuid4())
        now_iso  = datetime.now(timezone.utc).isoformat()

        # 1. Create batch ──────────────────────────────────────────────────────
        self._db.table("zone_batches").insert({
            "id":           batch_id,
            "started_at":   now_iso,
            "total_points": len(points),
            "status":       "running",
        }).execute()
        logger.info("Zone batch %s created (%d points)", batch_id, len(points))

        # 2. Bulk-insert grid points in chunks ─────────────────────────────────
        inserted = 0
        for start in range(0, len(points), _CHUNK_SIZE):
            chunk = points[start: start + _CHUNK_SIZE]
            rows  = [{"batch_id": batch_id, **p} for p in chunk]
            self._db.table("zone_grid_points").insert(rows).execute()
            inserted += len(chunk)
            logger.debug("Inserted %d/%d zone_grid_points", inserted, len(points))

        # 3. Mark complete ─────────────────────────────────────────────────────
        self._db.table("zone_batches").update({
            "status":       "complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", batch_id).execute()
        logger.info("Zone batch %s marked complete", batch_id)

        # 4. Delete old batches ────────────────────────────────────────────────
        self._delete_old_batches(keep_id=batch_id)

        return batch_id

    def _delete_old_batches(self, keep_id: str) -> None:
        """
        Remove every complete batch except keep_id.
        Deletes zone_grid_points first (FK constraint), then zone_batches.
        """
        old = (
            self._db.table("zone_batches")
            .select("id")
            .neq("id", keep_id)
            .execute()
        )
        old_ids = [row["id"] for row in (old.data or [])]
        if not old_ids:
            return

        for old_id in old_ids:
            self._db.table("zone_grid_points").delete().eq("batch_id", old_id).execute()
            self._db.table("zone_batches").delete().eq("id", old_id).execute()

        logger.info("Deleted %d old zone batch(es)", len(old_ids))
