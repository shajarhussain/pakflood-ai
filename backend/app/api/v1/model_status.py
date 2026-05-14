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
    # backend/app/api/v1/model_status.py → backend/app/api/v1 → backend/app/api → backend/app → backend → project_root
    return Path(__file__).resolve().parents[4]


@router.get("/model/status")
def get_model_status() -> dict:
    root = _project_root()
    artifact_path = root / settings.PREDICTION_MODEL_PATH
    metadata_path = root / settings.PREDICTION_METADATA_PATH

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
        "artifact_path": settings.PREDICTION_MODEL_PATH,
        "metadata_exists": metadata_exists,
        "metadata_path": settings.PREDICTION_METADATA_PATH,
        "is_prediction_model": is_prediction_model,
        "model_name": metadata.get("model_name"),
        "model_type": metadata.get("model_type"),
        "prediction_window": metadata.get("prediction_window"),
        "calibration_method": metadata.get("calibration_method"),
        "calibration_api": metadata.get("calibration_api"),
        "last_trained_iso": metadata.get("trained_at_iso"),
        "data_sources": metadata.get("data_sources"),
        "metric_crs": metadata.get("metric_crs"),
        "remediation": (
            None if (artifact_exists and is_prediction_model)
            else "Real prediction model unavailable — run the real-data pipeline first."
        ),
    }
