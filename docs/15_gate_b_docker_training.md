# 15 — Gate B inside the Docker backend container

This document explains how to run the v3 real-data prediction pipeline (Gate B)
from inside the existing `pakflood-ai-backend-1` container, avoiding the
GDAL/Fiona toolchain issues that block a host install on Windows.

## Why the host install (Windows + Python 3.14) failed

```
pip install -r ml/requirements.txt
…
CRITICAL:root:A GDAL API version must be specified. Provide a path to gdal-config
using a GDAL_CONFIG environment variable or use a GDAL_VERSION environment variable.
ERROR: Failed to build 'fiona' when getting requirements to build wheel
```

`fiona`, `rasterio` and `geopandas` need the GDAL native library. On Python 3.14
+ Windows there are no prebuilt wheels yet, so `pip` falls back to a source
build and fails because GDAL/`gdal-config` isn't on the host. Conda or
Python 3.12 wheels can fix this on the host — but the project already runs a
Linux Python 3.11 backend container with manylinux wheels available, so the
cleanest path is to run Gate B inside that container.

## Why Docker Python works

- The backend container runs Linux + Python 3.11.
- All 11 required libraries (`geopandas`, `rasterio`, `rasterstats`, `shapely`,
  `pyproj`, `joblib`, `pyarrow`, `pandas`, `numpy`, `scikit-learn`,
  `imbalanced-learn`) have prebuilt manylinux wheels — no GDAL source build is
  needed.

## Persistent docker-compose mounts

`docker-compose.yml` mounts the v3 training tree and the real-data tree into
the backend container so the scripts and inputs are visible without any ad-hoc
`docker cp`:

```yaml
backend:
  volumes:
    - ./backend:/app
    - ./ml:/app/ml
    - ./data:/app/data
```

With these mounts:

- `/app/ml/training/*.py` are the v3 pipeline scripts.
- `/app/data/real/raw/...` is where you place downloaded datasets.
- `/app/data/real/processed/`, `/app/data/real/training/`,
  `/app/data/real/reports/` are the script outputs.
- The container WORKDIR remains `/app`, so the relative paths inside
  `real_data_contract.py` (e.g. `data/real/raw/boundaries/...`) resolve
  cleanly.

The application-serving FastAPI process is unaffected — those mounts are
purely additive.

## Entering the container

```
docker-compose up -d backend
docker exec -it pakflood-ai-backend-1 bash
# inside the container:
cd /app
python --version          # → Python 3.11.x
ls ml/training            # → pipeline scripts
ls data/real/raw          # → 8 empty raw subdirs (waiting for downloads)
```

## Installing the v3 ML deps inside the container

The backend image only carries the FastAPI runtime by default. To enable the
Gate B pipeline:

```
docker exec pakflood-ai-backend-1 \
  python -m pip install --upgrade pip
docker exec pakflood-ai-backend-1 \
  python -m pip install -r /app/ml/requirements.txt
```

The install survives container restarts. If you ever rebuild the image
(`docker-compose build backend`), re-run the two commands above — the
backend `Dockerfile` does not bake these in to keep the served image small.

## Running the data contract

```
# Manifest of the 8 required datasets and where to put them:
docker exec pakflood-ai-backend-1 \
  python /app/ml/training/real_data_contract.py --print-manifest

# Full contract check — dependencies + files:
docker exec pakflood-ai-backend-1 \
  python /app/ml/training/real_data_contract.py --check
```

Until the 8 datasets are downloaded, `--check` exits non-zero with a
`DataMissingError` listing every missing path. That is the v3 fail-loud
contract behaving as designed.

## Where to place the 8 datasets

| key | local path | source |
|---|---|---|
| `boundaries` | `data/real/raw/boundaries/pakistan_districts.geojson` | HDX COD-AB Pakistan |
| `flood_extents` | `data/real/raw/flood_extents/unosat_flood_extents.geojson` | UNITAR-UNOSAT (LABELS ONLY) |
| `imerg_dir` | `data/real/raw/rainfall_imerg/imerg_YYYY-MM-DD.tif` | NASA GPM IMERG Final Run |
| `chirps_dir` | `data/real/raw/rainfall_chirps/chirps_YYYY-MM-DD.tif` | UCSB CHIRPS |
| `glofas` | `data/real/raw/glofas/glofas_district_daily.csv` | Copernicus GloFAS (pre-aggregated) |
| `elevation` | `data/real/raw/elevation/dem.tif` | SRTM v3 or Copernicus DEM GLO-30 |
| `rivers` | `data/real/raw/rivers/hydrorivers_pakistan.geojson` | HydroSHEDS / HydroRIVERS (clip to PK) |
| `population` | `data/real/raw/population/worldpop_pakistan.tif` (or `district_population_exposure.csv`) | WorldPop 2020 100 m |

