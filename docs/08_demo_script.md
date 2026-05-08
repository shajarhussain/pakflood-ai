# PakFlood AI — Demo Script

Audience: technical reviewers, educators, project evaluators.
Duration: ~10 minutes.

---

## Setup (before demo)

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install && npm run dev
# Open http://localhost:3000
```

> DB optional: tests and frontend mock work without it.
> To use the real DB: `docker-compose up db` then `python -m app.scripts.seed` from `backend/`.

---

## Step 1 — Map overview (1 min)

- Open [http://localhost:3000](http://localhost:3000)
- Point out: dark map, district polygons coloured by flood risk level
- Safety disclaimer bar at top — always visible
- Left panel: layer controls (Risk Layer ON, Boundaries ON)
- Bottom: historical flood timeline (2010, 2011, 2014, 2022)

**Key message:** Risk is shown as colour + text label + icon — not colour alone.

---

## Step 2 — District selection (2 min)

- Click **Sukkur** district (Sindh, near Indus river — red/High)
- Right panel opens: "Flood Risk — Sukkur · Sindh"
- Show:
  - Risk level (High) + risk score + confidence %
  - Main Causes — from ML feature importance
  - Historical Evidence — 2010 and 2022 flood events
  - Suggested Actions — rule-based by risk level
  - Official Sources — data freshness status
  - Disclaimer — always at the bottom

- Click **Quetta** (Balochistan — high plateau, lower risk)
- Notice different risk level, different causes, different suggested actions

---

## Step 3 — Search (1 min)

- Use search bar (top right): type "Jacobabad"
- Select result — map flies to Jacobabad
- Panel updates with Jacobabad's Severe risk explanation

---

## Step 4 — Historical timeline (1 min)

- Click **2022** in the bottom timeline
- Districts affected in 2022 highlight on the map
- Click **2010** — different district set highlighted

---

## Step 5 — Data sources panel (30 sec)

- Left panel, bottom: "Data Sources"
- Show: ReliefWeb (fresh dot), IMERG/GloFAS/FFD (stale dot)
- Explain: live circuit breaker architecture; stubs show as stale

---

## Step 6 — API walkthrough (3 min)

Open browser or use curl:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Risk for Sukkur
curl http://localhost:8000/api/v1/risk/by-boundary/PK-SD-SKR

# 7-field explanation
curl http://localhost:8000/api/v1/explain-risk/by-boundary/PK-SD-SKR

# Run ML model inference on all 10 districts
curl -X POST http://localhost:8000/api/v1/admin/run-risk-model

# Generate alert draft (never sent)
curl -X POST http://localhost:8000/api/v1/alerts/generate-draft \
  -H "Content-Type: application/json" \
  -d '{"boundary_id": "PK-SD-SKR"}'
```

**Key point for the alert draft:** Response has `"is_draft": true, "is_official": false`. Disclaimer says "NOT SENT — NOT AN OFFICIAL WARNING".

---

## Step 7 — ML model (1 min)

```bash
python ml/training/train_baseline.py
# Shows: AUC-ROC 0.90 (on synthetic test data), top-3 features
```

Explain:
- RandomForest, 200 trees, 300 synthetic training rows
- Synthetic data clearly labelled — not real flood labels
- AUC-ROC is on its own synthetic test split, not real-world validation

---

## Step 8 — Test suite (30 sec)

```bash
cd backend && pytest app/tests/ -q
# → 160 passed

cd frontend && npm test -- --run
# → 36 passed
```

---

## Close

Summarise the engineering architecture:
- Strategy + Adapter + Repository + Facade + Factory + Circuit Breaker + Pipeline
- All flood logic isolated in `backend/app/hazards/flood/`
- Phase 0→5 complete; Phase 6 hardening in progress
- Path to production realism: real IMERG/GloFAS/FFD integration + expert validation + NDMA partnership
