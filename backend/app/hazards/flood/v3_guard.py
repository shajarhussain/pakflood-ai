"""v3 fail-loud guard for the real prediction model.

When ``settings.MODEL_MODE == "real_prediction"`` and the calibrated artifact
is missing on disk, every model-dependent API route MUST refuse to serve a
response. No legacy rule-based score, no cached RiskSnapshot row, no
``data/seed/mock_risk.json`` value may be returned as v3 prediction output.

This module:
- exposes ``ModelArtifactMissingError`` — the typed exception
- exposes ``v3_artifact_state()`` — cheap on-disk inspection of the artifact
  and metadata pair
- exposes ``ensure_v3_ready()`` — raises ``ModelArtifactMissingError`` when
  the strict mode is active and the artifact is absent or its metadata is
  malformed
- registers a FastAPI exception handler that converts
  ``ModelArtifactMissingError`` into a structured HTTP 503 body
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings


def _resolve_project_root() -> Path:
    """Find the project root that contains ``ml/``.

    Host layout: ``pakflood-ai/backend/app/hazards/flood/v3_guard.py`` →
    ``pakflood-ai/`` (parents[4]).
    Container layout: ``/app/app/hazards/flood/v3_guard.py`` with the host's
    ``ml/`` bind-mounted at ``/app/ml`` → ``/app`` (parents[3]).
    The ``ml/`` directory is the universal anchor in both layouts.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "ml").is_dir():
            return ancestor
    return Path.cwd()


_PROJECT_ROOT = _resolve_project_root()


NEXT_STEPS = [
    "Download datasets listed in docs/14_data_intake_manifest.md",
    "Run precompute_district_zonal_stats.py",
    "Run precompute_river_features.py",
    "Run build_chirps_climatology.py",
    "Run build_flood_labels.py",
    "Run build_prediction_dataset.py",
    "Run train_prediction_model.py",
]


class ModelArtifactMissingError(RuntimeError):
    """Raised when the real prediction artifact is not available on disk.

    Mapped to HTTP 503 with a structured body by the FastAPI exception handler
    installed via ``install_v3_exception_handler``.
    """

    def __init__(self, reason: str, required_artifact: str, metadata_path: str):
        self.reason = reason
        self.required_artifact = required_artifact
        self.metadata_path = metadata_path
        super().__init__(reason)


@dataclass(frozen=True)
class V3ArtifactState:
    artifact_exists: bool
    metadata_exists: bool
    is_prediction_model: bool
    artifact_path: str
    metadata_path: str
    metadata: dict


def v3_artifact_state() -> V3ArtifactState:
    """Read the active model's artifact/metadata state from disk. Never raises.

    Honours ``settings.active_model_paths()`` so the same function works for
    both strict ``real_prediction`` and Gate B-Lite ``real_lite_prediction``.
    """
    artifact_rel, metadata_rel = settings.active_model_paths()
    artifact_path = _PROJECT_ROOT / artifact_rel
    metadata_path = _PROJECT_ROOT / metadata_rel

    artifact_exists = artifact_path.exists() and artifact_path.is_file()
    metadata_exists = metadata_path.exists() and metadata_path.is_file()

    metadata: dict = {}
    if metadata_exists:
        try:
            metadata = json.loads(metadata_path.read_text())
        except Exception:  # noqa: BLE001
            metadata = {}

    is_prediction_model = bool(metadata.get("is_prediction_model"))

    return V3ArtifactState(
        artifact_exists=artifact_exists,
        metadata_exists=metadata_exists,
        is_prediction_model=is_prediction_model,
        artifact_path=artifact_rel,
        metadata_path=metadata_rel,
        metadata=metadata,
    )


def ensure_v3_ready() -> V3ArtifactState:
    """Raise ``ModelArtifactMissingError`` unless the active model is fully ready.

    Both ``real_prediction`` (strict v3) and ``real_lite_prediction`` (Gate
    B-Lite weak-label prototype) flow through the same guard. In
    ``real_lite_prediction`` mode the artifact existing is enough to mark
    ``/model/status`` as available — but the risk endpoints still raise
    here because no live NASA-POWER-driven feature provider is wired yet,
    and we will not serve legacy mock scores as if they were v3 output.

    The escape hatch ``MODEL_MODE != real_prediction|real_lite_prediction``
    exists only for legacy tests that pin a different mode via env var.
    """
    state = v3_artifact_state()
    if settings.MODEL_MODE not in (
        "real_prediction", "real_lite_prediction", "dataset_based_prediction",
    ):
        return state

    # Gate B-Lite or dataset-based: even with the artifact present, no live
    # feature provider for the risk endpoints is wired yet. Block them with
    # a distinct message so legacy rule scores never leak through as v3 output.
    if settings.MODEL_MODE in ("real_lite_prediction", "dataset_based_prediction"):
        if not state.artifact_exists:
            raise ModelArtifactMissingError(
                reason=(
                    "Real-lite prediction model unavailable — run "
                    "ml/training/train_real_lite_model.py first."
                ),
                required_artifact=state.artifact_path,
                metadata_path=state.metadata_path,
            )
        raise ModelArtifactMissingError(
            reason=(
                "Real-lite prediction inference is not wired yet for the risk "
                "endpoints. /api/v1/model/status reports the trained artifact, "
                "but live per-request feature fetching from NASA POWER has not "
                "been implemented. No legacy rule-based score is served."
            ),
            required_artifact=state.artifact_path,
            metadata_path=state.metadata_path,
        )

    if not state.artifact_exists:
        raise ModelArtifactMissingError(
            reason="Real prediction model unavailable. Run the real-data pipeline first.",
            required_artifact=state.artifact_path,
            metadata_path=state.metadata_path,
        )
    if not state.metadata_exists or not state.is_prediction_model:
        raise ModelArtifactMissingError(
            reason="Real prediction model metadata missing or malformed.",
            required_artifact=state.artifact_path,
            metadata_path=state.metadata_path,
        )

    # Strict validation of metadata contract
    required_keys = ("feature_list", "target", "prediction_window", "calibration_method")
    missing = [k for k in required_keys if k not in state.metadata]
    if missing:
        raise ModelArtifactMissingError(
            reason=f"Real prediction model metadata is missing required keys: {missing}",
            required_artifact=state.artifact_path,
            metadata_path=state.metadata_path,
        )
    if state.metadata.get("is_detection_model") is True:
        raise ModelArtifactMissingError(
            reason="Refusing to serve a detection model from the prediction endpoint.",
            required_artifact=state.artifact_path,
            metadata_path=state.metadata_path,
        )

    return state


def _exception_handler(_request: Request, exc: ModelArtifactMissingError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "MODEL_ARTIFACT_MISSING",
                "message": exc.reason,
                "required_artifact": exc.required_artifact,
                "metadata_path": exc.metadata_path,
                "next_steps": NEXT_STEPS,
            }
        },
    )


def install_v3_exception_handler(app: FastAPI) -> None:
    """Wire the FastAPI app to convert ModelArtifactMissingError → HTTP 503."""
    app.add_exception_handler(ModelArtifactMissingError, _exception_handler)
