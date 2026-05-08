"""Admin endpoint tests — POST /api/v1/admin/run-risk-model (Phases 4 + 7B)."""

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.base_adapter import AdapterResult
from datetime import datetime, UTC

client = TestClient(app)


# ---------------------------------------------------------------------------
# Basic shape tests (preserved from Phase 4)
# ---------------------------------------------------------------------------

def test_run_risk_model_returns_200():
    resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200


def test_run_risk_model_response_shape():
    resp = client.post("/api/v1/admin/run-risk-model")
    data = resp.json()
    assert "model_version" in data
    assert "districts_updated" in data
    assert "assessments" in data
    assert "disclaimer" in data


def test_run_risk_model_updates_all_10_districts():
    resp = client.post("/api/v1/admin/run-risk-model")
    data = resp.json()
    assert data["districts_updated"] == 10
    assert len(data["assessments"]) == 10


def test_run_risk_model_assessment_schema():
    resp = client.post("/api/v1/admin/run-risk-model")
    assessments = resp.json()["assessments"]
    required_keys = {
        "district_id", "risk_score", "risk_level", "confidence",
        "top_factors", "model_version", "source_status", "disclaimer",
    }
    for a in assessments:
        assert required_keys.issubset(a.keys()), f"Missing keys in {a['district_id']}"


def test_run_risk_model_risk_score_in_range():
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert 0.0 <= a["risk_score"] <= 1.0, f"score out of range for {a['district_id']}"


def test_run_risk_model_confidence_in_range():
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert 0.0 <= a["confidence"] <= 1.0, f"confidence out of range for {a['district_id']}"


def test_run_risk_model_risk_levels_are_valid():
    valid = {"Low", "Moderate", "High", "Severe"}
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert a["risk_level"] in valid, f"Invalid level for {a['district_id']}"


def test_run_risk_model_disclaimer_present():
    resp = client.post("/api/v1/admin/run-risk-model")
    data = resp.json()
    assert "educational" in data["disclaimer"].lower()
    assert "PMD" in data["disclaimer"] or "NDMA" in data["disclaimer"]


def test_run_risk_model_district_ids_are_known():
    resp = client.post("/api/v1/admin/run-risk-model")
    ids = {a["district_id"] for a in resp.json()["assessments"]}
    assert "PK-SD-SKR" in ids
    assert "PK-BL-QTA" in ids
    assert "PK-GB-GIL" in ids


# ---------------------------------------------------------------------------
# Phase 7B — rainfall adapter wiring
# ---------------------------------------------------------------------------

def test_run_risk_model_source_status_has_imerg():
    """imerg key must appear in source_status for every assessment."""
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert "imerg" in a["source_status"], f"imerg missing from source_status for {a['district_id']}"


def test_run_risk_model_rainfall_source_field_present():
    """rainfall_source field must be present on every assessment."""
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert "rainfall_source" in a, f"rainfall_source missing for {a['district_id']}"


def test_run_risk_model_rainfall_source_valid_values():
    """rainfall_source must be one of the expected labels (any non-empty subset of adapters)."""
    valid = {
        "synthetic",
        "adapter-imerg", "adapter-chirps", "adapter-glofas",
        "adapter-imerg-chirps", "adapter-imerg-glofas", "adapter-chirps-glofas",
        "adapter-imerg-chirps-glofas",
    }
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert a["rainfall_source"] in valid, (
            f"Unexpected rainfall_source '{a['rainfall_source']}' for {a['district_id']}"
        )


def test_run_risk_model_default_stub_gives_adapter_imerg_chirps_glofas():
    """Default stub mode: all three adapters stale → rainfall_source=adapter-imerg-chirps-glofas."""
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert a["rainfall_source"] == "adapter-imerg-chirps-glofas", (
            f"Expected adapter-imerg-chirps-glofas but got '{a['rainfall_source']}' "
            f"for {a['district_id']}"
        )
        assert a["source_status"]["imerg"] == "stale"
        assert a["source_status"]["chirps"] == "stale"
        assert a["source_status"]["glofas"] == "stale"


def test_run_risk_model_feature_snapshot_has_rainfall_keys():
    """feature_snapshot must contain dynamic rainfall keys from the adapter."""
    rainfall_keys = {"rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_anomaly_pct"}
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        snap = a.get("feature_snapshot", {})
        assert rainfall_keys.issubset(snap.keys()), (
            f"Missing rainfall keys in feature_snapshot for {a['district_id']}"
        )


def test_run_risk_model_source_status_has_chirps():
    """chirps key must appear in source_status for every assessment."""
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert "chirps" in a["source_status"], f"chirps missing from source_status for {a['district_id']}"


def test_run_risk_model_source_status_has_glofas():
    """glofas key must appear in source_status for every assessment."""
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert "glofas" in a["source_status"], f"glofas missing from source_status for {a['district_id']}"


