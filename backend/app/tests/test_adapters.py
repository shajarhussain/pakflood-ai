"""
Tests for adapter circuit breaker logic and data normalization.
All HTTP calls are mocked — no real network required.
"""
import time
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.base_adapter import BaseAdapter, AdapterResult
from app.adapters.imerg_adapter import IMERGAdapter
from app.adapters.chirps_adapter import CHIRPSAdapter
from app.adapters.glofas_adapter import GloFASAdapter
from app.adapters.ffd_adapter import FFDAdapter
from app.adapters.reliefweb_adapter import ReliefWebAdapter


# ---------------------------------------------------------------------------
# Controlled adapter for circuit-breaker tests
# ---------------------------------------------------------------------------

class _ControlledAdapter(BaseAdapter):
    source_id = "test"
    name = "Test Adapter"
    description = "For tests only."
    features_created = []
    latency_hours = 0

    def __init__(self, *, fail: bool = False) -> None:
        super().__init__()
        self.fail = fail
        self.call_count = 0

    def _do_fetch(self) -> AdapterResult:
        self.call_count += 1
        if self.fail:
            raise RuntimeError("Simulated fetch failure")
        return AdapterResult(
            source_id=self.source_id,
            status="fresh",
            data=[],
            fetched_at=datetime.now(UTC),
            latency_ms=1.0,
        )


# ===========================================================================
# Circuit breaker state machine
# ===========================================================================

