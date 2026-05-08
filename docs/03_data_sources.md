# Data Sources

## Source Table

| Source | Purpose | Adapter | Priority |
|---|---|---|---|
| PMD/FFD Lahore | Flood bulletins, river flows, advisories | `FFDAdapter` | Must have |
| NDMA/NEOC | National disaster advisories | Manual / scraper | Must have |
| NASA GPM IMERG | Near-real-time rainfall (half-hourly) | `IMERGAdapter` | Must have |
| CHIRPS | 30+ year historical rainfall | `CHIRPSAdapter` | Must have |
| GloFAS | Global river discharge forecasts | `GloFASAdapter` | Must have |
| Sentinel-1 SAR | Satellite flood extent (SAR) | GEE adapter | Must have |
| Copernicus GFM | Automated Sentinel-1 flood monitoring | GEE adapter | Strong |
| HDX Pakistan Boundaries | Province/district/tehsil geometry | Static seed | Must have |
| OpenStreetMap/HDX | Roads, hospitals, schools, bridges | Static seed | Strong |
| ReliefWeb API | Situation reports, historical articles | `ReliefWebAdapter` | Strong |
| GDELT | Global news for flood events | Optional adapter | Optional |

## Data Source Registry Schema

```yaml
source_id: imerg_late
name: NASA GPM IMERG Late Run
hazard: flood
data_type: rainfall_raster
latency: near_real_time
spatial_resolution: approx_0_1_degree
adapter: IMERGAdapter
fallback: CHIRPS_PRELIM
quality_checks:
  - missing_pixel_rate
  - date_range_continuity
  - unit_validation
features_created:
  - rainfall_1d
  - rainfall_3d
  - rainfall_7d
  - rainfall_percentile
```

## Feature Store Plan

**Static features:** elevation, slope, distance to river, flow accumulation, land cover, drainage density, district/tehsil id, historical flood count, population density.

**Dynamic features:** rainfall 24h/72h/7d/15d/30d, rainfall anomaly, GloFAS discharge forecast percentile, FFD station category, Sentinel-1 detected water extent, official warning presence, verified report count.
