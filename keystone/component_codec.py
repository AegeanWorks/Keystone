"""Shared JSON codec for typed scene components.

Prefab files, scene snapshots and editor documents all persist components by
their class name. Dataclasses, objects with ``to_dict``/``from_dict`` and JSON
primitives are supported; loading needs an explicit name-to-type map.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass

__all__ = ["ComponentTypes", "component_from_dict", "component_to_dict", "json_safe"]

ComponentTypes = Mapping[str, type]


def json_safe(value: object, label: str) -> object:
    """Return the value after proving it can cross a JSON boundary."""
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-safe") from exc
    return value


def component_to_dict(component: object) -> dict:
    """Encode one component as ``{'type': name, 'data': ...}``."""
    component_type = type(component)
    if callable(getattr(component, "to_dict", None)):
        data = component.to_dict()
    elif is_dataclass(component):
        data = asdict(component)
    elif isinstance(component, (str, int, float, bool, type(None), list, tuple, dict)):
        data = component
    else:
        raise TypeError(f"component {component_type.__name__} is not serializable")
    return {
        "type": component_type.__name__,
        "data": json_safe(data, f"component {component_type.__name__}"),
    }


def component_from_dict(item: object, component_types: ComponentTypes | None) -> object:
    """Decode one component, requiring an explicit type map."""
    if not isinstance(item, Mapping) or not isinstance(item.get("type"), str) or "data" not in item:
        raise ValueError("component must hold 'type' and 'data'")
    if component_types is None:
        raise ValueError("loading components needs component_types")
    name = item["type"]
    component_type = component_types.get(name)
    if component_type is None:
        raise ValueError(f"unknown component type {name!r}")
    data = item["data"]
    from_dict = getattr(component_type, "from_dict", None)
    if callable(from_dict):
        return from_dict(data)
    if is_dataclass(component_type):
        if not isinstance(data, Mapping):
            raise ValueError(f"component {name!r} data must be a mapping")
        return component_type(**data)
    if component_type is type(None):
        if data is not None:
            raise ValueError(f"component {name!r} data must be null")
        return None
    if component_type in (list, tuple):
        if not isinstance(data, (list, tuple)):
            raise ValueError(f"component {name!r} data must be a list")
        return component_type(data)
    if component_type is dict:
        if not isinstance(data, Mapping):
            raise ValueError(f"component {name!r} data must be a mapping")
        return dict(data)
    if component_type is bool:
        if not isinstance(data, bool):
            raise ValueError(f"component {name!r} data must be a boolean")
        return data
    if component_type is int:
        if isinstance(data, bool) or not isinstance(data, int):
            raise ValueError(f"component {name!r} data must be an integer")
        return data
    if component_type is float:
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            raise ValueError(f"component {name!r} data must be a number")
        return float(data)
    if component_type is str:
        if not isinstance(data, str):
            raise ValueError(f"component {name!r} data must be a string")
        return data
    if isinstance(data, (list, tuple)):
        return component_type(*data)
    return component_type(data)
