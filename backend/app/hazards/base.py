from typing import Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class DataSourceSpec:
    source_id: str
    adapter_class: str


@dataclass
class FeatureFrame:
    features: dict
    location_id: str
    time_window_hours: int


@dataclass
class TrainingConfig:
    hazard: str
    version: str
    feature_columns: list[str]


@dataclass
class ModelArtifact:
    version: str
    artifact_path: str
    metrics_path: str
    feature_columns: list[str]


@dataclass
class RiskRequest:
    lat: float
    lon: float
    forecast_hours: int = 72


@dataclass
class RiskAssessment:
    risk_score: float
    risk_level: str
    confidence: float
    top_factors: list[str]
    model_version: str
    source_status: dict[str, str]


@dataclass
class RiskExplanation:
    risk_level: str
    main_causes: list[str]
    historical_evidence: list[str]
    suggested_actions: list[str]
    confidence: float
    data_sources: list[str]
    disclaimer: str


@runtime_checkable
class HazardModule(Protocol):
    hazard_name: str

    def get_required_sources(self) -> list[DataSourceSpec]: ...
    def build_features(self, location: str, time_window: int) -> FeatureFrame: ...
    def train(self, config: TrainingConfig) -> ModelArtifact: ...
    def infer(self, request: RiskRequest) -> RiskAssessment: ...
    def explain(self, assessment: RiskAssessment) -> RiskExplanation: ...
