from pydantic import BaseModel


class DistrictProperties(BaseModel):
    district_id: str
    name: str
    province: str


class BoundaryFeature(BaseModel):
    type: str = "Feature"
    properties: DistrictProperties
    geometry: dict


class BoundaryCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[BoundaryFeature]


class LocationSearchResult(BaseModel):
    district_id: str
    name: str
    province: str
    center: list[float]      # [lat, lng]
    risk_level: str
