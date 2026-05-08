Review the current codebase for architecture compliance. Check:

1. Flood-specific logic is only in `backend/app/hazards/flood/` — not leaked into services, adapters, or API routes
2. Every external data source has an Adapter class (no raw HTTP calls in services)
3. Every ML model artifact has version, feature_columns, metrics_path, artifact_path
4. Every risk explanation includes confidence, data_sources, disclaimer
5. No flood-specific logic in generic platform code (`core/`, `api/`, `services/`)
6. ADRs updated for any architecture decisions since last review

Report findings and violations.
