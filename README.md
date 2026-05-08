# PakFlood AI

Pakistan flood intelligence and early-risk visualization dashboard — educational engineering prototype.

> **Safety:** This is an educational decision-support prototype. For real emergencies always consult **PMD**, **FFD**, **NDMA**, and **PDMA** official warnings.

---

## Overview

PakFlood AI demonstrates a full-stack geospatial ML system:
- **Map-first UI** — dark Leaflet map, 10 Pakistan districts colored by flood risk level (color + text + icon)
- **FastAPI backend** — thin routes → Facade service → Repository → DB + Adapters
- **Flood ML model** — RandomForest baseline with SHAP-like feature importance, trained on synthetic data
- **Source-backed explanation** — deterministic 7-field risk explanation with confidence, source freshness, and disclaimer
- **Circuit-breaker adapters** — 5 data sources (ReliefWeb live, IMERG/CHIRPS/GloFAS/FFD stubs)
- **Draft-only alert endpoint** — never sent, never stored externally

All risk outputs are clearly labeled as synthetic/educational. No official warning authority.

---

## Quick start

### Prerequisites

- Python 3.11+ (Python 3.14 tested)
- Node.js 20+
- Docker Desktop (for PostgreSQL; optional for frontend-only dev)

### 1. Configure

```bash
git clone <repo-url>
cd pakflood-ai
cp .env.example .env
# Defaults work for local dev — no changes required
```

### 2. Start database (optional)

```bash
docker-compose up db
```

### 3. Run backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

> **Frontend works without the backend.** Mock data provides full UI functionality.

### 5. Full stack

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Seed database

```bash
cd backend
python -m app.scripts.seed
# Loads 10 districts, 4 flood events (2010/2011/2014/2022), risk snapshots
```

---

## Train the ML model

```bash
python ml/training/train_baseline.py
# Trains RandomForest on 300-row synthetic dataset
# Saves: ml/artifacts/flood_baseline_v1.pkl
#        ml/artifacts/model_metadata.json
#        ml/evaluation/metrics_report.json
# AUC-ROC: ~0.90 (on synthetic test split — NOT real-world accuracy)
```

---

## Run tests

```bash
# Backend (269 tests — no real DB required)
cd backend
pytest app/tests/ -q

# Frontend component tests (36 tests)
cd frontend
npm test -- --run

# E2E (requires: npm run dev on port 3000)
cd frontend
npx playwright test --project=chromium

# ESLint
cd frontend
npx eslint src --ext .ts,.tsx --max-warnings 0

# Security
cd backend && bandit -r app/ -ll           # 0 medium/high findings
cd frontend && npm audit --audit-level=high # 0 high findings
```

---

## API examples

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Flood risk for Sukkur district
curl http://localhost:8000/api/v1/risk/by-boundary/PK-SD-SKR

# 7-field source-backed explanation
curl http://localhost:8000/api/v1/explain-risk/by-boundary/PK-SD-SKR

# Data source freshness
curl http://localhost:8000/api/v1/data-sources

# Search districts
curl "http://localhost:8000/api/v1/location/search?q=Jacobabad"

# Run ML inference on all 10 districts (returns persisted_count, persistence_status)
curl -X POST http://localhost:8000/api/v1/admin/run-risk-model

# Model readiness check
curl http://localhost:8000/api/v1/admin/model-status

# Generate alert draft (never sent, never official)
curl -X POST http://localhost:8000/api/v1/alerts/generate-draft \
  -H "Content-Type: application/json" \
  -d '{"boundary_id": "PK-SD-SKR"}'
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Project structure

```
pakflood-ai/
├── CLAUDE.md                    # Project memory — read first every session
├── backend/
│   └── app/
│       ├── api/v1/              # Thin HTTP routes
│       ├── services/            # Facade (DisasterRiskService, SourceRegistryService)
│       ├── repositories/        # DB access (Repository pattern)
│       ├── adapters/            # External APIs (Circuit Breaker, Adapter pattern)
│       └── hazards/flood/       # ALL flood logic — features, model, explainer, rules
├── frontend/
│   └── src/
│       ├── components/map/      # Leaflet map, district layers, hover cards
│       ├── components/panels/   # Risk explanation, layer controls, data sources
│       └── lib/                 # Typed API client (with mock fallback)
├── ml/
│   ├── training/                # Feature pipeline + training script
│   ├── artifacts/               # Saved model + metadata
│   └── evaluation/              # Metrics report (JSON)
├── data/seed/                   # GeoJSON districts, flood events, risk scores
├── docs/                        # Architecture, data sources, testing, ADRs, demo script
└── infra/                       # Docker, CI scaffold, Terraform placeholder
```

---

## Phase status

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Scaffold, Docker, docs | ✅ Complete |
| 1 | Map UI (Leaflet, mock data, timeline) | ✅ Complete |
| 2 | FastAPI + PostGIS + seed data | ✅ Complete |
| 3 | Adapters + circuit breaker + ReliefWeb | ✅ Complete |
| 4 | RandomForest baseline ML + admin endpoint | ✅ Complete |
| 5 | 7-field explanation + draft alert | ✅ Complete |
| 6 | Security scan + hardening docs + README | ✅ Complete |
| 7 | IMERG + CHIRPS rainfall wiring into inference | ✅ Complete |
| 8 | GloFAS discharge + RiskSnapshot persistence | ✅ Complete |
| 9 | Demo reliability: model-status, persistence summary, E2E, docs | ✅ Complete |

---

## Environment variables

| Variable | Default | Required |
|---|---|---|
| `DATABASE_URL` | `postgresql://pakflood:pakflood@localhost:5432/pakflood` | For real DB |
| `ENVIRONMENT` | `development` | No |
| `SECRET_KEY` | *(set in .env)* | Change in production |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Frontend |
| `GEE_SERVICE_ACCOUNT` | *(optional)* | For live IMERG/CHIRPS |
| `NASA_EARTHDATA_USERNAME` | *(optional)* | For live IMERG via Earthdata |
| `NASA_EARTHDATA_PASSWORD` | *(optional)* | For live IMERG via Earthdata |
| `ENABLE_LIVE_RAINFALL` | `false` | Set `true` to enable live adapter calls |
| `RAINFALL_PROVIDER` | `stub` | `stub` \| `gee` \| `earthdata` |

Full list in [.env.example](.env.example).

---

## Demo walkthrough

See [docs/08_demo_script.md](docs/08_demo_script.md) for a 10-minute guided demo.

---

## Limitations

See [docs/07_realism_and_limitations.md](docs/07_realism_and_limitations.md) for a full breakdown.

**Short version:**
- ML model trained on **synthetic data** — AUC-ROC is not a real-world accuracy claim
- IMERG, CHIRPS, GloFAS, FFD adapters are **stubs** returning `status="stale"`
- Only **10 districts** (MVP); full Pakistan = 140+ districts
- No real alerting — draft endpoint never sends anything
- All outputs include confidence, source freshness, and a mandatory disclaimer

---

## Architecture decisions

See [docs/adr/](docs/adr/) and [docs/09_final_architecture_review.md](docs/09_final_architecture_review.md).

---

## Contributing

Read [CLAUDE.md](CLAUDE.md) before any work. Never skip phase acceptance criteria.
