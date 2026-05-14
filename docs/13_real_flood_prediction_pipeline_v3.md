# 13 — Real Flood Prediction Pipeline v3

## Status
Strict, real-data-only implementation. No synthetic fallback. No baseline educational fallback for the v3 prediction path. Missing real files → fail loudly with explicit remediation instructions. Co-exists with `13_command_center_design.md` (different file, different topic).

## 0. Detection vs. Susceptibility vs. Prediction
- **Detection** — *current* flood water observed in satellite/aerial imagery (e.g. SAR/UNOSAT). Allowed wording for the SAR evidence panel only.
- **Susceptibility** — *static* exposure score from elevation, slope, distance to river, soil, land use, historical density. Time-invariant; not a forecast.
- **Prediction (this pipeline)** — *future* district-day flood probability for windows T+1d, T+1–3d, T+1–7d, conditioned on rainfall, river discharge, antecedent conditions, terrain, exposure, and historical signal available at time T.

PakFlood AI v3 is a **prediction model**, not a detection model. The metadata and UI must say so. Historical UNOSAT/HDX flood extents are used **as labels only**, never as input features.

## 1. Real-data-only policy
A v3 pipeline run is valid only when all eight required datasets are present at the paths declared in `ml/training/real_data_contract.py`. The contract module is callable from the command line:
```
python ml/training/real_data_contract.py --print-manifest
python ml/training/real_data_contract.py --check
```
Every pipeline script also calls `validate_dependencies()` and `validate_real_data_contract(required_keys=...)` after argparse resolves a non-help invocation, so `--help` always works on a fresh environment but real work fails fast when inputs are missing.

There is no synthetic fallback anywhere in the v3 prediction path. There is no automatic generation of toy features, toy rainfall, toy labels, or toy training rows. Tiny in-memory DataFrames are permitted in `ml/tests/` only to validate utility logic (CRS guards, reindex, leakage).

## 2. District-day feature store architecture
The pipeline pre-aggregates raster sources (IMERG, CHIRPS, DEM, WorldPop) to one parquet keyed by `(district_id, date)` *before* training. This is the only acceptable design at our scale:
- Raster volumes (hundreds-to-thousands of daily TIFFs) cannot be re-read per training epoch.
- Pre-aggregation in `precompute_district_zonal_stats.py` exposes a single fast columnar feature store via `pyarrow`.
- Per-raster outputs are cached so re-runs only process new files.

Zonal statistics are computed in **parallel** via `joblib.Parallel(n_jobs=-1)`. Each `(raster, date)` pair is an independent job. Failures are written to `data/real/reports/zonal_stats_failures.json`; the run fails non-zero unless `--allow-partial` is passed.

## 3. Metric CRS requirement
All area, distance and length calculations must run in a projected metric CRS. The default is **EPSG:6933** (national equal-area). `EPSG:32642` (UTM zone 42N) is accepted for regional testing via `--metric-crs`. Refusing to compute area/distance in a geographic CRS (e.g. EPSG:4326) is a hard runtime guard in every script:
```python
if gdf.crs.is_geographic:
    raise RuntimeError("Refusing area calculation in geographic CRS …")
```
The chosen CRS is recorded in every output's metadata.

## 4. Continuous date-index requirement
Real satellite/rainfall feeds have missing days. Lag/rolling/antecedent features are correct only when every district is reindexed to a complete daily date range *before* the time-series transforms run:
```python
for district_id, group in features.groupby("district_id"):
    group = group.sort_values("date").set_index("date")
    full = group.reindex(pd.date_range(start, end, freq="D"))
    full["imerg_rainfall_mean_mm"] = full["imerg_rainfall_mean_mm"].fillna(0.0)
    ...  # then compute rolling/lag/antecedent
```
Missingness is preserved via `imerg_missing_flag`, `chirps_missing_flag`, `glofas_missing_flag` so downstream models can learn around it. Static features (elevation, slope, exposure) are forward/back-filled inside each district.

## 5. Feature design
**Lag**: `precip_lag_{1,3,7,14}d`, `discharge_lag_{1,3,7}d`
**Rolling (trailing only, never `center=True`)**: `rainfall_{1,3,7,14,30}d_mm`
**Antecedent (excludes today via `shift(1)`)**: `antecedent_precip_{3,7,14,30}d`
**Anomalies** (using `chirps_district_climatology.parquet` joined on `(district_id, day_of_year)`):
- `rainfall_anomaly_pct = (imerg - chirps_climatology) / chirps_climatology * 100`
- `chirps_anomaly_pct  = (chirps - chirps_climatology) / chirps_climatology * 100`
- `discharge_anomaly_pct` from a trailing 30-day rolling mean.
**Static**: elevation, slope, `distance_to_river_km`, `drainage_density`, `historical_flood_count`, `population_exposure_score`.
**Interactions**:
- `rainfall_7d_x_slope`
- `rainfall_7d_x_distance_to_river_inverse = rainfall_7d / (distance_to_river + 0.1)`
- `rainfall_7d_x_historical_flood_count`
- `discharge_x_rainfall_7d`
- `anomaly_x_discharge`
- `population_x_risk_exposure`

## 6. Future label shift design (T → T+1, T+3, T+7)
Labels are produced from `observed_flood_today` via **explicit forward shifts**, never `rolling(...).shift(...)`:
```python
flood_next_24h = obs.shift(-1).fillna(0)
flood_next_72h = max(obs.shift(-1), obs.shift(-2), obs.shift(-3))
flood_next_7d  = max(obs.shift(-1) … obs.shift(-7))
```
A unit test (`test_future_label_shifts_align_on_toy_series`) verifies the alignment against a hand-computed truth table.

