"""
Seed script — populates the database from the data/seed/ directory.

Usage (from backend/ directory, with DB running):
    python -m app.scripts.seed

Requires PostgreSQL to be running (docker-compose up db).
"""
import json
import os
import sys
from pathlib import Path

# Allow running as __main__ from backend/ directory
sys.path.insert(0, str(Path(__file__).parents[2]))

from sqlalchemy.orm import Session

from app.db.session import _get_engine, _get_session_factory

engine = _get_engine()
SessionLocal = _get_session_factory()
from app.db.base import Base
from app.db.models import District
from app.hazards.flood.db_models import RiskSnapshot, FloodEvent

# Centers per district_id — used to populate center_lat / center_lng
_CENTERS: dict[str, tuple[float, float]] = {
    "PK-SD-SKR": (27.70, 68.86),
    "PK-SD-JCB": (28.28, 68.43),
    "PK-SD-LRK": (27.56, 68.21),
    "PK-PB-MUL": (30.20, 71.44),
    "PK-PB-RWP": (33.60, 73.04),
    "PK-PB-LHR": (31.55, 74.36),
    "PK-KP-PSH": (34.01, 71.58),
    "PK-BL-QTA": (30.18, 67.00),
    "PK-BL-NAS": (28.90, 68.28),
    "PK-GB-GIL": (35.92, 74.31),
}

SEED_DIR = Path(os.environ.get("SEED_DATA_DIR", Path(__file__).parents[3] / "data" / "seed"))


def _load_json(filename: str):
    path = SEED_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_districts(db: Session) -> None:
    geojson = _load_json("districts.geojson")
    for feature in geojson["features"]:
        props = feature["properties"]
        did = props["district_id"]
        lat, lng = _CENTERS.get(did, (30.0, 70.0))
        if db.query(District).filter(District.district_id == did).first():
            continue
        db.add(District(
            district_id=did,
            name=props["name"],
            province=props["province"],
            center_lat=lat,
            center_lng=lng,
            geom_json=json.dumps(feature["geometry"]),
        ))
    db.commit()
    print(f"  districts: seeded {len(geojson['features'])} rows")


def seed_risk_snapshots(db: Session) -> None:
    mock_risk = _load_json("mock_risk.json")
    count = 0
    for entry in mock_risk:
        did = entry["district_id"]
        if db.query(RiskSnapshot).filter(RiskSnapshot.district_id == did).first():
            continue
        db.add(RiskSnapshot(
            district_id=did,
            risk_score=entry["risk_score"],
            risk_level=entry["risk_level"],
            confidence=entry["confidence"],
            top_factors=json.dumps(entry["top_factors"]),
        ))
        count += 1
    db.commit()
    print(f"  risk_snapshots: seeded {count} rows")


def seed_flood_events(db: Session) -> None:
    events = _load_json("flood_events.json")
    count = 0
    for event in events:
        eid = event["id"]
        if db.query(FloodEvent).filter(FloodEvent.event_id == eid).first():
            continue
        db.add(FloodEvent(
            event_id=eid,
            year=event["year"],
            title=event["title"],
            affected_provinces=json.dumps(event.get("affected_provinces", [])),
            affected_districts=json.dumps(event.get("affected_districts", [])),
            peak_month=event.get("peak_month"),
            estimated_affected=event.get("estimated_affected"),
            damage_usd_billion=event.get("damage_usd_billion"),
            description=event.get("description"),
        ))
        count += 1
    db.commit()
    print(f"  flood_events: seeded {count} rows")


def run() -> None:
    print("Creating tables (if not exist)…")
    Base.metadata.create_all(bind=engine)

    print("Seeding…")
    db: Session = SessionLocal()
    try:
        seed_districts(db)
        seed_risk_snapshots(db)
        seed_flood_events(db)
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    run()
