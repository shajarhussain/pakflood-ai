"""
IMERGAdapter — NASA GPM IMERG near-real-time precipitation.

Default mode (ENABLE_LIVE_RAINFALL=false): returns synthetic stub data,
status="stale". Safe for tests and local development with no credentials.

Live mode (ENABLE_LIVE_RAINFALL=true, RAINFALL_PROVIDER=gee|earthdata):
Attempts a real fetch. If auth or network fails, falls back to stub with
status="stale" — never raises, never returns status="error" from config alone.

Production path: NASA Earthdata (earthdata.nasa.gov) or Google Earth Engine.
Synthetic stub data is clearly labeled — not real observations.
"""

import logging
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, UTC

from app.adapters.base_adapter import BaseAdapter, AdapterResult
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalized rainfall output schema
# ---------------------------------------------------------------------------

@dataclass
class RainfallReading:
    """Normalized per-district rainfall record produced by rainfall adapters."""
    district_id: str
    rainfall_1d_mm: float       # 24-hour accumulated rainfall (mm)
    rainfall_3d_mm: float       # 3-day accumulated (mm)
    rainfall_7d_mm: float       # 7-day accumulated (mm)
    rainfall_anomaly_pct: float # % deviation from seasonal historical mean (CHIRPS baseline)
    source: str                 # "imerg-stub" | "imerg-gee" | "imerg-earthdata"
    observed_at: str            # ISO-8601 datetime string
    status: str                 # "fresh" | "stale" | "disabled" | "error"
    confidence: float           # 0.0 (synthetic) – 1.0 (validated real-time)
    notes: str = ""             # human-readable provenance note


# ---------------------------------------------------------------------------
# Synthetic stub — clearly labeled, not real observations
# Anomaly values derived from CHIRPS seasonal baseline (see chirps_adapter.py)
# ---------------------------------------------------------------------------

_STUB_TIMESTAMP = "2026-05-06T00:00:00Z"

_STUB_READINGS: list[RainfallReading] = [
    RainfallReading("PK-SD-SKR", 48.2,  112.5, 280.3, 73.0,   "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-SD-JCB", 62.7,  145.1, 342.8, 123.0,  "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-SD-LRK", 41.0,  98.3,  231.6, 78.0,   "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-PB-MUL", 18.5,  47.2,  89.4,  -14.0,  "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-PB-RWP", 8.1,   22.0,  41.3,  -18.0,  "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-PB-LHR", 12.3,  31.5,  58.2,  -8.0,   "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-KP-PSH", 22.1,  55.8,  108.4, 15.0,   "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-BL-QTA", 5.3,   14.2,  28.1,  -22.0,  "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-BL-NAS", 55.9,  131.4, 310.7, 146.0,  "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
    RainfallReading("PK-GB-GIL", 18.7,  44.2,  89.6,  32.0,   "imerg-stub", _STUB_TIMESTAMP, "stale", 0.0),
]

_STUB_INDEX: dict[str, RainfallReading] = {r.district_id: r for r in _STUB_READINGS}


class IMERGAdapter(BaseAdapter):
    source_id = "imerg"
    name = "NASA IMERG (GPM)"
    description = (
        "Near-real-time satellite precipitation at 0.1°/30-min resolution. "
        "Stub mode (default): synthetic data, status=stale, confidence=0. "
        "Live mode: requires NASA Earthdata or GEE auth — set ENABLE_LIVE_RAINFALL=true."
    )
    features_created = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_anomaly_pct"]
    latency_hours = 12

    def _do_fetch(self) -> AdapterResult:
        if settings.ENABLE_LIVE_RAINFALL:
            return self._try_live_or_stub()
        return self._stub_result()

    def normalized_for_district(self, district_id: str) -> RainfallReading | None:
        """Return a RainfallReading for the given district from the last fetch result."""
        return _STUB_INDEX.get(district_id)

    # ── Live dispatch (real-data-ready paths) ─────────────────────────────────

    def _try_live_or_stub(self) -> AdapterResult:
        """Attempt live fetch; fall back gracefully on any failure."""
        provider = settings.RAINFALL_PROVIDER.lower()
        try:
            if provider == "gee":
                return self._do_fetch_live_gee()
            if provider == "earthdata":
                return self._do_fetch_live_earthdata()
            logger.warning("RAINFALL_PROVIDER=%s not recognised; using stub", provider)
        except NotImplementedError as exc:
            # Live path exists but credentials/config not yet provided — flag explicitly.
            warnings.warn(f"IMERG live mode not yet implemented: {exc}", stacklevel=3)
            return self._disabled_result(str(exc))
        except Exception as exc:
            logger.warning("IMERG live fetch failed (%s); falling back to stub", exc)
        return self._stub_result()

    def _do_fetch_live_gee(self) -> AdapterResult:
        """
        Hook for Google Earth Engine IMERG fetch.

        Implementation steps (future):
          1. import ee; ee.Initialize(credentials, project=settings.GEE_PROJECT)
          2. Load ImageCollection("NASA/GPM_L3/IMERG_V07") filtered to Pakistan bbox
          3. Reduce per-district boundary polygon to mean rainfall values
          4. Return fresh AdapterResult with confidence > 0
        """
        raise NotImplementedError(
            "GEE live IMERG not yet implemented. "
            "Set RAINFALL_PROVIDER=stub or configure GEE_SERVICE_ACCOUNT and GEE_PROJECT."
        )

    def _do_fetch_live_earthdata(self) -> AdapterResult:
        """
        Hook for NASA Earthdata IMERG API fetch.

        Implementation steps (future):
          1. Authenticate with EARTHDATA_USERNAME / EARTHDATA_PASSWORD from env
          2. GET https://gpm.nasa.gov/data/imerg/... for latest 24h/3d/7d accumulations
          3. Spatially aggregate to Pakistan district centroids
          4. Return fresh AdapterResult with confidence > 0
        """
        raise NotImplementedError(
            "Earthdata live IMERG not yet implemented. "
            "Set RAINFALL_PROVIDER=stub or configure EARTHDATA credentials in .env."
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
        """Return stub data with status=disabled when live mode is configured but not operational."""
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
