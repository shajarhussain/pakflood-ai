"""Tests for the /predict endpoint — mocks the weather service and Supabase."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.hazards.flood.features import FEATURE_COLS


MOCK_FEATURES = {f: 1.0 for f in FEATURE_COLS}
MOCK_FEATURES.update({
    "precipitation": 5.2,
    "pressure": 100500.0,
    "temperature": 38.0,
    "humidity": 72.0,
    "is_monsoon": 1.0,
    "month": 8.0,
    "day_of_year": 220.0,
})


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.controllers.prediction_controller.fetch_weather_features", new_callable=AsyncMock)
def test_predict_returns_200(mock_fetch, client):
    mock_fetch.return_value = MOCK_FEATURES
    resp = client.get("/api/v1/predict?lat=27.7&lng=68.85")
    assert resp.status_code == 200


@patch("app.controllers.prediction_controller.fetch_weather_features", new_callable=AsyncMock)
def test_predict_response_schema(mock_fetch, client):
    mock_fetch.return_value = MOCK_FEATURES
    data = client.get("/api/v1/predict?lat=27.7&lng=68.85").json()
    assert "flood_probability" in data
    assert "risk_level" in data
    assert "confidence" in data
    assert "top_factors" in data
    assert "weather_features" in data
    assert "disclaimer" in data


@patch("app.controllers.prediction_controller.fetch_weather_features", new_callable=AsyncMock)
def test_predict_lat_lng_echoed(mock_fetch, client):
    mock_fetch.return_value = MOCK_FEATURES
    data = client.get("/api/v1/predict?lat=27.7&lng=68.85").json()
    assert data["latitude"] == pytest.approx(27.7)
    assert data["longitude"] == pytest.approx(68.85)


@patch("app.controllers.prediction_controller.fetch_weather_features", new_callable=AsyncMock)
def test_predict_risk_level_valid(mock_fetch, client):
    mock_fetch.return_value = MOCK_FEATURES
    data = client.get("/api/v1/predict?lat=27.7&lng=68.85").json()
    assert data["risk_level"] in {"Low", "Moderate", "High", "Severe", "Unknown"}


@patch("app.controllers.prediction_controller.fetch_weather_features", new_callable=AsyncMock)
def test_predict_weather_features_in_response(mock_fetch, client):
    mock_fetch.return_value = MOCK_FEATURES
    data = client.get("/api/v1/predict?lat=27.7&lng=68.85").json()
    for feat in FEATURE_COLS:
        assert feat in data["weather_features"]


@patch("app.controllers.prediction_controller.fetch_weather_features", side_effect=Exception("API down"))
def test_predict_weather_error_returns_502(mock_fetch, client):
    resp = client.get("/api/v1/predict?lat=27.7&lng=68.85")
    assert resp.status_code == 502


def test_predict_missing_lat_returns_422(client):
    resp = client.get("/api/v1/predict?lng=68.85")
    assert resp.status_code == 422


def test_model_status_returns_200(client):
    resp = client.get("/api/v1/model/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "artifact_ready" in data
    assert "model_version" in data
