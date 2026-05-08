"""
GloFASAdapter — ECMWF Global Flood Awareness System river discharge forecasts.

Default mode (ENABLE_LIVE_GLOFAS=false): returns synthetic stub data,
status="stale". Safe for tests with no credentials.

Live mode (future): Copernicus Climate Data Store (CDS) API.

GloFAS (Global Flood Awareness System):
- 0.1° resolution, 30-day ensemble discharge forecasts
- Used for river_discharge_m3s feature in flood risk model
- Requires Copernicus CDS API key (free registration)

Synthetic stub data is clearly labeled — not real discharge observations.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, UTC

from app.adapters.base_adapter import BaseAdapter, AdapterResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalized discharge output schema
# ---------------------------------------------------------------------------

@dataclass
class DischargeReading:
    """Normalized per-district GloFAS discharge record."""
    district_id: str
    river_discharge_m3s: float    # 3-day ensemble mean discharge (m³/s)
    discharge_anomaly_pct: float  # % deviation from 30-year climatological mean
    alert_level: str              # "None" | "Yellow" | "Orange" | "Red"
    forecast_window_hours: int    # hours ahead the forecast covers
    source: str                   # "glofas-stub" | "glofas-cds"
    observed_at: str              # ISO-8601 datetime string
    status: str                   # "fresh" | "stale" | "disabled" | "error"
    confidence: float             # 0.0 (synthetic) – 1.0 (validated)
    notes: str = ""               # human-readable provenance note


# ---------------------------------------------------------------------------
# Synthetic stub — clearly labeled, not real discharge observations
# ---------------------------------------------------------------------------

_STUB_TIMESTAMP = "2026-05-06T00:00:00Z"

_STUB_READINGS: list[DischargeReading] = [
    DischargeReading("PK-SD-SKR", 8540.0,  131.0, "Red",    72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-SD-JCB", 11200.0, 212.0, "Red",    72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-SD-LRK", 7100.0,  95.0,  "Orange", 72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-PB-MUL", 3200.0,  -18.0, "Yellow", 72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-PB-RWP", 420.0,   -85.0, "None",   72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-PB-LHR", 1850.0,  -12.0, "Yellow", 72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-KP-PSH", 2100.0,  28.0,  "Yellow", 72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-BL-QTA", 85.0,    -42.0, "None",   72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-BL-NAS", 9800.0,  174.0, "Red",    72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
    DischargeReading("PK-GB-GIL", 1240.0,  32.0,  "Yellow", 72, "glofas-stub", _STUB_TIMESTAMP, "stale", 0.0),
]

_STUB_INDEX: dict[str, DischargeReading] = {r.district_id: r for r in _STUB_READINGS}


class GloFASAdapter(BaseAdapter):
    source_id = "glofas"
    name = "GloFAS River Discharge"
    description = (
        "ECMWF Global Flood Awareness System 3-day river discharge ensemble forecasts. "
        "Stub mode (default): synthetic data, status=stale, confidence=0. "
        "Live mode: requires Copernicus CDS API key — set ENABLE_LIVE_GLOFAS=true."
    )
    features_created = ["river_discharge_m3s", "discharge_anomaly_pct", "alert_level"]
    latency_hours = 24

    def _do_fetch(self) -> AdapterResult:
        return self._stub_result()

    def normalized_for_district(self, district_id: str) -> DischargeReading | None:
        """Return a DischargeReading for the given district."""
        return _STUB_INDEX.get(district_id)

    # ── Live dispatch (placeholder — future CDS integration) ──────────────────

    def _do_fetch_live_cds(self) -> AdapterResult:
        """
        Hook for Copernicus CDS GloFAS fetch.

        Implementation steps (future):
          1. import cdsapi; client = cdsapi.Client(key=settings.CDS_API_KEY)
          2. Request 'cems-glofas-forecast' for Pakistan river reaches
          3. Aggregate discharge to district centroids (nearest gauge)
          4. Compute 30-year climatological anomaly
          5. Return fresh AdapterResult with confidence > 0
        """
        raise NotImplementedError(
            "CDS live GloFAS not yet implemented. "
            "Set ENABLE_LIVE_GLOFAS=true and configure CDS_API_KEY."
        )

    # ── Stub / disabled results ───────────────────────────────────────────────

    def _stub_result(self) -> AdapterResult:
        note = "synthetic stub — live GloFAS not configured"
        data = [asdict(r) | {"notes": note} for r in _STUB_READINGS]
        return AdapterResult(
            source_id=self.source_id,
            status="stale",
            data=data,
            fetched_at=datetime.now(UTC),
            latency_ms=0.0,
        )

    def _disabled_result(self, reason: str) -> AdapterResult:
        note = f"live mode not configured — {reason}"
        data = [asdict(r) | {"notes": note} for r in _STUB_READINGS]
        return AdapterResult(
            source_id=self.source_id,
            status="disabled",
            data=data,
            fetched_at=datetime.now(UTC),
            latency_ms=0.0,
            error_message=reason,
        )
