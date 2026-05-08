"""
FloodExplainer — deterministic, source-backed flood risk explanation.

Pure class: accepts pre-fetched data, returns a RiskExplanation Pydantic model.
No DB calls, no HTTP calls inside this class — all data must be passed in.
This design makes unit testing trivial and keeps the class side-effect-free.
"""

from __future__ import annotations

from app.schemas.data_source import DataSourceResponse
from app.schemas.flood_event import FloodEventResponse
from app.schemas.risk import RiskExplanation

_DISCLAIMER = (
    "Educational prototype. Not an official warning. "
    "Follow PMD, FFD, NDMA, PDMA, and local authorities."
)

_ACTIONS: dict[str, list[str]] = {
    "Low": [
        "Monitor PMD/FFD/NDMA updates during monsoon season.",
        "Keep an emergency kit (water, documents, medicine) ready.",
        "Stay aware of river levels and local authority alerts.",
    ],
    "Moderate": [
        "Prepare emergency supplies (water, documents, medicine).",
        "Monitor rainfall and river-level announcements closely.",
        "Identify nearest safe locations and evacuation routes.",
        "Avoid unnecessary travel in low-lying or flood-prone areas.",
    ],
    "High": [
        "Avoid low-lying roads and areas near rivers or canals.",
        "Prepare and discuss your evacuation plan with your household.",
        "Protect important documents and electronics from water damage.",
        "Identify nearby high-ground safe locations.",
        "Follow all official NDMA/PDMA advisories (helpline: 1700).",
    ],
    "Severe": [
        "Follow official evacuation instructions immediately.",
        "Move away from floodplain and river areas now.",
        "Do not enter or cross any floodwater — even 15 cm can sweep a person.",
        "Contact local authorities if you need evacuation assistance.",
        "Call NDMA emergency helpline: 1700.",
        "Do not return home until authorities give an official all-clear.",
    ],
}

# Human-readable labels for ML feature names
_FEATURE_LABELS: dict[str, str] = {
    "river_discharge_m3s": "Elevated river discharge (GloFAS forecast)",
    "rainfall_anomaly_pct": "Rainfall anomaly above seasonal average",
    "rainfall_7d_mm": "High 7-day accumulated rainfall",
    "rainfall_3d_mm": "High 3-day accumulated rainfall",
    "rainfall_1d_mm": "High 24-hour rainfall",
    "distance_to_river_km": "Close proximity to major river",
    "elevation_mean_m": "Low elevation — floodplain exposure",
    "historical_flood_count": "History of repeated flooding",
    "population_exposure_score": "High population density in flood zone",
    "slope_mean_deg": "Flat terrain (low drainage gradient)",
    "source_freshness_score": "Data freshness factor",
}


def _humanise_factor(factor: str) -> str:
    """Return a readable cause string from a raw feature or factor name."""
    return _FEATURE_LABELS.get(factor, factor.replace("_", " ").capitalize())


def _format_event(event: FloodEventResponse) -> str:
    affected = f"{event.estimated_affected:,}" if event.estimated_affected else "many"
    dmg = f", ~USD {event.damage_usd_billion:.1f}B damage" if event.damage_usd_billion else ""
    return (
        f"{event.year}: {event.title} ({event.peak_month})"
        f" — {affected} people affected{dmg}."
    )


def _format_source(src: DataSourceResponse) -> str:
    status = src.status.capitalize()
    return f"{src.name} ({status})"


class FloodExplainer:
    """Generates a deterministic 7-field flood risk explanation."""

    def explain(
        self,
        district_id: str,
        district_name: str,
        risk_level: str,
        confidence: float,
        top_factors: list[str],
        model_version: str,
        flood_events: list[FloodEventResponse],
        source_statuses: list[DataSourceResponse],
        reliefweb_articles: list[dict] | None = None,
    ) -> RiskExplanation:
        """
        Build and return a RiskExplanation.

        All arguments must be pre-fetched by the caller — this method performs
        no I/O. Returns "data unavailable" strings when data is missing.
        """
        main_causes = self._build_causes(top_factors)
        historical_evidence = self._build_history(
            district_name, flood_events, reliefweb_articles
        )
        suggested_actions = _ACTIONS.get(risk_level, _ACTIONS["Low"])
        data_sources = self._build_sources(source_statuses)
        safe_confidence = max(0.0, min(1.0, confidence))

        return RiskExplanation(
            risk_level=risk_level,
            main_causes=main_causes,
            historical_evidence=historical_evidence,
            suggested_actions=suggested_actions,
            confidence=safe_confidence,
            data_sources=data_sources,
            disclaimer=_DISCLAIMER,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_causes(self, top_factors: list[str]) -> list[str]:
        if not top_factors:
            return ["data unavailable"]
        return [_humanise_factor(f) for f in top_factors]

    def _build_history(
        self,
        district_name: str,
        flood_events: list[FloodEventResponse],
        reliefweb_articles: list[dict] | None,
    ) -> list[str]:
        evidence: list[str] = []

        # Seed DB flood events
        for event in flood_events:
            if district_name in event.affected_districts:
                evidence.append(_format_event(event))

        # ReliefWeb article titles (if fresh and available)
        if reliefweb_articles:
            for article in reliefweb_articles[:2]:
                title = article.get("title", "")
                source = article.get("source", "ReliefWeb")
                date = article.get("published_date", "")
                if title:
                    evidence.append(f"ReliefWeb ({date}): {title} — {source}")

        return evidence if evidence else ["data unavailable"]

    def _build_sources(self, source_statuses: list[DataSourceResponse]) -> list[str]:
        if not source_statuses:
            return ["data unavailable"]
        return [_format_source(s) for s in source_statuses]


# Module-level singleton
_explainer_instance: FloodExplainer | None = None


def get_flood_explainer() -> FloodExplainer:
    global _explainer_instance
    if _explainer_instance is None:
        _explainer_instance = FloodExplainer()
    return _explainer_instance
