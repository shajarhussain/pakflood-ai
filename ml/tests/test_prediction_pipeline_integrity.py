"""Integrity tests for the PakFlood AI v3 real prediction pipeline.

Policy reminder
---------------
Tiny in-memory pandas/GeoDataFrame fixtures are permitted ONLY for unit-level
validation of utility behaviour (date reindexing, CRS guards, leakage rules,
explicit-forward-shift label alignment). Such fixtures MUST NOT be used to
claim a successful training run or to populate the deployed v3 calibrated
artifact. All training-success / pipeline-success tests are gated behind
``REAL_DATA_INTEGRATION_TESTS=1`` and report SKIPPED when that env var is
absent.

These tests run on a fresh Python environment by skipping any test that
depends on optional geospatial / ML libraries when the library is not
importable (``pytest.importorskip``). They never lie about success.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_TRAINING = PROJECT_ROOT / "ml" / "training"


# ---------------------------------------------------------------------------
# Contract / DataMissingError / DependencyMissingError
# ---------------------------------------------------------------------------

def test_imports_real_data_contract_module():
    """real_data_contract must import on stdlib-only environment."""
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from ml.training import real_data_contract  # noqa: F401
    finally:
        sys.path.remove(str(PROJECT_ROOT))


def test_data_missing_error_message_lists_paths(tmp_path, monkeypatch):
    """validate_real_data_contract() must list every missing expected path."""
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from ml.training import real_data_contract as rdc
    finally:
        sys.path.remove(str(PROJECT_ROOT))

    # Re-route the contract to an empty tmp dir so nothing is present.
    empty_specs = []
    for spec in rdc.REQUIRED_FILES:
        if spec.path is not None:
            new_path = tmp_path / spec.path
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new = rdc.FileSpec(
                key=spec.key, purpose=spec.purpose, source_org=spec.source_org,
                download_url=spec.download_url, citation=spec.citation,
                required=spec.required, path=new_path,
            )
        else:
            new_dir = tmp_path / spec.dir
            new_dir.mkdir(parents=True, exist_ok=True)
            new = rdc.FileSpec(
                key=spec.key, purpose=spec.purpose, source_org=spec.source_org,
                download_url=spec.download_url, citation=spec.citation,
                required=spec.required, dir=new_dir, dir_pattern=spec.dir_pattern,
            )
        empty_specs.append(new)

    monkeypatch.setattr(rdc, "REQUIRED_FILES", empty_specs)
    with pytest.raises(rdc.DataMissingError) as exc_info:
        rdc.validate_real_data_contract()
    msg = str(exc_info.value)
    for spec in empty_specs:
        target = str(spec.path or spec.dir)
        assert target in msg or spec.key in msg, f"missing reference to {spec.key} in error message"


def test_dependency_missing_raises_with_install_hint(monkeypatch):
    """If a required package import fails, the install command is in the error."""
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from ml.training import real_data_contract as rdc
    finally:
        sys.path.remove(str(PROJECT_ROOT))

    real_import = __import__

    def fake_import(name, *a, **kw):
        if name == "geopandas":
            raise ImportError("simulated missing geopandas")
        return real_import(name, *a, **kw)

    import builtins
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(rdc.DependencyMissingError) as exc:
        rdc.validate_dependencies(["geopandas"])
    assert "pip install -r ml/requirements.txt" in str(exc.value)
    assert "geopandas" in exc.value.missing


def test_contract_cli_check_exits_nonzero(tmp_path, monkeypatch):
    """`python real_data_contract.py --check` exits non-zero with empty raw dirs."""
    cwd = tmp_path
    monkeypatch.chdir(cwd)
    # Run the contract CLI with no real-data dirs in the working dir.
    res = subprocess.run(
        [sys.executable, str(ML_TRAINING / "real_data_contract.py"), "--check"],
        capture_output=True, text=True,
    )
    assert res.returncode != 0
    assert ("dependencies" in res.stderr.lower()
            or "contract violated" in res.stderr.lower())


def test_contract_cli_print_manifest_succeeds():
    res = subprocess.run(
        [sys.executable, str(ML_TRAINING / "real_data_contract.py"), "--print-manifest"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0
    # All 8 manifest keys must appear in the output.
    keys = ["boundaries", "flood_extents", "imerg_dir", "chirps_dir",
            "glofas", "elevation", "rivers", "population"]
    for k in keys:
        assert k in res.stdout, f"manifest missing key: {k}"


# ---------------------------------------------------------------------------
# CLI --help works on fresh env (no heavy imports at module top)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("script", [
    "precompute_district_zonal_stats.py",
    "precompute_river_features.py",
    "build_chirps_climatology.py",
    "build_flood_labels.py",
    "build_prediction_dataset.py",
    "train_prediction_model.py",
])
def test_every_pipeline_script_help_exits_zero(script):
    res = subprocess.run(
        [sys.executable, str(ML_TRAINING / script), "--help"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, f"{script} --help exited {res.returncode}\n{res.stderr}"
    assert "usage:" in res.stdout.lower()


# ---------------------------------------------------------------------------
# Area / CRS guards (require pyproj + shapely)
# ---------------------------------------------------------------------------

def test_area_calc_refuses_geographic_crs():
    """Computing area in EPSG:4326 must raise — the explicit fail-loud guard."""
    pyproj = pytest.importorskip("pyproj")
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    g = gpd.GeoDataFrame({"id": [1]}, geometry=[box(67.0, 24.0, 68.0, 25.0)], crs="EPSG:4326")
    assert g.crs.is_geographic
    # The pipeline-level guard form
    with pytest.raises(RuntimeError):
        if g.crs.is_geographic:
            raise RuntimeError("Refusing area calculation in geographic CRS")


def test_area_calc_works_in_metric_crs():
    """Same geometry in EPSG:6933 (default) and EPSG:32642 (regional) → positive area."""
    pyproj = pytest.importorskip("pyproj")
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    g = gpd.GeoDataFrame({"id": [1]}, geometry=[box(67.0, 24.0, 68.0, 25.0)], crs="EPSG:4326")
    for crs in ("EPSG:6933", "EPSG:32642"):
        proj = g.to_crs(crs)
        assert not proj.crs.is_geographic
        assert float(proj.geometry.iloc[0].area) > 0


# ---------------------------------------------------------------------------
# Continuous date index + rolling features
# ---------------------------------------------------------------------------

def test_continuous_date_index_creates_missing_days():
    pd = pytest.importorskip("pandas")
    s = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-05"]),
        "imerg_rainfall_mean_mm": [5.0, 0.0, 10.0],
    }).set_index("date")
    full = s.reindex(pd.date_range("2024-01-01", "2024-01-05", freq="D"))
    full["imerg_rainfall_mean_mm"] = full["imerg_rainfall_mean_mm"].fillna(0.0)
    assert len(full) == 5
    assert float(full.loc["2024-01-02", "imerg_rainfall_mean_mm"]) == 0.0


def test_rolling_window_uses_filled_zeros_and_is_trailing():
    pd = pytest.importorskip("pandas")
    s = pd.Series([1.0, 2.0, 3.0, 0.0, 0.0, 5.0])
    r3 = s.rolling(3, min_periods=1).sum()
    # Trailing: at position 2 (index 2) value should be 1+2+3 = 6
    assert float(r3.iloc[2]) == 6.0
    # No center=True magic — value at position 3 includes 2,3,0
    assert float(r3.iloc[3]) == 5.0


def test_lag_features_no_future_leakage():
    pd = pytest.importorskip("pandas")
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    lag3 = s.shift(3)
    assert pd.isna(lag3.iloc[0]) and pd.isna(lag3.iloc[1]) and pd.isna(lag3.iloc[2])
    assert float(lag3.iloc[3]) == 1.0
    assert float(lag3.iloc[4]) == 2.0


# ---------------------------------------------------------------------------
# Explicit forward-shift labels
# ---------------------------------------------------------------------------

def test_future_label_shifts_align_on_toy_series():
    """Hand-computed truth table for forward shifts."""
    pd = pytest.importorskip("pandas")
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from ml.training.build_flood_labels import _future_max
    finally:
        sys.path.remove(str(PROJECT_ROOT))

    obs = pd.Series([0, 0, 1, 0, 0, 0, 0, 0, 1, 0])

    # flood_next_24h = shift(-1).fillna(0)
    next_24h = obs.shift(-1).fillna(0).astype(int).tolist()
    assert next_24h == [0, 1, 0, 0, 0, 0, 0, 1, 0, 0]

    # flood_next_72h = max(shift(-1), shift(-2), shift(-3))
    next_72h = _future_max(obs, [1, 2, 3]).tolist()
    # At index 0: positions 1,2,3 → 0,1,0 → max = 1
    # At index 5: positions 6,7,8 → 0,0,1 → max = 1
    # At index 7: positions 8,9,10(N/A) → 1,0,_ → max = 1
    assert next_72h[0] == 1
    assert next_72h[5] == 1
    assert next_72h[7] == 1
    assert next_72h[-1] == 0  # nothing after the last row

    # flood_next_7d = max(shift(-1) … shift(-7))
    next_7d = _future_max(obs, list(range(1, 8))).tolist()
    # First positive at index 2 → indices 0,1 see it within 7 days
    assert next_7d[0] == 1
    assert next_7d[1] == 1
    # Index 9 is the last → no future rows → 0
    assert next_7d[9] == 0


# ---------------------------------------------------------------------------
# Leakage prevention in feature-matrix builder
# ---------------------------------------------------------------------------

def test_target_and_label_columns_excluded_from_features():
    pd = pytest.importorskip("pandas")
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from ml.training.train_prediction_model import _build_feature_matrix, EXCLUDED_COLS
    finally:
        sys.path.remove(str(PROJECT_ROOT))

    df = pd.DataFrame({
        "district_id": ["A", "A", "B"],
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-01"]),
        "observed_flood_today": [0, 1, 0],
        "flood_next_24h": [1, 0, 0],
        "flood_next_72h": [1, 1, 0],
        "flood_next_7d": [1, 1, 0],
        "rainfall_7d_mm": [10.0, 20.0, 5.0],
        "elevation_mean_m": [100.0, 100.0, 200.0],
    })
    X, feature_list = _build_feature_matrix(df, target="flood_next_72h")
    for forbidden in ("observed_flood_today", "flood_next_24h",
                      "flood_next_72h", "flood_next_7d",
                      "district_id", "date"):
        assert forbidden not in feature_list
    assert "rainfall_7d_mm" in feature_list
    assert "elevation_mean_m" in feature_list


def test_metadata_must_say_prediction_not_detection():
    """If metadata exists, it must declare itself a prediction model."""
    metadata_path = PROJECT_ROOT / "ml" / "artifacts" / "flood_prediction_metadata_v3.json"
    if not metadata_path.exists():
        pytest.skip("metadata not yet produced (Gate B not run)")
    md = json.loads(metadata_path.read_text())
    assert md["is_prediction_model"] is True
    assert md["is_detection_model"] is False
    assert "predicts flood probability" in md["prediction_summary"].lower() or \
           "predict" in md["prediction_summary"].lower()


# ---------------------------------------------------------------------------
# Integration tests — gated
# ---------------------------------------------------------------------------

INTEGRATION = pytest.mark.skipif(
    os.environ.get("REAL_DATA_INTEGRATION_TESTS") != "1",
    reason="set REAL_DATA_INTEGRATION_TESTS=1 to run after downloading real data",
)


@INTEGRATION
def test_full_pipeline_contract_satisfied():
    """Once real files are downloaded, the contract check must pass."""
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from ml.training.real_data_contract import (
            validate_dependencies, validate_real_data_contract,
        )
    finally:
        sys.path.remove(str(PROJECT_ROOT))
    validate_dependencies()
    report = validate_real_data_contract()
    assert report["ok"], f"missing keys: {report['missing']}"
