from pydantic import BaseModel


class DataSourceResponse(BaseModel):
    id: str
    name: str
    status: str                          # fresh | stale | error | disabled
    last_updated: str | None = None
    latency_hours: int | None = None
    latency_ms: float | None = None      # measured round-trip latency
    description: str
    features_created: list[str]
    circuit_state: str | None = None     # closed | open | half_open
    error_message: str | None = None
