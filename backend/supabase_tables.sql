-- ============================================================
--  PakFlood AI — Supabase Table Creation Script
--  Paste this entire file into:
--    Supabase Dashboard → SQL Editor → New query → Run
-- ============================================================


-- ── 1. districts ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS districts (
    id          SERIAL PRIMARY KEY,
    district_id VARCHAR(20)  UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    province    VARCHAR(100) NOT NULL,
    center_lat  FLOAT        NOT NULL,
    center_lng  FLOAT        NOT NULL,
    geom_json   TEXT
);

CREATE INDEX IF NOT EXISTS ix_districts_district_id
    ON districts (district_id);


-- ── 2. data_sources ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_sources (
    id               SERIAL PRIMARY KEY,
    source_id        VARCHAR(50)  UNIQUE NOT NULL,
    name             VARCHAR(200) NOT NULL,
    status           VARCHAR(20)  NOT NULL DEFAULT 'mock',
    latency_hours    INTEGER,
    description      TEXT,
    features_created TEXT,
    last_updated     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_data_sources_source_id
    ON data_sources (source_id);


-- ── 3. flood_events ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flood_events (
    id                  SERIAL PRIMARY KEY,
    event_id            VARCHAR(100) UNIQUE NOT NULL,
    year                INTEGER      NOT NULL,
    title               VARCHAR(200) NOT NULL,
    affected_provinces  TEXT,
    affected_districts  TEXT,
    peak_month          VARCHAR(20),
    estimated_affected  BIGINT,
    damage_usd_billion  FLOAT,
    description         TEXT
);

CREATE INDEX IF NOT EXISTS ix_flood_events_event_id
    ON flood_events (event_id);

CREATE INDEX IF NOT EXISTS ix_flood_events_year
    ON flood_events (year);


-- ── 4. risk_snapshots ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_snapshots (
    id                    SERIAL PRIMARY KEY,
    district_id           VARCHAR(20) NOT NULL REFERENCES districts(district_id),
    risk_score            FLOAT       NOT NULL,
    risk_level            VARCHAR(20) NOT NULL,
    confidence            FLOAT       NOT NULL,
    top_factors           TEXT,
    forecast_window_hours INTEGER     DEFAULT 72,
    model_version         VARCHAR(50) DEFAULT 'seed-v1.0',
    feature_snapshot_json TEXT,
    source_status_json    TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_risk_snapshots_district_id
    ON risk_snapshots (district_id);


-- ── 5. zone_batches ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zone_batches (
    id           VARCHAR(36) PRIMARY KEY,   -- UUID
    started_at   TIMESTAMP   NOT NULL,
    completed_at TIMESTAMP,
    total_points INTEGER,
    status       VARCHAR(20) NOT NULL DEFAULT 'running'
    -- status values: running | complete | failed
);


-- ── 6. zone_grid_points ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS zone_grid_points (
    id       SERIAL PRIMARY KEY,
    batch_id VARCHAR(36) NOT NULL REFERENCES zone_batches(id),

    -- Location
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,

    -- Model output
    flood_prob  FLOAT       NOT NULL,
    risk_level  VARCHAR(20) NOT NULL,
    confidence  FLOAT       NOT NULL,

    -- Feature group 1: Rainfall
    precipitation    FLOAT,   -- mm/day today
    precip_3day_avg  FLOAT,   -- mm/day 3-day avg
    precip_7day_avg  FLOAT,   -- mm/day 7-day avg

    -- Feature group 2: Atmospheric
    pressure      FLOAT,      -- hPa
    temperature   FLOAT,      -- °C max
    temp_3day_avg FLOAT,      -- °C 3-day avg

    -- Feature group 3: Soil
    soil_moisture FLOAT,      -- m³/m³
    soil_3day_avg FLOAT,      -- m³/m³ 3-day avg

    -- Feature group 4: Wind + Humidity
    wind_speed  FLOAT,        -- m/s
    humidity    FLOAT,        -- % relative
    evaporation FLOAT,        -- mm (stored as negative)

    -- Feature group 5: Temporal
    is_monsoon  FLOAT,        -- 0.0 or 1.0
    month       FLOAT,        -- 1.0–12.0
    day_of_year FLOAT,        -- 1.0–365.0

    -- Top-3 feature importances (for explainer panel)
    top_feature_1_name  VARCHAR(50),
    top_feature_1_value FLOAT,
    top_feature_1_imp   FLOAT,

    top_feature_2_name  VARCHAR(50),
    top_feature_2_value FLOAT,
    top_feature_2_imp   FLOAT,

    top_feature_3_name  VARCHAR(50),
    top_feature_3_value FLOAT,
    top_feature_3_imp   FLOAT,

    -- Metadata
    weather_source VARCHAR(50) DEFAULT 'open-meteo',
    computed_at    TIMESTAMP   NOT NULL,
    data_age_hours FLOAT
);

CREATE INDEX IF NOT EXISTS ix_zone_grid_points_batch_id
    ON zone_grid_points (batch_id);

CREATE INDEX IF NOT EXISTS ix_zone_grid_points_lat
    ON zone_grid_points (lat);

CREATE INDEX IF NOT EXISTS ix_zone_grid_points_lng
    ON zone_grid_points (lng);

CREATE INDEX IF NOT EXISTS ix_zone_batch_location
    ON zone_grid_points (batch_id, lat, lng);







-- ============================================================
--  Row Level Security — allow backend anon key to write
--  (Run this block after the tables above)
-- ============================================================

-- zone_batches: allow anon INSERT + UPDATE (backend writes predictions)
ALTER TABLE zone_batches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon insert zone_batches" ON zone_batches;
CREATE POLICY "anon insert zone_batches"
    ON zone_batches FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update zone_batches" ON zone_batches;
CREATE POLICY "anon update zone_batches"
    ON zone_batches FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon select zone_batches" ON zone_batches;
CREATE POLICY "anon select zone_batches"
    ON zone_batches FOR SELECT TO anon USING (true);


-- zone_grid_points: allow anon INSERT + SELECT
ALTER TABLE zone_grid_points ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon insert zone_grid_points" ON zone_grid_points;
CREATE POLICY "anon insert zone_grid_points"
    ON zone_grid_points FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon select zone_grid_points" ON zone_grid_points;
CREATE POLICY "anon select zone_grid_points"
    ON zone_grid_points FOR SELECT TO anon USING (true);

