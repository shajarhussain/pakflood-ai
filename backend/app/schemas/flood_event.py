from pydantic import BaseModel


class FloodEventResponse(BaseModel):
    id: str
    year: int
    title: str
    affected_provinces: list[str]
    affected_districts: list[str]
    peak_month: str
    estimated_affected: int
    damage_usd_billion: float | None = None
    description: str
