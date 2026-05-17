# PakFlood AI — Full Project Report

> A Pakistan flood intelligence and early-risk visualization system combining real-time weather data,
> XGBoost machine learning, geospatial mapping, and an AI copilot — built as a full-stack engineering capstone.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack & External Services](#3-tech-stack--external-services)
4. [Database — Supabase](#4-database--supabase)
5. [ML Model](#5-ml-model)
6. [Backend — FastAPI](#6-backend--fastapi)
7. [All API Endpoints](#7-all-api-endpoints)
8. [Frontend — Next.js](#8-frontend--nextjs)
9. [Background Scheduler](#9-background-scheduler)
10. [Auth & User Accounts (Planned)](#10-auth--user-accounts-planned)
11. [Education Module (Planned)](#11-education-module-planned)
12. [Gemini AI Agents (Planned)](#12-gemini-ai-agents-planned)
13. [Feature Status](#13-feature-status)
14. [Running the Project](#14-running-the-project)
15. [Environment Variables](#15-environment-variables)
16. [Safety & Disclaimer Policy](#16-safety--disclaimer-policy)

---

## 1. Project Overview

**PakFlood AI** predicts flood risk across all of Pakistan using live weather data from Open-Meteo
and an XGBoost classifier trained on real Pakistan flood records (Dadu district 2022–2024).

The system computes a 952-point grid covering Pakistan every 3 hours, stores predictions in Supabase,
and serves them instantly to a Leaflet-based map dashboard. Users can search any district, view risk
levels, understand the top weather drivers, and read historical flood context.

### What it is
- A real-time flood risk map for all 142 Pakistan districts
- An educational decision-support tool with AI explainability
- A full-stack capstone demonstrating clean architecture, ML pipelines, and geospatial systems

### What it is NOT
- Not an official emergency alert system
- Not a replacement for PMD, FFD, NDMA, or PDMA warnings
- Every prediction output carries a mandatory disclaimer enforced at the code level

---

## 2. Architecture

### Clean Architecture (Layered)

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│          Next.js 16 · React 19 · TypeScript             │
│          Leaflet Map · Tailwind CSS · shadcn/ui          │
└──────────────────────────┬──────────────────────────────┘
                           │  HTTP / REST (JSON)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI (Python)                      │
│  ┌──────────┐  ┌───────────┐  ┌────────────────────┐   │
│  │  Routes  │→ │Controllers│→ │  Services / Logic   │   │
│  └──────────┘  └───────────┘  └────────┬───────────┘   │
│                                         │               │
│              ┌──────────────────────────┤               │
│              ▼                          ▼               │
│  ┌───────────────────┐   ┌──────────────────────────┐  │
│  │  ZoneRepository   │   │  open_meteo_adapter.py   │  │
│  │  (Supabase reads/ │   │  (External API adapter)  │  │
│  │   writes)         │   └──────────┬───────────────┘  │
│  └─────────┬─────────┘              │                  │
│            │                        ▼                  │
│            ▼               ┌────────────────┐          │
│  ┌──────────────────┐      │  Open-Meteo    │          │
│  │    Supabase      │      │  Weather API   │          │
│  │  (PostgreSQL)    │      └────────────────┘          │
│  └──────────────────┘                                  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  APScheduler (AsyncIOScheduler)                  │  │
│  │  Zone grid computation every 3h on startup       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Design Patterns

| Pattern | Where Used |
|---|---|
| **Repository** | `ZoneRepository` — all DB access; routes never touch Supabase directly |
| **Adapter** | `open_meteo_adapter.py` — wraps Open-Meteo; routes never call the API directly |
| **Singleton** | `get_flood_model()` — XGBoost artifact loaded once at startup, reused |
| **Strategy** | `app/hazards/flood/` — all flood logic isolated; other hazards can be added without touching core |
| **Scheduler** | APScheduler `AsyncIOScheduler` — zone jobs run on FastAPI's own event loop |
| **Stale-while-revalidate** | `/zones/geojson` serves cached data instantly; triggers background refresh if stale |
| **Sentinel object** | `RATE_LIMITED` class instance — propagates 429 exhaustion without raising exceptions |
| **Adaptive rate control** | Per-request delay doubles after 429 cascade; 180s cooldown resets the window |
| **Point-in-polygon filter** | Pure-Python ray-casting in `district_filter.py` — no shapely dependency |
| **Pagination** | `ZoneRepository._fetch_all_points()` — paginates Supabase's 1000-row cap |

### File Structure

```
pakflood-ai/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # All settings via pydantic-settings (.env)
│   │   │   ├── logging.py         # configure_logging() — called at module load
│   │   │   ├── supabase.py        # Supabase client singleton (get_supabase())
│   │   │   └── errors.py          # Custom exception classes
│   │   │
│   │   ├── hazards/flood/
│   │   │   ├── features.py        # FEATURE_COLS — the 14 model input names
│   │   │   ├── model.py           # get_flood_model() — XGBoost loader/singleton
│   │   │   └── rules.py           # classify_risk(), RISK_THRESHOLDS, DISCLAIMER
│   │   │
│   │   ├── zones/
│   │   │   ├── grid_generator.py  # generate_pakistan_grid(), compute_all_zones()
│   │   │   ├── zone_scheduler.py  # APScheduler setup, startup/hourly jobs
│   │   │   ├── zone_repository.py # All DB reads/writes for batches + grid points
│   │   │   ├── open_meteo_adapter.py  # fetch_weather_features(), RATE_LIMITED sentinel
│   │   │   ├── zone_geojson.py    # points_to_geojson(), single_point_to_geojson()
│   │   │   └── district_filter.py # filter_points_by_district(), district_zone_summary()
│   │   │
│   │   ├── routes/
│   │   │   ├── router.py          # Aggregates all routers under /api/v1
│   │   │   ├── health.py          # GET /health
│   │   │   ├── prediction.py      # GET /predict, /risk/by-location, /model/status
│   │   │   ├── zones.py           # GET /zones/geojson, /zones/status, POST /zones/compute
│   │   │   ├── districts.py       # GET /districts/search, /districts/{id}
│   │   │   ├── boundaries.py      # GET /admin-boundaries, /location/search
│   │   │   └── flood_events.py    # GET /flood-events
│   │   │
│   │   ├── controllers/
│   │   │   └── prediction_controller.py  # run_prediction() orchestrates weather+model
│   │   │
│   │   ├── models/
│   │   │   ├── prediction.py      # PredictionResponse Pydantic schema
│   │   │   └── zone.py            # Zone-related Pydantic schemas
│   │   │
│   │   └── main.py                # FastAPI app, CORS, lifespan (scheduler start/stop)
│   │
│   ├── scripts/
│   │   ├── seed_districts.py          # Seeds 142 districts into Supabase
│   │   ├── patch_district_geom.py     # Patches geom_json from GADM 4.1 (120 districts)
│   │   └── patch_district_geom_hdx.py # Patches remaining from geoBoundaries (13 more)
│   │
│   ├── ml/
│   │   ├── artifacts/
│   │   │   ├── flood_xgb_pakistan_v2.pkl   # Trained XGBoost model artifact
│   │   │   └── flood_xgb_pakistan_v2.ipynb # Training notebook
│   │   ├── notebooks/
│   │   │   └── pak-flood-prediction-model.ipynb
│   │   └── train_local.py
│   │
│   ├── supabase_tables.sql    # Full DB schema + RLS policies
│   ├── requirements.txt
│   └── Dockerfile
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx         # Root layout — fonts, metadata
    │   │   └── page.tsx           # Main page — renders MapDashboard
    │   │
    │   ├── components/
    │   │   ├── map/
    │   │   │   ├── PakistanMap.tsx         # Core Leaflet map component
    │   │   │   ├── GridRiskLayer.tsx       # Zone grid points coloured by risk
    │   │   │   ├── MapDashboard.tsx        # Main layout: map + panels + KPIs
    │   │   │   ├── MapLegend.tsx           # Risk level colour legend
    │   │   │   ├── KPICards.tsx            # Summary stats cards
    │   │   │   ├── CleanCommandCenter.tsx  # Top command bar
    │   │   │   ├── CleanLayerSwitcher.tsx  # Toggle map layers
    │   │   │   ├── CityWeatherLabels.tsx   # City weather pins on map
    │   │   │   ├── CompactCityChips.tsx    # City quick-select chips
    │   │   │   ├── RainCanvas.tsx          # Rainfall animation canvas
    │   │   │   ├── WindVectorLayer.tsx     # Wind direction vectors
    │   │   │   ├── RainfallStationLayer.tsx # Rainfall station markers
    │   │   │   ├── WeatherLayerLegend.tsx  # Weather layer colour scales
    │   │   │   └── RiskIndexBadge.tsx      # Top-level risk index badge
    │   │   │
    │   │   ├── copilot/
    │   │   │   ├── CopilotPanel.tsx        # Right-panel container with 7 tabs
    │   │   │   └── tabs/
    │   │   │       ├── RiskBrief.tsx       # AI risk summary for selected district
    │   │   │       ├── CopilotChat.tsx     # AI Q&A chat for district analysis
    │   │   │       ├── SimulationLab.tsx   # What-if scenario sliders
    │   │   │       ├── ResponsePlan.tsx    # Recommended emergency actions
    │   │   │       ├── EvidencePack.tsx    # Supporting data and sources
    │   │   │       ├── SAREvidencePanel.tsx     # SAR/satellite evidence viewer
    │   │   │       └── EducationalSourcesPanel.tsx # Links to educational sources
    │   │   │
    │   │   ├── panels/
    │   │   │   ├── RiskExplanationPanel.tsx  # Detailed risk breakdown panel
    │   │   │   ├── DataSourcesPanel.tsx      # Data source status indicators
    │   │   │   └── LayerControlPanel.tsx     # Map layer visibility toggles
    │   │   │
    │   │   ├── timeline/
    │   │   │   └── FloodTimeline.tsx         # Historical flood events timeline
    │   │   │
    │   │   └── layout/
    │   │       ├── Header.tsx          # Top navigation header
    │   │       ├── StatusBar.tsx       # Model status + data freshness bar
    │   │       ├── SafetyDisclaimer.tsx # Mandatory disclaimer banner
    │   │       └── SourceBadge.tsx     # Source attribution badges
    │   │
    │   ├── data/
    │   │   ├── mock.ts                 # Mock risk entries (fallback when API down)
    │   │   ├── districts.json          # Static district list for frontend
    │   │   ├── provinces.json          # Province boundaries
    │   │   ├── educational-sources.ts  # Educational resource links
    │   │   ├── sar-evidence.ts         # SAR evidence data
    │   │   └── pakistan-cities-weather.ts # City weather data
    │   │
    │   └── lib/
    │       ├── api.ts          # Typed API client (all backend calls + mock fallback)
    │       ├── types.ts        # TypeScript types: RiskLevel, District, RiskSnapshot, etc.
    │       ├── grid-risk.ts    # Grid cell risk utilities
    │       ├── risk-colors.ts  # Risk level → colour mapping
    │       └── useModelStatus.ts # React hook for /model/status polling
    │
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── playwright.config.ts
    └── vitest.config.ts
```

---

## 3. Tech Stack & External Services

### Backend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.13 | Core backend |
| Framework | FastAPI | 0.115.6 | REST API, async request handling |
| Server | Uvicorn | 0.32.1 | ASGI server with hot reload |
| ML | XGBoost | 2.x | Flood probability classification |
| ML support | scikit-learn | 1.4 | Feature pipeline, joblib serialization |
| Scheduler | APScheduler | 3.10.4 | Async background zone computation |
| HTTP client | httpx | 0.28.1 | Async Open-Meteo requests |
| DB client | supabase-py | 2.x | PostgreSQL via Supabase REST API |
| Validation | Pydantic | 2.10.3 | Request/response schemas |
| Config | pydantic-settings | 2.7.0 | `.env` file loading |
| Testing | pytest + pytest-asyncio | 8.3 | Unit and async tests |
| Numerics | numpy | 1.26+ | Feature vectors, importances |

### Frontend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | TypeScript | 5.x | Type-safe frontend |
| Framework | Next.js | 16.2.4 | App Router, SSR/CSR |
| UI library | React | 19.2.4 | Component model |
| Styling | Tailwind CSS | 4.x | Utility-first CSS |
| Map | Leaflet + react-leaflet | 1.9 / 5.0 | Interactive Pakistan map |
| Geospatial | Turf.js | 7.3.5 | Client-side geospatial operations |
| Unit tests | Vitest | 4.x | Fast component + logic tests |
| E2E tests | Playwright | 1.59 | Browser automation tests |

### External Services & Data Sources

| Service | Type | Purpose | Cost |
|---|---|---|---|
| **Supabase** | BaaS (PostgreSQL) | Database, Auth (planned), Row-level security | Free tier |
| **Open-Meteo** | Weather API | 7-day history + today for any lat/lng | Free (10,000 req/day) |
| **GADM 4.1** | GeoJSON dataset | Pakistan district polygon boundaries (120 districts) | Free, open |
| **geoBoundaries** | GeoJSON API | Supplemental boundaries for newer districts (13 more) | Free, open |
| **Google Gemini** | AI API | Learning chatbot + help bot (planned) | Pay per use |

---

## 4. Database — Supabase

Supabase provides PostgreSQL + REST API + Auth. The backend uses the `supabase-py` client (anon key for reads, service key for writes).

### Row Level Security (RLS)

RLS is enabled on `zone_batches` and `zone_grid_points`. Policies allow the anon key to INSERT, UPDATE, and SELECT — so the backend can write predictions without exposing a service-role key in routes.

---

### Table: `districts` ✅ Active

Stores all 142 Pakistan districts with boundary polygons.

```sql
CREATE TABLE districts (
    id          SERIAL PRIMARY KEY,
    district_id VARCHAR(20)  UNIQUE NOT NULL,  -- "PK-PB-LH"
    name        VARCHAR(100) NOT NULL,          -- "Lahore"
    province    VARCHAR(100) NOT NULL,          -- "Punjab"
    center_lat  FLOAT        NOT NULL,
    center_lng  FLOAT        NOT NULL,
    geom_json   TEXT                            -- GeoJSON Polygon/MultiPolygon string
);
```

**Status:** 142 districts seeded. 135 have real polygon boundaries (GADM + geoBoundaries). 7 newer districts (Chiniot, Sujawal, Lehri, Sohbatpur, Washuk, Haveli, Hattian Bala) have NULL geom_json — bounding-box fallback used.

**CRUD:**
- CREATE: `scripts/seed_districts.py` (one-time seed)
- READ: `GET /admin-boundaries`, `GET /districts/search`, `GET /districts/{id}`
- UPDATE: `scripts/patch_district_geom.py`, `scripts/patch_district_geom_hdx.py`
- DELETE: Not exposed (admin only via Supabase dashboard)

---

### Table: `zone_batches` ✅ Active

Tracks each full grid computation run. One row per computation cycle.

```sql
CREATE TABLE zone_batches (
    id           VARCHAR(36) PRIMARY KEY,  -- UUID
    started_at   TIMESTAMP   NOT NULL,
    completed_at TIMESTAMP,
    total_points INTEGER,
    status       VARCHAR(20) NOT NULL DEFAULT 'running'
    -- status: running | complete | failed
);
```

**CRUD:**
- CREATE: `ZoneRepository.save_zone_batch()` — inserts with status='running'
- READ: `ZoneRepository.get_latest_batch()` — latest complete batch
- UPDATE: `ZoneRepository.save_zone_batch()` — marks status='complete' when done
- DELETE: `ZoneRepository._delete_old_batches()` — removes all except the newest complete batch

---

### Table: `zone_grid_points` ✅ Active

One row per grid point per batch. ~952 points per complete batch (0.5° grid).

```sql
CREATE TABLE zone_grid_points (
    id       SERIAL PRIMARY KEY,
    batch_id VARCHAR(36) NOT NULL REFERENCES zone_batches(id),

    -- Location
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,

    -- Model output
    flood_prob  FLOAT       NOT NULL,  -- 0.0 to 1.0
    risk_level  VARCHAR(20) NOT NULL,  -- Low | Moderate | High | Severe
    confidence  FLOAT       NOT NULL,  -- 2 × |flood_prob − 0.5|

    -- 14 model input features
    precipitation    FLOAT,   -- mm/day today
    precip_3day_avg  FLOAT,   -- mm/day 3-day avg
    precip_7day_avg  FLOAT,   -- mm/day 7-day avg
    pressure         FLOAT,   -- Pa (hPa × 100)
    temperature      FLOAT,   -- °C max
    temp_3day_avg    FLOAT,   -- °C 3-day avg
    soil_moisture    FLOAT,   -- m³/m³
    soil_3day_avg    FLOAT,   -- m³/m³ 3-day avg
    wind_speed       FLOAT,   -- m/s
    humidity         FLOAT,   -- % relative humidity
    evaporation      FLOAT,   -- negative metres (ERA5 convention)
    is_monsoon       FLOAT,   -- 0.0 or 1.0
    month            FLOAT,   -- 1.0 to 12.0
    day_of_year      FLOAT,   -- 1.0 to 365.0

    -- Top-3 feature importances (for frontend explainer)
    top_feature_1_name  VARCHAR(50),
    top_feature_1_value FLOAT,
    top_feature_1_imp   FLOAT,
    top_feature_2_name  VARCHAR(50),
    top_feature_2_value FLOAT,
    top_feature_2_imp   FLOAT,
    top_feature_3_name  VARCHAR(50),
    top_feature_3_value FLOAT,
    top_feature_3_imp   FLOAT,

    weather_source VARCHAR(50) DEFAULT 'open-meteo',
    computed_at    TIMESTAMP   NOT NULL
);
```

**CRUD:**
- CREATE: `ZoneRepository.save_zone_batch()` — bulk inserts in chunks of 200
- READ: `ZoneRepository.get_latest_zone_points()` (paginated), `get_zone_points_in_bbox()` (bounding box filter)
- UPDATE: Never updated — immutable once written
- DELETE: `ZoneRepository._delete_old_batches()` — cascades to delete grid points for old batches

**Indexes:**
```sql
ix_zone_grid_points_batch_id
ix_zone_grid_points_lat
ix_zone_grid_points_lng
ix_zone_batch_location  (batch_id, lat, lng)
```

---

### Table: `flood_events` ⬜ Schema ready, data not yet seeded

Historical Pakistan flood events. Used by `GET /flood-events` and planned education timeline.

```sql
CREATE TABLE flood_events (
    id                  SERIAL PRIMARY KEY,
    event_id            VARCHAR(100) UNIQUE NOT NULL,  -- "pak-flood-2022"
    year                INTEGER      NOT NULL,
    title               VARCHAR(200) NOT NULL,
    affected_provinces  TEXT,       -- JSON array string
    affected_districts  TEXT,       -- JSON array string
    peak_month          VARCHAR(20),
    estimated_affected  BIGINT,
    damage_usd_billion  FLOAT,
    description         TEXT
);
```

**Events to seed:** 2010 super flood, 2011 Sindh, 2014 AJK/Punjab, 2015 Chitral, 2020 monsoon, 2022 Dadu catastrophe.

**CRUD (all planned):**
- CREATE: seed script + admin endpoint
- READ: `GET /flood-events`, `GET /flood-events?district_name=Dadu`
- UPDATE: Admin dashboard
- DELETE: Admin dashboard

---

### Table: `data_sources` ❌ Unused

Registry of data adapters. Adapters were removed in the Phase 10 refactor. Table is inert.

---

### Table: `risk_snapshots` ❌ Unused

Was written by the old district-level prediction service. Replaced by `zone_grid_points`. Table is inert.

---

### Planned Tables

#### `users` (Auth — via Supabase Auth)
Managed by Supabase Auth — not a manual table. Accessed via `supabase.auth`.

#### `user_profiles`
```sql
CREATE TABLE user_profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id),
    display_name VARCHAR(100),
    saved_districts TEXT[],       -- array of district_ids
    alert_email  BOOLEAN DEFAULT false,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### `education_articles`
```sql
CREATE TABLE education_articles (
    id           SERIAL PRIMARY KEY,
    slug         VARCHAR(100) UNIQUE NOT NULL,  -- "monsoon-mechanics"
    title        VARCHAR(200) NOT NULL,
    category     VARCHAR(50)  NOT NULL,          -- "hydrology" | "history" | "guide"
    summary      TEXT,
    content_md   TEXT,                           -- full markdown content
    cover_image  TEXT,                           -- URL
    read_time_min INTEGER,
    published_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `chat_sessions` (Gemini — optional logging)
```sql
CREATE TABLE chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES auth.users(id),  -- nullable for anonymous
    bot_type    VARCHAR(20) NOT NULL,             -- "learn" | "help"
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    message_count INTEGER DEFAULT 0
);
```

---

## 5. ML Model

### Model: `flood_xgb_pakistan_v2`

| Property | Value |
|---|---|
| Algorithm | XGBoost Binary Classifier |
| Artifact | `backend/ml/artifacts/flood_xgb_pakistan_v2.pkl` |
| Training data | Pakistan Dadu district real flood records 2022–2024 |
| Input features | 14 weather + temporal features |
| Output | Flood probability 0.0–1.0 |
| Serialization | joblib (`.pkl`) |

### 14 Input Features

| # | Feature | Source API variable | Unit | Processing |
|---|---|---|---|---|
| 1 | `precipitation` | `precipitation_sum` (daily) | mm/day | Last value |
| 2 | `precip_3day_avg` | `precipitation_sum` (daily) | mm/day | 3-day tail mean |
| 3 | `precip_7day_avg` | `precipitation_sum` (daily) | mm/day | 7-day tail mean |
| 4 | `pressure` | `surface_pressure` (hourly) | Pa | Daily mean × 100 |
| 5 | `temperature` | `temperature_2m_max` (daily) | °C | Last value |
| 6 | `temp_3day_avg` | `temperature_2m_max` (daily) | °C | 3-day tail mean |
| 7 | `soil_moisture` | `soil_moisture_0_to_1cm` (hourly) | m³/m³ | Daily mean |
| 8 | `soil_3day_avg` | `soil_moisture_0_to_1cm` (hourly) | m³/m³ | 3-day mean of daily means |
| 9 | `wind_speed` | `wind_speed_10m_max` (daily) | m/s | Last value ÷ 3.6 |
| 10 | `humidity` | `relative_humidity_2m` (hourly) | % | Daily mean |
| 11 | `evaporation` | `et0_fao_evapotranspiration` (daily) | negative m | −abs(value)/1000 |
| 12 | `is_monsoon` | Derived | 0 or 1 | month ∈ {6,7,8,9,10} |
| 13 | `month` | Derived | 1–12 | Current month |
| 14 | `day_of_year` | Derived | 1–365 | Day number |

### Risk Classification

```
flood_prob ∈ [0.00, 0.30) → Low
flood_prob ∈ [0.30, 0.55) → Moderate
flood_prob ∈ [0.55, 0.75) → High
flood_prob ∈ [0.75, 1.00] → Severe
```

### Confidence Score

```
confidence = 2 × |flood_prob − 0.5|
```

- 0.0 = maximally uncertain (model is at 50/50)
- 1.0 = maximally confident (model predicts 0.0 or 1.0)

### Zone Grid

| Property | Value |
|---|---|
| Grid step | 0.5° (~55 km between points) |
| Pakistan bbox | N 37.0°, S 23.5°, W 60.5°, E 77.0° |
| Total points | ~952 per batch |
| Refresh interval | Every 3 hours |
| Daily API cost | 952 × 8 = 7,616 requests (under 10,000 free-tier limit) |

---

## 6. Backend — FastAPI

### App Startup (`main.py`)

```
1. configure_logging()           ← sets up all app loggers
2. get_flood_model()             ← loads flood_xgb_pakistan_v2.pkl into memory
3. start_zone_scheduler(model)   ← registers APScheduler jobs
4. FastAPI app starts            ← all routes ready
5. 5 seconds after start         → _startup_zone_job fires
   └── is_cache_fresh()?
       ├── YES → skip (log: "Zone cache is fresh")
       └── NO  → compute_all_zones() → save to Supabase
6. Every 3 hours                 → _zone_job fires (always computes)
```

### CORS

```python
allow_origins = settings.CORS_ORIGINS   # default: ["http://localhost:3000"]
allow_methods = ["*"]
allow_headers = ["*"]
allow_credentials = True
```

### Key Config Values

```python
GRID_STEP_DEGREES          = 0.5    # grid resolution
ZONE_CACHE_TTL_MINUTES     = 180    # 3h — cache freshness threshold
ZONE_STARTUP_DELAY_SEC     = 60     # startup wait before first run check
OPEN_METEO_REQUEST_DELAY   = 0.70s  # delay between each of 952 requests
OPEN_METEO_MAX_RETRIES     = 4      # retries on 429
OPEN_METEO_RETRY_BASE_SEC  = 15.0s  # 429 backoff: 15s → 30s → 60s → 120s
```

---

## 7. All API Endpoints

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/api/docs` (Swagger UI)

---

### Health

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Liveness check — returns `{ status: "ok" }` |

---

### Prediction (live — hits Open-Meteo, ~1–2s)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/predict?lat=&lng=` | None | Full prediction. Fetches live weather → XGBoost → risk + confidence + top factors |
| GET | `/risk/by-location?lat=&lng=` | None | Same as above, returns GeoJSON Feature — drop directly onto map |
| GET | `/model/status` | None | Whether XGBoost artifact is loaded and ready |

**Sample `/predict` response:**
```json
{
  "flood_prob": 0.23,
  "risk_level": "Low",
  "confidence": 0.54,
  "top_factors": [
    { "name": "soil_moisture", "value": 0.12, "importance": 0.31 },
    { "name": "precipitation", "value": 4.2,  "importance": 0.27 },
    { "name": "is_monsoon",    "value": 0.0,  "importance": 0.19 }
  ],
  "disclaimer": "PakFlood AI is an educational decision-support prototype..."
}
```

---

### Zone Grid (DB-cached, instant)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/zones/geojson` | None | All ~952 zone points as GeoJSON FeatureCollection |
| GET | `/zones/status` | None | Cache age, freshness, point count, is_computing, next refresh ETA |
| POST | `/zones/compute` | None | Trigger background recomputation (no-op if already running) |
| POST | `/zones/admin/refresh-zones` | `X-Api-Key` header | Force refresh, bypasses TTL |

**`/zones/geojson` feature properties:**
```json
{
  "flood_prob": 0.23,
  "risk_level": "Low",
  "risk_score": 1,
  "confidence": 0.54,
  "precipitation": 0.0,
  "precip_3day_avg": 1.2,
  "temperature": 38.4,
  "soil_moisture": 0.12,
  "humidity": 42.0,
  "top_factors": [...],
  "computed_at": "2026-05-17T11:43:38Z",
  "weather_source": "open-meteo"
}
```

**`/zones/status` response:**
```json
{
  "status": "complete",
  "has_data": true,
  "is_fresh": true,
  "is_computing": false,
  "computed_at": "2026-05-17T11:43:38Z",
  "age_minutes": 47.3,
  "next_refresh_in_min": 132.7,
  "total_points": 952,
  "last_batch_id": "f31c1a5e-..."
}
```

---

### Districts (DB-cached, instant)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/districts/search?q=lahore` | None | Search districts by name — returns boundary + zone summary per result |
| GET | `/districts/{district_id}` | None | Full detail: boundary GeoJSON Feature + zone points + risk summary |

**`/districts/search` response:**
```json
[{
  "district_id": "PK-PB-LH",
  "name": "Lahore",
  "province": "Punjab",
  "center": { "lat": 31.55, "lng": 74.34 },
  "boundary": {
    "type": "Feature",
    "geometry": { "type": "MultiPolygon", "coordinates": [...] },
    "properties": { "district_id": "PK-PB-LH", "name": "Lahore", "province": "Punjab" }
  },
  "summary": {
    "total_points": 2,
    "avg_flood_prob": 0.13,
    "max_flood_prob": 0.17,
    "dominant_risk": "Low",
    "risk_breakdown": { "Low": 2, "Moderate": 0, "High": 0, "Severe": 0 },
    "computed_at": "2026-05-17T11:43:38Z"
  }
}]
```

**`/districts/{district_id}` response:**
```json
{
  "district": {
    "district_id": "PK-PB-LH",
    "name": "Lahore",
    "province": "Punjab",
    "center": { "lat": 31.55, "lng": 74.34 },
    "has_boundary": true
  },
  "boundary": { "type": "Feature", "geometry": {...}, "properties": {...} },
  "summary": { "dominant_risk": "Low", "avg_flood_prob": 0.13, ... },
  "zones": {
    "type": "FeatureCollection",
    "features": [...],
    "metadata": { "total_points": 2, "is_fresh": true, "grid_step_degrees": 0.5 }
  }
}
```

---

### Boundaries

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin-boundaries` | None | All 142 districts as GeoJSON FeatureCollection (polygons for map layer) |
| GET | `/location/search?q=lahore` | None | Lightweight district search — name, province, center only |

---

### Flood Events

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/flood-events` | None | All historical flood events |
| GET | `/flood-events?district_name=Dadu` | None | Filter by affected district |

---

### Planned Auth Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | None | Register with email + password |
| POST | `/auth/login` | None | Login, returns JWT |
| POST | `/auth/logout` | JWT | Invalidate session |
| GET | `/auth/me` | JWT | Get current user profile |
| PUT | `/auth/me` | JWT | Update display name, saved districts, alert preferences |
| POST | `/auth/google` | None | Google OAuth redirect |

---

### Planned Education Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/education/articles` | None | List all articles (slug, title, category, summary, read_time) |
| GET | `/education/articles/{slug}` | None | Full article content in markdown |
| POST | `/education/articles` | Admin | Create new article |
| PUT | `/education/articles/{slug}` | Admin | Update article content |
| DELETE | `/education/articles/{slug}` | Admin | Remove article |

---

### Planned Gemini Chat Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/chat/learn` | None / JWT | Learning chatbot — flood/hydrology Q&A |
| POST | `/chat/help` | None / JWT | Help bot — explains the dashboard |
| GET | `/chat/history` | JWT | User's past chat sessions |
| DELETE | `/chat/history/{session_id}` | JWT | Delete a session |

---

## 8. Frontend — Next.js

### Pages

| Route | Component | Description |
|---|---|---|
| `/` | `MapDashboard` | Main dashboard — Pakistan map + copilot panel |
| `/education` | *(planned)* | Education hub — article cards |
| `/education/[slug]` | *(planned)* | Individual article reader |
| `/auth/login` | *(planned)* | Login / signup |
| `/auth/profile` | *(planned)* | User profile + saved districts |

### Map Layers (Leaflet)

| Layer | Component | Data source |
|---|---|---|
| District boundaries | `PakistanMap` | `GET /admin-boundaries` |
| Zone risk grid | `GridRiskLayer` | `GET /zones/geojson` |
| City weather pins | `CityWeatherLabels` | Static (`pakistan-cities-weather.ts`) |
| Rainfall canvas | `RainCanvas` | Simulated animation |
| Wind vectors | `WindVectorLayer` | Simulated |
| Rainfall stations | `RainfallStationLayer` | Static |

### Copilot Panel Tabs

| Tab | ID | Requires district | Content |
|---|---|---|---|
| Brief | `brief` | Yes | AI risk summary — level, causes, confidence, actions |
| Copilot | `copilot` | Yes | Free-form AI Q&A about the district |
| Simulate | `simulate` | Yes | What-if sliders (rainfall+, temperature+, soil saturation) |
| Action | `response` | Yes | Emergency response plan by risk level |
| Data | `evidence` | Yes | Supporting weather data, source citations |
| SAR | `sar` | No | SAR/satellite evidence viewer |
| Sources | `sources` | No | Educational source links and references |

### API Client (`src/lib/api.ts`)

All backend calls are typed and fall back to mock data if the backend is unreachable:

```typescript
fetchBoundaries()           → GET /admin-boundaries
fetchRiskByDistrict(id)     → GET /risk/by-boundary/{id}
fetchFloodEvents(district?) → GET /flood-events
fetchModelStatus()          → GET /model/status
searchLocations(q)          → GET /location/search?q=
```

### Frontend Environment

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 9. Background Scheduler

### APScheduler Setup

```python
_scheduler = AsyncIOScheduler()   # runs on FastAPI's own event loop

# Job 1: startup (one-shot, 5s after server start)
_startup_zone_job  →  checks DB freshness first
                       if fresh → skip
                       if stale → run compute_all_zones()

# Job 2: recurring (every 3 hours)
_zone_job          →  always runs compute_all_zones()
                       blocked by _is_computing flag (no concurrent runs)
```

### Rate Limit Strategy

```
Normal flow:
  Request 1 → 0.7s wait → Request 2 → 0.7s wait → ... → Request 952

On 429 (all 4 retries exhausted):
  → 180s cooldown (rate window clears)
  → delay doubles (0.7s → 1.4s → max 3.0s)
  → continues with remaining points

On 502/503/504 (transient server error):
  → 3s, 6s, 12s, 24s backoff (fast retry — not a rate limit)

On server shutdown:
  → asyncio.CancelledError swallowed in _zone_job
  → APScheduler does NOT log "raised an exception"
```

### Scheduler Lifecycle

| Event | Action |
|---|---|
| FastAPI startup | `start_zone_scheduler(model)` called |
| 5s after start | `_startup_zone_job` — freshness check then compute if needed |
| Every 3 hours | `_zone_job` — unconditional compute |
| FastAPI shutdown | `stop_zone_scheduler()` — graceful APScheduler shutdown |
| Job fires late | `misfire_grace_time=300` — allows up to 5 min late start |

---

## 10. Auth & User Accounts (Planned)

### Technology: Supabase Auth

Supabase Auth provides authentication out of the box — no custom auth code needed beyond JWT middleware in FastAPI.

### Supported Methods
- Email + password
- Magic link (passwordless email)
- Google OAuth

### Backend Implementation Plan

```python
# middleware/auth.py
async def get_current_user(authorization: str = Header(...)) -> dict:
    token = authorization.replace("Bearer ", "")
    user  = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user

# Protected route example
@router.get("/auth/me")
async def get_me(user = Depends(get_current_user)) -> dict:
    profile = db.table("user_profiles").select("*").eq("id", user.id).execute()
    return profile.data[0]
```

### CRUD — User Profiles

| Operation | Endpoint | Description |
|---|---|---|
| **Create** | `POST /auth/signup` | Supabase creates auth.users row; trigger creates user_profiles row |
| **Read** | `GET /auth/me` | Returns profile — display_name, saved_districts, alert_email |
| **Update** | `PUT /auth/me` | Update display name, toggle alerts, add/remove saved districts |
| **Delete** | `DELETE /auth/me` | Deletes user_profiles row + Supabase auth user |

### RLS Policy (user_profiles)

```sql
-- Users can only read/write their own row
CREATE POLICY "own profile" ON user_profiles
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());
```

### Frontend Auth Flow

```
1. User clicks "Sign In"
2. → /auth/login page
3. → Supabase Auth UI (email/password or Google)
4. → On success: JWT stored in localStorage / httpOnly cookie
5. → All API calls include "Authorization: Bearer <token>"
6. → Profile page shows saved districts, preferences
```

---

## 11. Education Module (Planned)

A structured learning section teaching users about floods, hydrology, and how the dashboard works.

### Pages

| Route | Title | Description |
|---|---|---|
| `/education` | Learn About Floods | Hub page — article cards by category |
| `/education/water-cycle` | The Water Cycle | Precipitation, evaporation, runoff, infiltration |
| `/education/monsoon` | Pakistan's Monsoon | Why Pakistan floods June–October |
| `/education/indus-river` | The Indus River System | Glacial melt, snowmelt, basin dynamics |
| `/education/flood-types` | Types of Floods | Flash floods, riverine, urban, glacial outburst |
| `/education/pakistan-history` | Pakistan Flood History | Interactive timeline: 2010, 2011, 2014, 2015, 2020, 2022 |
| `/education/reading-the-map` | How to Read the Risk Map | Dashboard guide with annotations |
| `/education/data-sources` | Our Data Sources | Open-Meteo, NDMA, PMD, FFD explained |
| `/education/climate-change` | Climate Change & Floods | How warming intensifies Pakistan's flood risk |

### Article CRUD

| Operation | Endpoint | Auth | Description |
|---|---|---|---|
| **Create** | `POST /education/articles` | Admin API key | Add new article with markdown content |
| **Read (list)** | `GET /education/articles` | None | All articles — slug, title, category, summary, read_time |
| **Read (one)** | `GET /education/articles/{slug}` | None | Full article with markdown content |
| **Update** | `PUT /education/articles/{slug}` | Admin API key | Edit content, title, category |
| **Delete** | `DELETE /education/articles/{slug}` | Admin API key | Remove article |

### Flood Events CRUD (for History Timeline)

| Operation | Endpoint | Auth | Description |
|---|---|---|---|
| **Create** | `POST /flood-events` | Admin API key | Add historical event |
| **Read** | `GET /flood-events` | None | All events ordered by year desc |
| **Read (filtered)** | `GET /flood-events?district_name=Dadu` | None | Events affecting a district |
| **Update** | `PUT /flood-events/{event_id}` | Admin API key | Edit event details |
| **Delete** | `DELETE /flood-events/{event_id}` | Admin API key | Remove event |

### Historical Events to Seed

| Year | Event | Affected | Damage |
|---|---|---|---|
| 2010 | Super Flood | 20M people, all provinces | $10B |
| 2011 | Sindh Monsoon Floods | 5.3M people, Sindh | $3.7B |
| 2014 | AJK & Punjab Floods | 2.5M people | $1.5B |
| 2015 | Chitral Flash Floods | 250,000 people, KPK | $150M |
| 2020 | Monsoon Floods | 15M people, Balochistan/Sindh | $1.5B |
| 2022 | Dadu Catastrophe | 33M people, 1/3 of Pakistan submerged | $30B |

---

## 12. Gemini AI Agents (Planned)

Two distinct bot personas sharing one Gemini API integration, routed through FastAPI so the API key is never exposed to the browser.

### Learning Bot (`/chat/learn`)

Teaches users about floods, hydrology, the monsoon, and Pakistan's flood history.

**System prompt (excerpt):**
```
You are FloodLearn, an educational AI assistant for PakFlood AI.
Your role is to help users understand:
- How floods form and spread
- Pakistan's monsoon system and the Indus river basin
- The history of floods in Pakistan (focus on 2010, 2022)
- How to interpret flood risk maps and weather data
- Climate change and its effect on Pakistan's flood patterns

Rules:
- Only answer questions related to floods, hydrology, climate, or Pakistan geography
- Always cite sources (PMD, NDMA, scientific studies) when possible
- Never claim your output is an official warning
- If you don't know something, say so clearly
- Keep answers educational and accessible, not technical jargon
```

**CRUD — Chat Sessions:**

| Operation | Endpoint | Auth | Description |
|---|---|---|---|
| **Create / send** | `POST /chat/learn` | None / JWT | Send message, get reply |
| **Read history** | `GET /chat/history?bot=learn` | JWT | Past sessions |
| **Delete session** | `DELETE /chat/history/{id}` | JWT | Remove a session |

**Request / Response:**
```json
POST /chat/learn
{
  "message": "Why does Pakistan flood every monsoon season?",
  "history": [
    { "role": "user", "content": "Tell me about the Indus river" },
    { "role": "assistant", "content": "The Indus river originates..." }
  ]
}

Response:
{
  "reply": "Pakistan experiences severe flooding each monsoon (June–October)...",
  "sources": ["PMD Annual Report 2023", "NDMA Flood Bulletin 2022"]
}
```

---

### Help Bot (`/chat/help`)

Explains the dashboard — what the risk levels mean, how to read the map, what to do with the information.

**System prompt (excerpt):**
```
You are FloodGuide, the help assistant for the PakFlood AI dashboard.
You help users navigate and understand the application.

You know about:
- The risk map: what Low/Moderate/High/Severe colours mean
- The grid points: 0.5° spacing, ~55km per cell, updated every 3 hours
- The Copilot panel: Brief, Copilot, Simulate, Action, Data, SAR, Sources tabs
- How to search for a district and read its risk summary
- The confidence score: 0 = uncertain, 1 = confident
- The top-3 feature drivers shown for each prediction
- The disclaimer: this is educational, always check PMD/NDMA for official warnings

Rules:
- Only answer questions about this dashboard and its features
- Always remind users to check PMD/NDMA for real emergency decisions
- Be concise — users are in an emergency-response mindset, not reading essays
```

**CRUD — Chat Sessions:**

| Operation | Endpoint | Auth | Description |
|---|---|---|---|
| **Create / send** | `POST /chat/help` | None | Send question, get instant help |
| **Read history** | `GET /chat/history?bot=help` | JWT | Past sessions |
| **Delete session** | `DELETE /chat/history/{id}` | JWT | Remove a session |

**Request / Response:**
```json
POST /chat/help
{
  "message": "What does the orange colour on the map mean?",
  "current_page": "/"
}

Response:
{
  "reply": "Orange zones show Moderate flood risk (30–55% flood probability). This means weather conditions — particularly rainfall, soil saturation, and humidity — are elevated compared to normal. You should monitor these areas but immediate evacuation is not indicated. Always confirm with NDMA/PDMA for official guidance."
}
```

### Implementation Architecture

```
Frontend chat widget (floating, bottom-right corner)
    │
    │  POST /api/v1/chat/learn  or  /api/v1/chat/help
    ▼
FastAPI route (app/routes/chat.py)
    │
    ├── Rate limit: max 20 messages/hour per IP (anonymous)
    ├── Rate limit: max 100 messages/hour per user (authenticated)
    │
    ▼
Gemini API  (google-generativeai SDK, server-side only)
    │  model: gemini-1.5-flash
    │  System prompt injection per bot type
    │  Conversation history passed each turn
    ▼
Streamed response back to frontend
```

---

## 13. Feature Status

### Completed ✅

- [x] Pakistan flood risk map — Leaflet, district polygons, zone grid layer
- [x] XGBoost model — trained on real Pakistan flood data, 14 weather features
- [x] Live prediction endpoint — any lat/lng → real-time Open-Meteo → risk
- [x] Zone grid system — 952 points computed every 3h, cached in Supabase
- [x] Stale-while-revalidate cache — zone GeoJSON always instant from DB
- [x] Adaptive rate limiter — handles Open-Meteo 429 and 502/503/504 separately
- [x] District search API — search by name, returns boundary polygon + zone summary
- [x] District detail API — boundary GeoJSON Feature + zone points filtered by polygon
- [x] Point-in-polygon filter — pure Python ray-casting, no shapely dependency
- [x] Pagination — Supabase 1000-row cap handled with range-based pagination
- [x] 142 Pakistan districts seeded (name, province, center, district_id)
- [x] 135/142 districts have real polygon boundaries (GADM 4.1 + geoBoundaries ADM2)
- [x] Risk classification — Low / Moderate / High / Severe with thresholds
- [x] Confidence score — 2 × |prob − 0.5|
- [x] Top-3 feature importance per grid point (stored in DB, served in API)
- [x] Copilot panel — 7 tabs: Brief, Copilot, Simulate, Action, Data, SAR, Sources
- [x] Safety disclaimer — DISCLAIMER constant enforced in every prediction response
- [x] APScheduler misfire_grace_time — jobs survive late firing
- [x] CancelledError swallowed on shutdown — clean server restart
- [x] Startup freshness check — skip computation if DB cache < 3h old
- [x] Admin refresh endpoint — `POST /zones/admin/refresh-zones` with API key auth
- [x] Flood events schema — table created, endpoint ready
- [x] Seed scripts — `seed_districts.py`, `patch_district_geom.py`, `patch_district_geom_hdx.py`

### In Progress / Partial ⚠️

- [~] Flood events data — schema and endpoint exist, historical data not yet seeded
- [~] Frontend API client — some endpoints call old route paths (pre-district-endpoint refactor)

### Planned 🔲

- [ ] **Auth** — Supabase Auth, JWT middleware, user_profiles table, RLS
- [ ] **User CRUD** — signup, login, logout, profile read/update/delete, saved districts
- [ ] **Education module** — 9 article pages, education_articles table, article CRUD
- [ ] **Flood events seed** — 6 major Pakistan flood events (2010–2022)
- [ ] **Learning Bot** — Gemini chatbot for flood/hydrology education
- [ ] **Help Bot** — Gemini chatbot for dashboard navigation
- [ ] **Chat sessions** — chat_sessions table, history CRUD
- [ ] **Gemini streaming** — streamed responses for real-time feel
- [ ] **District frontend integration** — wire `/districts/search` into the map search bar
- [ ] **Zone geojson frontend** — wire `GET /zones/geojson` into `GridRiskLayer`
- [ ] **Flood events seed script** — write and run `seed_flood_events.py`
- [ ] **Deploy** — Docker → Cloud Run (backend) + Vercel (frontend)

---

## 14. Running the Project

### Prerequisites
- Python 3.11+
- Node.js 20+
- A Supabase project (free tier works)
- Open-Meteo (no key needed, free tier = 10K req/day)

### Backend Setup

```bash
cd pakflood-ai/backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set SUPABASE_URL and SUPABASE_KEY

# Create Supabase tables (run once in Supabase SQL editor)
# → paste contents of supabase_tables.sql

# Seed database (run once)
python scripts/seed_districts.py           # 142 districts
python scripts/patch_district_geom.py      # GADM boundaries (120 districts)
python scripts/patch_district_geom_hdx.py  # geoBoundaries patch (13 more)

# Place ML model artifact
# Download flood_xgb_pakistan_v2.pkl from Kaggle → backend/ml/artifacts/

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd pakflood-ai/frontend

npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

npm run dev     # starts at http://localhost:3000
```

### Running Tests

```bash
# Backend unit tests
cd pakflood-ai/backend
pytest
pytest --cov=app --cov-report=html   # with coverage

# Frontend unit tests (Vitest)
cd pakflood-ai/frontend
npm test

# Frontend E2E tests (Playwright)
npx playwright test
npx playwright test --headed   # see the browser
```

### Seed Commands Reference

```bash
# Districts (run in order)
python scripts/seed_districts.py           # must run first
python scripts/patch_district_geom.py      # run after seed
python scripts/patch_district_geom_hdx.py  # run after patch_district_geom

# Trigger zone computation manually (after server is running)
curl -X POST http://localhost:8000/api/v1/zones/compute
```

---

## 15. Environment Variables

### `backend/.env`

```env
# ── App ──────────────────────────────────────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=INFO
SECRET_KEY=change-me-in-production
CORS_ORIGINS=["http://localhost:3000"]

# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-publishable-key

# ── Admin API ─────────────────────────────────────────────────────────────────
# Protects POST /zones/admin/refresh-zones
# Pass as: X-Api-Key: <value>
ADMIN_API_KEY=your-secret-admin-key

# ── Zone Grid Scheduler ──────────────────────────────────────────────────────
GRID_STEP_DEGREES=0.5          # grid spacing in degrees (~55km)
ZONE_CACHE_TTL_MINUTES=180     # 3h freshness window
ZONE_STARTUP_DELAY_SEC=60      # wait before startup freshness check

# ── Open-Meteo Rate Control ──────────────────────────────────────────────────
OPEN_METEO_REQUEST_DELAY_SEC=0.70   # delay between each of 952 requests
OPEN_METEO_MAX_RETRIES=4            # retries on 429 / transient errors
OPEN_METEO_RETRY_BASE_SEC=15.0      # 429 backoff: 15s → 30s → 60s → 120s

# ── Pakistan Bounding Box ────────────────────────────────────────────────────
PAK_NORTH=37.0
PAK_SOUTH=23.5
PAK_EAST=77.0
PAK_WEST=60.5

# ── Planned — Not Yet Active ─────────────────────────────────────────────────
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 16. Safety & Disclaimer Policy

PakFlood AI is an **educational decision-support prototype**. It is not authorized for use in real emergency management without validation against official sources.

### Enforced in Code

```python
# backend/app/hazards/flood/rules.py
DISCLAIMER = (
    "PakFlood AI is an educational decision-support prototype. "
    "Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions."
)
```

This constant is included in **every prediction API response** — `/predict`, `/risk/by-location`, `/zones/geojson`, and all district endpoints.

### Displayed in Frontend

- `SafetyDisclaimer` banner component on every page
- Bottom bar of `CopilotPanel`: *"Educational prototype · Not an authoritative emergency alert · PMD · FFD · NDMA · PDMA"*
- `StatusBar` shows model status honestly — if the artifact is missing, it says so rather than showing fake data

### Official Sources to Direct Users To

| Agency | Role |
|---|---|
| **PMD** (Pakistan Meteorological Department) | Official weather forecasts |
| **FFD** (Federal Flood Division) | Flood monitoring and river gauges |
| **NDMA** (National Disaster Management Authority) | National emergency coordination |
| **PDMA** (Provincial Disaster Management Authority) | Provincial emergency response |
