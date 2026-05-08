"""
FFDAdapter — stub for Pakistan PMD / Federal Flood Division bulletins.

Production path: PMD FFD bulletin page scraping or official data feed (no public API).
Phase 3: returns synthetic FFD station readings. Live connection deferred to Phase 4+.
"""
from datetime import datetime, UTC

from app.adapters.base_adapter import BaseAdapter, AdapterResult

_STUB_DATA = [
    {"station": "Indus at Sukkur",        "category": "High Flood",   "level_m": 152.3, "danger_level_m": 145.0, "trend": "rising",  "issued_at": "2026-05-06T06:00:00Z"},
    {"station": "Indus at Guddu",         "category": "High Flood",   "level_m": 148.7, "danger_level_m": 139.0, "trend": "rising",  "issued_at": "2026-05-06T06:00:00Z"},
    {"station": "Indus at Kotri",         "category": "Medium Flood", "level_m": 96.1,  "danger_level_m": 90.0,  "trend": "steady",  "issued_at": "2026-05-06T06:00:00Z"},
    {"station": "Chenab at Trimmu",       "category": "Low Flood",    "level_m": 119.4, "danger_level_m": 115.0, "trend": "falling", "issued_at": "2026-05-06T06:00:00Z"},
    {"station": "Chenab at Head Panjnad", "category": "Normal",       "level_m": 82.3,  "danger_level_m": 88.0,  "trend": "steady",  "issued_at": "2026-05-06T06:00:00Z"},
]


class FFDAdapter(BaseAdapter):
    source_id = "ffd"
    name = "PMD / FFD Bulletin"
    description = (
        "Pakistan Meteorological Department and Federal Flood Division official river gauge bulletins. "
        "No public machine-readable API available — stub in Phase 3."
    )
    features_created = ["ffd_category", "ffd_level_m", "ffd_trend"]
    latency_hours = 6

    def _do_fetch(self) -> AdapterResult:
        return AdapterResult(
            source_id=self.source_id,
            status="stale",
            data=_STUB_DATA,
            fetched_at=datetime.now(UTC),
            latency_ms=0.0,
        )
