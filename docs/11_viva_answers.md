# Viva Q&A — PakFlood AI

Prepared answers for likely viva / presentation questions.

---

## Architecture

**Q: Why FastAPI and not Django/Flask?**
FastAPI gives automatic OpenAPI docs, native Pydantic validation, and async support — all critical for a data API that will eventually handle concurrent sensor ingestion. Flask has no built-in validation; Django is too heavy for a pure API service.

**Q: Why the Facade pattern for DisasterRiskService?**
Routes must stay thin. Without a Facade, each route would need to know about repositories, adapters, and the ML strategy — coupling that breaks the moment we add a new hazard module. The Facade is a single dependency injection point that hides all orchestration.

**Q: Why does every adapter inherit a Circuit Breaker?**
External data sources (IMERG, GloFAS, ReliefWeb) fail independently. Without a circuit breaker, one failing source would either crash the whole inference batch or silently return stale data. The circuit breaker tracks failure count, trips at a threshold, waits a recovery timeout, and then probes again — all without the caller knowing.

**Q: What does "CQRS-lite" mean here?**
Full CQRS uses separate write and read models. Here it means: ingestion pipelines write to `risk_snapshots`; map reads use an optimized query on the latest snapshot per district. No separate read database — just a discipline of keeping write and read paths separate in code.

---

## ML Model

**Q: Why RandomForest and not a neural network?**
RandomForest gives interpretable feature importances (SHAP-equivalent), trains in seconds on the synthetic 300-row dataset, and degrades gracefully on small data. A neural network would overfit immediately on 300 rows. The architecture allows swapping in XGBoost or a neural model later without changing the `HazardModule` interface.

**Q: Why synthetic training data?**
Real labeled flood risk data at district level for Pakistan is not publicly available in a form suitable for supervised learning. The synthetic data is seeded from realistic ranges (from NDMA historical reports), and the model is clearly labeled as "educational prototype." AUC-ROC of ~0.90 is on the synthetic test split — not a real-world accuracy claim.

**Q: How does the model use IMERG/CHIRPS/GloFAS?**
At inference time (not training time): IMERG provides 1d/3d/7d rainfall totals; CHIRPS provides the rainfall anomaly percentile; GloFAS provides river discharge. These override the static synthetic features via a layered merge: `{**static, **imerg, **chirps, **glofas}`. If an adapter fails, its features are simply absent from the merge — the model falls back to static values.

**Q: What are SHAP values doing here?**
The production SHAP library is not used. Instead, `FloodPredictionStrategy._ml_infer()` extracts feature importances from the trained RandomForest and labels the top-3 as "top factors" in the risk assessment. This is a lightweight SHAP-like explanation — honest about what it is.

---

## Data Sources

**Q: Which adapters are live and which are stubs?**
ReliefWeb is live (free public API). IMERG, CHIRPS, GloFAS, and FFD are stubs returning `status="stale"` synthetic data. Live mode for IMERG/CHIRPS requires a GEE service account; GloFAS requires a CDS API key. The `ENABLE_LIVE_RAINFALL` config flag gates live mode — stub mode is safe for demos.

**Q: What happens if all adapters fail simultaneously?**
Each adapter's circuit breaker returns `status="error"` without raising. The feature builders (`build_rainfall_features`, `build_chirps_anomaly`, `build_glofas_discharge`) all return `{}` on error. The merged feature dict contains only static features. `rainfall_source` is set to `"synthetic"`. Inference still produces a valid assessment.

**Q: Why is `status="disabled"` different from `status="stale"`?**
`stale` means "data is from a stub but structurally valid." `disabled` means "live mode was attempted but a required config (API key, credentials) is missing — the system fell back to stub data with a warning." The distinction tells operators whether the system is running as intended or in a degraded configuration.

---

## Safety & Ethics

**Q: How do you ensure the system never claims to be an official warning?**
Three layers: (1) every `RiskAssessment` and `RiskExplanation` response includes a `disclaimer` field set to the project DISCLAIMER constant; (2) the `AlertDraftResponse` schema has `is_draft=True` and `is_official=False` hardcoded; (3) the explanation panel in the frontend renders the disclaimer visibly on every district click.

**Q: What are the real-world limitations of this system?**
See `docs/07_realism_and_limitations.md`. Short version: synthetic training data, 10-district coverage, no real-time ingestion, no SMS/push alerting, rule-based explanations (no actual LLM), stub adapters in default mode. The system is a decision-support prototype — not a replacement for PMD, NDMA, or PDMA.

**Q: Who is the intended user?**
District-level emergency coordinators and humanitarian aid planners who need a synthesized view of flood risk across multiple data sources. The system surfaces information that would otherwise require checking 3–5 separate agency portals.

---

## Testing

**Q: How many tests and what coverage?**
~160+ backend pytest tests covering: circuit breaker state machine, adapter normalization, feature engineering pipeline, ML inference (rule-based and model-based), admin endpoint with all adapter combinations, risk endpoint schemas. ~36 frontend Vitest tests. No live DB required for any test — MockDisasterRiskService is injected via FastAPI dependency override.

**Q: How do you test adapter failure without hitting real APIs?**
`patch("app.api.v1.admin.IMERGAdapter")` replaces the class constructor. The mock returns a pre-built `AdapterResult(status="disabled", data=[])`. The test then asserts the endpoint still returns 200 with correct `rainfall_source` labels and score ranges. This is the same pattern as ReliefWeb's `patch("httpx.Client")` test.

**Q: How do you prevent test-time DB dependency?**
`conftest.py` has an `autouse=True` fixture that overrides `get_disaster_risk_service` with `MockDisasterRiskService`. This means every test — including admin endpoint tests — uses the mock without any DB connection. The mock's `persist_model_run` returns `len(assessments)` without touching PostgreSQL.

---

## Future work

**Q: How would you add a new hazard (e.g., heatwave)?**
Create `backend/app/hazards/heatwave/` with `model.py`, `features.py`, `rules.py`, `explainer.py`. Implement the `HazardModule` Protocol. Register the module in `HazardModuleFactory`. Add a new adapter for the relevant data source. No existing code needs to change.

**Q: How would you deploy this to production?**
`docker-compose up` for local. For cloud: backend → Cloud Run (Dockerfile in `backend/`), frontend → Vercel (`vercel.json`), DB → Cloud SQL/Supabase with `alembic upgrade head`. CI pipeline in `infra/ci/.github/workflows/ci.yml` runs lint → test → build → bandit → docker build on every push.
