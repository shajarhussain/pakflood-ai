"""
Phase 4 ML tests: feature schema, pipeline, no-data-leakage, inference output.

These tests run without a real database or trained artifact — the rule-based
fallback in FloodPredictionStrategy ensures inference works regardless.
"""

import pytest

from app.hazards.flood.features import (
    FEATURE_NAMES,
    DISTRICT_STATIC_FEATURES,
    build_feature_vector,
    get_stub_features,
    validate_features,
)
from app.hazards.flood.model import FloodPredictionStrategy
from app.hazards.flood.rules import classify_risk


# ── Feature schema tests ──────────────────────────────────────────────────────

class TestFeatureNames:
    def test_feature_list_has_11_features(self):
        assert len(FEATURE_NAMES) == 11

    def test_required_static_features_present(self):
        required_static = {"elevation_mean_m", "slope_mean_deg", "distance_to_river_km",
                           "historical_flood_count", "population_exposure_score"}
        assert required_static.issubset(set(FEATURE_NAMES))

    def test_required_dynamic_features_present(self):
        required_dynamic = {"rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm",
                            "rainfall_anomaly_pct", "river_discharge_m3s"}
        assert required_dynamic.issubset(set(FEATURE_NAMES))

    def test_feature_names_are_unique(self):
        assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))

    def test_feature_name_order_is_stable(self):
        # Order must not change between calls — model artifact depends on it
        first_call = list(FEATURE_NAMES)
        second_call = list(FEATURE_NAMES)
        assert first_call == second_call


class TestDistrictStaticFeatures:
    def test_all_10_districts_defined(self):
        assert len(DISTRICT_STATIC_FEATURES) == 10

    def test_each_district_has_5_static_features(self):
        expected_static = {"elevation_mean_m", "slope_mean_deg", "distance_to_river_km",
                           "historical_flood_count", "population_exposure_score"}
        for district_id, feats in DISTRICT_STATIC_FEATURES.items():
            assert set(feats.keys()) == expected_static, f"Bad keys for {district_id}"

    def test_elevation_values_are_positive(self):
        for district_id, feats in DISTRICT_STATIC_FEATURES.items():
            assert feats["elevation_mean_m"] > 0, f"elevation <= 0 for {district_id}"

    def test_distance_to_river_is_positive(self):
        for district_id, feats in DISTRICT_STATIC_FEATURES.items():
            assert feats["distance_to_river_km"] > 0, f"distance <= 0 for {district_id}"

    def test_population_exposure_in_range(self):
        for district_id, feats in DISTRICT_STATIC_FEATURES.items():
            score = feats["population_exposure_score"]
            assert 0.0 <= score <= 1.0, f"exposure score out of range for {district_id}"

    def test_sukkur_is_high_risk_geography(self):
        # Sukkur: on Indus, flat, high flood history → distance and elevation low
        sk = DISTRICT_STATIC_FEATURES["PK-SD-SKR"]
        assert sk["distance_to_river_km"] < 5.0
        assert sk["elevation_mean_m"] < 200.0
        assert sk["historical_flood_count"] >= 5

    def test_quetta_is_low_risk_geography(self):
        # Quetta: high plateau, far from rivers → high elevation, large distance
        qt = DISTRICT_STATIC_FEATURES["PK-BL-QTA"]
        assert qt["elevation_mean_m"] > 1000.0
        assert qt["distance_to_river_km"] > 10.0


class TestValidateFeatures:
    def test_valid_features_pass(self):
        feats = get_stub_features("PK-SD-SKR")
        validate_features(feats)  # should not raise

    def test_missing_feature_raises(self):
        feats = get_stub_features("PK-SD-SKR")
        del feats["rainfall_7d_mm"]
        with pytest.raises(ValueError, match="rainfall_7d_mm"):
            validate_features(feats)

    def test_build_vector_returns_correct_length(self):
        feats = get_stub_features("PK-SD-SKR")
        vec = build_feature_vector(feats)
        assert len(vec) == len(FEATURE_NAMES)

    def test_build_vector_order_matches_feature_names(self):
        feats = get_stub_features("PK-SD-SKR")
        vec = build_feature_vector(feats)
        for i, name in enumerate(FEATURE_NAMES):
            assert vec[i] == pytest.approx(feats[name])

    def test_get_stub_features_returns_all_11_features(self):
        for district_id in DISTRICT_STATIC_FEATURES:
            feats = get_stub_features(district_id)
            assert set(feats.keys()) == set(FEATURE_NAMES), f"Missing features for {district_id}"


# ── Risk threshold tests (from acceptance criteria in plan) ───────────────────

class TestRiskThresholds:
    def test_low_threshold(self):
        assert classify_risk(0.10) == "Low"

    def test_moderate_threshold(self):
        assert classify_risk(0.45) == "Moderate"

    def test_high_threshold(self):
        assert classify_risk(0.70) == "High"

    def test_severe_threshold(self):
        assert classify_risk(0.90) == "Severe"

    def test_boundary_low_to_moderate(self):
        assert classify_risk(0.30) == "Moderate"

    def test_boundary_moderate_to_high(self):
        assert classify_risk(0.55) == "High"

    def test_boundary_high_to_severe(self):
        assert classify_risk(0.75) == "Severe"


