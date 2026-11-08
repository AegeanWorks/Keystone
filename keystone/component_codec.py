"""Shared JSON codec for typed scene components.

Prefab files, scene snapshots and editor documents all persist components by
their class name. Dataclasses, objects with ``to_dict``/``from_dict`` and JSON
primitives are supported; loading needs an explicit name-to-type map.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, fields, is_dataclass

__all__ = [
    "ComponentTypes",
    "component_from_dict",
    "component_to_dict",
    "json_safe",
    "validate_component_types",
]

ComponentTypes = Mapping[str, type]


def validate_component_types(
    component_types: Mapping[str, type] | None,
) -> dict[str, type] | None:
    """Copy and validate a component name-to-type map."""
    if component_types is None:
        return None
    if not isinstance(component_types, Mapping):
        raise TypeError("component_types must be a mapping of names to types")
    cleaned: dict[str, type] = {}
    for name, component_type in component_types.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("component type names must be non-blank strings")
        if not isinstance(component_type, type):
            raise TypeError("component_types values must be types")
        cleaned[name] = component_type
    return cleaned


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


def _dataclass_from_mapping(
    name: str, component_type: type, data: Mapping[str, object]
) -> object:
    """Construct a dataclass, rejecting fields it does not declare."""
    declared = {field.name for field in fields(component_type)}
    unknown = sorted(set(data) - declared)
    if unknown:
        raise ValueError(
            f"component {name!r} has unknown fields: {', '.join(unknown)}"
        )
    try:
        return component_type(**data)
    except TypeError as exc:
        raise ValueError(f"component {name!r} could not be built: {exc}") from exc


def component_from_dict(item: object, component_types: ComponentTypes | None) -> object:
    """Decode one component, requiring an explicit type map.

    Unknown keys are rejected, matching every other versioned loader in the
    engine: a typo in an authored component document must fail loudly rather
    than be silently dropped.
    """
    if not isinstance(item, Mapping) or not isinstance(item.get("type"), str) or "data" not in item:
        raise ValueError("component must hold 'type' and 'data'")
    unknown = sorted(set(item) - {"type", "data"})
    if unknown:
        raise ValueError(f"component has unknown keys: {unknown}")
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
        return _dataclass_from_mapping(name, component_type, data)
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