## 7. Class imbalance strategy
Flood-positive days are rare. The classifier is `imblearn.ensemble.BalancedRandomForestClassifier` with 400 trees. If `imbalanced-learn` is not importable, the script exits with `pip install imbalanced-learn>=0.12` — no silent fallback to a vanilla RandomForest.

The script refuses to train if `y.sum() == 0` or `y.sum() < --min-positive-samples` (default 20).

## 8. Probability calibration strategy
Random-forest probabilities are well-known to be biased toward 0 / 1. v3 wraps the fitted base estimator in `sklearn.calibration.CalibratedClassifierCV` using **sigmoid (Platt) scaling by default**, evaluated against an isotonic option for sufficiently large datasets.

The three row sets are **disjoint** by construction:
- `fit_train` → fits `BalancedRandomForestClassifier`
- `calibration_train` → fits `CalibratedClassifierCV`
- `test` → final evaluation only

Calibration API: `sklearn.frozen.FrozenEstimator` is preferred (scikit-learn ≥ 1.6). Older versions fall back to `cv="prefit"` with a documented compatibility comment in the code. The actual API used is recorded in metadata as `calibration_api`.

A 10-bin reliability table is saved to the metrics JSON for inspection.

Risk-level mapping from calibrated probability:
- Low: probability < 0.30
- Moderate: 0.30 ≤ probability < 0.55
- High: 0.55 ≤ probability < 0.75
- Severe: probability ≥ 0.75

## 9. Leakage prevention rules
- Target columns (`flood_next_24h/72h/7d`) and `observed_flood_today` are excluded from the feature matrix in `_build_feature_matrix()`.
- Rolling windows are trailing-only; `center=True` is forbidden.
- Lag features use `shift(N)` with N > 0 only.
- Antecedent precipitation uses `shift(1).rolling(N)` to exclude *today*.
- Future-window labels are produced by explicit forward shifts, never by rolling+shift composition.

## 10. File contract
```
data/real/raw/boundaries/pakistan_districts.geojson        boundaries  [required]
data/real/raw/flood_extents/unosat_flood_extents.geojson   flood_extents [required, labels-only]
data/real/raw/rainfall_imerg/*.tif                          imerg_dir   [required]
data/real/raw/rainfall_chirps/*.tif                         chirps_dir  [required]
data/real/raw/glofas/glofas_district_daily.csv              glofas      [required, pre-aggregated]
data/real/raw/elevation/dem.tif                             elevation   [required]
data/real/raw/rivers/hydrorivers_pakistan.geojson           rivers      [required, clip to PK]
data/real/raw/population/worldpop_pakistan.tif              population  [required (or district CSV)]
```
GloFAS NetCDF/GRIB → district-day CSV conversion is **out of scope for v3**. The CSV must exist before the dataset builder runs.

## 11. Training commands
```
python ml/training/precompute_district_zonal_stats.py \
  --boundaries data/real/raw/boundaries/pakistan_districts.geojson \
  --imerg-dir data/real/raw/rainfall_imerg \
  --chirps-dir data/real/raw/rainfall_chirps \
  --elevation data/real/raw/elevation/dem.tif \
  --population data/real/raw/population/worldpop_pakistan.tif \
  --output data/real/processed/district_day_feature_store.parquet \
  --n-jobs -1

python ml/training/precompute_river_features.py \
  --boundaries data/real/raw/boundaries/pakistan_districts.geojson \
  --rivers data/real/raw/rivers/hydrorivers_pakistan.geojson \
  --output data/real/processed/district_river_features.parquet

python ml/training/build_chirps_climatology.py \
  --features data/real/processed/district_day_feature_store.parquet \
  --output data/real/processed/chirps_district_climatology.parquet

python ml/training/build_flood_labels.py \
  --boundaries data/real/raw/boundaries/pakistan_districts.geojson \
  --flood-extents data/real/raw/flood_extents/unosat_flood_extents.geojson \
  --output data/real/processed/district_day_labels.parquet \
  --metric-crs EPSG:6933 \
  --flood-area-threshold-pct 0.5 \
  --start-date 2010-01-01 --end-date 2025-12-31

python ml/training/build_prediction_dataset.py \
  --features data/real/processed/district_day_feature_store.parquet \
  --labels data/real/processed/district_day_labels.parquet \
  --glofas data/real/raw/glofas/glofas_district_daily.csv \
  --river-features data/real/processed/district_river_features.parquet \
  --chirps-climatology data/real/processed/chirps_district_climatology.parquet \
  --output data/real/training/pakistan_flood_prediction_v3.csv

python ml/training/train_prediction_model.py \
  --dataset data/real/training/pakistan_flood_prediction_v3.csv \
  --target flood_next_72h \
  --model balanced_random_forest \
  --calibrate sigmoid \
  --test-strategy time_holdout
```

## 12. Limitations
- Educational decision-support prototype only. Not an authoritative emergency alert.
- Coverage limited to Pakistan districts; behaviour outside Pakistan is undefined.
- Performance depends on UNOSAT label coverage during the training period; districts/events with no labels appear as `0` in the future-window target and may suppress recall.
- The v3 calibrated artifact exists only after Gate B (real-data download + full pipeline run). Until then `/api/v1/model/status` returns `artifact_exists: false` and the frontend chrome shows "Real prediction model unavailable".
