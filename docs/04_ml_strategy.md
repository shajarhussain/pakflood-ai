# ML Strategy

## Three ML Layers

| Layer | Question | MVP Model | Advanced Model |
|---|---|---|---|
| A. Susceptibility | Where is this area naturally flood-prone? | RandomForest / XGBoost | Spatial ensemble + catchment features |
| B. Short-term forecast | Will risk rise in next 24–72h? | XGBoost with rainfall/discharge time-windows | LSTM, Temporal Fusion Transformer |
| C. Satellite flood extent | Where is water visible now? | Sentinel-1 threshold/change detection in GEE | U-Net / Nested U-Net for SAR segmentation |

## Why RandomForest/XGBoost First

- Explainable (feature importance, SHAP)
- Easier to test and validate
- Suitable for tabular geospatial features
- Supported by Pakistan-specific flood susceptibility research (Waleed et al. 2025; Rahman et al. 2025)

## Model Versioning Requirements

Every trained model must record:
- `version` — semantic version string (e.g. `baseline-v1.0`)
- `feature_columns` — ordered list of input features
- `training_date` — ISO 8601 timestamp
- `metrics_path` — path to `metrics_report.json`
- `artifact_path` — path to serialized model file

## Explainability

Every prediction must include:
- Risk score (float 0–1)
- Risk level (Low/Moderate/High/Severe)
- Confidence score (float 0–1)
- Top 3–5 contributing factors (SHAP values or feature importance)
- Data freshness per source
- Model version
- Disclaimer (never claim official government warning status)

## Quality Gates (Phase 4)

- Training script runs to completion
- AUC-ROC > 0.65 on held-out test split
- No data leakage (test features not derived from test labels)
- `metrics_report.json` auto-generated after every training run
- SHAP top-3 factors returned in inference response
