"""Scene-editor helpers for the local web console.

Pure functions build a hierarchy document, validate transform edits and
capture/insert prefabs. The HTTP session owns selection and prefab state.
"""

from __future__ import annotations

import math

from keystone.math3d import Quat, Vec3
from keystone.prefab import Prefab
from keystone.scene import Node, Scene, Transform
from keystone.schema import EDITOR_SCHEMA_VERSION

__all__ = [
    "EDITOR_ACTIONS",
    "editor_document",
    "find_node",
    "insert_prefab",
    "save_prefab",
    "transform_from_payload",
]

EDITOR_ACTIONS = ("select", "transform", "save_prefab", "insert_prefab")


def _finite_array(value: object, length: int, label: str) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{label} must contain {length} numbers")
    result: list[float] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{label} must contain numbers")
        number = float(component)
        if not math.isfinite(number):
            raise ValueError(f"{label} must contain finite numbers")
        result.append(number)
    return tuple(result)


def node_document(node: Node, selected_id: str | None) -> dict:
    transform = node.transform
    rotation = transform.rotation
    return {
        "id": node.id,
        "name": node.name,
        "parent_id": node.parent.id if node.parent is not None and node.parent.id else None,
        "children": [child.id for child in node.children],
        "visible": node.visible,
        "selected": node.id == selected_id,
        "tags": sorted(node.tags),
        "layer": node.layer,
        "components": sorted(component_type.__name__ for component_type in node.components),
        "transform": {
            "position": [transform.position.x, transform.position.y, transform.position.z],
            "rotation": [rotation.x, rotation.y, rotation.z, rotation.w],
            "scale": [transform.scale.x, transform.scale.y, transform.scale.z],
        },
        "world": list(node.world_matrix().flat()),
    }


def editor_document(scene: Scene, selected_id: str | None, prefabs: dict[str, Prefab]) -> dict:
    nodes = [node_document(node, selected_id) for node in scene.traverse()]
    selection = next((node for node in nodes if node["id"] == selected_id), None)
    return {
        "schema": EDITOR_SCHEMA_VERSION,
        "game": None,
        "roots": [node.id for node in scene.root.children],
        "selection": selection,
        "nodes": nodes,
        "prefabs": [
            {"name": name, "node_count": prefabs[name].node_count}
            for name in sorted(prefabs)
        ],
        "actions": list(EDITOR_ACTIONS),
    }


def find_node(scene: Scene, node_id: str) -> Node:
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("node id must be a non-blank string")
    node = scene.find_by_id(node_id)
    if node is None:
        raise KeyError(f"no scene node {node_id!r}")
    return node


def transform_from_payload(node: Node, payload: dict) -> Transform:
    fields = [name for name in ("position", "rotation", "scale") if name in payload]
    if not fields:
        raise ValueError("transform needs position, rotation or scale")
    current = node.transform
    position = (
        Vec3(*_finite_array(payload["position"], 3, "position"))
        if "position" in payload
        else current.position
    )
    scale = (
        Vec3(*_finite_array(payload["scale"], 3, "scale"))
        if "scale" in payload
        else current.scale
    )
    if "rotation" in payload:
        x, y, z, w = _finite_array(payload["rotation"], 4, "rotation")
        rotation = Quat(w, x, y, z)
    else:
        rotation = current.rotation
    return Transform(position=position, rotation=rotation, scale=scale)


def save_prefab(scene: Scene, node: Node, name: str, prefabs: dict[str, Prefab]) -> Prefab:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("prefab name must be a non-blank string")
    prefab = Prefab.from_node(node, name=name)
    prefabs[name] = prefab
    return prefab


def insert_prefab(
    scene: Scene,
    prefabs: dict[str, Prefab],
    name: str,
    parent: Node | None,
    instance: str | None,
) -> list[Node]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("prefab name must be a non-blank string")
    if name not in prefabs:
        raise KeyError(f"no saved prefab {name!r}")
    roots = prefabs[name].instantiate(scene, parent=parent, instance=instance)
    # Materialize IDs for instances attached below a non-root parent.
    list(scene.traverse())
    return roots
