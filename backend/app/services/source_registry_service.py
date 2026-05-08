"""
SourceRegistryService — tracks all external data source adapters.

Maintains adapter instances, runs health checks with per-source caching,
and converts results to API response schemas.
"""
import time
from datetime import datetime

from app.adapters.base_adapter import BaseAdapter, AdapterResult
from app.schemas.data_source import DataSourceResponse

_CACHE_TTL_SECONDS = 300.0  # 5 minutes


class SourceRegistryService:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}
        self._cache: dict[str, AdapterResult] = {}
        self._cache_time: dict[str, float] = {}

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.source_id] = adapter

    def get_adapter(self, source_id: str) -> BaseAdapter | None:
        return self._adapters.get(source_id)

    def get_status(self, source_id: str) -> AdapterResult | None:
        adapter = self._adapters.get(source_id)
        if adapter is None:
            return None
        return self._fetch_with_cache(adapter)

    def get_all_statuses(self) -> list[AdapterResult]:
        return [self._fetch_with_cache(a) for a in self._adapters.values()]

    def to_data_source_responses(self) -> list[DataSourceResponse]:
        results = self.get_all_statuses()
        responses = []
        for result in results:
            adapter = self._adapters.get(result.source_id)
            responses.append(DataSourceResponse(
                id=result.source_id,
                name=adapter.name if adapter else result.source_id,
                status=result.status,
                last_updated=result.fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                latency_hours=adapter.latency_hours if adapter else None,
                latency_ms=round(result.latency_ms, 1),
                description=adapter.description if adapter else "",
                features_created=adapter.features_created if adapter else [],
                circuit_state=result.circuit_state,
                error_message=result.error_message,
            ))
        return responses

    def invalidate_cache(self, source_id: str | None = None) -> None:
        if source_id:
            self._cache.pop(source_id, None)
            self._cache_time.pop(source_id, None)
        else:
            self._cache.clear()
            self._cache_time.clear()

    def _fetch_with_cache(self, adapter: BaseAdapter) -> AdapterResult:
        sid = adapter.source_id
        age = time.monotonic() - self._cache_time.get(sid, 0.0)
        if sid in self._cache and age < _CACHE_TTL_SECONDS:
            return self._cache[sid]
        result = adapter.fetch()
        self._cache[sid] = result
        self._cache_time[sid] = time.monotonic()
        return result


# ---------------------------------------------------------------------------
# Singleton — persists circuit breaker state across requests
# ---------------------------------------------------------------------------

_registry_instance: SourceRegistryService | None = None


def _build_default_registry() -> SourceRegistryService:
    from app.adapters.imerg_adapter import IMERGAdapter
    from app.adapters.chirps_adapter import CHIRPSAdapter
    from app.adapters.glofas_adapter import GloFASAdapter
    from app.adapters.ffd_adapter import FFDAdapter
    from app.adapters.reliefweb_adapter import ReliefWebAdapter

    reg = SourceRegistryService()
    reg.register(IMERGAdapter())
    reg.register(CHIRPSAdapter())
    reg.register(GloFASAdapter())
    reg.register(FFDAdapter())
    reg.register(ReliefWebAdapter())
    return reg


def get_source_registry() -> SourceRegistryService:
    """FastAPI dependency — override in tests via app.dependency_overrides."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = _build_default_registry()
    return _registry_instance
