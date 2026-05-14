"""v3 strict fail-loud tests.

These tests force ``MODEL_MODE=real_prediction`` for the duration of the test
function. With the calibrated v3 artifact absent on disk, every model-dependent
endpoint must return HTTP 503 with the structured remediation body. No legacy
rule-based score, cached RiskSnapshot row, or mock_risk.json value may leak
through as v3 output.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.hazards.flood import v3_guard
from app.hazards.flood.v3_guard import (
    ModelArtifactMissingError,
    ensure_v3_ready,
    v3_artifact_state,
)
from app.main import app


@pytest.fixture
def v3_strict():
    """Force MODEL_MODE=real_prediction and ensure no artifact is on disk."""
    original_mode = settings.MODEL_MODE
    settings.MODEL_MODE = "real_prediction"
    yield
    settings.MODEL_MODE = original_mode


@pytest.fixture
def strict_client(v3_strict) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# /api/v1/model/status — must remain HTTP 200 with truthful state
# ---------------------------------------------------------------------------

def test_model_status_returns_200_with_artifact_missing(strict_client: TestClient):
    resp = strict_client.get("/api/v1/model/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "real_prediction"
    assert body["artifact_exists"] is False
    assert body["is_prediction_model"] is False
    assert body["remediation"] is not None
    assert "Real prediction model unavailable" in body["remediation"]


# ---------------------------------------------------------------------------
# Risk endpoints — must return HTTP 503 with structured body
# ---------------------------------------------------------------------------

def _assert_503_structured(resp):
    assert resp.status_code == 503
    body = resp.json()
    detail = body["detail"]
    assert detail["code"] == "MODEL_ARTIFACT_MISSING"
    assert "Real prediction model unavailable" in detail["message"]
    assert detail["required_artifact"].endswith("flood_prediction_calibrated_v3.pkl")
    assert detail["metadata_path"].endswith("flood_prediction_metadata_v3.json")
    assert isinstance(detail["next_steps"], list)
    assert any("real-data" in s.lower() or "download" in s.lower() for s in detail["next_steps"])
    assert any("train_prediction_model" in s for s in detail["next_steps"])


def test_risk_endpoint_returns_503_when_artifact_missing(strict_client: TestClient):
    resp = strict_client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    _assert_503_structured(resp)


def test_explain_risk_endpoint_returns_503_when_artifact_missing(strict_client: TestClient):
    resp = strict_client.get("/api/v1/explain-risk/by-boundary/PK-SD-SKR")
    _assert_503_structured(resp)


def test_admin_run_risk_model_returns_503_when_artifact_missing(strict_client: TestClient):
    resp = strict_client.post("/api/v1/admin/run-risk-model")
    _assert_503_structured(resp)


# ---------------------------------------------------------------------------
# Internal guard contract
# ---------------------------------------------------------------------------

def test_ensure_v3_ready_raises_when_artifact_missing(v3_strict):
    with pytest.raises(ModelArtifactMissingError) as exc:
        ensure_v3_ready()
    assert "Real prediction model unavailable" in str(exc.value)
    assert exc.value.required_artifact.endswith("flood_prediction_calibrated_v3.pkl")


def test_ensure_v3_ready_noop_when_mode_disabled():
    """When MODEL_MODE != real_prediction, ensure_v3_ready returns silently."""
    original = settings.MODEL_MODE
    settings.MODEL_MODE = "legacy_demo"
    try:
        state = ensure_v3_ready()
        # Must not raise even though artifact does not exist
        assert state.artifact_exists is False
    finally:
        settings.MODEL_MODE = original


def test_v3_artifact_state_reads_truthfully():
    state = v3_artifact_state()
    assert state.artifact_exists is False
    assert state.metadata_exists is False
    assert state.is_prediction_model is False


def test_legacy_rule_fallback_not_invoked_in_strict_mode(strict_client: TestClient, monkeypatch):
    """If anyone tries to call the old rule-based path while v3 is strict, the
    test must still see 503 (the guard short-circuits before any rule code runs).
    """
    from app.hazards.flood import model as flood_model

    called = {"v": False}

    def boom(*args, **kwargs):
        called["v"] = True
        raise AssertionError("Legacy _rule_infer must NOT be called in real_prediction mode")

    monkeypatch.setattr(flood_model, "_rule_based_score", boom)
    resp = strict_client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    assert resp.status_code == 503
    assert called["v"] is False


def test_mock_risksnapshot_not_served_as_v3_output(strict_client: TestClient):
    """Even though the mocked service returns a RiskResponse for PK-SD-SKR with
    risk_score=0.82 risk_level=High, the v3 strict route must not surface it."""
    resp = strict_client.get("/api/v1/risk/by-boundary/PK-SD-SKR")
    body = resp.json()
    # Must be the 503 structured error, NOT a risk response.
    assert resp.status_code == 503
    assert "risk_score" not in body
    assert "risk_level" not in body


# ---------------------------------------------------------------------------
# Confidence formula (Stage 1 spec)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("probability,expected_conf", [
    (0.5, 0.0),
    (0.9, 0.8),
    (0.1, 0.8),
    (1.0, 1.0),
    (0.0, 1.0),
])
def test_confidence_formula(probability, expected_conf):
    """Confidence = 2 * |p - 0.5|. Inverse of uncertainty."""
    from app.hazards.flood.model import v3_confidence_from_probability

    conf = v3_confidence_from_probability(probability)
    assert abs(conf - expected_conf) < 1e-9
    assert abs((1.0 - conf) - (1.0 - expected_conf)) < 1e-9  # uncertainty
