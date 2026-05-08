import pytest
from fastapi.testclient import TestClient


def test_get_admin_boundaries_returns_feature_collection(client: TestClient):
    resp = client.get("/api/v1/admin-boundaries")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert isinstance(body["features"], list)
    assert len(body["features"]) > 0


def test_boundary_feature_has_required_properties(client: TestClient):
    resp = client.get("/api/v1/admin-boundaries")
    feature = resp.json()["features"][0]
    assert feature["type"] == "Feature"
    props = feature["properties"]
    assert "district_id" in props
    assert "name" in props
    assert "province" in props


def test_boundary_feature_has_geometry(client: TestClient):
    resp = client.get("/api/v1/admin-boundaries")
    feature = resp.json()["features"][0]
    geom = feature["geometry"]
    assert geom["type"] == "Polygon"
    assert "coordinates" in geom


def test_location_search_returns_match(client: TestClient):
    resp = client.get("/api/v1/location/search?q=Sukkur")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["district_id"] == "PK-SD-SKR"
    assert results[0]["risk_level"] == "High"
    assert len(results[0]["center"]) == 2


def test_location_search_no_match_returns_empty(client: TestClient):
    resp = client.get("/api/v1/location/search?q=Nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []


def test_location_search_short_query_rejected(client: TestClient):
    resp = client.get("/api/v1/location/search?q=x")
    assert resp.status_code == 422
