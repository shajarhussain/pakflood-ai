"""Tests for Phase 7A rainfall adapter realism upgrade.

Covers: IMERGAdapter, CHIRPSAdapter, and build_rainfall_features().
No live credentials or network required — all tests use stub mode.
"""

import pytest
from dataclasses import fields

from app.adapters.imerg_adapter import IMERGAdapter, RainfallReading
from app.adapters.chirps_adapter import CHIRPSAdapter, ClimatologyReading
from app.hazards.flood.features import build_chirps_anomaly
from app.adapters.base_adapter import AdapterResult
from app.hazards.flood.features import build_rainfall_features, _STUB_DYNAMIC, FEATURE_NAMES


# ---------------------------------------------------------------------------
# IMERGAdapter — stub mode (default, no env change needed)
# ---------------------------------------------------------------------------

class TestIMERGAdapterStub:
    def setup_method(self):
        self.adapter = IMERGAdapter()
        self.adapter.reset()

    def test_returns_adapter_result(self):
        result = self.adapter.fetch()
        assert isinstance(result, AdapterResult)

    def test_status_is_stale(self):
        result = self.adapter.fetch()
        assert result.status == "stale"

    def test_source_id(self):
        result = self.adapter.fetch()
        assert result.source_id == "imerg"

    def test_data_is_list_of_dicts(self):
        result = self.adapter.fetch()
        assert isinstance(result.data, list)
        assert len(result.data) == 10
        assert all(isinstance(row, dict) for row in result.data)

    def test_schema_fields_present(self):
        result = self.adapter.fetch()
        required = {f.name for f in fields(RainfallReading)}
        for row in result.data:
            assert required == set(row.keys()), f"Schema mismatch for {row.get('district_id')}"

    def test_all_district_ids_unique(self):
        result = self.adapter.fetch()
        ids = [row["district_id"] for row in result.data]
        assert len(ids) == len(set(ids))

    def test_confidence_is_zero_in_stub(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert row["confidence"] == 0.0

    def test_source_label_is_stub(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert row["source"] == "imerg-stub"

    def test_rainfall_values_non_negative(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert row["rainfall_1d_mm"] >= 0
            assert row["rainfall_3d_mm"] >= 0
            assert row["rainfall_7d_mm"] >= 0

    def test_notes_field_present_and_non_empty(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert "notes" in row
            assert isinstance(row["notes"], str)
            assert len(row["notes"]) > 0


class TestIMERGNormalizedForDistrict:
    def setup_method(self):
        self.adapter = IMERGAdapter()

    def test_known_district_returns_reading(self):
        reading = self.adapter.normalized_for_district("PK-SD-SKR")
        assert isinstance(reading, RainfallReading)
        assert reading.district_id == "PK-SD-SKR"

    def test_unknown_district_returns_none(self):
        assert self.adapter.normalized_for_district("PK-XX-UNKNOWN") is None

    def test_reading_fields(self):
        reading = self.adapter.normalized_for_district("PK-BL-NAS")
        assert reading is not None
        assert reading.rainfall_1d_mm >= 0
        assert reading.status == "stale"
        assert reading.confidence == 0.0


# ---------------------------------------------------------------------------
# CHIRPSAdapter — stub mode
# ---------------------------------------------------------------------------

class TestCHIRPSAdapterStub:
    def setup_method(self):
        self.adapter = CHIRPSAdapter()
        self.adapter.reset()

    def test_returns_adapter_result(self):
        result = self.adapter.fetch()
        assert isinstance(result, AdapterResult)

    def test_status_is_stale(self):
        result = self.adapter.fetch()
        assert result.status == "stale"

    def test_data_length(self):
        result = self.adapter.fetch()
        assert len(result.data) == 10

    def test_schema_fields_present(self):
        result = self.adapter.fetch()
        required = {f.name for f in fields(ClimatologyReading)}
        for row in result.data:
            assert required == set(row.keys())

    def test_percentile_range(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert 0 <= row["rainfall_percentile"] <= 100

    def test_source_label(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert row["source"] == "chirps-stub"

    def test_confidence_zero(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert row["confidence"] == 0.0

    def test_notes_field_present_and_non_empty(self):
        result = self.adapter.fetch()
        for row in result.data:
            assert "notes" in row
            assert isinstance(row["notes"], str)
            assert len(row["notes"]) > 0


class TestCHIRPSNormalizedForDistrict:
    def setup_method(self):
        self.adapter = CHIRPSAdapter()

    def test_known_district(self):
        reading = self.adapter.normalized_for_district("PK-SD-JCB")
        assert isinstance(reading, ClimatologyReading)
        assert reading.district_id == "PK-SD-JCB"

    def test_unknown_district_returns_none(self):
        assert self.adapter.normalized_for_district("PK-XX-FOO") is None


# ---------------------------------------------------------------------------
# build_rainfall_features() — feature extraction from adapter output
# ---------------------------------------------------------------------------

class TestBuildRainfallFeatures:
    def _make_result(self, district_id: str, **overrides) -> AdapterResult:
        """Build a minimal fake AdapterResult for one district."""
        row = {
            "district_id": district_id,
            "rainfall_1d_mm": 25.0,
            "rainfall_3d_mm": 60.0,
            "rainfall_7d_mm": 120.0,
            "rainfall_anomaly_pct": 45.0,
            "source": "imerg-gee",
            "observed_at": "2026-05-06T00:00:00Z",
            "status": "fresh",
            "confidence": 0.85,
            **overrides,
        }

        class FakeResult:
            status = row.get("status", "fresh")
            data = [row]

        return FakeResult()

    def test_none_result_returns_stub_dynamic(self):
        features = build_rainfall_features("PK-SD-SKR", None)
        assert features == dict(_STUB_DYNAMIC)

    def test_extracts_rainfall_fields(self):
        result = self._make_result("PK-SD-SKR")
        features = build_rainfall_features("PK-SD-SKR", result)
        assert features["rainfall_1d_mm"] == 25.0
        assert features["rainfall_3d_mm"] == 60.0
        assert features["rainfall_7d_mm"] == 120.0
        assert features["rainfall_anomaly_pct"] == 45.0

    def test_confidence_becomes_freshness_score(self):
        result = self._make_result("PK-SD-SKR", confidence=0.85)
        features = build_rainfall_features("PK-SD-SKR", result)
        assert features["source_freshness_score"] == 0.85

    def test_zero_confidence_falls_back_to_stub_freshness(self):
        result = self._make_result("PK-SD-SKR", confidence=0.0)
        features = build_rainfall_features("PK-SD-SKR", result)
        assert features["source_freshness_score"] == _STUB_DYNAMIC["source_freshness_score"]

    def test_river_discharge_always_stub(self):
        result = self._make_result("PK-SD-SKR")
        features = build_rainfall_features("PK-SD-SKR", result)
        assert features["river_discharge_m3s"] == _STUB_DYNAMIC["river_discharge_m3s"]

    def test_unknown_district_returns_stub(self):
        result = self._make_result("PK-SD-SKR")
        features = build_rainfall_features("PK-XX-UNKNOWN", result)
        assert features == dict(_STUB_DYNAMIC)

    def test_result_with_no_data_returns_stub(self):
        class EmptyResult:
            status = "fresh"
            data = []

        features = build_rainfall_features("PK-SD-SKR", EmptyResult())
        assert features == dict(_STUB_DYNAMIC)

    def test_output_keys_cover_dynamic_feature_names(self):
        result = self._make_result("PK-SD-SKR")
        features = build_rainfall_features("PK-SD-SKR", result)
        dynamic_names = {n for n in FEATURE_NAMES if n not in (
            "elevation_mean_m", "slope_mean_deg", "distance_to_river_km",
            "historical_flood_count", "population_exposure_score",
        )}
        assert dynamic_names == set(features.keys())

    def test_real_imerg_stub_result_extracts_skr(self):
        """Integration: use actual IMERGAdapter stub output."""
        adapter = IMERGAdapter()
        adapter.reset()
        result = adapter.fetch()
        features = build_rainfall_features("PK-SD-SKR", result)
        # Stub confidence is 0.0, so freshness falls back to stub
        assert features["source_freshness_score"] == _STUB_DYNAMIC["source_freshness_score"]
        assert features["rainfall_1d_mm"] == pytest.approx(48.2)

    def test_real_imerg_stub_result_extracts_nas(self):
        adapter = IMERGAdapter()
        adapter.reset()
        result = adapter.fetch()
        features = build_rainfall_features("PK-BL-NAS", result)
        assert features["rainfall_7d_mm"] == pytest.approx(310.7)


# ---------------------------------------------------------------------------
# Disabled status — when live mode attempted but not yet implemented
# ---------------------------------------------------------------------------

class TestDisabledStatus:
    def test_imerg_disabled_result_has_correct_status(self):
        """_disabled_result() must set status=disabled and include error_message."""
        adapter = IMERGAdapter()
        result = adapter._disabled_result("GEE live IMERG not yet implemented.")
        assert result.status == "disabled"
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_imerg_disabled_result_still_has_data(self):
        adapter = IMERGAdapter()
        result = adapter._disabled_result("test reason")
        assert isinstance(result.data, list)
        assert len(result.data) == 10

    def test_imerg_disabled_notes_mention_live_mode(self):
        adapter = IMERGAdapter()
        result = adapter._disabled_result("not configured")
        for row in result.data:
            assert "live mode" in row["notes"].lower() or "not configured" in row["notes"].lower()

    def test_chirps_disabled_result_has_correct_status(self):
        adapter = CHIRPSAdapter()
        result = adapter._disabled_result("GEE live CHIRPS not yet implemented.")
        assert result.status == "disabled"
        assert result.error_message is not None

    def test_chirps_disabled_result_still_has_data(self):
        adapter = CHIRPSAdapter()
        result = adapter._disabled_result("test reason")
        assert isinstance(result.data, list)
        assert len(result.data) == 10

    def test_stub_result_status_is_stale_not_disabled(self):
        """Default stub (ENABLE_LIVE_RAINFALL=false) must remain stale, not disabled."""
        adapter = IMERGAdapter()
        adapter.reset()
        result = adapter.fetch()
        assert result.status == "stale"


# ---------------------------------------------------------------------------
# feature_pipeline inject_rainfall
# ---------------------------------------------------------------------------

def _load_feature_pipeline():
    """Add ml/training to sys.path and import generate_dataset. Skip if unavailable."""
    import sys
    from pathlib import Path
    training_dir = Path(__file__).resolve().parents[3] / "ml" / "training"
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))
    try:
        from feature_pipeline import generate_dataset, FEATURE_NAMES  # noqa: F401
        return generate_dataset, FEATURE_NAMES
    except ImportError:
        return None, None


_SKR_INJECT = {
    "PK-SD-SKR": {
        "rainfall_1d_mm": 55.0,
        "rainfall_3d_mm": 130.0,
        "rainfall_7d_mm": 300.0,
        "rainfall_anomaly_pct": 90.0,
        "river_discharge_m3s": 7500.0,
        "source_freshness_score": 0.9,
    }
}


class TestFeaturePipelineInjectRainfall:
    def test_inject_adds_extra_rows(self):
        generate_dataset, _ = _load_feature_pipeline()
        if generate_dataset is None:
            pytest.skip("feature_pipeline not importable from this environment")
        base = generate_dataset(seed=42)
        enriched = generate_dataset(seed=42, inject_rainfall=_SKR_INJECT)
        assert len(enriched) == len(base) + 1

    def test_inject_row_uses_real_values(self):
        generate_dataset, FEATURE_NAMES = _load_feature_pipeline()
        if generate_dataset is None:
            pytest.skip("feature_pipeline not importable from this environment")
        enriched = generate_dataset(seed=42, inject_rainfall=_SKR_INJECT)
        # Injected row is appended after SKR's 30 synthetic rows; find it by district_ids
        r7d_idx = FEATURE_NAMES.index("rainfall_7d_mm")
        skr_rows = [
            enriched.X[i]
            for i, did in enumerate(enriched.district_ids)
            if did == "PK-SD-SKR"
        ]
        # One row must have exactly the injected 7d value
        assert any(abs(row[r7d_idx] - 300.0) < 0.01 for row in skr_rows)

    def test_inject_none_unchanged(self):
        generate_dataset, _ = _load_feature_pipeline()
        if generate_dataset is None:
            pytest.skip("feature_pipeline not importable from this environment")
        base = generate_dataset(seed=42)
        same = generate_dataset(seed=42, inject_rainfall=None)
        assert len(base) == len(same)


# ---------------------------------------------------------------------------
# build_chirps_anomaly() — anomaly extraction from CHIRPS adapter output
# ---------------------------------------------------------------------------

class TestBuildChirpsAnomaly:
    def _make_chirps_result(self, district_id: str, anomaly_pct: float, status: str = "stale"):
        row = {
            "district_id": district_id,
            "historical_mean_mm": 185.0,
            "current_season_mm": 320.0,
            "rainfall_percentile": 92,
            "anomaly_pct": anomaly_pct,
            "period": "2025-09-01/2026-05-06",
            "source": "chirps-stub",
            "observed_at": "2026-05-06T00:00:00Z",
            "status": status,
            "confidence": 0.0,
            "notes": "test",
        }
        class FakeResult:
            pass
        r = FakeResult()
        r.status = status
        r.data = [row]
        return r

    def test_none_result_returns_empty_dict(self):
        assert build_chirps_anomaly("PK-SD-SKR", None) == {}

    def test_extracts_anomaly_pct_from_stale_result(self):
        result = self._make_chirps_result("PK-SD-SKR", 73.0, status="stale")
        out = build_chirps_anomaly("PK-SD-SKR", result)
        assert out == {"rainfall_anomaly_pct": 73.0}

    def test_extracts_anomaly_pct_from_fresh_result(self):
        result = self._make_chirps_result("PK-SD-JCB", 123.0, status="fresh")
        out = build_chirps_anomaly("PK-SD-JCB", result)
        assert out == {"rainfall_anomaly_pct": 123.0}

    def test_disabled_status_returns_empty_dict(self):
        result = self._make_chirps_result("PK-SD-SKR", 73.0, status="disabled")
        assert build_chirps_anomaly("PK-SD-SKR", result) == {}

    def test_error_status_returns_empty_dict(self):
        result = self._make_chirps_result("PK-SD-SKR", 73.0, status="error")
        assert build_chirps_anomaly("PK-SD-SKR", result) == {}

    def test_unknown_district_returns_empty_dict(self):
        result = self._make_chirps_result("PK-SD-SKR", 73.0)
        assert build_chirps_anomaly("PK-XX-UNKNOWN", result) == {}

    def test_empty_data_returns_empty_dict(self):
        class EmptyResult:
            status = "stale"
            data = []
        assert build_chirps_anomaly("PK-SD-SKR", EmptyResult()) == {}

    def test_negative_anomaly_preserved(self):
        result = self._make_chirps_result("PK-BL-QTA", -22.0)
        out = build_chirps_anomaly("PK-BL-QTA", result)
        assert out == {"rainfall_anomaly_pct": -22.0}

    def test_real_chirps_stub_output_extracts_skr(self):
        """Integration: use real CHIRPSAdapter stub output."""
        adapter = CHIRPSAdapter()
        adapter.reset()
        result = adapter.fetch()
        out = build_chirps_anomaly("PK-SD-SKR", result)
        assert "rainfall_anomaly_pct" in out
        assert out["rainfall_anomaly_pct"] == pytest.approx(73.0)

    def test_real_chirps_stub_output_extracts_jcb(self):
        adapter = CHIRPSAdapter()
        adapter.reset()
        result = adapter.fetch()
        out = build_chirps_anomaly("PK-SD-JCB", result)
        assert out["rainfall_anomaly_pct"] == pytest.approx(123.0)

    def test_output_key_is_exactly_rainfall_anomaly_pct(self):
        """The feature name must match FEATURE_NAMES exactly."""
        from app.hazards.flood.features import FEATURE_NAMES
        result = self._make_chirps_result("PK-SD-SKR", 50.0)
        out = build_chirps_anomaly("PK-SD-SKR", result)
        assert set(out.keys()) == {"rainfall_anomaly_pct"}
        assert "rainfall_anomaly_pct" in FEATURE_NAMES
