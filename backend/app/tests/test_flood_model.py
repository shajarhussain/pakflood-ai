"""Tests for the new XGBoost flood model and feature pipeline."""

import pytest

from app.hazards.flood.features import FEATURE_COLS, build_feature_vector
from app.hazards.flood.model import FloodModel, get_flood_model
from app.hazards.flood.rules import classify_risk, DISCLAIMER


class TestFeatureCols:
    def test_has_14_features(self):
        assert len(FEATURE_COLS) == 14

    def test_feature_names_are_unique(self):
        assert len(FEATURE_COLS) == len(set(FEATURE_COLS))

    def test_expected_features_present(self):
        expected = {
            "precipitation", "precip_3day_avg", "precip_7day_avg",
            "pressure", "temperature", "temp_3day_avg",
            "soil_moisture", "soil_3day_avg", "wind_speed",
            "humidity", "evaporation", "is_monsoon", "month", "day_of_year",
        }
        assert expected == set(FEATURE_COLS)

    def test_order_is_stable(self):
        assert list(FEATURE_COLS) == list(FEATURE_COLS)

    def test_no_leaky_columns(self):
        leaky = {"water_area_km2", "days_since_last_flood", "flood_event"}
        assert not leaky.intersection(set(FEATURE_COLS))


class TestBuildFeatureVector:
    def test_returns_14_values(self):
        features = {f: 1.0 for f in FEATURE_COLS}
        vec = build_feature_vector(features)
        assert len(vec) == 14

    def test_order_matches_feature_cols(self):
        features = {f: float(i) for i, f in enumerate(FEATURE_COLS)}
        vec = build_feature_vector(features)
        for i, name in enumerate(FEATURE_COLS):
            assert vec[i] == pytest.approx(float(i))

    def test_missing_keys_default_to_zero(self):
        vec = build_feature_vector({})
        assert all(v == 0.0 for v in vec)


class TestClassifyRisk:
    def test_low(self):
        assert classify_risk(0.10) == "Low"

    def test_moderate(self):
        assert classify_risk(0.40) == "Moderate"

    def test_high(self):
        assert classify_risk(0.65) == "High"

    def test_severe(self):
        assert classify_risk(0.85) == "Severe"

    def test_boundary_low_moderate(self):
        assert classify_risk(0.30) == "Moderate"

    def test_boundary_moderate_high(self):
        assert classify_risk(0.55) == "High"

    def test_boundary_high_severe(self):
        assert classify_risk(0.75) == "Severe"


class TestFloodModel:
    def test_predict_returns_all_keys(self):
        model = FloodModel()
        features = {f: 0.0 for f in FEATURE_COLS}
        result = model.predict(features)
        assert "flood_probability" in result
        assert "risk_level" in result
        assert "confidence" in result
        assert "top_factors" in result
        assert "model_version" in result
        assert "disclaimer" in result

    def test_predict_probability_range(self):
        model = FloodModel()
        features = {f: 0.5 for f in FEATURE_COLS}
        result = model.predict(features)
        assert 0.0 <= result["flood_probability"] <= 1.0

    def test_predict_confidence_range(self):
        model = FloodModel()
        features = {f: 0.5 for f in FEATURE_COLS}
        result = model.predict(features)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_predict_risk_level_valid(self):
        model = FloodModel()
        features = {f: 0.5 for f in FEATURE_COLS}
        result = model.predict(features)
        assert result["risk_level"] in {"Low", "Moderate", "High", "Severe", "Unknown"}

    def test_disclaimer_present(self):
        model = FloodModel()
        features = {f: 0.0 for f in FEATURE_COLS}
        result = model.predict(features)
        assert "PMD" in result["disclaimer"] or "educational" in result["disclaimer"].lower()

    def test_singleton_returns_same_instance(self):
        a = get_flood_model()
        b = get_flood_model()
        assert a is b
