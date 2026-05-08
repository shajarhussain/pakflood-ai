# PakFlood AI — Final Architecture Review (Phase 6)

## Phase completion summary

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Scaffold, Docker, docs | ✅ |
| 1 | Dark map UI, mock data, Leaflet | ✅ |
| 2 | FastAPI + PostGIS + repositories + seed | ✅ |
| 3 | Adapters + circuit breaker + SourceRegistry + ReliefWeb | ✅ |
| 4 | RandomForest baseline + ML pipeline + admin endpoint | ✅ |
| 5 | FloodExplainer + 7-field explanation + draft alert | ✅ |
| 6 | Security scan, hardening docs, README | ✅ |

---

## Architecture diagram (current state)

```
Browser
  │
  └─ Next.js 16 (port 3000)
       ├─ PakistanMap (Leaflet)
       ├─ RiskExplanationPanel  ──────────────────────────────┐
       ├─ DataSourcesPanel                                    │
       └─ Header (search)                                     │
                                                             HTTP
FastAPI (port 8000) / api/v1/                                 │
  ├─ GET  /health                                             │
  ├─ GET  /admin-boundaries                                   │
  ├─ GET  /risk/by-boundary/{id}          ← RiskResponse      │
  ├─ GET  /explain-risk/by-boundary/{id}  ← RiskExplanation ──┘
  ├─ GET  /flood-events
  ├─ GET  /data-sources
  ├─ GET  /location/search
  ├─ POST /admin/run-risk-model           ← RunModelResponse
  └─ POST /alerts/generate-draft         ← AlertDraftResponse

Services (business logic, Facade)
  ├─ DisasterRiskService        ← BoundaryRepo, RiskRepo, FloodEventRepo
  └─ SourceRegistryService      ← 5 adapters, 5-min cache, singleton

Adapters (Circuit Breaker — CLOSED/OPEN/HALF_OPEN)
  ├─ ReliefWebAdapter   ← LIVE (no auth, public API)
  ├─ IMERGAdapter       ← STUB (status=stale)
  ├─ CHIRPSAdapter      ← STUB (status=stale)
  ├─ GloFASAdapter      ← STUB (status=stale)
  └─ FFDAdapter         ← STUB (status=stale)

Hazards (flood-specific, isolated)
  ├─ FloodPredictionStrategy  ← HazardModule Protocol, lazy sklearn
  ├─ FloodExplainer           ← pure class, 7-field explanation
  ├─ features.py              ← 11-feature schema, district statics
  └─ rules.py                 ← risk thresholds + DISCLAIMER constant

ML Pipeline
  ├─ ml/training/feature_pipeline.py   ← 300-row synthetic dataset
  ├─ ml/training/train_baseline.py     ← RandomForest, saves artifacts
  ├─ ml/artifacts/flood_baseline_v1.pkl
  └─ ml/evaluation/metrics_report.json

Database (PostgreSQL + PostGIS — lazy connection)
  ├─ districts (with geom_json + optional PostGIS geometry column)
  ├─ risk_snapshots
  ├─ flood_events
  └─ articles
```

---

## Design pattern assignments

| Pattern | Location |
|---|---|
| Strategy | `FloodPredictionStrategy` in `hazards/flood/model.py` |
| Adapter | `*Adapter` classes in `adapters/`, wrapping circuit breaker |
| Repository | `BoundaryRepository`, `RiskRepository`, `FloodEventRepository` |
| Facade | `DisasterRiskService` — single entry point for all business logic |
| Factory | `HazardModuleFactory` in `hazards/factory.py` |
| Pipeline | `feature_pipeline.py` + `train_baseline.py` |
| Circuit Breaker | `BaseAdapter` — CLOSED/OPEN/HALF_OPEN, failure_threshold=3, recovery_timeout=30s |
| Singleton | `get_source_registry()`, `get_flood_strategy()`, `get_flood_explainer()` |
| CQRS-lite | Read path (`GET /risk/by-boundary`) vs write path (`POST /admin/run-risk-model`) |

---

## Test coverage (Phase 6 baseline)

| Suite | Tool | Count | Status |
|---|---|---|---|
| Backend unit + integration | pytest | 160 tests | ✅ pass |
| Frontend component | Vitest + RTL | 36 tests | ✅ pass |
| Lint | ESLint | — | ✅ clean |
| Security | Bandit (-ll) | 0 medium/high | ✅ pass |
| Dependency audit | npm audit --high | 0 high | ✅ pass |

Note: 2 moderate vulns in Next.js-bundled PostCSS (`GHSA-qx2v-qp2m-jg93`). Fix requires breaking Next.js downgrade; risk is low for a local demo prototype. Document and accept.

---

## Key architectural decisions

**1. Lazy DB engine** — `db/session.py` defers psycopg2 import until first real DB call. Tests never import psycopg2.

**2. Dependency injection via FastAPI** — all services injected through `app.dependency_overrides` in tests. No mocking frameworks needed.

**3. Pure FloodExplainer** — accepts pre-fetched data, no I/O. Trivially testable.

**4. Rule-based before LLM** — explanation is deterministic. Confidence, sources, and disclaimer are always structurally guaranteed.

**5. Mock fallback in frontend** — `apiFetch` returns null on error; every function falls back to mock data. UI always works without backend.

**6. Flood isolation** — all flood-specific logic inside `backend/app/hazards/flood/`. Other hazard modules (GLOF, drought, heatwave) can be added without touching flood code.

---

## Known gaps (path to Phase 7+)

| Gap | What's needed |
|---|---|
| Real dynamic features | Live IMERG/GloFAS adapters (GEE auth, ECMWF API) |
| Real training labels | NDMA/PDMA post-event district flood labels |
| Full district coverage | HDX 140+ Pakistan district polygons |
| Sentinel-1 SAR | GEE or Copernicus Data Space flood extent processing |
| Production auth | JWT or API key layer on admin/alerts endpoints |
| Rate limiting | FastAPI middleware or reverse proxy |
| CI/CD pipeline | GitHub Actions → Cloud Run (infra/ci/ scaffold exists) |
| E2E tests | Playwright tests (playwright.config.ts exists) |
| Accessibility audit | axe-playwright on district click + disclaimer visibility |

---

## Safety and realism guardrails (enforced in code)

- `DISCLAIMER` constant imported from `hazards/flood/rules.py` — single source of truth
- `AlertDraftResponse.is_official = False` — enforced at schema level
- `is_draft = True` — field default in schema
- Confidence always in `[0.0, 1.0]` — clamped in FloodExplainer before schema validation
- "data unavailable" returned (never invented text) when source data is missing
- Risk communicated as colour + text label + icon (not colour alone) — `RISK_ICONS` + labels in frontend
