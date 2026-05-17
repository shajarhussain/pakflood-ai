import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.supabase import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/flood-events")
def get_flood_events(
    district_name: str | None = Query(default=None, description="Filter by district name"),
) -> list[dict]:
    """Return historical flood events from Supabase."""
    try:
        query = get_supabase().table("flood_events").select("*").order("year", desc=True)
        result = query.execute()
    except Exception as exc:
        logger.error("Supabase flood_events query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    events = []
    for row in result.data:
        affected = json.loads(row.get("affected_districts") or "[]")
        if district_name and district_name not in affected:
            continue
        events.append({
            "id":                  row["event_id"],
            "year":                row["year"],
            "title":               row["title"],
            "affected_provinces":  json.loads(row.get("affected_provinces") or "[]"),
            "affected_districts":  affected,
            "peak_month":          row.get("peak_month", ""),
            "estimated_affected":  row.get("estimated_affected"),
            "damage_usd_billion":  row.get("damage_usd_billion"),
            "description":         row.get("description", ""),
        })

    return events
