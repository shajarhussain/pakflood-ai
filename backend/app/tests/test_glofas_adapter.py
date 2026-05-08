"""Tests for Phase 8 GloFAS adapter and build_glofas_discharge()."""

import pytest
from dataclasses import fields

from app.adapters.glofas_adapter import GloFASAdapter, DischargeReading, _STUB_READINGS
from app.adapters.base_adapter import AdapterResult
from app.hazards.flood.features import build_glofas_discharge, _STUB_DYNAMIC, FEATURE_NAMES


# ---------------------------------------------------------------------------
# GloFASAdapter — stub mode
# ---------------------------------------------------------------------------

class TestGloFASAdapterStub:
    def setup_method(self):
        self.adapter = GloFASAdapter()
        self.adapter.reset()

    def test_returns_adapter_result(self):
        assert isinstance(self.adapter.fetch(), AdapterResult)

    def test_status_is_stale(self):
        assert self.adapter.fetch().status == "stale"

    def test_source_id(self):
        assert self.adapter.fetch().source_id == "glofas"

    def test_data_has_10_districts(self):
        result = self.adapter.fetch()
        assert len(result.data) == 10

    def test_all_district_ids_unique(self):
        result = self.adapter.fetch()
        ids = [row["district_id"] for row in result.data]
        assert len(ids) == len(set(ids))

    def test_schema_fields_present(self):
        result = self.adapter.fetch()
        required = {f.name for f in fields(DischargeReading)}
        for row in result.data:
            assert required == set(row.keys()), f"Schema mismatch for {row.get('district_id')}"

    def test_confidence_zero_in_stub(self):
        for row in self.adapter.fetch().data:
            assert row["confidence"] == 0.0

    def test_source_label_is_stub(self):
        for row in self.adapter.fetch().data:
            assert row["source"] == "glofas-stub"

    def test_discharge_values_positive(self):
        for row in self.adapter.fetch().data:
            assert row["river_discharge_m3s"] > 0

    def test_alert_levels_valid(self):
        valid = {"None", "Yellow", "Orange", "Red"}
        for row in self.adapter.fetch().data:
            assert row["alert_level"] in valid

    def test_notes_field_present_and_non_empty(self):
        for row in self.adapter.fetch().data:
            assert isinstance(row["notes"], str)
            assert len(row["notes"]) > 0

    def test_all_10_known_districts_covered(self):
        expected = {
            "PK-SD-SKR", "PK-SD-JCB", "PK-SD-LRK", "PK-PB-MUL", "PK-PB-RWP",
            "PK-PB-LHR", "PK-KP-PSH", "PK-BL-QTA", "PK-BL-NAS", "PK-GB-GIL",
        }
        ids = {row["district_id"] for row in self.adapter.fetch().data}
        assert ids == expected


class TestGloFASNormalizedForDistrict:
    def setup_method(self):
        self.adapter = GloFASAdapter()

    def test_known_district_returns_reading(self):
        reading = self.adapter.normalized_for_district("PK-SD-SKR")
        assert isinstance(reading, DischargeReading)
        assert reading.district_id == "PK-SD-SKR"

    def test_unknown_district_returns_none(self):
        assert self.adapter.normalized_for_district("PK-XX-UNKNOWN") is None

    def test_high_risk_district_has_red_alert(self):
        skr = self.adapter.normalized_for_district("PK-SD-SKR")
        assert skr is not None
        assert skr.alert_level == "Red"

    def test_low_risk_district_has_none_alert(self):
        rwp = self.adapter.normalized_for_district("PK-PB-RWP")
        assert rwp is not None
        assert rwp.alert_level == "None"


class TestGloFASDisabledResult:
    def test_disabled_result_status(self):
        adapter = GloFASAdapter()
        result = adapter._disabled_result("CDS not configured")
        assert result.status == "disabled"
        assert result.error_message is not None

    def test_disabled_result_still_has_data(self):
        adapter = GloFASAdapter()
        result = adapter._disabled_result("test")
        assert len(result.data) == 10

    def test_disabled_notes_mention_live_mode(self):
        adapter = GloFASAdapter()
        result = adapter._disabled_result("not configured")
        for row in result.data:
            assert "live mode" in row["notes"].lower() or "not configured" in row["notes"].lower()


