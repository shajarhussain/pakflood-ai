from app.hazards.base import HazardModule

_REGISTRY: dict[str, type] = {}


def register_hazard(name: str, cls: type) -> None:
    _REGISTRY[name] = cls


def get_hazard_module(name: str) -> HazardModule:
    if name not in _REGISTRY:
        raise KeyError(f"Hazard module '{name}' not registered. Available: {list(_REGISTRY)}")
    return _REGISTRY[name]()
