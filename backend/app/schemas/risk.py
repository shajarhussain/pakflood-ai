from pydantic import BaseModel, Field

DISCLAIMER = (
    "PakFlood AI is an educational decision-support prototype. "
    "Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions."
)


# ── Phase 2 schema ────────────────────────────────────────────────────────────

class RiskResponse(BaseModel):
    district_id: str
    name: str
    province: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_factors: list[str]
    forecast_window_hours: int = 72
    model_version: str = "seed-v1.0"
    source_status: dict[str, str] = Field(default_factory=lambda: {"imerg": "mock"})
    disclaimer: str = DISCLAIMER


# ── Phase 4 schemas ───────────────────────────────────────────────────────────

class DistrictRiskAssessment(BaseModel):
    district_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_factors: list[str]
    model_version: str
    source_status: dict[str, str]
    feature_snapshot: dict[str, float] = Field(default_factory=dict)
    rainfall_source: str = "synthetic"  # "synthetic" | "adapter-stale" | "adapter-disabled" | "adapter-fresh"
    disclaimer: str = DISCLAIMER


class RunModelResponse(BaseModel):
    model_version: str
    districts_updated: int
    assessments: list[DistrictRiskAssessment]
    persisted_count: int = 0
    persistence_failed_count: int = 0
    persistence_status: str = "skipped"  # "ok" | "partial" | "failed" | "skipped"
    disclaimer: str = DISCLAIMER


# ── Phase 5 schemas ───────────────────────────────────────────────────────────

class ExplanationCause(BaseModel):
    """Structured cause entry — use text field when embedding in other schemas."""
    text: str
    feature_name: str | None = None


class HistoricalEvidence(BaseModel):
    """Structured historical event reference."""
    text: str
    year: int | None = None
    source: str = "flood event database"


class SuggestedAction(BaseModel):
    """Structured action recommendation."""
    text: str
    urgency: str = "routine"  # routine | urgent | critical


class ExplanationSource(BaseModel):
    """Structured data source with freshness status."""
    name: str
    status: str  # fresh | stale | error | disabled
    description: str = ""


class RiskExplanation(BaseModel):
    """
    7-field flood risk explanation returned by GET /explain-risk/by-boundary/{id}.
    Field names and types match the frontend RiskExplanation TypeScript interface.
    """
    risk_level: str
    main_causes: list[str]
    historical_evidence: list[str]
    suggested_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    data_sources: list[str]
    disclaimer: str


class AlertDraftRequest(BaseModel):
    boundary_id: str


class AlertDraftResponse(BaseModel):
    """
    CAP-like alert draft. This is generated only — never sent anywhere.
    is_draft and is_official clarify this is not an authoritative warning.
    """
    headline: str
    severity: str            # Minor | Moderate | Severe | Extreme
    area: str
    description: str
    instruction: str
    sources: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    disclaimer: str
    is_draft: bool = True
    is_official: bool = False
