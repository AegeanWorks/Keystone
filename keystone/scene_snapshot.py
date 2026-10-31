"""Versioned, asset-aware snapshots of a Keystone scene."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from keystone.math3d import Quat, Vec3
from keystone.scene import Node, Scene

SCENE_SNAPSHOT_VERSION = 1


def _transform_to_dict(transform: Any) -> dict[str, Any]:
    rotation = transform.rotation
    return {
        "position": [transform.position.x, transform.position.y, transform.position.z],
        "rotation": [rotation.x, rotation.y, rotation.z, rotation.w],
        "scale": [transform.scale.x, transform.scale.y, transform.scale.z],
    }


def _transform_from_dict(data: Mapping[str, Any]) -> Any:
    from keystone.scene import Transform

    position = data.get("position", [0.0, 0.0, 0.0])
    rotation = data.get("rotation", [0.0, 0.0, 0.0, 1.0])
    scale = data.get("scale", [1.0, 1.0, 1.0])
    if not (isinstance(position, (list, tuple)) and len(position) == 3):
        raise ValueError("snapshot transform position must have three values")
    if not (isinstance(rotation, (list, tuple)) and len(rotation) == 4):
        raise ValueError("snapshot transform rotation must have four values")
    if not (isinstance(scale, (list, tuple)) and len(scale) == 3):
        raise ValueError("snapshot transform scale must have three values")
    return Transform(
        position=Vec3(float(position[0]), float(position[1]), float(position[2])),
        rotation=Quat(float(rotation[3]), float(rotation[0]), float(rotation[1]), float(rotation[2])),
        scale=Vec3(float(scale[0]), float(scale[1]), float(scale[2])),
    )


def _asset_id(payload: object, registry: Any) -> str | None:
    if registry is None or payload is None:
        return None
    for record in registry:
        if record.payload is payload:
            return record.id
    return None


def scene_to_dict(scene: Scene, registry: Any = None) -> dict[str, Any]:
    """Serialize a scene to a versioned, JSON-safe dictionary."""
    nodes: list[dict[str, Any]] = []
    mesh_ids: dict[int, str | None] = {}
    material_ids: dict[int, str | None] = {}
    if registry is not None:
        for node in scene.traverse():
            if node.mesh is not None and id(node.mesh) not in mesh_ids:
                mesh_ids[id(node.mesh)] = _asset_id(node.mesh, registry)
            if node.material is not None and id(node.material) not in material_ids:
                material_ids[id(node.material)] = _asset_id(node.material, registry)
    for node in scene.traverse():
        if node is scene.root:
            continue
        nodes.append(
            {
                "id": node.id,
                "name": node.name,
                "parent_id": node.parent.id if node.parent is not None and node.parent is not scene.root else None,
                "tags": sorted(node.tags),
                "layer": node.layer,
                "visible": node.visible,
                "transform": _transform_to_dict(node.transform),
                "mesh": mesh_ids.get(id(node.mesh)) if node.mesh is not None else None,
                "material": material_ids.get(id(node.material)) if node.material is not None else None,
            }
        )
    return {
        "schema": SCENE_SNAPSHOT_VERSION,
        "camera": {
            "position": [scene.camera.position.x, scene.camera.position.y, scene.camera.position.z],
            "yaw": scene.camera.yaw,
            "pitch": scene.camera.pitch,
            "fov_y": scene.camera.fov_y,
        },
        "nodes": nodes,
    }


def scene_from_dict(data: Mapping[str, Any], registry: Any = None) -> Scene:
    """Rebuild a scene from a versioned snapshot."""
    if not isinstance(data, Mapping):
        raise TypeError("scene snapshot must be a mapping")
    version = data.get("schema", data.get("version", SCENE_SNAPSHOT_VERSION))
    if version != SCENE_SNAPSHOT_VERSION:
        raise ValueError(f"unsupported scene snapshot version {version}")
    scene = Scene()
    camera = data.get("camera", {})
    if isinstance(camera, Mapping):
        position = camera.get("position", [0.0, 0.0, 0.0])
        if isinstance(position, (list, tuple)) and len(position) == 3:
            scene.camera.position = Vec3(float(position[0]), float(position[1]), float(position[2]))
        scene.camera.yaw = float(camera.get("yaw", 0.0))
        scene.camera.pitch = float(camera.get("pitch", 0.0))
        scene.camera.fov_y = float(camera.get("fov_y", scene.camera.fov_y))
    raw_nodes = data.get("nodes", [])
    if not isinstance(raw_nodes, (list, tuple)):
        raise TypeError("scene snapshot nodes must be a list")
    created: dict[str, Node] = {}
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise TypeError("scene snapshot node must be a mapping")
        node_id = str(raw.get("id", ""))
        if not node_id:
            raise ValueError("scene snapshot node id must be non-blank")
        name = str(raw.get("name", node_id))
        node = Node(name, id=node_id)
        node.transform = _transform_from_dict(raw.get("transform", {}))
        node.visible = bool(raw.get("visible", True))
        node.layer = str(raw.get("layer", "default"))
        tags = raw.get("tags", [])
        if isinstance(tags, (list, tuple)):
            for tag in tags:
                if isinstance(tag, str):
                    node.add_tag(tag)
        mesh_id = raw.get("mesh")
        if isinstance(mesh_id, str) and registry is not None:
            try:
                record = registry.require(mesh_id)
            except KeyError:
                record = None
            if record is not None and getattr(record, "payload", None) is not None:
                node.mesh = record.payload
        material_id = raw.get("material")
        if isinstance(material_id, str) and registry is not None:
            try:
                record = registry.require(material_id)
            except KeyError:
                record = None
            if record is not None and getattr(record, "payload", None) is not None:
                node.material = record.payload
        created[node_id] = node
    # Link parents.
    by_id = {node.id: node for node in created.values()}
    for raw in raw_nodes:
        node_id = str(raw.get("id", ""))
        node = by_id.get(node_id)
        if node is None:
            continue
        parent_id = raw.get("parent_id")
        if isinstance(parent_id, str) and parent_id in by_id:
            by_id[parent_id].add_child(node)
        else:
            scene.add(node)
    return scene