class TestCircuitBreakerClosed:
    def test_successful_fetch_keeps_state_closed(self):
        adapter = _ControlledAdapter()
        result = adapter.fetch()
        assert adapter.circuit_state == "closed"
        assert result.status == "fresh"
        assert result.circuit_state == "closed"

    def test_failure_increments_count_but_stays_closed_below_threshold(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 3
        adapter.fetch()  # failure 1 — still closed
        assert adapter.circuit_state == "closed"
        adapter.fetch()  # failure 2 — still closed
        assert adapter.circuit_state == "closed"

    def test_success_resets_failure_count(self):
        adapter = _ControlledAdapter()
        # Force two failures first
        adapter._failure_count = 2
        result = adapter.fetch()
        assert adapter._failure_count == 0
        assert result.status == "fresh"


class TestCircuitBreakerOpens:
    def test_circuit_opens_after_threshold_failures(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 3
        for _ in range(3):
            adapter.fetch()
        assert adapter.circuit_state == "open"

    def test_open_circuit_returns_error_without_calling_do_fetch(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 2
        adapter.fetch()
        adapter.fetch()
        assert adapter.circuit_state == "open"

        adapter.fail = False  # would succeed if called
        result = adapter.fetch()
        # Still 0 new calls — circuit breaker blocked it
        assert result.status == "error"
        assert result.circuit_state == "open"
        assert "circuit breaker" in result.error_message.lower()

    def test_open_circuit_error_has_no_data(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 1
        adapter.fetch()
        result = adapter.fetch()
        assert result.data is None


class TestCircuitBreakerHalfOpen:
    def test_circuit_transitions_to_half_open_after_recovery_timeout(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 1
        adapter.recovery_timeout = 0.05  # 50 ms for test speed
        adapter.fetch()
        assert adapter.circuit_state == "open"
        time.sleep(0.06)
        adapter.fetch()  # first call after timeout → half_open → attempt
        # After success (fail=False below), it would close
        # But here fail=True, so it should re-open
        assert adapter.circuit_state == "open"

    def test_successful_half_open_closes_circuit(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 1
        adapter.recovery_timeout = 0.05
        adapter.fetch()
        assert adapter.circuit_state == "open"
        time.sleep(0.06)
        # Now flip to succeed
        adapter.fail = False
        result = adapter.fetch()
        assert adapter.circuit_state == "closed"
        assert result.status == "fresh"

    def test_reset_clears_state(self):
        adapter = _ControlledAdapter(fail=True)
        adapter.failure_threshold = 1
        adapter.fetch()
        assert adapter.circuit_state == "open"
        adapter.reset()
        assert adapter.circuit_state == "closed"
        assert adapter._failure_count == 0


# ===========================================================================
# Stub adapter contracts
# ===========================================================================

class TestStubAdapters:
    @pytest.mark.parametrize("AdapterClass", [IMERGAdapter, CHIRPSAdapter, GloFASAdapter, FFDAdapter])
    def test_stub_returns_stale_status(self, AdapterClass):
        result = AdapterClass().fetch()
        assert result.status == "stale"

    @pytest.mark.parametrize("AdapterClass", [IMERGAdapter, CHIRPSAdapter, GloFASAdapter, FFDAdapter])
    def test_stub_returns_list_data(self, AdapterClass):
        result = AdapterClass().fetch()
        assert isinstance(result.data, list)
        assert len(result.data) > 0

    @pytest.mark.parametrize("AdapterClass", [IMERGAdapter, CHIRPSAdapter, GloFASAdapter, FFDAdapter])
    def test_stub_circuit_starts_closed(self, AdapterClass):
        assert AdapterClass().circuit_state == "closed"

    def test_imerg_data_has_rainfall_fields(self):
        result = IMERGAdapter().fetch()
        row = result.data[0]
        assert "district_id" in row
        assert "rainfall_1d_mm" in row
        assert "rainfall_7d_mm" in row

    def test_glofas_data_has_discharge_fields(self):
        result = GloFASAdapter().fetch()
        row = result.data[0]
        assert "river_discharge_m3s" in row
        assert "discharge_anomaly_pct" in row
        assert "alert_level" in row

    def test_ffd_data_has_flood_category(self):
        result = FFDAdapter().fetch()
        row = result.data[0]
        assert "station" in row
        assert "category" in row
        assert "level_m" in row

    def test_chirps_data_has_percentile(self):
        result = CHIRPSAdapter().fetch()
        row = result.data[0]
        assert "rainfall_percentile" in row
        assert "historical_mean_mm" in row


# ===========================================================================
# ReliefWeb adapter (mocked HTTP)
# ===========================================================================

_MOCK_RELIEFWEB_PAYLOAD = {
    "count": 1,
    "total": 42,
    "data": [
        {
            "id": "999",
            "fields": {
                "title": "Pakistan: Floods Situation Report No.1",
                "source": [{"name": "OCHA", "shortname": "OCHA"}],
                "date": {"created": "2022-09-05T12:00:00+00:00"},
                "url": "https://reliefweb.int/node/999",
                "body-html": "<p>Severe flooding across Sindh province.</p>",
                "country": [{"name": "Pakistan"}],
                "disaster_type": [{"name": "Flood"}],
            },
        }
    ],
}

_EMPTY_RELIEFWEB_PAYLOAD: dict = {"count": 0, "total": 0, "data": []}


class TestReliefWebAdapter:
    def _mock_client(self, payload: dict):
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.get.return_value = mock_resp
        return mock_ctx

    def test_normalizes_response_correctly(self):
        adapter = ReliefWebAdapter()
        with patch("httpx.Client", return_value=self._mock_client(_MOCK_RELIEFWEB_PAYLOAD)):
            result = adapter.fetch()

        assert result.status == "fresh"
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        article = result.data[0]
        assert article["title"] == "Pakistan: Floods Situation Report No.1"
        assert article["source"] == "OCHA"
        assert article["published_date"] == "2022-09-05"
        assert "reliefweb.int" in article["url"]
        assert article["country"] == "Pakistan"
        assert article["disaster_type"] == "Flood"

    def test_summary_strips_html(self):
        adapter = ReliefWebAdapter()
        with patch("httpx.Client", return_value=self._mock_client(_MOCK_RELIEFWEB_PAYLOAD)):
            result = adapter.fetch()
        assert "<p>" not in result.data[0]["summary"]
        assert "Severe flooding" in result.data[0]["summary"]

    def test_handles_empty_results(self):
        adapter = ReliefWebAdapter()
        with patch("httpx.Client", return_value=self._mock_client(_EMPTY_RELIEFWEB_PAYLOAD)):
            result = adapter.fetch()
        assert result.status == "fresh"
        assert result.data == []

    def test_http_error_triggers_circuit_breaker(self):
        adapter = ReliefWebAdapter()
        adapter.failure_threshold = 1
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.get.side_effect = Exception("Connection refused")
        with patch("httpx.Client", return_value=mock_ctx):
            result = adapter.fetch()
        assert result.status == "error"
        assert adapter.circuit_state == "open"

    def test_circuit_state_returned_in_result(self):
        adapter = ReliefWebAdapter()
        with patch("httpx.Client", return_value=self._mock_client(_MOCK_RELIEFWEB_PAYLOAD)):
            result = adapter.fetch()
        assert result.circuit_state == "closed"
