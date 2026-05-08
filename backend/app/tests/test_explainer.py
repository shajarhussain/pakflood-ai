"""
Phase 5 — pure unit tests for FloodExplainer.

No HTTP client, no mocking required — the explainer is a pure class.
"""

import pytest

from app.hazards.flood.explainer import FloodExplainer, _humanise_factor
from app.schemas.data_source import DataSourceResponse
from app.schemas.flood_event import FloodEventResponse
from app.schemas.risk import RiskExplanation

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_sources(statuses: list[tuple[str, str]]) -> list[DataSourceResponse]:
    return [
        DataSourceResponse(
            id=sid, name=name, status=status,
            description="test", features_created=[],
        )
        for sid, name, status in [
            (s[0], s[0].upper(), s[1]) for s in statuses
        ]
    ]


def _make_events(districts: list[str]) -> list[FloodEventResponse]:
    return [
        FloodEventResponse(
            id="evt-2022",
            year=2022,
            title="2022 Catastrophic Floods",
            affected_provinces=["Sindh"],
            affected_districts=districts,
            peak_month="August",
            estimated_affected=33_000_000,
            damage_usd_billion=14.9,
            description="Unprecedented floods.",
        ),
        FloodEventResponse(
            id="evt-2010",
            year=2010,
            title="2010 Pakistan Super Floods",
            affected_provinces=["Sindh", "Punjab"],
            affected_districts=districts + ["Nowshera"],
            peak_month="August",
            estimated_affected=20_000_000,
            description="One of the worst floods.",
        ),
    ]


def _explain(
    risk_level: str = "High",
    district_name: str = "Sukkur",
    top_factors: list[str] | None = None,
    flood_events: list[FloodEventResponse] | None = None,
    source_statuses: list[DataSourceResponse] | None = None,
    reliefweb_articles: list[dict] | None = None,
    confidence: float = 0.74,
) -> RiskExplanation:
    explainer = FloodExplainer()
    return explainer.explain(
        district_id="PK-SD-SKR",
        district_name=district_name,
        risk_level=risk_level,
        confidence=confidence,
        top_factors=["rainfall_7d_mm", "distance_to_river_km"] if top_factors is None else top_factors,
        model_version="flood-baseline-v1",
        flood_events=flood_events or [],
        source_statuses=source_statuses or [],
        reliefweb_articles=reliefweb_articles,
    )


# ── 7-field completeness ──────────────────────────────────────────────────────

class TestExplanationCompleteness:
    def test_returns_risk_explanation_schema(self):
        result = _explain()
        assert isinstance(result, RiskExplanation)

    def test_all_7_fields_present(self):
        result = _explain()
        assert result.risk_level != ""
        assert isinstance(result.main_causes, list)
        assert isinstance(result.historical_evidence, list)
        assert isinstance(result.suggested_actions, list)
        assert isinstance(result.confidence, float)
        assert isinstance(result.data_sources, list)
        assert result.disclaimer != ""

    def test_all_7_fields_non_empty(self):
        result = _explain()
        assert len(result.main_causes) >= 1
        assert len(result.historical_evidence) >= 1
        assert len(result.suggested_actions) >= 1
        assert len(result.data_sources) >= 1


# ── Disclaimer ────────────────────────────────────────────────────────────────

class TestDisclaimer:
    def test_disclaimer_always_present(self):
        for level in ["Low", "Moderate", "High", "Severe"]:
            result = _explain(risk_level=level)
            assert result.disclaimer != ""

    def test_disclaimer_contains_educational(self):
        result = _explain()
        assert "educational" in result.disclaimer.lower() or "Educational" in result.disclaimer

    def test_disclaimer_mentions_official_authorities(self):
        result = _explain()
        disclaimer = result.disclaimer
        assert "PMD" in disclaimer or "NDMA" in disclaimer

    def test_disclaimer_does_not_claim_official_warning(self):
        result = _explain()
        assert "official warning from" not in result.disclaimer.lower()
        assert "official government warning" not in result.disclaimer.lower()

    def test_disclaimer_says_not_official(self):
        result = _explain()
        assert "not an official warning" in result.disclaimer.lower()


# ── Confidence ────────────────────────────────────────────────────────────────

class TestConfidence:
    def test_confidence_within_range(self):
        result = _explain(confidence=0.74)
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_clamped_above_one(self):
        result = _explain(confidence=1.5)
        assert result.confidence <= 1.0

    def test_confidence_clamped_below_zero(self):
        result = _explain(confidence=-0.3)
        assert result.confidence >= 0.0

    def test_confidence_preserved_in_range(self):
        result = _explain(confidence=0.65)
        assert result.confidence == pytest.approx(0.65)


