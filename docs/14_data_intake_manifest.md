# 14 — Data Intake Manifest (PakFlood AI v3)

This is the canonical list of real datasets required to train the v3 flood
**probability prediction** model. Every dataset below must be downloaded by the
user and placed at the exact local path. No synthetic substitute exists.

Quick verification:
```
python ml/training/real_data_contract.py --print-manifest
python ml/training/real_data_contract.py --check
```

---

## 1. Pakistan district boundaries

- **Source organisation:** HDX (Humanitarian Data Exchange) / OCHA — COD-AB Pakistan
- **Required:** yes
- **File type:** GeoJSON preferred; Shapefile acceptable (convert with `ogr2ogr`)
- **Local path:** `data/real/raw/boundaries/pakistan_districts.geojson`
- **Filename rule:** exact name `pakistan_districts.geojson`
- **Download:** <https://data.humdata.org/dataset/cod-ab-pak>
- **Purpose:** district polygons used by every zonal-stat and label step
- **Common issues:**
  - GeoJSON has no CRS → set EPSG:4326 explicitly before placing
  - Field name for district id must be `district_id` (rename in QGIS / `ogr2ogr -sql`)
- **Citation:** HDX / COD-AB Pakistan (latest release)

## 2. UNOSAT / HDX flood extents (LABELS ONLY)

- **Source organisation:** UNITAR-UNOSAT, published via HDX
- **Required:** yes
- **File type:** GeoJSON / Shapefile
- **Local path:** `data/real/raw/flood_extents/unosat_flood_extents.geojson`
- **Filename rule:** exact name `unosat_flood_extents.geojson`
- **Download:** <https://data.humdata.org/dataset?q=pakistan+flood+unosat>
- **Purpose:** **labels only** — never used as features. Spatial intersection with district polygons yields `observed_flood_today`, which is shifted into future-window labels.
- **Required property per feature:** event date in `event_date` (override with `--date-property`)
- **Common issues:**
  - Multiple UNOSAT products per year — concatenate them into one FeatureCollection before placing
  - Feature dates given as `OBSERVED_AT` etc. → use `--date-property OBSERVED_AT`
- **Citation:** UNITAR-UNOSAT Pakistan flood mapping products

## 3. IMERG daily rainfall (NASA GPM)

- **Source organisation:** NASA GPM IMERG Final Run
- **Required:** yes
- **File type:** daily GeoTIFF (exported from HDF5 / Google Earth Engine)
- **Local directory:** `data/real/raw/rainfall_imerg/`
- **Filename pattern:** `imerg_YYYY-MM-DD.tif` (date in filename is mandatory; ISO or compact YYYYMMDD both accepted)
- **Download:** <https://gpm.nasa.gov/data/imerg> or via Google Earth Engine `NASA/GPM_L3/IMERG_V07`
- **Purpose:** primary daily rainfall input for rolling/lag features and anomalies
- **CRS:** GeoTIFFs must be EPSG:4326 with explicit CRS metadata
- **Common issues:**
  - Native HDF5 → use `gdal_translate` with `-of GTiff` to produce daily tiffs
  - Filename without date → re-run rename script
- **Citation:** Huffman et al. — NASA GPM IMERG Final Run

## 4. CHIRPS daily rainfall (UCSB)

- **Source organisation:** UC Santa Barbara Climate Hazards Group
- **Required:** yes
- **File type:** daily GeoTIFF
- **Local directory:** `data/real/raw/rainfall_chirps/`
- **Filename pattern:** `chirps_YYYY-MM-DD.tif`
- **Download:** <https://www.chc.ucsb.edu/data/chirps>
- **Purpose:** historical rainfall baseline → `chirps_climatology` parquet; also used directly as a second rainfall source
- **Common issues:**
  - Files arrive `.tif.gz` — decompress before placing
  - Some Pakistan-clipped tiles available; full Africa+global grids also work but are larger
- **Citation:** Funk et al. 2015 — CHIRPS

## 5. GloFAS river discharge (pre-aggregated district-day CSV)

- **Source organisation:** Copernicus Emergency Management Service / GloFAS
- **Required:** yes
- **File type:** CSV, pre-aggregated to district-day
- **Local path:** `data/real/raw/glofas/glofas_district_daily.csv`
- **Filename rule:** exact name `glofas_district_daily.csv`
- **Download:** <https://www.globalfloods.eu/> or via Copernicus CDS API
- **Schema (required columns):**
  | column | type | required | notes |
  |---|---|---|---|
  | district_id | string | yes | matches boundaries |
  | date | YYYY-MM-DD | yes | UTC |
  | river_discharge_m3s | float | yes | m³/s |
  | discharge_anomaly_pct | float | optional | computed downstream if absent |
  | source | string | yes | e.g. `"GloFAS-CDS v4.0"` |
