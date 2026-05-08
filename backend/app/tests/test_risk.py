import pytest
from fastapi.testclient import TestClient


def test_get_risk_known_district(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    assert resp.status_code == 200
    body = resp.json()
    assert body["district_id"] == "PK-SD-SKR"
    assert body["name"] == "Sukkur"
    assert body["province"] == "Sindh"


def test_risk_response_has_required_fields(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    body = resp.json()
    assert "risk_score" in body
    assert "risk_level" in body
    assert "confidence" in body
    assert "top_factors" in body
    assert "disclaimer" in body


def test_risk_score_within_bounds(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    body = resp.json()
    assert 0.0 <= body["risk_score"] <= 1.0
    assert 0.0 <= body["confidence"] <= 1.0


def test_risk_level_is_valid(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-SD-JCB")
    assert resp.json()["risk_level"] in {"Low", "Moderate", "High", "Severe"}


def test_disclaimer_never_claims_official_warning(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    disclaimer = resp.json()["disclaimer"]
    assert "official warning from" not in disclaimer.lower()
    assert "prototype" in disclaimer.lower()


def test_top_factors_is_list(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    assert isinstance(resp.json()["top_factors"], list)
    assert len(resp.json()["top_factors"]) > 0


def test_unknown_district_returns_404(client: TestClient):
    resp = client.get("/api/v1/risk/by-boundary/PK-XX-ZZZ")
    assert resp.status_code == 404
