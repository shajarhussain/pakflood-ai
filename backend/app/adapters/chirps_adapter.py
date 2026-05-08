"""
CHIRPSAdapter — CHIRPS historical rainfall climatology baseline.

Default mode (ENABLE_LIVE_RAINFALL=false): returns synthetic stub data,
status="stale". Safe for tests with no credentials.

Live mode (ENABLE_LIVE_RAINFALL=true, RAINFALL_PROVIDER=gee):
Attempts GEE fetch of CHIRPS pentad product. Falls back to stub on failure.

CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data):
- 0.05° resolution, 1981–present
- Used for seasonal historical baseline and rainfall anomaly computation
- Public dataset, no auth required for bulk download; GEE preferred for spatial aggregation

Synthetic stub data is clearly labeled — not real climatology observations.
"""

import logging
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, UTC

from app.adapters.base_adapter import BaseAdapter, AdapterResult
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalized climatology output schema
# ---------------------------------------------------------------------------

@dataclass
class ClimatologyReading:
    """Normalized per-district CHIRPS climatology record."""
    district_id: str
    historical_mean_mm: float   # long-term seasonal mean rainfall (mm, since 1981)
    current_season_mm: float    # rainfall accumulated this season to date (mm)
    rainfall_percentile: int    # 0–100 percentile vs 1981–present climatology
    anomaly_pct: float          # (current - mean) / mean * 100
    period: str                 # ISO date range "YYYY-MM-DD/YYYY-MM-DD"
    source: str                 # "chirps-stub" | "chirps-gee"
    observed_at: str            # ISO-8601 datetime string
    status: str                 # "fresh" | "stale" | "disabled" | "error"
    confidence: float           # 0.0 (synthetic) – 1.0 (validated)
    notes: str = ""             # human-readable provenance note


# ---------------------------------------------------------------------------
# Synthetic stub — clearly labeled, not real observations
# ---------------------------------------------------------------------------

_STUB_TIMESTAMP = "2026-05-06T00:00:00Z"
_STUB_PERIOD = "2025-09-01/2026-05-06"

_STUB_READINGS: list[ClimatologyReading] = [
    ClimatologyReading("PK-SD-SKR", 185.2, 320.5, 92,  73.0,  _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-SD-JCB", 178.4, 398.1, 97,  123.0, _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-SD-LRK", 165.9, 295.4, 88,  78.0,  _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-PB-MUL", 210.1, 181.3, 45,  -14.0, _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-PB-RWP", 380.5, 312.7, 38,  -18.0, _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-PB-LHR", 295.3, 271.2, 42,  -8.0,  _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-KP-PSH", 320.8, 368.9, 65,  15.0,  _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-BL-QTA", 180.4, 140.6, 28,  -22.0, _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-BL-NAS", 143.6, 352.9, 95,  146.0, _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
    ClimatologyReading("PK-GB-GIL", 210.5, 277.9, 62,  32.0,  _STUB_PERIOD, "chirps-stub", _STUB_TIMESTAMP, "stale", 0.0),
]

_STUB_INDEX: dict[str, ClimatologyReading] = {r.district_id: r for r in _STUB_READINGS}


class CHIRPSAdapter(BaseAdapter):
    source_id = "chirps"
    name = "CHIRPS Historical Rainfall"
    description = (
        "Climate Hazards Group InfraRed Precipitation with Station data (1981–present). "
        "Used for seasonal baseline and rainfall anomaly. "
        "Stub mode (default): synthetic data, status=stale, confidence=0. "
        "Live mode: GEE ImageCollection('UCSB-CHG/CHIRPS/DAILY') — set ENABLE_LIVE_RAINFALL=true."
    )
    features_created = ["historical_mean_mm", "current_season_mm", "rainfall_percentile", "anomaly_pct"]
    latency_hours = 720  # monthly product

    def _do_fetch(self) -> AdapterResult:
        if settings.ENABLE_LIVE_RAINFALL:
            return self._try_live_or_stub()
        return self._stub_result()

    def normalized_for_district(self, district_id: str) -> ClimatologyReading | None:
        """Return a ClimatologyReading for the given district."""
        return _STUB_INDEX.get(district_id)

    # ── Live dispatch ─────────────────────────────────────────────────────────

    def _try_live_or_stub(self) -> AdapterResult:
        provider = settings.RAINFALL_PROVIDER.lower()
        try:
            if provider == "gee":
                return self._do_fetch_live_gee()
            logger.warning("RAINFALL_PROVIDER=%s not supported for CHIRPS; using stub", provider)
        except NotImplementedError as exc:
            warnings.warn(f"CHIRPS live mode not yet implemented: {exc}", stacklevel=3)
            return self._disabled_result(str(exc))
        except Exception as exc:
            logger.warning("CHIRPS live fetch failed (%s); falling back to stub", exc)
        return self._stub_result()

    def _do_fetch_live_gee(self) -> AdapterResult:
        """
        Hook for GEE CHIRPS fetch.

        Implementation steps (future):
          1. import ee; ee.Initialize(credentials, project=settings.GEE_PROJECT)
          2. Load ImageCollection("UCSB-CHG/CHIRPS/DAILY"), filter to current season
          3. Reduce per-district polygon to seasonal sum
          4. Compare to 1981–2020 climatological mean per district
          5. Return fresh AdapterResult with confidence > 0
        """
        raise NotImplementedError(
            "GEE live CHIRPS not yet implemented. "
            "Set RAINFALL_PROVIDER=stub or configure GEE_SERVICE_ACCOUNT and GEE_PROJECT."
        )

    # ── Stub / disabled results ───────────────────────────────────────────────

    def _stub_result(self) -> AdapterResult:
        note = "synthetic stub — ENABLE_LIVE_RAINFALL=false"
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
