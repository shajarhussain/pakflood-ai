import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import supabase as supabase_module


def _make_supabase_mock():
    """Return a mock Supabase client pre-loaded with fixture data."""

    districts_data = [
        {
            "district_id": "PK-SD-SKR",
            "name": "Sukkur",
            "province": "Sindh",
            "center_lat": 27.7,
            "center_lng": 68.86,
            "geom_json": json.dumps({
                "type": "Polygon",
                "coordinates": [[[68.3, 27.4], [69.3, 27.5], [69.2, 28.1], [68.3, 27.4]]],
            }),
        }
    ]

    flood_events_data = [
        {
            "event_id": "evt-2022-record-floods",
            "year": 2022,
            "title": "2022 Pakistan Catastrophic Floods",
            "affected_provinces": json.dumps(["Sindh", "Balochistan"]),
            "affected_districts": json.dumps(["Jacobabad", "Sukkur"]),
            "peak_month": "August",
            "estimated_affected": 33000000,
            "damage_usd_billion": 14.9,
            "description": "Unprecedented floods affecting 1/3 of Pakistan.",
        },
        {
            "event_id": "evt-2010-super-floods",
            "year": 2010,
            "title": "2010 Pakistan Super Floods",
            "affected_provinces": json.dumps(["KPK", "Punjab", "Sindh", "Balochistan"]),
            "affected_districts": json.dumps(["Nowshera", "Charsadda", "Sukkur", "Larkana"]),
            "peak_month": "August",
            "estimated_affected": 20000000,
            "damage_usd_billion": None,
            "description": "One of the worst floods in Pakistan's history.",
        },
    ]

    def _chain(data):
        """Build a fluent mock that always returns data on .execute()."""
        result = MagicMock()
        result.data = data

        chain = MagicMock()
        chain.execute.return_value = result
        chain.select.return_value = chain
        chain.order.return_value = chain
        chain.ilike.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain
        return chain

    client = MagicMock()
    client.table.side_effect = lambda name: (
        _chain(districts_data) if name == "districts"
        else _chain(flood_events_data) if name == "flood_events"
        else _chain([])
    )
    return client


@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    mock = _make_supabase_mock()
    monkeypatch.setattr(supabase_module, "_client", mock)
    yield mock


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
