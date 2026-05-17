# PakFlood AI — Complete API Reference

> **Base URL:** `http://localhost:8000/api/v1`  
> **Interactive docs:** `http://localhost:8000/api/docs` (Swagger UI)  
> **ReDoc:** `http://localhost:8000/api/redoc`  
> **Content-Type:** All responses are `application/json`

---

## Table of Contents

1. [Overview & Conventions](#1-overview--conventions)
2. [Health](#2-health)
3. [Flood Prediction (Live)](#3-flood-prediction-live)
4. [Zone Grid (Cached)](#4-zone-grid-cached)
5. [Districts](#5-districts)
6. [Admin Boundaries (Legacy)](#6-admin-boundaries-legacy)
7. [Flood Events (Historical)](#7-flood-events-historical)
8. [Admin — Protected](#8-admin--protected)
9. [Planned: Authentication & Users](#9-planned-authentication--users)
10. [Planned: Education Module](#10-planned-education-module)
11. [Planned: Gemini Learning Bot](#11-planned-gemini-learning-bot)
12. [Planned: Help Bot](#12-planned-help-bot)
13. [Error Codes](#13-error-codes)
14. [Frontend Implementation Guide](#14-frontend-implementation-guide)

---

## 1. Overview & Conventions

### Risk Levels

| Level      | Flood Probability Range | Colour (hex) |
|------------|------------------------|--------------|
| `Low`      | 0.00 – 0.29            | `#22C55E`    |
| `Moderate` | 0.30 – 0.54            | `#EAB308`    |
| `High`     | 0.55 – 0.74            | `#F97316`    |
| `Severe`   | 0.75 – 1.00            | `#EF4444`    |

### Confidence Score

`confidence = 2 × |flood_prob − 0.5|`  
Range: 0.0 (maximally uncertain) → 1.0 (perfectly confident)

### Safety Disclaimer

Every response that contains a prediction **must** surface this disclaimer:

> "PakFlood AI is an educational decision-support prototype. Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions."

This is returned by the API inside a `disclaimer` field. The frontend must display it whenever a risk level is shown.

### Pagination

Endpoints that return lists support:
- `limit` — max rows to return (default: 20, max: 100)
- `offset` — rows to skip (default: 0)

### Authentication (Planned)

Once auth is implemented, protected endpoints require:
```
Authorization: Bearer <jwt_token>
```

---

## 2. Health

### `GET /health`

Check that the server is running. No authentication required.

**Request**
```
GET /api/v1/health
```

**Response `200 OK`**
```json
{
  "status": "ok",
  "timestamp": "2026-05-17T10:30:00.123456+00:00",
  "service": "pakflood-ai"
}
```

**Frontend use:** Poll on page load to show a "Backend offline" banner if this returns an error.

---

## 3. Flood Prediction (Live)

These endpoints call **Open-Meteo live** and run the XGBoost classifier in real time. They take 1–3 seconds to respond. Use the cached zone endpoints for map rendering.

---

### `GET /predict`

Predict flood risk for any lat/lng coordinate. Fetches 7-day weather history, computes 14 features, runs XGBoost, and persists the result to Supabase.

**Query Parameters**

| Parameter | Type  | Required | Description            |
|-----------|-------|----------|------------------------|
| `lat`     | float | Yes      | Latitude (-90 to 90)   |
| `lng`     | float | Yes      | Longitude (-180 to 180)|

**Request**
```
GET /api/v1/predict?lat=31.5497&lng=74.3436
```

**Response `200 OK`**
```json
{
  "district_id": null,
  "name": "31.5497,74.3436",
  "province": null,
  "risk_score": 0.4823,
  "risk_level": "Moderate",
  "confidence": 0.6354,
  "top_factors": [
    "precipitation_sum_7d",
    "soil_moisture_mean",
    "relative_humidity_2m_max"
  ],
  "forecast_window_hours": 72,
  "model_version": "flood_xgb_pakistan_v2",
  "source_status": {
    "open_meteo": "ok"
  },
  "disclaimer": "PakFlood AI is an educational decision-support prototype..."
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `422`  | `lat` or `lng` out of valid range |
| `502`  | Open-Meteo unreachable or returned bad data |
| `503`  | ML model artifact not loaded |

---

### `GET /risk/by-location`

Returns flood risk as a **GeoJSON Feature** for direct use in Mapbox/Leaflet. Includes weather feature values.

**Query Parameters**

| Parameter | Type  | Required | Description            |
|-----------|-------|----------|------------------------|
| `lat`     | float | Yes      | Latitude               |
| `lng`     | float | Yes      | Longitude              |

**Request**
```
GET /api/v1/risk/by-location?lat=31.5497&lng=74.3436
```

**Response `200 OK`**
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [74.3436, 31.5497]
  },
  "properties": {
    "flood_prob": 0.4823,
    "risk_level": "Moderate",
    "confidence": 0.6354,
    "top_factors": [
      {
        "name": "precipitation_sum_7d",
        "value": 42.5,
        "importance": 0.312
      },
      {
        "name": "soil_moisture_mean",
        "value": 0.38,
        "importance": 0.198
      },
      {
        "name": "relative_humidity_2m_max",
        "value": 87.0,
        "importance": 0.145
      }
    ],
    "disclaimer": "PakFlood AI is an educational decision-support prototype...",
    "weather_features": {
      "precipitation_sum_7d": 42.5,
      "precipitation_max_1d": 18.2,
      "precipitation_days_7d": 3,
      "rain_sum_7d": 40.1,
      "soil_moisture_mean": 0.38,
      "soil_moisture_max": 0.44,
      "relative_humidity_2m_max": 87.0,
      "temperature_2m_max": 34.1,
      "temperature_2m_min": 24.5,
      "wind_speed_10m_max": 22.3,
      "wind_gusts_10m_max": 31.0,
      "et0_fao_evapotranspiration_sum": 6.2,
      "surface_pressure_mean": 996.4,
      "cloud_cover_mean": 68.0
    }
  }
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `503`  | Model not loaded or weather data unavailable |

---

### `GET /model/status`

Check whether the XGBoost model artifact is loaded and ready.

**Request**
```
GET /api/v1/model/status
```

**Response `200 OK`**
```json
{
  "model_version": "flood_xgb_pakistan_v2",
  "artifact_ready": true,
  "features": 14,
  "disclaimer": "PakFlood AI is an educational decision-support prototype..."
}
```

**Frontend use:** If `artifact_ready` is `false`, show "Predictions unavailable" instead of risk scores.

---

## 4. Zone Grid (Cached)

These endpoints serve pre-computed data from the Supabase cache. They respond **instantly** (< 50ms). The 952-point grid covering all of Pakistan is recomputed every 3 hours in the background.

---

### `GET /zones/geojson`

Return the full Pakistan zone grid as a GeoJSON FeatureCollection. Every point has its flood probability and risk level attached as GeoJSON properties.

**Stale-while-revalidate:** If the cache is older than 3 hours, returns the existing data immediately **and** triggers a background refresh. The next request (a few minutes later) will get fresh data.

**Request**
```
GET /api/v1/zones/geojson
```

**Response `200 OK`**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [74.0, 31.5]
      },
      "properties": {
        "id": "31.5_74.0",
        "lat": 31.5,
        "lng": 74.0,
        "flood_prob": 0.4823,
        "risk_level": "Moderate",
        "confidence": 0.6354,
        "computed_at": "2026-05-17T10:00:00+00:00"
      }
    }
    // ... 951 more features
  ],
  "metadata": {
    "computed_at": "2026-05-17T10:00:00+00:00",
    "is_fresh": true,
    "total_points": 952,
    "grid_step_degrees": 0.5,
    "model_features": ["precipitation_sum_7d", "soil_moisture_mean", "..."],
    "message": null
  }
}
```

**When no data exists yet (`200 OK` with empty collection)**
```json
{
  "type": "FeatureCollection",
  "features": [],
  "metadata": {
    "computed_at": null,
    "is_fresh": false,
    "total_points": 0,
    "grid_step_degrees": 0.25,
    "model_features": [],
    "message": "No zone data yet — computation queued, retry in ~10 min."
  }
}
```

**Frontend use:** Render each feature as a circle on the map, coloured by `risk_level`. Check `metadata.is_fresh` — if false, show a subtle "Refreshing data…" indicator.

---

### `GET /zones/status`

Check cache age and refresh progress. Poll this every 30 seconds to drive a loading indicator.

**Request**
```
GET /api/v1/zones/status
```

**Response `200 OK`**
```json
{
  "status": "completed",
  "has_data": true,
  "is_fresh": true,
  "is_computing": false,
  "computed_at": "2026-05-17T10:00:00+00:00",
  "age_minutes": 45.2,
  "next_refresh_in_min": 134.8,
  "total_points": 952,
  "last_batch_id": "batch_uuid_here"
}
```

**`status` values:** `completed` | `running` | `failed` | `never_computed`

---

### `POST /zones/compute`

Manually trigger a background zone recomputation. Returns immediately. Poll `/zones/status` for progress.

**Request**
```
POST /api/v1/zones/compute
```

**Response `200 OK` — started**
```json
{
  "started": true,
  "message": "Zone computation started — poll /zones/status."
}
```

**Response `200 OK` — already running**
```json
{
  "started": false,
  "reason": "Computation already running."
}
```

---

## 5. Districts

These endpoints search and retrieve district-level flood risk data. Risk data comes from the zone grid cache — no live API calls are made.

---

### `GET /districts/search`

Search Pakistan districts by name. Returns up to 10 matches, each with:
- District metadata and center coordinates
- The district's GeoJSON boundary polygon (from GADM/geoBoundaries — 135 of 142 districts have real polygons)
- A flood risk summary computed from zone grid points inside the district

**Query Parameters**

| Parameter | Type   | Required | Description                             |
|-----------|--------|----------|-----------------------------------------|
| `q`       | string | Yes      | District name, min 2 characters         |

**Request**
```
GET /api/v1/districts/search?q=lahore
```

**Response `200 OK`**
```json
[
  {
    "district_id": "PK-PB-LHR",
    "name": "Lahore",
    "province": "Punjab",
    "center": {
      "lat": 31.5497,
      "lng": 74.3436
    },
    "boundary": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[74.01, 31.25], [74.60, 31.25], [74.60, 31.80], [74.01, 31.80], [74.01, 31.25]]]
      },
      "properties": {
        "district_id": "PK-PB-LHR",
        "name": "Lahore",
        "province": "Punjab"
      }
    },
    "summary": {
      "total_points": 4,
      "avg_flood_prob": 0.4210,
      "max_flood_prob": 0.6130,
      "dominant_risk": "Moderate",
      "risk_breakdown": {
        "Low": 2,
        "Moderate": 1,
        "High": 1,
        "Severe": 0
      },
      "computed_at": "2026-05-17T10:00:00+00:00"
    }
  }
]
```

**Notes:**
- `boundary` is `null` for the 7 districts with no public polygon data (newer administrative units)
- `summary` is `null` when no zone computation has run yet, or if the district has zero grid points inside it (very small districts)

**Errors**

| Status | Reason |
|--------|--------|
| `422`  | `q` is shorter than 2 characters |
| `503`  | Database unavailable |

---

### `GET /districts/{district_id}`

Full flood risk data for a single district. Returns the boundary polygon, zone summary, and every individual grid point inside the district as a GeoJSON FeatureCollection.

**Path Parameters**

| Parameter     | Type   | Required | Description                     |
|---------------|--------|----------|---------------------------------|
| `district_id` | string | Yes      | e.g. `PK-PB-LHR`, `PK-SD-KHI`  |

**District ID Format:** `PK-{PROVINCE_CODE}-{DISTRICT_CODE}`

| Province code | Province         |
|---------------|------------------|
| `PB`          | Punjab           |
| `SD`          | Sindh            |
| `KP`          | Khyber Pakhtunkhwa |
| `BL`          | Balochistan      |
| `GB`          | Gilgit-Baltistan |
| `AJ`          | Azad Jammu & Kashmir |
| `IC`          | Islamabad Capital Territory |

**Request**
```
GET /api/v1/districts/PK-PB-LHR
```

**Response `200 OK`**
```json
{
  "district": {
    "district_id": "PK-PB-LHR",
    "name": "Lahore",
    "province": "Punjab",
    "center": {
      "lat": 31.5497,
      "lng": 74.3436
    },
    "has_boundary": true
  },
  "boundary": {
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[74.01, 31.25], ["..."]]]
    },
    "properties": {
      "district_id": "PK-PB-LHR",
      "name": "Lahore",
      "province": "Punjab"
    }
  },
  "summary": {
    "total_points": 4,
    "avg_flood_prob": 0.4210,
    "max_flood_prob": 0.6130,
    "dominant_risk": "Moderate",
    "risk_breakdown": {
      "Low": 2,
      "Moderate": 1,
      "High": 1,
      "Severe": 0
    },
    "computed_at": "2026-05-17T10:00:00+00:00"
  },
  "zones": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [74.0, 31.5]
        },
        "properties": {
          "id": "31.5_74.0",
          "lat": 31.5,
          "lng": 74.0,
          "flood_prob": 0.4823,
          "risk_level": "Moderate",
          "confidence": 0.6354,
          "computed_at": "2026-05-17T10:00:00+00:00"
        }
      }
      // ... more points inside this district
    ],
    "metadata": {
      "computed_at": "2026-05-17T10:00:00+00:00",
      "is_fresh": true,
      "total_points": 4,
      "grid_step_degrees": 0.5,
      "model_features": ["precipitation_sum_7d", "..."]
    }
  }
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `404`  | District ID does not exist |
| `503`  | Database unavailable |

---

## 6. Admin Boundaries (Legacy)

> These endpoints pre-date the `/districts` API. Use `/districts/search` and `/districts/{id}` for new frontend work.

---

### `GET /admin-boundaries`

Return all district boundaries as a GeoJSON FeatureCollection. Large payload (~2 MB) — load once and cache client-side.

**Request**
```
GET /api/v1/admin-boundaries
```

**Response `200 OK`**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "district_id": "PK-PB-LHR",
        "name": "Lahore",
        "province": "Punjab"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[74.01, 31.25], ["..."]]]
      }
    }
    // ... 141 more features
  ]
}
```

---

### `GET /location/search`

Legacy district name search. Returns center coordinates only — no boundary or risk data.

**Query Parameters**

| Parameter | Type   | Required | Description                |
|-----------|--------|----------|----------------------------|
| `q`       | string | Yes      | District name, min 2 chars |

**Request**
```
GET /api/v1/location/search?q=karachi
```

**Response `200 OK`**
```json
[
  {
    "district_id": "PK-SD-KHI",
    "name": "Karachi",
    "province": "Sindh",
    "center": [24.8607, 67.0011]
  }
]
```

> **Prefer `/districts/search` instead** — it returns boundary polygons and real risk summaries.

---

## 7. Flood Events (Historical)

### `GET /flood-events`

Return historical Pakistan flood events. Can be filtered by district name.

**Query Parameters**

| Parameter       | Type   | Required | Description                                |
|-----------------|--------|----------|--------------------------------------------|
| `district_name` | string | No       | Filter to events that affected this district |

**Request — all events**
```
GET /api/v1/flood-events
```

**Request — filtered by district**
```
GET /api/v1/flood-events?district_name=Dadu
```

**Response `200 OK`**
```json
[
  {
    "id": "flood-2022-sindh",
    "year": 2022,
    "title": "2022 Pakistan Floods — Worst in 30 Years",
    "affected_provinces": ["Sindh", "Balochistan", "Punjab", "KPK"],
    "affected_districts": ["Dadu", "Larkana", "Jacobabad", "Sukkur", "Naseerabad"],
    "peak_month": "August–September",
    "estimated_affected": 33000000,
    "damage_usd_billion": 30.0,
    "description": "Record monsoon rainfall caused catastrophic flooding covering one-third of Pakistan's land area..."
  }
]
```

**Response fields**

| Field                  | Type            | Description                          |
|------------------------|-----------------|--------------------------------------|
| `id`                   | string          | Unique event identifier              |
| `year`                 | integer         | Year of the flood                    |
| `title`                | string          | Human-readable title                 |
| `affected_provinces`   | string[]        | List of province names               |
| `affected_districts`   | string[]        | List of district names               |
| `peak_month`           | string          | Month(s) of peak flooding            |
| `estimated_affected`   | integer         | Number of people affected            |
| `damage_usd_billion`   | number \| null  | Estimated economic damage (USD B)    |
| `description`          | string          | Narrative description                |

**Errors**

| Status | Reason |
|--------|--------|
| `503`  | Database unavailable |

---

## 8. Admin — Protected

### `POST /zones/admin/refresh-zones`

Force an immediate full zone recomputation, bypassing the 3-hour cache TTL.

**When to use:** After updating the ML model artifact, after a major weather event, or for debugging.

**Authentication:** Pass your admin key in the `X-Api-Key` header (set `ADMIN_API_KEY` in `backend/.env`).

**Request**
```
POST /api/v1/zones/admin/refresh-zones
X-Api-Key: your-secret-admin-key
```

**Response `200 OK` — triggered**
```json
{
  "status": "triggered",
  "message": "Zone recomputation started in background."
}
```

**Response `200 OK` — already running**
```json
{
  "status": "already_computing",
  "message": "A computation is already running."
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `401`  | Invalid or missing `X-Api-Key` |
| `503`  | ADMIN_API_KEY not configured, or model not loaded |

---

## 9. Planned: Authentication & Users

> Status: **Not yet implemented.** The design below matches the planned Supabase Auth + FastAPI JWT architecture.

### Auth Flow Overview

```
1. POST /auth/register       → Create account (email + password)
2. POST /auth/login          → Returns JWT access_token + refresh_token
3. POST /auth/refresh        → Exchange refresh_token for new access_token
4. POST /auth/logout         → Invalidate refresh_token
5. GET  /auth/me             → Returns current user profile
6. PATCH /auth/me            → Update name / avatar
7. DELETE /auth/me           → Delete account
8. POST /auth/forgot-password → Send password reset email
9. POST /auth/reset-password  → Confirm reset with token
```

---

### `POST /auth/register`

Create a new account.

**Request Body**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Ahmed Khan"
}
```

**Response `201 Created`**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "full_name": "Ahmed Khan",
  "created_at": "2026-05-17T10:00:00+00:00",
  "message": "Account created. Check your email to verify."
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `409`  | Email already registered |
| `422`  | Weak password or invalid email format |

---

### `POST /auth/login`

Authenticate and receive tokens.

**Request Body**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response `200 OK`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "uuid-here",
    "email": "user@example.com",
    "full_name": "Ahmed Khan",
    "role": "user"
  }
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `401`  | Wrong email or password |
| `403`  | Email not verified |

---

### `POST /auth/refresh`

Get a new access token using a refresh token.

**Request Body**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200 OK`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

---

### `POST /auth/logout`

Invalidate the current session.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{ "message": "Logged out successfully." }
```

---

### `GET /auth/me`

Return the authenticated user's profile.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "full_name": "Ahmed Khan",
  "avatar_url": null,
  "role": "user",
  "created_at": "2026-05-17T10:00:00+00:00",
  "last_login": "2026-05-17T12:00:00+00:00"
}
```

---

### `PATCH /auth/me`

Update the user's own profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body** (all fields optional)
```json
{
  "full_name": "Ahmed Ali Khan",
  "avatar_url": "https://cdn.example.com/avatars/user.jpg"
}
```

**Response `200 OK`**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "full_name": "Ahmed Ali Khan",
  "avatar_url": "https://cdn.example.com/avatars/user.jpg"
}
```

---

### `DELETE /auth/me`

Permanently delete the user's account and all their data.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{ "message": "Account deleted." }
```

---

### `POST /auth/forgot-password`

Send a password reset link to the user's email.

**Request Body**
```json
{ "email": "user@example.com" }
```

**Response `200 OK`** (always returns 200 regardless of whether email exists, to prevent enumeration)
```json
{ "message": "If that email is registered, a reset link has been sent." }
```

---

### `POST /auth/reset-password`

Set a new password using the token from the reset email.

**Request Body**
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass456!"
}
```

**Response `200 OK`**
```json
{ "message": "Password updated successfully." }
```

---

## 10. Planned: Education Module

> Status: **Not yet implemented.** Covers the "How Floods Work" section with articles, quizzes, and historical flood events.

### Education Articles

---

### `GET /education/articles`

List all published education articles. No authentication required.

**Query Parameters**

| Parameter  | Type    | Required | Description                                  |
|------------|---------|----------|----------------------------------------------|
| `category` | string  | No       | Filter by category (see below)               |
| `limit`    | integer | No       | Max results (default: 20, max: 100)          |
| `offset`   | integer | No       | Pagination offset (default: 0)               |

**Category values:** `hydrology` | `climate` | `disaster-risk` | `pakistan-history` | `preparedness`

**Request**
```
GET /api/v1/education/articles?category=hydrology&limit=10
```

**Response `200 OK`**
```json
{
  "total": 24,
  "articles": [
    {
      "article_id": "art-001",
      "title": "How Floods Form: The Water Cycle Explained",
      "slug": "how-floods-form",
      "category": "hydrology",
      "summary": "A plain-language guide to how rainfall, runoff, and river levels combine to produce flooding.",
      "reading_time_minutes": 5,
      "published_at": "2026-05-01T00:00:00+00:00",
      "author": "PakFlood AI Team",
      "thumbnail_url": "https://cdn.example.com/articles/water-cycle.jpg",
      "tags": ["water-cycle", "rivers", "rainfall"]
    }
  ]
}
```

---

### `GET /education/articles/{slug}`

Fetch the full content of one article.

**Request**
```
GET /api/v1/education/articles/how-floods-form
```

**Response `200 OK`**
```json
{
  "article_id": "art-001",
  "title": "How Floods Form: The Water Cycle Explained",
  "slug": "how-floods-form",
  "category": "hydrology",
  "content_md": "## The Water Cycle\n\nWater evaporates from oceans and lakes...",
  "summary": "A plain-language guide...",
  "reading_time_minutes": 5,
  "published_at": "2026-05-01T00:00:00+00:00",
  "author": "PakFlood AI Team",
  "thumbnail_url": "https://cdn.example.com/articles/water-cycle.jpg",
  "tags": ["water-cycle", "rivers", "rainfall"],
  "related_articles": ["monsoon-and-pakistan", "river-basins-indus"]
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `404`  | Article not found |

---

### `POST /education/articles` *(Admin only)*

Create a new education article.

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body**
```json
{
  "title": "Understanding Flash Floods in KPK",
  "slug": "flash-floods-kpk",
  "category": "pakistan-history",
  "content_md": "## Flash Floods in KPK\n\nKhyber Pakhtunkhwa's steep terrain...",
  "summary": "How topography and monsoon combine to make KPK vulnerable.",
  "reading_time_minutes": 7,
  "author": "Dr. Arif Khan",
  "thumbnail_url": "https://cdn.example.com/articles/kpk-flood.jpg",
  "tags": ["kpk", "flash-floods", "terrain"]
}
```

**Response `201 Created`**
```json
{
  "article_id": "art-025",
  "slug": "flash-floods-kpk",
  "title": "Understanding Flash Floods in KPK",
  "created_at": "2026-05-17T10:00:00+00:00"
}
```

---

### `PATCH /education/articles/{article_id}` *(Admin only)*

Update an existing article.

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body** (all fields optional)
```json
{
  "title": "Updated title",
  "content_md": "Updated content...",
  "tags": ["new-tag"]
}
```

**Response `200 OK`**
```json
{
  "article_id": "art-025",
  "title": "Updated title",
  "updated_at": "2026-05-17T11:00:00+00:00"
}
```

---

### `DELETE /education/articles/{article_id}` *(Admin only)*

Delete an article.

**Headers:** `Authorization: Bearer <admin_token>`

**Response `200 OK`**
```json
{ "message": "Article deleted." }
```

---

### User Progress (Requires Auth)

### `GET /education/progress`

Get the authenticated user's reading progress across all articles.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{
  "articles_read": 3,
  "total_articles": 24,
  "progress_percent": 12.5,
  "last_read": {
    "article_id": "art-001",
    "slug": "how-floods-form",
    "title": "How Floods Form",
    "read_at": "2026-05-17T09:00:00+00:00"
  }
}
```

---

### `POST /education/progress/{article_id}`

Mark an article as read.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{
  "article_id": "art-001",
  "read_at": "2026-05-17T12:00:00+00:00"
}
```

---

## 11. Planned: Gemini Learning Bot

> Status: **Not yet implemented.** The Learning Bot answers questions about flood science, hydrology, climate, and Pakistan-specific flood history. It uses Google Gemini's API under the hood. It is NOT a risk prediction tool — it explains concepts and directs users to official sources.

### System Prompt (Excerpt)

The backend will configure Gemini with a system prompt that:
- Restricts answers to flood science, hydrology, climate, and Pakistan geography
- Always ends answers with a link or reference to PMD, NDMA, or PDMA
- Refuses to make real-time emergency predictions (redirects to the map)
- Responds in simple English (or Urdu if requested)

---

### `POST /chat/learn`

Ask the Learning Bot a question about floods, climate, or hydrology.

**Authentication:** Optional. Unauthenticated users can ask questions but history is not saved.

**Request Body**
```json
{
  "message": "Why does Pakistan flood every monsoon season?",
  "session_id": "optional-uuid-to-continue-a-session",
  "language": "en"
}
```

**Request Fields**

| Field        | Type   | Required | Description                                     |
|--------------|--------|----------|-------------------------------------------------|
| `message`    | string | Yes      | The user's question (max 1000 characters)       |
| `session_id` | string | No       | Continue a previous conversation                |
| `language`   | string | No       | `"en"` (default) or `"ur"` for Urdu response   |

**Response `200 OK`**
```json
{
  "session_id": "uuid-here",
  "answer": "Pakistan sits at the confluence of the South Asian Monsoon and the Himalayan snowmelt system...",
  "sources": [
    {
      "name": "Pakistan Meteorological Department",
      "url": "https://www.pmd.gov.pk"
    },
    {
      "name": "NDMA Pakistan",
      "url": "https://www.ndma.gov.pk"
    }
  ],
  "related_articles": ["monsoon-and-pakistan", "indus-river-basin"],
  "disclaimer": "This is educational content only. For real-time flood warnings consult PMD, NDMA, and PDMA."
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `400`  | Message is empty or exceeds 1000 characters |
| `422`  | Message is off-topic (e.g. not about floods or climate) |
| `503`  | Gemini API unavailable |

---

### `GET /chat/learn/sessions`

List all past learning chat sessions for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{
  "sessions": [
    {
      "session_id": "uuid-here",
      "title": "Why does Pakistan flood every monsoon?",
      "message_count": 5,
      "created_at": "2026-05-16T08:00:00+00:00",
      "last_message_at": "2026-05-16T08:12:00+00:00"
    }
  ]
}
```

---

### `GET /chat/learn/sessions/{session_id}`

Retrieve the full message history for one chat session.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{
  "session_id": "uuid-here",
  "messages": [
    {
      "role": "user",
      "content": "Why does Pakistan flood every monsoon season?",
      "created_at": "2026-05-16T08:00:00+00:00"
    },
    {
      "role": "assistant",
      "content": "Pakistan sits at the confluence of the South Asian Monsoon...",
      "sources": ["pmd.gov.pk", "ndma.gov.pk"],
      "created_at": "2026-05-16T08:00:02+00:00"
    }
  ]
}
```

---

### `DELETE /chat/learn/sessions/{session_id}`

Delete a learning chat session and all its messages.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{ "message": "Session deleted." }
```

---

## 12. Planned: Help Bot

> Status: **Not yet implemented.** The Help Bot assists users in navigating the PakFlood AI dashboard — how to use the map, what the risk levels mean, how to read zone data, and how to find resources. It does NOT answer general flood science questions (that is the Learning Bot's job).

### System Prompt (Excerpt)

The backend will configure Gemini with a system prompt that:
- Only answers questions about how to use the PakFlood AI platform
- Explains what each map layer, KPI card, and panel does
- Explains what risk levels and confidence scores mean in the context of this tool
- Directs all emergency-related questions to PMD/NDMA/PDMA
- Refuses to speculate on future flood events

---

### `POST /chat/help`

Ask the Help Bot how to use the dashboard.

**Request Body**
```json
{
  "message": "What does the Severe risk colour mean on the map?",
  "session_id": "optional-uuid",
  "context": {
    "current_page": "map",
    "selected_district": "PK-PB-LHR"
  }
}
```

**Request Fields**

| Field           | Type   | Required | Description                                          |
|-----------------|--------|----------|------------------------------------------------------|
| `message`       | string | Yes      | User's question (max 500 characters)                 |
| `session_id`    | string | No       | Continue a previous help session                     |
| `context`       | object | No       | Current page context to make answers more relevant   |
| `context.current_page` | string | No | Which page/view the user is on (`"map"`, `"education"`, `"profile"`) |
| `context.selected_district` | string | No | `district_id` currently selected on the map |

**Response `200 OK`**
```json
{
  "session_id": "uuid-here",
  "answer": "The **Severe** risk colour (red) means the AI model predicts a flood probability above 75% for that area. This is based on current weather data — it is not an official government warning. For real emergencies, contact NDMA at 1700.",
  "quick_actions": [
    {
      "label": "View Lahore risk details",
      "action": "select_district",
      "payload": "PK-PB-LHR"
    },
    {
      "label": "Open emergency contacts",
      "action": "open_panel",
      "payload": "emergency"
    }
  ],
  "disclaimer": "Always verify risk information with PMD, NDMA, and PDMA for real emergencies."
}
```

**Response Fields**

| Field           | Type     | Description                                                   |
|-----------------|----------|---------------------------------------------------------------|
| `answer`        | string   | Markdown-formatted answer (safe to render)                    |
| `quick_actions` | array    | Optional clickable actions the frontend can wire up           |
| `disclaimer`    | string   | Safety disclaimer (always present)                            |

---

### `GET /chat/help/sessions`

List the authenticated user's past help sessions.

**Headers:** `Authorization: Bearer <token>`

**Response:** Same shape as `/chat/learn/sessions`.

---

### `GET /chat/help/sessions/{session_id}`

Get full message history for a help session.

**Headers:** `Authorization: Bearer <token>`

**Response:** Same shape as `/chat/learn/sessions/{session_id}`.

---

### `DELETE /chat/help/sessions/{session_id}`

Delete a help session.

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`**
```json
{ "message": "Session deleted." }
```

---

## 13. Error Codes

All error responses follow this shape:

```json
{
  "detail": "Human-readable error description"
}
```

| HTTP Status | Meaning                                                    |
|-------------|------------------------------------------------------------|
| `400`       | Bad request — malformed input                              |
| `401`       | Unauthorized — missing or invalid token                    |
| `403`       | Forbidden — valid token but insufficient permissions       |
| `404`       | Resource not found                                         |
| `409`       | Conflict — e.g. email already registered                   |
| `422`       | Validation error — query param or body field invalid       |
| `502`       | Upstream API error — Open-Meteo or Gemini unreachable      |
| `503`       | Service unavailable — database down or model not loaded    |

---

## 14. Frontend Implementation Guide

### Calling the search endpoint

```typescript
// api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// Search districts — returns boundary + risk summary
export async function searchDistricts(q: string) {
  if (q.length < 2) return [];
  return apiFetch<DistrictSearchResult[]>(`/districts/search?q=${encodeURIComponent(q)}`) ?? [];
}
```

### Rendering zone GeoJSON on a Leaflet map

```typescript
import { GeoJSON } from "react-leaflet";
import { riskColor } from "@/lib/risk-colors";

// In your component:
const [zones, setZones] = useState(null);

useEffect(() => {
  fetch(`${API_BASE}/zones/geojson`)
    .then(r => r.json())
    .then(setZones);
}, []);

// In JSX:
{zones && (
  <GeoJSON
    data={zones}
    pointToLayer={(feature, latlng) =>
      L.circleMarker(latlng, {
        radius: 8,
        fillColor: riskColor(feature.properties.risk_level),
        fillOpacity: 0.7,
        color: "transparent",
      })
    }
  />
)}
```

### Calling the Learning Bot

```typescript
export async function askLearningBot(message: string, sessionId?: string) {
  const res = await fetch(`${API_BASE}/chat/learn`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Bot unavailable");
  return res.json();
}
```

### Showing the safety disclaimer

**Never** display a risk level without the disclaimer. Use a shared component:

```tsx
// SafetyDisclaimer.tsx
export function SafetyDisclaimer() {
  return (
    <div className="text-xs text-slate-400 border-t border-slate-800 px-4 py-2">
      PakFlood AI is an educational decision-support prototype.
      Always consult official{" "}
      <a href="https://www.pmd.gov.pk" target="_blank" rel="noopener noreferrer" className="underline">PMD</a>,{" "}
      <a href="https://www.ndma.gov.pk" target="_blank" rel="noopener noreferrer" className="underline">NDMA</a>, and{" "}
      <a href="https://www.pdma.gop.pk" target="_blank" rel="noopener noreferrer" className="underline">PDMA</a>{" "}
      sources for real emergency decisions.
    </div>
  );
}
```

### TypeScript interfaces for all planned response types

```typescript
// auth
interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
}

interface UserProfile {
  user_id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  role: "user" | "admin";
  created_at: string;
}

// education
interface Article {
  article_id: string;
  title: string;
  slug: string;
  category: string;
  content_md?: string;
  summary: string;
  reading_time_minutes: number;
  published_at: string;
  author: string;
  thumbnail_url: string | null;
  tags: string[];
}

// learning bot
interface BotResponse {
  session_id: string;
  answer: string;
  sources: Array<{ name: string; url: string }>;
  related_articles: string[];
  disclaimer: string;
}

// help bot
interface HelpBotResponse {
  session_id: string;
  answer: string;
  quick_actions: Array<{
    label: string;
    action: "select_district" | "open_panel" | "navigate";
    payload: string;
  }>;
  disclaimer: string;
}
```
