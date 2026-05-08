from fastapi import APIRouter, Depends

from app.services.source_registry_service import SourceRegistryService, get_source_registry
from app.schemas.data_source import DataSourceResponse

router = APIRouter()


@router.get("/data-sources", response_model=list[DataSourceResponse])
def get_data_sources(
    registry: SourceRegistryService = Depends(get_source_registry),
) -> list[DataSourceResponse]:
    """Return live status of all registered data source adapters."""
    return registry.to_data_source_responses()
