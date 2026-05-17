import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.supabase import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/admin-boundaries")
def get_admin_boundaries() -> dict:
    """Return GeoJSON FeatureCollection of all districts from Supabase."""
    try:
        result = get_supabase().table("districts").select("*").execute()
    except Exception as exc:
        logger.error("Supabase districts query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    features = []
    for row in result.data:
        import json
        geom = json.loads(row["geom_json"]) if row.get("geom_json") else {
            "type": "Polygon", "coordinates": []
        }
        features.append({
            "type": "Feature",
            "properties": {
                "district_id": row["district_id"],
                "name": row["name"],
                "province": row["province"],
            },
            "geometry": geom,
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/location/search")
def search_location(
    q: str = Query(..., min_length=2, description="District name search string"),
) -> list[dict]:
    """Search districts by name."""
    try:
        result = (
            get_supabase()
            .table("districts")
            .select("district_id, name, province, center_lat, center_lng")
            .ilike("name", f"%{q}%")
            .execute()
        )
    except Exception as exc:
        logger.error("Supabase location search failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    return [
        {
            "district_id": row["district_id"],
            "name": row["name"],
            "province": row["province"],
            "center": [row["center_lat"], row["center_lng"]],
        }
        for row in result.data
    ]
