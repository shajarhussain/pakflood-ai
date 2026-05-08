# ADR-001: Technology Stack Selection

Date: 2026-05-06
Status: Accepted

## Context

PakFlood AI requires a geospatial web application with an interactive map, a real-time risk API, ML model serving, and geospatial database queries. The stack must support future hazard modules without rewriting core platform code.

## Decision

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui | App Router, SSR/SSG, type safety, rapid component development |
| Map rendering | Leaflet.js (react-leaflet) | Open source, well-documented, supports GeoJSON overlays, lighter than Mapbox for MVP |
| Backend API | FastAPI + Pydantic v2 | Async, typed, auto-docs (OpenAPI), excellent SQLAlchemy integration |
| Database | PostgreSQL 16 + PostGIS 3.4 | Geospatial queries, district polygon storage, spatial indexing |
| ORM | SQLAlchemy 2 + GeoAlchemy2 | Native PostGIS support, repository pattern friendly |
| ML | scikit-learn / XGBoost | Explainable, tabular data, SHAP support; PyTorch/U-Net deferred to post-MVP |
| Geospatial processing | GeoPandas + Rasterio + Google Earth Engine | Satellite data, raster processing, CHIRPS/IMERG ingestion |
| Containerization | Docker + Docker Compose | Reproducible local dev and deployment |
| CI/CD | GitHub Actions | Standard, free for public repos, integrates with all deployment targets |
| Frontend hosting | Vercel | Zero-config Next.js deployment |
| Backend hosting | Cloud Run / Render | Containerized FastAPI, scale-to-zero |
| Database hosting | Supabase / Cloud SQL | Managed PostGIS, easy migrations |
| Object storage | Google Cloud Storage | GeoTIFFs, model artifacts, map tiles |

## Consequences

**Positive:**
- All choices are well-supported with active communities
- PostGIS eliminates need for a separate geospatial service for district queries
- FastAPI's dependency injection suits the Repository + Facade pattern
- Next.js App Router supports server-side data fetching for map tiles

**Negative:**
- GeoAlchemy2 adds complexity to migrations (PostGIS extension must be enabled)
- Leaflet lacks some advanced styling of Mapbox GL; may need upgrade in Phase 6
- GEE requires service account setup — deferred to Phase 3

## Alternatives Considered

- **Mapbox GL JS:** More powerful styling but requires paid API key for production use
- **Django/DRF:** Heavier than FastAPI for a new project; slower development iteration
- **MongoDB:** Lacks native PostGIS-level geospatial support without separate service
- **SQLite/SpatiaLite:** Not suitable for concurrent writes or production scale

## Impact on Future Hazards

The HazardModule Protocol is independent of this stack. Adding a GLOF or heatwave module requires only:
1. A new directory under `hazards/glof/` or `hazards/heatwave/`
2. Implementing the `HazardModule` Protocol
3. Registering via `HazardModuleFactory`

No changes to the API layer, database schema (beyond new tables), or frontend architecture.