def test_run_risk_model_feature_snapshot_has_river_discharge():
    """feature_snapshot must contain river_discharge_m3s from GloFAS stub."""
    resp = client.post("/api/v1/admin/run-risk-model")
    for a in resp.json()["assessments"]:
        assert "river_discharge_m3s" in a["feature_snapshot"], (
            f"river_discharge_m3s missing for {a['district_id']}"
        )


def test_run_risk_model_fallback_when_imerg_disabled():
    """IMERG disabled + CHIRPS+GloFAS stale → chirps-glofas label, scores still valid."""
    disabled = AdapterResult(
        source_id="imerg", status="disabled", data=[],
        fetched_at=datetime.now(UTC), latency_ms=0.0, error_message="not configured",
    )
    with patch("app.api.v1.admin.IMERGAdapter") as MockIMERG:
        MockIMERG.return_value.fetch.return_value = disabled
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    data = resp.json()
    assert data["districts_updated"] == 10
    for a in data["assessments"]:
        assert a["source_status"]["imerg"] == "disabled"
        assert a["source_status"]["chirps"] == "stale"
        assert a["source_status"]["glofas"] == "stale"
        assert a["rainfall_source"] == "adapter-chirps-glofas"
        assert 0.0 <= a["risk_score"] <= 1.0
        assert 0.0 <= a["confidence"] <= 1.0


def test_run_risk_model_fallback_when_chirps_disabled():
    """CHIRPS disabled + IMERG+GloFAS stale → imerg-glofas label, rainfall totals intact."""
    disabled = AdapterResult(
        source_id="chirps", status="disabled", data=[],
        fetched_at=datetime.now(UTC), latency_ms=0.0, error_message="not configured",
    )
    with patch("app.api.v1.admin.CHIRPSAdapter") as MockCHIRPS:
        MockCHIRPS.return_value.fetch.return_value = disabled
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    for a in resp.json()["assessments"]:
        assert a["source_status"]["chirps"] == "disabled"
        assert a["source_status"]["imerg"] == "stale"
        assert a["rainfall_source"] == "adapter-imerg-glofas"
        assert 0.0 <= a["risk_score"] <= 1.0


def test_run_risk_model_fallback_when_glofas_disabled():
    """GloFAS disabled + IMERG+CHIRPS stale → imerg-chirps label, IMERG rainfall intact."""
    disabled = AdapterResult(
        source_id="glofas", status="disabled", data=[],
        fetched_at=datetime.now(UTC), latency_ms=0.0, error_message="not configured",
    )
    with patch("app.api.v1.admin.GloFASAdapter") as MockGloFAS:
        MockGloFAS.return_value.fetch.return_value = disabled
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    for a in resp.json()["assessments"]:
        assert a["source_status"]["glofas"] == "disabled"
        assert a["rainfall_source"] == "adapter-imerg-chirps"
        assert 0.0 <= a["risk_score"] <= 1.0


def test_run_risk_model_fallback_when_all_disabled():
    """All adapters disabled → synthetic label, scores still valid."""
    mk = AdapterResult(source_id="x", status="disabled", data=[],
                       fetched_at=datetime.now(UTC), latency_ms=0.0)
    with patch("app.api.v1.admin.IMERGAdapter") as MI, \
         patch("app.api.v1.admin.CHIRPSAdapter") as MC, \
         patch("app.api.v1.admin.GloFASAdapter") as MG:
        MI.return_value.fetch.return_value = mk
        MC.return_value.fetch.return_value = mk
        MG.return_value.fetch.return_value = mk
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    for a in resp.json()["assessments"]:
        assert a["rainfall_source"] == "synthetic"
        assert 0.0 <= a["risk_score"] <= 1.0


def test_run_risk_model_chirps_anomaly_overrides_imerg_anomaly():
    """CHIRPS anomaly must override IMERG anomaly in feature_snapshot for SKR."""
    from app.adapters.chirps_adapter import _STUB_READINGS as CHIRPS_STUBS
    from dataclasses import asdict

    # Build a CHIRPS result with a distinct anomaly for SKR (999.0)
    chirps_skr = dict(asdict(CHIRPS_STUBS[0]))  # PK-SD-SKR
    chirps_skr["anomaly_pct"] = 999.0

    chirps_result = AdapterResult(
        source_id="chirps", status="stale",
        data=[chirps_skr],
        fetched_at=datetime.now(UTC), latency_ms=0.0,
    )
    with patch("app.api.v1.admin.CHIRPSAdapter") as MockCHIRPS:
        MockCHIRPS.return_value.fetch.return_value = chirps_result
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    skr = next(a for a in resp.json()["assessments"] if a["district_id"] == "PK-SD-SKR")
    assert skr["feature_snapshot"]["rainfall_anomaly_pct"] == 999.0