- **Scope note:** raw GloFAS NetCDF/GRIB → district-day conversion is **out of scope for v3**. Pre-aggregate externally (QGIS, `xarray`, or CDS Toolbox) before placing the CSV.
- **Citation:** Copernicus Emergency Management Service / GloFAS

## 6. DEM / elevation (SRTM or Copernicus DEM)

- **Source organisation:** USGS SRTM v3, or Copernicus DEM GLO-30
- **Required:** yes
- **File type:** GeoTIFF (single file, mosaic of tiles if needed)
- **Local path:** `data/real/raw/elevation/dem.tif`
- **Filename rule:** exact name `dem.tif`
- **Download:** <https://srtm.csi.cgiar.org/> or <https://spacedata.copernicus.eu/>
- **Purpose:** elevation features and on-the-fly slope derivation
- **Mosaicking:** if downloaded as multiple tiles, merge with `gdal_merge.py -o dem.tif tile_*.tif`
- **Optional companion:** pre-computed slope raster via `--slope-raster path/to/slope.tif`
- **Citation:** USGS SRTM v3 / Copernicus DEM GLO-30

## 7. HydroRIVERS (clip to Pakistan)

- **Source organisation:** HydroSHEDS / HydroRIVERS v1.0
- **Required:** yes
- **File type:** GeoJSON / Shapefile
- **Local path:** `data/real/raw/rivers/hydrorivers_pakistan.geojson`
- **Filename rule:** exact name `hydrorivers_pakistan.geojson`
- **Download:** <https://www.hydrosheds.org/products/hydrorivers>
- **Pre-processing:** clip the global HydroRIVERS layer to a Pakistan bounding box (or the COD-AB national outline) before placing. Loading the unclipped global file at runtime is rejected by the performance contract.
- **Purpose:** `distance_to_river_km`, `drainage_density`, `total_river_length_km` per district. Computed in `precompute_river_features.py` using a spatial index + per-district envelope clip.
- **Citation:** Linke et al. 2019 — HydroRIVERS v1.0

## 8. Population exposure (WorldPop)

- **Source organisation:** WorldPop
- **Required:** yes (raster OR pre-aggregated district CSV)
- **File type:** GeoTIFF (raster) OR CSV (pre-aggregated district scores)
- **Local path (raster):** `data/real/raw/population/worldpop_pakistan.tif`
- **Local path (CSV alternative):** `data/real/raw/population/district_population_exposure.csv`
- **Download:** <https://hub.worldpop.org/geodata/listing?id=29>
- **CSV schema (when used):**
  | column | type | required | notes |
  |---|---|---|---|
  | district_id | string | yes |  |
  | population_exposure_score | float | yes | 0–1 normalised |
  | population_total | int | optional | absolute count |
  | source | string | yes | e.g. `"WorldPop 2020 100m unconstrained"` |
- **Purpose:** population exposure score per district (raster → zonal sum → max-normalised; or read directly from CSV)
- **Citation:** WorldPop 2020 unconstrained 100 m

---

## General download workflow

1. Make sure dependencies are installed: `pip install -r ml/requirements.txt`.
2. Visit each source above and download to the indicated local path.
3. After every download (or batch of downloads), run:
   ```
   python ml/training/real_data_contract.py --check
   ```
   Continue downloading until that command exits 0. The output lists every still-missing path with its remediation hint.
4. When the contract passes, run the pipeline commands listed in `docs/13_real_flood_prediction_pipeline_v3.md` §11 in order.

## CRS conversion notes
- Boundaries / flood extents / rivers: keep WGS84 (EPSG:4326) source; the scripts reproject to a projected metric CRS (`EPSG:6933` default) for all area/distance work.
- Rasters (IMERG, CHIRPS, DEM, WorldPop): leave native; `rasterio` and `rasterstats` handle resampling.

## Common file-naming errors
- IMERG/CHIRPS tiffs missing the date → script skips them and writes the failure to `data/real/reports/zonal_stats_failures.json`. Rename to `imerg_YYYY-MM-DD.tif` and re-run.
- `pakistan_districts.geojson` lacking a `district_id` field → rename via `ogr2ogr -sql "SELECT *, OLD_FIELD AS district_id FROM …" out.geojson in.geojson`.

## Attribution summary
Use these citations in any public artefact:
- HDX COD-AB Pakistan (UN OCHA)
- UNITAR-UNOSAT Pakistan Flood Mapping
- NASA GPM IMERG Final Run (Huffman et al.)
- UCSB CHIRPS (Funk et al. 2015)
- Copernicus Emergency Management Service / GloFAS
- USGS SRTM v3 / Copernicus DEM GLO-30
- HydroSHEDS / HydroRIVERS v1.0 (Linke et al. 2019)
- WorldPop 2020 unconstrained 100 m
