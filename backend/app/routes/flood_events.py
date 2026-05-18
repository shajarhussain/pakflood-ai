import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.supabase import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/flood-events/{event_id}/districts")
def get_flood_event_districts(event_id: str) -> dict:
    """
    Return the coordinates of all districts affected by a flood event.

    Matches the event's affected_districts names against the districts table
    and returns center coordinates + boundary availability for each match.
    Unmatched district names (not seeded in DB) are returned separately.

    Response:
      event_id    — the requested event
      matched     — districts found in DB with id, name, province, center lat/lng,
                    and has_boundary flag
      unmatched   — district names from the event that had no DB record
    """
    db = get_supabase()

    # 1. Fetch the event
    try:
        result = (
            db.table("flood_events")
            .select("event_id, title, year, affected_districts")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("flood_events query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Flood event '{event_id}' not found.")

    event = result.data[0]
    district_names: list[str] = json.loads(event.get("affected_districts") or "[]")

    if not district_names:
        return {
            "event_id": event_id,
            "title":    event.get("title", ""),
            "year":     event.get("year"),
            "matched":  [],
            "unmatched": [],
        }

    # 2. Query districts table — match by name (case-insensitive IN-list)
    # Supabase doesn't support ilike with list, so we use OR filter via in_() on lowercased
    # names. We lowercase both sides in Python after fetching by name.
    try:
        districts_result = (
            db.table("districts")
            .select("district_id, name, province, center_lat, center_lng, geom_json")
            .in_("name", district_names)
            .execute()
        )
    except Exception as exc:
        logger.error("districts query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    db_rows = districts_result.data or []

    # Build lookup by name (lower) to handle case differences
    db_lookup = {r["name"].lower(): r for r in db_rows}

    matched   = []
    unmatched = []

    for name in district_names:
        row = db_lookup.get(name.lower())
        if row:
            matched.append({
                "district_id":    row["district_id"],
                "name":           row["name"],
                "province":       row["province"],
                "center":         {"lat": row["center_lat"], "lng": row["center_lng"]},
                "has_boundary":   row.get("geom_json") is not None,
            })
        else:
            unmatched.append(name)

    return {
        "event_id":  event_id,
        "title":     event.get("title", ""),
        "year":      event.get("year"),
        "matched":   matched,
        "unmatched": unmatched,
    }


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
