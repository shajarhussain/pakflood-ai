import pytest
from fastapi.testclient import TestClient

from app.core.config import settings as _settings
# Legacy tests use a fully mocked DisasterRiskService and never touch the v3
# artifact path. We disable strict v3 fail-loud mode for the legacy suite by
# pinning MODEL_MODE to a non-real-prediction value BEFORE app/main is imported.
# The dedicated v3-strict tests pin MODEL_MODE="real_prediction" explicitly.
_settings.MODEL_MODE = "legacy_demo"

from app.main import app  # noqa: E402 — must follow the MODEL_MODE override
from app.services.disaster_risk_service import get_disaster_risk_service  # noqa: E402
from app.services.source_registry_service import get_source_registry  # noqa: E402
from app.schemas.boundary import LocationSearchResult  # noqa: E402
from app.schemas.risk import RiskResponse, DISCLAIMER  # noqa: E402
from app.schemas.flood_event import FloodEventResponse  # noqa: E402
from app.schemas.data_source import DataSourceResponse  # noqa: E402


# ---------------------------------------------------------------------------
# Mock DisasterRiskService — no real DB
# ---------------------------------------------------------------------------

class MockDisasterRiskService:
    def get_all_boundaries(self) -> dict:
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"district_id": "PK-SD-SKR", "name": "Sukkur", "province": "Sindh"},
                    "geometry": {"type": "Polygon", "coordinates": [[[68.3, 27.4], [69.3, 27.5], [69.2, 28.1], [68.4, 28.0], [68.3, 27.4]]]},
                },
                {
                    "type": "Feature",
                    "properties": {"district_id": "PK-SD-JCB", "name": "Jacobabad", "province": "Sindh"},
                    "geometry": {"type": "Polygon", "coordinates": [[[68.0, 28.0], [68.9, 28.1], [68.7, 28.9], [67.8, 28.7], [68.0, 28.0]]]},
                },
                {
                    "type": "Feature",
                    "properties": {"district_id": "PK-BL-NAS", "name": "Naseerabad", "province": "Balochistan"},
                    "geometry": {"type": "Polygon", "coordinates": [[[68.0, 28.5], [69.0, 28.6], [68.8, 29.3], [67.9, 29.1], [68.0, 28.5]]]},
                },
            ],
        }

    def get_risk_by_boundary(self, boundary_id: str) -> RiskResponse:
        _data = {
            "PK-SD-SKR": RiskResponse(
                district_id="PK-SD-SKR", name="Sukkur", province="Sindh",
                risk_score=0.82, risk_level="High", confidence=0.74,
                top_factors=["7-day rainfall anomaly", "near Indus floodplain", "historical flood frequency"],
                disclaimer=DISCLAIMER,
            ),
            "PK-SD-JCB": RiskResponse(
                district_id="PK-SD-JCB", name="Jacobabad", province="Sindh",
                risk_score=0.91, risk_level="Severe", confidence=0.81,
                top_factors=["extreme monsoon rainfall", "flat terrain", "2022 flood history"],
                disclaimer=DISCLAIMER,
            ),
        }
        if boundary_id not in _data:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"No risk data found for district '{boundary_id}'")
        return _data[boundary_id]

    def get_flood_events(self, district_name: str | None = None) -> list[FloodEventResponse]:
        all_events = [
            FloodEventResponse(
                id="evt-2010-super-floods", year=2010, title="2010 Pakistan Super Floods",
                affected_provinces=["KPK", "Punjab", "Sindh", "Balochistan"],
                affected_districts=["Nowshera", "Charsadda", "Sukkur", "Larkana", "Jacobabad", "Naseerabad"],
                peak_month="August", estimated_affected=20000000,
                description="One of the worst floods in Pakistan's history.",
            ),
            FloodEventResponse(
                id="evt-2022-record-floods", year=2022, title="2022 Pakistan Catastrophic Floods",
                affected_provinces=["Sindh", "Balochistan", "KPK", "Punjab"],
                affected_districts=["Jacobabad", "Sukkur", "Larkana", "Naseerabad"],
                peak_month="August", estimated_affected=33000000, damage_usd_billion=14.9,
                description="Unprecedented floods affecting 1/3 of Pakistan.",
            ),
        ]
        if district_name:
            return [e for e in all_events if district_name in e.affected_districts]
        return all_events

    def persist_model_run(self, assessments: list) -> int:
        """Mock persistence — returns count without touching DB."""
        return len(assessments)

    def search_locations(self, q: str) -> list[LocationSearchResult]:
        _all = [
            LocationSearchResult(district_id="PK-SD-SKR", name="Sukkur", province="Sindh",
                                 center=[27.7, 68.86], risk_level="High"),
            LocationSearchResult(district_id="PK-SD-JCB", name="Jacobabad", province="Sindh",
                                 center=[28.28, 68.43], risk_level="Severe"),
        ]
        return [r for r in _all if q.lower() in r.name.lower()]


# ---------------------------------------------------------------------------
# Mock SourceRegistryService — pre-canned adapter statuses
# ---------------------------------------------------------------------------

class MockSourceRegistryService:
    def to_data_source_responses(self) -> list[DataSourceResponse]:
        return [
            DataSourceResponse(
                id="imerg", name="NASA IMERG (GPM)", status="stale",
                latency_hours=12, latency_ms=1.2,
                description="Satellite precipitation estimates.",
                features_created=["rainfall_1d_mm", "rainfall_7d_mm"],
                circuit_state="closed",
            ),
            DataSourceResponse(
                id="chirps", name="CHIRPS Historical Rainfall", status="stale",
                latency_hours=720, latency_ms=0.8,
                description="Historical rainfall baseline.",
                features_created=["historical_mean_mm", "rainfall_percentile"],
                circuit_state="closed",
            ),
            DataSourceResponse(
                id="glofas", name="GloFAS River Discharge", status="stale",
                latency_hours=24, latency_ms=1.5,
                description="River discharge forecasts.",
                features_created=["discharge_m3s"],
                circuit_state="closed",
            ),
            DataSourceResponse(
                id="ffd", name="PMD / FFD Bulletin", status="stale",
                latency_hours=6, latency_ms=0.5,
                description="PMD official bulletins.",
                features_created=["ffd_category"],
                circuit_state="closed",
            ),
            DataSourceResponse(
                id="reliefweb", name="ReliefWeb Articles", status="fresh",
                latency_hours=1, latency_ms=250.0,
                description="Humanitarian reports.",
                features_created=["article_count", "latest_headline"],
                circuit_state="closed",
            ),
        ]


def _mock_drs():
    return MockDisasterRiskService()


def _mock_registry():
    return MockSourceRegistryService()


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    # Existing test suite asserts legacy 200 responses with mocked data.
    # The v3 strict mode is enabled by default in production, so for the
    # legacy tests we relax MODEL_MODE here. New v3 fail-loud tests in
    # test_v3_fail_loud.py explicitly set MODEL_MODE="real_prediction".
    from app.core.config import settings
    monkeypatch.setattr(settings, "MODEL_MODE", "legacy_demo")
    app.dependency_overrides[get_disaster_risk_service] = _mock_drs
    app.dependency_overrides[get_source_registry] = _mock_registry
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
