import pytest
from fastapi.testclient import TestClient


def test_get_all_flood_events(client: TestClient):
    resp = client.get("/api/v1/flood-events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    assert len(events) >= 2


def test_flood_event_schema(client: TestClient):
    resp = client.get("/api/v1/flood-events")
    event = resp.json()[0]
    assert "id" in event
    assert "year" in event
    assert "title" in event
    assert "affected_districts" in event
    assert "estimated_affected" in event


def test_flood_events_filtered_by_district(client: TestClient):
    resp = client.get("/api/v1/flood-events?district_name=Sukkur")
    assert resp.status_code == 200
    events = resp.json()
    for event in events:
        assert "Sukkur" in event["affected_districts"]


def test_flood_events_filter_no_match(client: TestClient):
    resp = client.get("/api/v1/flood-events?district_name=Timbuktu")
    assert resp.status_code == 200
    assert resp.json() == []


def test_2022_event_has_damage_figure(client: TestClient):
    resp = client.get("/api/v1/flood-events")
    events_2022 = [e for e in resp.json() if e["year"] == 2022]
    assert len(events_2022) == 1
    assert events_2022[0]["damage_usd_billion"] == pytest.approx(14.9)


def test_2010_event_has_no_damage_figure(client: TestClient):
    resp = client.get("/api/v1/flood-events")
    events_2010 = [e for e in resp.json() if e["year"] == 2010]
    assert len(events_2010) == 1
    assert events_2010[0]["damage_usd_billion"] is None
