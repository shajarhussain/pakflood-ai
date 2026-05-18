"""
One-shot script — delete zone_batches with fewer than MIN_POINTS points.

Usage (from backend/ directory):
    python scripts/purge_bad_batches.py

Deletes zone_grid_points first (FK), then the batch row.
Safe to run any time — only touches batches with total_points < MIN_POINTS.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.supabase import get_supabase

MIN_POINTS = 100  # anything below this is considered a bad/partial batch

db = get_supabase()

# ── Fetch all batches below threshold ─────────────────────────────────────────
result = (
    db.table("zone_batches")
    .select("id, total_points, status, started_at")
    .lt("total_points", MIN_POINTS)
    .execute()
)

bad_batches = result.data or []

if not bad_batches:
    print(f"No bad batches found (all have >= {MIN_POINTS} points). Nothing to do.")
    sys.exit(0)

print(f"Found {len(bad_batches)} bad batch(es) to delete:\n")
for b in bad_batches:
    print(f"  id={b['id']}  total_points={b['total_points']}  status={b['status']}  started={b['started_at']}")

print()

# ── Delete grid points first (FK constraint), then the batch rows ──────────────
deleted_points = 0
deleted_batches = 0

for b in bad_batches:
    bid = b["id"]

    pts = db.table("zone_grid_points").delete().eq("batch_id", bid).execute()
    n   = len(pts.data) if pts.data else 0
    deleted_points += n

    db.table("zone_batches").delete().eq("id", bid).execute()
    deleted_batches += 1

    print(f"  Deleted batch {bid} — {n} grid point(s) removed")

print(f"\nDone. Removed {deleted_batches} batch(es) and {deleted_points} grid point(s).")
