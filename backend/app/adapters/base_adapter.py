"""
BaseAdapter — Adapter Pattern + Circuit Breaker.

Every external data source must subclass BaseAdapter.
The circuit breaker prevents cascading failures when an upstream source is down.

States:
  CLOSED    — normal operation; failures are counted
  OPEN      — adapter disabled; fetch() returns error immediately
  HALF_OPEN — one test request allowed after recovery_timeout expires
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Result schema — all adapters return this
# ---------------------------------------------------------------------------

@dataclass
class AdapterResult:
    source_id: str
    status: Literal["fresh", "stale", "error", "disabled"]
    data: list[dict[str, Any]] | dict[str, Any] | None
    fetched_at: datetime
    latency_ms: float
    error_message: str | None = None
    circuit_state: str = "closed"   # closed | open | half_open


# ---------------------------------------------------------------------------
# Circuit breaker constants (overridable per subclass)
# ---------------------------------------------------------------------------

DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_RECOVERY_TIMEOUT = 30.0   # seconds before OPEN → HALF_OPEN
DEFAULT_REQUEST_TIMEOUT = 10.0    # seconds per HTTP call


class BaseAdapter(ABC):
    """Abstract base for all external data source adapters."""

    source_id: str               # unique registry key, e.g. "imerg"
    name: str                    # human-readable
    description: str
    features_created: list[str]  # feature names produced by this adapter
    latency_hours: int           # expected data freshness in hours

    # Circuit breaker configuration (override in subclass if needed)
    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT

    def __init__(self) -> None:
        self._failure_count: int = 0
        self._state: str = "closed"
        self._last_failure_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self) -> AdapterResult:
        """Run the adapter with circuit-breaker protection."""
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
            else:
                return AdapterResult(
                    source_id=self.source_id,
                    status="error",
                    data=None,
                    fetched_at=datetime.now(UTC),
                    latency_ms=0.0,
                    error_message="Circuit breaker open — adapter temporarily disabled",
                    circuit_state="open",
                )

        t0 = time.monotonic()
        try:
            result = self._do_fetch()
            latency_ms = (time.monotonic() - t0) * 1000
            self._on_success()
            result.latency_ms = latency_ms
            result.circuit_state = self._state
            return result
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            self._on_failure()
            return AdapterResult(
                source_id=self.source_id,
                status="error",
                data=None,
                fetched_at=datetime.now(UTC),
                latency_ms=latency_ms,
                error_message=str(exc),
                circuit_state=self._state,
            )

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED — useful in tests and admin ops."""
        self._failure_count = 0
        self._state = "closed"
        self._last_failure_time = 0.0

    @property
    def circuit_state(self) -> str:
        return self._state

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abstractmethod
    def _do_fetch(self) -> AdapterResult:
        """Perform the actual fetch. Raise any exception on failure."""
        ...

    # ------------------------------------------------------------------
    # Circuit breaker internals
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
