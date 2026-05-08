# Architecture

## Clean Architecture Layers

```
HTTP Request
    ↓
API Route (FastAPI router — thin, no logic)
    ↓
Service / Facade (business logic, orchestration)
    ↓
Repository (DB access only, SQLAlchemy + GeoAlchemy2)
    ↓
Database (PostgreSQL + PostGIS)

    [parallel path for external data]
Service / Facade
    ↓
Adapter (external API normalization + Circuit Breaker)
    ↓
External API (IMERG, GloFAS, FFD, ReliefWeb, etc.)
```

## Design Patterns

| Pattern | Class / Location |
|---|---|
| Strategy | `FloodPredictionStrategy` in `hazards/flood/model.py` |
| Adapter | `IMERGAdapter`, `CHIRPSAdapter`, etc. in `adapters/` |
| Repository | `RiskRepository`, `FloodEventRepository`, etc. in `repositories/` |
| Facade | `DisasterRiskService` in `services/` |
| Factory | `HazardModuleFactory` in `hazards/factory.py` |
| Pipeline | `feature_pipeline.py` — ingest → validate → features → infer → store |
| Observer/PubSub | `RiskChanged` event → cache invalidation + alert draft |
| Circuit Breaker | Base class in `adapters/base_adapter.py` |
| CQRS-lite | Write: ingestion; Read: optimized map query view |

## HazardModule Protocol

```python
class HazardModule(Protocol):
    hazard_name: str
    def get_required_sources(self) -> list[DataSourceSpec]: ...
    def build_features(self, location, time_window) -> FeatureFrame: ...
    def train(self, config: TrainingConfig) -> ModelArtifact: ...
    def infer(self, request: RiskRequest) -> RiskAssessment: ...
    def explain(self, assessment: RiskAssessment) -> RiskExplanation: ...
```

## Module Boundaries

- `/backend/app/api` — HTTP routes only, no business logic
- `/backend/app/services` — business logic, orchestration
- `/backend/app/repositories` — database access, no HTTP concerns
- `/backend/app/adapters` — external API normalization
- `/backend/app/hazards/flood` — ALL flood-specific code isolated here
- `/backend/app/core` — shared config, logging, errors
- `/frontend` — UI only, no business logic
- `/ml` — notebooks, training scripts, artifacts

## Risk Output Schema

```json
{
  "risk_score": 0.82,
  "risk_level": "High",
  "forecast_window_hours": 72,
  "confidence": 0.74,
  "top_factors": ["7-day rainfall anomaly", "near Indus floodplain", "historical flood frequency"],
  "source_status": {"imerg": "fresh", "glofas": "fresh", "ffd": "stale"},
  "model_version": "baseline-v1.0",
  "disclaimer": "Educational prototype. Consult PMD/FFD/NDMA for official warnings."
}
```