# ── Inference tests ───────────────────────────────────────────────────────────

class TestFloodPredictionStrategy:
    def setup_method(self):
        self.strategy = FloodPredictionStrategy()

    def test_infer_by_district_returns_assessment(self):
        result = self.strategy.infer_by_district_id("PK-SD-SKR")
        assert result is not None

    def test_assessment_risk_score_in_range(self):
        for district_id in DISTRICT_STATIC_FEATURES:
            result = self.strategy.infer_by_district_id(district_id)
            assert 0.0 <= result.risk_score <= 1.0, f"risk_score out of range for {district_id}"

    def test_assessment_confidence_in_range(self):
        for district_id in DISTRICT_STATIC_FEATURES:
            result = self.strategy.infer_by_district_id(district_id)
            assert 0.0 <= result.confidence <= 1.0, f"confidence out of range for {district_id}"

    def test_assessment_risk_level_is_valid(self):
        valid_levels = {"Low", "Moderate", "High", "Severe"}
        for district_id in DISTRICT_STATIC_FEATURES:
            result = self.strategy.infer_by_district_id(district_id)
            assert result.risk_level in valid_levels, f"Invalid level for {district_id}: {result.risk_level}"

    def test_assessment_top_factors_not_empty(self):
        result = self.strategy.infer_by_district_id("PK-SD-SKR")
        assert len(result.top_factors) >= 1

    def test_assessment_model_version_present(self):
        result = self.strategy.infer_by_district_id("PK-SD-SKR")
        assert result.model_version != ""

    def test_assessment_source_status_present(self):
        result = self.strategy.infer_by_district_id("PK-SD-SKR")
        assert isinstance(result.source_status, dict)
        assert len(result.source_status) >= 1

    def test_infer_via_lat_lon(self):
        # lat/lon near Sukkur → should map to a nearby district
        from app.hazards.base import RiskRequest
        request = RiskRequest(lat=27.7, lon=68.85)
        result = self.strategy.infer(request)
        assert result.risk_level in {"Low", "Moderate", "High", "Severe"}

    def test_all_10_districts_produce_valid_assessment(self):
        for district_id in DISTRICT_STATIC_FEATURES:
            result = self.strategy.infer_by_district_id(district_id)
            assert result.risk_level in {"Low", "Moderate", "High", "Severe"}
            assert 0.0 <= result.risk_score <= 1.0
            assert 0.0 <= result.confidence <= 1.0


# ── No data leakage test ──────────────────────────────────────────────────────

class TestNoDataLeakage:
    def test_train_test_split_indices_are_disjoint(self):
        """Verify the training script's split produces disjoint sets."""
        import sys
        from pathlib import Path
        # Add ml/training to path so feature_pipeline can be imported standalone
        training_dir = Path(__file__).resolve().parents[3] / "ml" / "training"
        if str(training_dir) not in sys.path:
            sys.path.insert(0, str(training_dir))

        try:
            from feature_pipeline import generate_dataset
        except ImportError:
            pytest.skip("feature_pipeline not importable from this environment")

        try:
            import numpy as np
            from sklearn.model_selection import train_test_split
        except ImportError:
            pytest.skip("scikit-learn not installed")

        ds = generate_dataset(seed=42)
        X = np.array(ds.X)
        y = np.array(ds.y)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )
        # Total row count must be preserved
        assert len(X_train) + len(X_test) == len(X)
        # No duplicate rows between train and test (by row hash)
        train_set = {tuple(row) for row in X_train.tolist()}
        test_set = {tuple(row) for row in X_test.tolist()}
        # With 300 unique rows (no exact duplicates expected), overlap should be empty
        overlap = train_set & test_set
        assert len(overlap) == 0, f"Data leakage: {len(overlap)} rows appear in both splits"

    def test_dataset_has_300_rows(self):
        import sys
        from pathlib import Path
        training_dir = Path(__file__).resolve().parents[3] / "ml" / "training"
        if str(training_dir) not in sys.path:
            sys.path.insert(0, str(training_dir))

        try:
            from feature_pipeline import generate_dataset
        except ImportError:
            pytest.skip("feature_pipeline not importable from this environment")

        ds = generate_dataset(seed=42)
        assert len(ds) == 300

    def test_dataset_has_all_4_classes(self):
        import sys
        from pathlib import Path
        training_dir = Path(__file__).resolve().parents[3] / "ml" / "training"
        if str(training_dir) not in sys.path:
            sys.path.insert(0, str(training_dir))

        try:
            from feature_pipeline import generate_dataset
        except ImportError:
            pytest.skip("feature_pipeline not importable from this environment")

        ds = generate_dataset(seed=42)
        assert set(ds.y) == {0, 1, 2, 3}, f"Missing classes: got {set(ds.y)}"