# ---------------------------------------------------------------------------
# build_glofas_discharge() — feature extraction
# ---------------------------------------------------------------------------

class TestBuildGlofasDischarge:
    def _make_result(self, district_id: str, discharge: float, status: str = "stale"):
        from dataclasses import asdict
        row = dict(asdict(_STUB_READINGS[0]))
        row["district_id"] = district_id
        row["river_discharge_m3s"] = discharge

        class FakeResult:
            pass
        r = FakeResult()
        r.status = status
        r.data = [row]
        return r

    def test_none_result_returns_empty_dict(self):
        assert build_glofas_discharge("PK-SD-SKR", None) == {}

    def test_extracts_discharge_from_stale_result(self):
        result = self._make_result("PK-SD-SKR", 8540.0, "stale")
        out = build_glofas_discharge("PK-SD-SKR", result)
        assert out == {"river_discharge_m3s": 8540.0}

    def test_extracts_discharge_from_fresh_result(self):
        result = self._make_result("PK-SD-JCB", 11200.0, "fresh")
        out = build_glofas_discharge("PK-SD-JCB", result)
        assert out == {"river_discharge_m3s": 11200.0}

    def test_disabled_status_returns_empty_dict(self):
        result = self._make_result("PK-SD-SKR", 8540.0, "disabled")
        assert build_glofas_discharge("PK-SD-SKR", result) == {}

    def test_error_status_returns_empty_dict(self):
        result = self._make_result("PK-SD-SKR", 8540.0, "error")
        assert build_glofas_discharge("PK-SD-SKR", result) == {}

    def test_unknown_district_returns_empty_dict(self):
        result = self._make_result("PK-SD-SKR", 8540.0)
        assert build_glofas_discharge("PK-XX-UNKNOWN", result) == {}

    def test_empty_data_returns_empty_dict(self):
        class EmptyResult:
            status = "stale"
            data = []
        assert build_glofas_discharge("PK-SD-SKR", EmptyResult()) == {}

    def test_output_key_is_river_discharge_m3s(self):
        result = self._make_result("PK-SD-SKR", 5000.0)
        out = build_glofas_discharge("PK-SD-SKR", result)
        assert set(out.keys()) == {"river_discharge_m3s"}
        assert "river_discharge_m3s" in FEATURE_NAMES

    def test_real_glofas_stub_extracts_skr(self):
        adapter = GloFASAdapter()
        adapter.reset()
        result = adapter.fetch()
        out = build_glofas_discharge("PK-SD-SKR", result)
        assert out == {"river_discharge_m3s": pytest.approx(8540.0)}

    def test_real_glofas_stub_extracts_nas(self):
        adapter = GloFASAdapter()
        adapter.reset()
        result = adapter.fetch()
        out = build_glofas_discharge("PK-BL-NAS", result)
        assert out == {"river_discharge_m3s": pytest.approx(9800.0)}

    def test_glofas_failure_does_not_erase_other_features(self):
        """Empty dict from failed GloFAS must not overwrite IMERG features."""
        from app.hazards.flood.features import build_rainfall_features
        from app.adapters.imerg_adapter import IMERGAdapter

        adapter = IMERGAdapter()
        adapter.reset()
        imerg_result = adapter.fetch()
        imerg_features = build_rainfall_features("PK-SD-SKR", imerg_result)

        # Simulate GloFAS failure
        glofas_discharge = {}  # empty — what build_glofas_discharge returns on error

        merged = {**imerg_features, **glofas_discharge}
        # IMERG rainfall values must still be present
        assert "rainfall_1d_mm" in merged
        assert "rainfall_7d_mm" in merged

    def test_static_fallback_when_glofas_unavailable(self):
        """When GloFAS returns {}, static stub dynamic provides river_discharge_m3s."""
        # {} merged into static+IMERG still results in _STUB_DYNAMIC discharge
        assert _STUB_DYNAMIC["river_discharge_m3s"] == 500.0
        empty = build_glofas_discharge("PK-SD-SKR", None)
        assert empty == {}
        # Caller must keep _STUB_DYNAMIC["river_discharge_m3s"] in that case
        # (tested in admin endpoint integration tests)