Full per-dataset notes, filename rules, CRS notes and citation strings are in
`docs/14_data_intake_manifest.md`.

## The six Gate B training commands (after datasets are in place)

Run them in this exact order from inside the container:

```
docker exec pakflood-ai-backend-1 bash -lc '
cd /app && \
python ml/training/precompute_district_zonal_stats.py \
  --boundaries data/real/raw/boundaries/pakistan_districts.geojson \
  --imerg-dir data/real/raw/rainfall_imerg \
  --chirps-dir data/real/raw/rainfall_chirps \
  --elevation data/real/raw/elevation/dem.tif \
  --population data/real/raw/population/worldpop_pakistan.tif \
  --output data/real/processed/district_day_feature_store.parquet \
  --n-jobs -1
'

docker exec pakflood-ai-backend-1 bash -lc '
cd /app && \
python ml/training/precompute_river_features.py \
  --boundaries data/real/raw/boundaries/pakistan_districts.geojson \
  --rivers data/real/raw/rivers/hydrorivers_pakistan.geojson \
  --output data/real/processed/district_river_features.parquet \
  --metric-crs EPSG:6933
'

docker exec pakflood-ai-backend-1 bash -lc '
cd /app && \
python ml/training/build_chirps_climatology.py \
  --features data/real/processed/district_day_feature_store.parquet \
  --output data/real/processed/chirps_district_climatology.parquet \
  --min-years 10
'

docker exec pakflood-ai-backend-1 bash -lc '
cd /app && \
python ml/training/build_flood_labels.py \
  --boundaries data/real/raw/boundaries/pakistan_districts.geojson \
  --flood-extents data/real/raw/flood_extents/unosat_flood_extents.geojson \
  --output data/real/processed/district_day_labels.parquet \
  --metric-crs EPSG:6933 \
  --flood-area-threshold-pct 0.5 \
  --start-date 2010-01-01 \
  --end-date 2025-12-31
'

docker exec pakflood-ai-backend-1 bash -lc '
cd /app && \
python ml/training/build_prediction_dataset.py \
  --features data/real/processed/district_day_feature_store.parquet \
  --labels data/real/processed/district_day_labels.parquet \
  --glofas data/real/raw/glofas/glofas_district_daily.csv \
  --river-features data/real/processed/district_river_features.parquet \
  --chirps-climatology data/real/processed/chirps_district_climatology.parquet \
  --output data/real/training/pakistan_flood_prediction_v3.csv
'

docker exec pakflood-ai-backend-1 bash -lc '
cd /app && \
python ml/training/train_prediction_model.py \
  --dataset data/real/training/pakistan_flood_prediction_v3.csv \
  --target flood_next_72h \
  --model balanced_random_forest \
  --calibrate sigmoid \
  --test-strategy time_holdout \
  --output-dir ml/artifacts
'
```

After the last command finishes, the calibrated artifact lands at
`ml/artifacts/flood_prediction_calibrated_v3.pkl` on the host (via the bind
mount). The next backend restart picks it up automatically; `GET /api/v1/model/status`
flips to `{"artifact_exists": true, "is_prediction_model": true, ...}` and the
frontend swaps every "Real prediction model unavailable" string for the
"Real prediction v3" badge — without any code change.

## Reminders

- This document is for Gate B environment setup only. **No** training has been
  run yet, **no** datasets are downloaded yet, and the v3 real-data contract
  is unchanged. Do not introduce synthetic / mock / fallback inputs.
- If you rebuild the backend image, you must re-install
  `ml/requirements.txt` once with the `docker exec` command shown above.
- Application behaviour (FastAPI routes, frontend) is unchanged by the mount
  additions — they are pure read paths for Gate B tooling.
