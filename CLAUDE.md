# CLAUDE.md - PakFlood AI

## Mission
Build PakFlood AI: a Pakistan-only flood intelligence, prediction and response dashboard. The MVP focuses on floods, but the architecture must support future hazards through modular hazard plugins.

## Non-Negotiables
- Keep flood-specific code inside `backend/app/hazards/flood`.
- Use clean architecture: routes -> services -> repositories/adapters -> data/model layers.
- Every external data source must use an Adapter class.
- Every ML model must store version, features, metrics and artifact path.
- Every risk explanation must include confidence, data freshness and sources.
- Never describe AI output as an official government warning.
- Run tests after every implementation phase.
- Do not implement a new phase until the previous phase passes its acceptance criteria.
- Update docs/ADR when architecture changes.

## Tech Stack
Frontend: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Mapbox GL JS or Leaflet.
Backend: FastAPI, SQLAlchemy, Pydantic, PostgreSQL + PostGIS.
ML: scikit-learn, XGBoost/RandomForest baseline; PyTorch/U-Net later.
Geospatial: GeoPandas, Rasterio, Shapely, Google Earth Engine, geemap.
Cloud: Docker, GitHub Actions, Cloud Run/Render, Vercel/Firebase, object storage.

## Required Design Patterns
- Strategy Pattern for hazard models.
- Adapter Pattern for external APIs/data sources.
- Repository Pattern for database access.
- Facade Pattern for `DisasterRiskService`.
- Factory Pattern for hazard module creation.
- Pipeline Pattern for data ingestion and ML inference.
- Observer/PubSub for risk-change events.
- Circuit Breaker for fragile external APIs.
- CQRS-lite for optimized map reads.

## Architecture Rules
- `/frontend` contains UI only.
- `/backend/app/api` contains API routes.
- `/backend/app/services` contains business logic.
- `/backend/app/repositories` contains database access.
- `/backend/app/adapters` contains API/data source adapters.
- `/backend/app/hazards/flood` contains flood-specific features, models, rules and explainers.
- `/backend/app/core` contains shared config, logging, security and errors.
- `/ml` contains notebooks, training scripts, model artifacts and evaluation reports.
- `/docs` contains architecture, API contracts, data dictionary, testing strategy and ADRs.

## AI Suggestor Rules
Use this public response structure:
1. Risk level
2. Main causes
3. Historical evidence
4. Suggested actions
5. Confidence
6. Data sources
7. Limitations / official-warning disclaimer

Never invent sources. If data is missing, say data is missing. Prefer official PMD, FFD, NDMA, PDMA and local authority sources when available.

## Work Style
1. Read only the docs relevant to the current phase.
2. Produce a short plan before editing.
3. Implement small vertical slices.
4. Run tests and lint.
5. Update docs/ADR when architecture changes.
6. Summarize changed files, test results and remaining risks.

## Testing Requirements
- Backend unit tests for services, adapters and repositories.
- API tests for risk, event, article and source endpoints.
- Frontend component tests for map, panel, timeline and legend.
- Playwright E2E test for searching/clicking a district and viewing risk explanation.
- ML tests for feature schema, no data leakage and model artifact creation.
- Geospatial tests for CRS, valid geometry and raster/vector alignment.
- Accessibility checks for color contrast, keyboard navigation and source labels.

## Phase Discipline
Phase 0: repository scaffold and docs only.
Phase 1: polished map UI with mock data only.
Phase 2: FastAPI + PostGIS + seed data.
Phase 3: data adapters and source registry.
Phase 4: baseline ML model and metrics.
Phase 5: AI explanation/RAG with source controls.
Phase 6: hardening, testing, deployment and final demo.

## Safety
This project is an educational decision-support prototype. It must always direct users to official PMD, FFD, NDMA, PDMA and local authority warnings for real emergency decisions.
