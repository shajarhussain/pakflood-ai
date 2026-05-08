# PakFlood AI — Realism and Limitations

## Status

Educational prototype. Not operationally deployed. All risk outputs are for demonstration and engineering learning purposes only.

---

## What the system does

| Capability | Status |
|---|---|
| Pakistan flood map UI (dark, color + icon + label) | ✅ Implemented |
| District-level flood risk scoring | ✅ Baseline RandomForest on synthetic data |
| Source-backed 7-field risk explanation | ✅ Deterministic, rule-based |
| Circuit-breaker adapter layer (5 sources) | ✅ ReliefWeb live; IMERG/CHIRPS/GloFAS/FFD stubs |
| Draft-only alert generation (CAP-like) | ✅ Never sent anywhere |
| Historical flood event overlay (2010–2022) | ✅ Seed data |
| Source freshness badges | ✅ From SourceRegistryService |
| Confidence score shown with every risk output | ✅ Always visible |
| Safety disclaimer on every explanation | ✅ Always present |

---

## What the system does NOT do

| Claim | Reality |
|---|---|
| "Real-time" rainfall data | ❌ IMERG/CHIRPS adapters return stubs with status="stale" |
| Real GloFAS river discharge | ❌ GloFAS adapter is a stub |
| Real PMD/FFD bulletins | ❌ FFD adapter is a stub |
| Official Pakistan government warnings | ❌ Explicitly marked draft-only; disclaimer on every output |
| Full 140+ district coverage | ❌ MVP uses 10 representative districts |
| Validated ML model | ❌ Trained on synthetic data; AUC=0.90 on its own synthetic test set (not real labels) |
| Sentinel-1 flood extent mapping | ❌ Not implemented |
| Real-time alerting | ❌ No send/push capability exists |

---

## Model limitations

- **Training data:** 300 synthetic samples generated from a deterministic risk formula + 15% noise. Not real historical flood labels.
- **Features:** 11 features, all static or stub-dynamic. In production, dynamic features (rainfall, discharge) must come from real adapters.
- **AUC-ROC 0.90:** Measured on the model's own synthetic test split. This is not a real-world accuracy claim.
- **4 risk classes:** Low / Moderate / High / Severe — thresholds chosen for educational clarity, not validated by domain experts.
- **Feature importance top-3:** river_discharge_m3s, rainfall_anomaly_pct, rainfall_7d_mm — these are features that drive the synthetic risk formula, not independently validated drivers.
- **No cross-validation, no temporal split, no out-of-sample evaluation.**

---

## Data source limitations

| Source | What's real | What's a stub |
|---|---|---|
| ReliefWeb | Live API — Pakistan flood articles | — |
| NASA IMERG | Auth-gated GEE API | Entire adapter returns status="stale" |
| CHIRPS | Auth-gated GEE API | Entire adapter returns status="stale" |
| GloFAS | ECMWF copernicus (registration required) | Entire adapter returns status="stale" |
| PMD/FFD | Bulletin scraping (format varies) | Entire adapter returns status="stale" |
| Historical events | Seed JSON (2010, 2011, 2014, 2022) | Not pulled from live DB |

---

## Path to production realism

For this system to approach operational use, the following would be required:

1. **Full district/tehsil dataset** — HDX Pakistan boundaries (140+ districts, tehsil level)
2. **Real historical flood labels** — NDMA/PDMA post-event assessments, UNOCHA GLIDE numbers
3. **CHIRPS/IMERG live integration** — GEE service account with proper auth
4. **GloFAS live integration** — ECMWF API key, Pakistani river reach IDs
5. **Sentinel-1 flood extent** — GEE or Copernicus Data Space, SAR preprocessing
6. **FFD bulletin parsing** — PMD API or structured bulletin format
7. **Expert model validation** — collaboration with PMD, NDMA, FFD, academic partners
8. **Official partnership** before any real alerts — NDMA/PDMA authorization required
9. **Security audit** — production hardening, rate limiting, auth layer
10. **Load/resilience testing** — monsoon-season traffic spikes

---

## Rainfall live mode (Phase 7A)

IMERG and CHIRPS adapters now support an optional live mode, but it is **off by default** and prototype-level only:

| Flag | Default | Effect |
|---|---|---|
| `ENABLE_LIVE_RAINFALL` | `false` | `false` → always use stub; `true` → attempt live fetch |
| `RAINFALL_PROVIDER` | `stub` | `gee` → GEE ImageCollection; `earthdata` → NASA Earthdata API |
| `GEE_PROJECT` | `""` | Required when provider=gee; must have Earth Engine quota |

**Limitations of live mode:**
- GEE and Earthdata paths raise `NotImplementedError` — they are real-data-ready hooks, not functional integrations.
- Any live fetch failure falls back to stub data with `status="stale"`.
- `build_rainfall_features()` in `features.py` can consume live adapter output, but until a real credentials setup is provided, it will always receive stub data.
- `river_discharge_m3s` is never supplied by IMERG; it always falls back to the static stub default (500 m³/s).
- Live CHIRPS provides seasonal climatology (monthly product, 720-hour latency) — not real-time.

**How to apply:** Do not claim live rainfall capability in demos unless GEE credentials are configured and the provider is tested end-to-end.

---

## Safety commitment

Every risk output in this system includes:
- A confidence score (0–1)
- Source freshness status (fresh/stale/error) for each data source
- A mandatory disclaimer: *"Educational prototype. Not an official warning. Follow PMD, FFD, NDMA, PDMA, and local authorities."*
- No claim of official government warning authority

Risk is communicated using **color + text label + icon** — never color alone.