# ── Suggested actions ─────────────────────────────────────────────────────────

class TestSuggestedActions:
    def test_low_risk_has_monitoring_actions(self):
        result = _explain(risk_level="Low")
        combined = " ".join(result.suggested_actions).lower()
        assert "monitor" in combined or "pmd" in combined or "ndma" in combined

    def test_moderate_risk_has_preparation_actions(self):
        result = _explain(risk_level="Moderate")
        combined = " ".join(result.suggested_actions).lower()
        assert "emergency" in combined or "evacuation" in combined or "prepare" in combined

    def test_high_risk_has_evacuation_actions(self):
        result = _explain(risk_level="High")
        combined = " ".join(result.suggested_actions).lower()
        assert "evacuation" in combined or "avoid" in combined or "official" in combined

    def test_severe_risk_has_immediate_actions(self):
        result = _explain(risk_level="Severe")
        combined = " ".join(result.suggested_actions).lower()
        assert "evacuate" in combined or "immediately" in combined or "1700" in combined

    def test_all_4_levels_have_different_actions(self):
        results = {level: _explain(risk_level=level) for level in ["Low", "Moderate", "High", "Severe"]}
        action_sets = [tuple(r.suggested_actions) for r in results.values()]
        # All 4 should be distinct
        assert len(set(action_sets)) == 4


# ── Main causes ───────────────────────────────────────────────────────────────

class TestMainCauses:
    def test_causes_from_top_factors(self):
        result = _explain(top_factors=["rainfall_7d_mm", "distance_to_river_km"])
        assert len(result.main_causes) == 2

    def test_no_factors_returns_unavailable(self):
        result = _explain(top_factors=[])
        assert "data unavailable" in " ".join(result.main_causes).lower()

    def test_feature_names_humanised(self):
        result = _explain(top_factors=["rainfall_7d_mm"])
        assert result.main_causes[0] != "rainfall_7d_mm"  # must be human-readable

    def test_humanise_known_feature(self):
        label = _humanise_factor("river_discharge_m3s")
        assert "river" in label.lower() or "discharge" in label.lower()

    def test_humanise_unknown_feature_returns_something(self):
        label = _humanise_factor("some_unknown_feature_xyz")
        assert label != ""


# ── Historical evidence ───────────────────────────────────────────────────────

class TestHistoricalEvidence:
    def test_events_for_matching_district_included(self):
        events = _make_events(["Sukkur", "Jacobabad"])
        result = _explain(district_name="Sukkur", flood_events=events)
        combined = " ".join(result.historical_evidence)
        assert "2022" in combined or "2010" in combined

    def test_events_for_non_matching_district_excluded(self):
        events = _make_events(["Jacobabad"])  # Sukkur NOT in affected_districts
        result = _explain(district_name="Sukkur", flood_events=events)
        assert "data unavailable" in " ".join(result.historical_evidence).lower()

    def test_no_events_returns_unavailable(self):
        result = _explain(flood_events=[])
        assert "data unavailable" in " ".join(result.historical_evidence).lower()

    def test_event_includes_year_and_title(self):
        events = _make_events(["Sukkur"])
        result = _explain(district_name="Sukkur", flood_events=events)
        combined = " ".join(result.historical_evidence)
        assert "2022" in combined
        assert "Catastrophic" in combined or "2022" in combined

    def test_reliefweb_articles_enrich_history(self):
        articles = [
            {"title": "Pakistan flood update", "source": "OCHA", "published_date": "2022-09-01"},
        ]
        result = _explain(flood_events=[], reliefweb_articles=articles)
        combined = " ".join(result.historical_evidence)
        assert "ReliefWeb" in combined or "Pakistan flood update" in combined

    def test_reliefweb_none_does_not_crash(self):
        result = _explain(reliefweb_articles=None)
        assert isinstance(result.historical_evidence, list)


# ── Data sources ──────────────────────────────────────────────────────────────

class TestDataSources:
    def test_sources_from_registry_included(self):
        sources = _make_sources([("imerg", "stale"), ("glofas", "fresh")])
        result = _explain(source_statuses=sources)
        combined = " ".join(result.data_sources)
        assert "IMERG" in combined
        assert "GLOFAS" in combined

    def test_source_status_shown_in_string(self):
        sources = _make_sources([("imerg", "stale")])
        result = _explain(source_statuses=sources)
        assert "stale" in result.data_sources[0].lower() or "Stale" in result.data_sources[0]

    def test_no_sources_returns_unavailable(self):
        result = _explain(source_statuses=[])
        assert "data unavailable" in " ".join(result.data_sources).lower()
