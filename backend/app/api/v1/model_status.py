"""GET /api/v1/model/status — truthful real-prediction-model status reporter.

Returns a JSON document describing whether the v3 calibrated artifact exists
on disk and what its metadata says. The frontend uses this to decide whether
to show "Real prediction v3" labels or the honest "Real prediction model
unavailable" message. The endpoint never lies and never falls back.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings


router = APIRouter()


def _project_root() -> Path:
    """Find the project root that contains ``ml/`` (host AND container)."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "ml").is_dir():
            return ancestor
    return Path.cwd()


@router.get("/model/status")
def get_model_status() -> dict:
    root = _project_root()
    artifact_rel, metadata_rel = settings.active_model_paths()
    artifact_path = root / artifact_rel
    metadata_path = root / metadata_rel

    artifact_exists = artifact_path.exists() and artifact_path.is_file()
    metadata_exists = metadata_path.exists() and metadata_path.is_file()

    metadata: dict = {}
    if metadata_exists:
        try:
            metadata = json.loads(metadata_path.read_text())
        except Exception:  # noqa: BLE001 — don't lie about success
            metadata = {}

    is_prediction_model = bool(metadata.get("is_prediction_model"))

    return {
        "mode": settings.MODEL_MODE,
        "artifact_exists": artifact_exists,
        "artifact_path": artifact_rel,
        "metadata_exists": metadata_exists,
        "metadata_path": metadata_rel,
        "is_prediction_model": is_prediction_model,
        "model_name": metadata.get("model_name"),
        "model_type": metadata.get("model_type"),
        "model_scope": metadata.get("model_scope"),
        "prediction_window": metadata.get("prediction_window"),
        "calibration_method": metadata.get("calibration_method"),
        "calibration_api": metadata.get("calibration_api"),
        "last_trained_iso": metadata.get("trained_at_iso"),
        "data_sources": metadata.get("data_sources"),
        "metric_crs": metadata.get("metric_crs"),
        "limitations": metadata.get("limitations"),
        "remediation": (
            None if (artifact_exists and is_prediction_model)
            else (
                "Real prediction model unavailable — run the real-data pipeline first."
                if settings.MODEL_MODE == "real_prediction"
                else "Real-lite prediction model unavailable — run ml/training/train_real_lite_model.py first."
            )
        ),
    }
