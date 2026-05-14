"""v3 FeatureVectorProvider — Stage-1 bridge for Gate B inference.

After the user completes Gate B (downloads real datasets and runs the six
pipeline scripts), the latest feature row per district lives in
``data/real/training/pakistan_flood_prediction_v3.csv``. This provider reads
that file lazily and returns a dict of features for a single district_id,
stripped of leakage columns so the calibrated model never sees a future label.

It NEVER reads:
  - data/seed/mock_risk.json
  - DB RiskSnapshot rows
  - synthetic / hand-tuned fallback features

If the CSV is missing or the requested district is not present, it raises
``ModelArtifactMissingError`` so the API layer returns the structured HTTP 503.

TODO (post-Gate-B):
    The training CSV contains the target labels (``flood_next_*``) — we strip
    them with V3_LEAKAGE_COLUMNS before returning, but the file should not be
    used for inference long-term. Replace this bridge with a labels-free
    ``data/real/inference/latest_prediction_features.parquet`` produced by a
    future ``build_latest_features.py``, and have inference read that file
    directly. The bridge keeps end-to-end wiring testable immediately after
    Gate B, at the cost of an extra leakage-strip step.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.hazards.flood.model import V3_LEAKAGE_COLUMNS
from app.hazards.flood.v3_guard import ModelArtifactMissingError


_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_FEATURE_CSV = _PROJECT_ROOT / "data" / "real" / "training" / "pakistan_flood_prediction_v3.csv"


def _raise_missing(reason: str) -> None:
    raise ModelArtifactMissingError(
        reason=reason,
        required_artifact="data/real/training/pakistan_flood_prediction_v3.csv",
        metadata_path="ml/artifacts/flood_prediction_metadata_v3.json",
    )


def latest_features_for(district_id: str, required_feature_list: list[str]) -> dict[str, Any]:
    """Return the most recent feature row for ``district_id``, leakage-stripped.

    Args:
        district_id: e.g. "PK-SD-SKR"
        required_feature_list: the model metadata.feature_list — every entry
            must exist as a column in the CSV; missing columns raise.

    Returns:
        A dict ``{feature_name: value}`` with exactly the keys in
        ``required_feature_list``.

    Raises:
        ModelArtifactMissingError: file absent OR district absent OR required
            features missing OR all rows for this district are empty.
    """
    if not _FEATURE_CSV.exists():
        _raise_missing(
            "Real feature vector unavailable — run build_prediction_dataset.py "
            "and provide latest feature rows."
        )

    # Defer pandas import — backend is not required to have pandas in legacy mode
    import pandas as pd  # noqa: PLC0415

    df = pd.read_csv(_FEATURE_CSV)
    if "district_id" not in df.columns or "date" not in df.columns:
        _raise_missing("pakistan_flood_prediction_v3.csv missing district_id/date columns")

    sub = df[df["district_id"] == district_id]
    if sub.empty:
        _raise_missing(f"District {district_id} has no rows in pakistan_flood_prediction_v3.csv")

    # Latest row per district by date
    sub = sub.sort_values("date").iloc[-1]
    row = sub.to_dict()

    # Strip leakage columns (labels, ids, dates, metadata) before exposing.
    for col in V3_LEAKAGE_COLUMNS:
        row.pop(col, None)

    # Validate the model's required feature list
    missing = [c for c in required_feature_list if c not in row]
    if missing:
        _raise_missing(
            f"Latest feature row is missing required model features: {missing}. "
            f"Re-run build_prediction_dataset.py."
        )

    # Return ONLY the columns the model expects, in the same order.
    return {c: row[c] for c in required_feature_list}