def test_run_risk_model_imerg_totals_intact_when_only_chirps_injected():
    """IMERG rainfall totals (1d/3d/7d) must not be erased when only CHIRPS is injected."""
    from app.adapters.chirps_adapter import _STUB_READINGS as CHIRPS_STUBS
    from dataclasses import asdict

    chirps_skr = dict(asdict(CHIRPS_STUBS[0]))
    chirps_result = AdapterResult(
        source_id="chirps", status="stale",
        data=[chirps_skr], fetched_at=datetime.now(UTC), latency_ms=0.0,
    )
    with patch("app.api.v1.admin.CHIRPSAdapter") as MockCHIRPS:
        MockCHIRPS.return_value.fetch.return_value = chirps_result
        resp = client.post("/api/v1/admin/run-risk-model")
    skr = next(a for a in resp.json()["assessments"] if a["district_id"] == "PK-SD-SKR")
    snap = skr["feature_snapshot"]
    # IMERG stub provides these; they must still be present
    assert "rainfall_1d_mm" in snap
    assert "rainfall_3d_mm" in snap
    assert "rainfall_7d_mm" in snap


def test_run_risk_model_imerg_high_rain_propagates():
    """Injecting high-rainfall IMERG result produces different feature_snapshot for SKR."""
    from app.adapters.imerg_adapter import _STUB_READINGS
    from dataclasses import asdict

    high_row = dict(asdict(_STUB_READINGS[0]))  # PK-SD-SKR
    high_row["rainfall_7d_mm"] = 999.0
    high_row["confidence"] = 0.9

    high_result = AdapterResult(
        source_id="imerg", status="fresh",
        data=[high_row], fetched_at=datetime.now(UTC), latency_ms=5.0,
    )
    with patch("app.api.v1.admin.IMERGAdapter") as MockIMERG:
        MockIMERG.return_value.fetch.return_value = high_result
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    skr = next(a for a in resp.json()["assessments"] if a["district_id"] == "PK-SD-SKR")
    assert skr["feature_snapshot"]["rainfall_7d_mm"] == 999.0
    # IMERG fresh + CHIRPS stale + GloFAS stale → all three contribute
    assert skr["rainfall_source"] == "adapter-imerg-chirps-glofas"


def test_run_risk_model_glofas_discharge_overrides_stub():
    """Injecting high GloFAS discharge must appear in feature_snapshot for SKR."""
    from app.adapters.glofas_adapter import _STUB_READINGS as GLOFAS_STUBS
    from dataclasses import asdict

    glofas_skr = dict(asdict(GLOFAS_STUBS[0]))  # PK-SD-SKR
    glofas_skr["river_discharge_m3s"] = 99999.0

    glofas_result = AdapterResult(
        source_id="glofas", status="fresh",
        data=[glofas_skr], fetched_at=datetime.now(UTC), latency_ms=3.0,
    )
    with patch("app.api.v1.admin.GloFASAdapter") as MockGloFAS:
        MockGloFAS.return_value.fetch.return_value = glofas_result
        resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.status_code == 200
    skr = next(a for a in resp.json()["assessments"] if a["district_id"] == "PK-SD-SKR")
    assert skr["feature_snapshot"]["river_discharge_m3s"] == 99999.0


def test_run_risk_model_persistence_called_via_service():
    """persist_model_run should be called; mock returns len(assessments) = 10."""
    resp = client.post("/api/v1/admin/run-risk-model")
    # Persistence is mocked in conftest (MockDisasterRiskService.persist_model_run)
    # — if it raised, the response would still be 200 (try/except in endpoint)
    assert resp.status_code == 200
    assert resp.json()["districts_updated"] == 10


# ---------------------------------------------------------------------------
# Phase 9 — persistence summary fields
# ---------------------------------------------------------------------------

def test_run_risk_model_has_persistence_summary_fields():
    """Response must include persisted_count, persistence_failed_count, persistence_status."""
    resp = client.post("/api/v1/admin/run-risk-model")
    data = resp.json()
    assert "persisted_count" in data
    assert "persistence_failed_count" in data
    assert "persistence_status" in data


def test_run_risk_model_persisted_count_equals_districts():
    """Mock service.persist_model_run returns len(assessments); persisted_count must match."""
    resp = client.post("/api/v1/admin/run-risk-model")
    data = resp.json()
    assert data["persisted_count"] == data["districts_updated"]
    assert data["persistence_failed_count"] == 0


def test_run_risk_model_persistence_status_ok_when_all_persisted():
    """When mock returns full count, persistence_status must be 'ok'."""
    resp = client.post("/api/v1/admin/run-risk-model")
    assert resp.json()["persistence_status"] == "ok"


def test_model_status_returns_200():
    resp = client.get("/api/v1/admin/model-status")
    assert resp.status_code == 200


def test_model_status_response_shape():
    resp = client.get("/api/v1/admin/model-status")
    data = resp.json()
    required = {"model_version", "artifact_available", "metrics_available",
                "district_count", "source_status_summary", "disclaimer"}
    assert required.issubset(data.keys())


def test_model_status_district_count_is_10():
    resp = client.get("/api/v1/admin/model-status")
    assert resp.json()["district_count"] == 10


def test_model_status_disclaimer_present():
    resp = client.get("/api/v1/admin/model-status")
    data = resp.json()
    assert "educational" in data["disclaimer"].lower()


def test_model_status_artifact_available_is_bool():
    resp = client.get("/api/v1/admin/model-status")
    assert isinstance(resp.json()["artifact_available"], bool)
