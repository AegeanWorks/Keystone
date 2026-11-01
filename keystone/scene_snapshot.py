"""Versioned, asset-aware snapshots of a Keystone scene."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from keystone.math3d import Quat, Vec3
from keystone.scene import DirectionalLight, Node, PointLight, Scene

SCENE_SNAPSHOT_VERSION = 1


def _vec3_to_list(value: Vec3) -> list[float]:
    return [value.x, value.y, value.z]


def _vec3_from_value(value: Any, label: str, default: Vec3) -> Vec3:
    if value is None:
        return default
    if not (isinstance(value, (list, tuple)) and len(value) == 3):
        raise ValueError(f"{label} must have three values")
    return Vec3(float(value[0]), float(value[1]), float(value[2]))


def _light_to_dict(light: DirectionalLight) -> dict[str, Any]:
    return {
        "direction": _vec3_to_list(light.direction),
        "color": _vec3_to_list(light.color),
        "intensity": light.intensity,
    }


def _light_from_dict(data: Mapping[str, Any]) -> DirectionalLight:
    return DirectionalLight(
        direction=_vec3_from_value(data.get("direction"), "light direction", Vec3(-0.4, -1.0, -0.6)),
        color=_vec3_from_value(data.get("color"), "light color", Vec3(1.0, 0.97, 0.9)),
        intensity=float(data.get("intensity", 1.0)),
    )


def _point_light_to_dict(light: PointLight) -> dict[str, Any]:
    return {
        "position": _vec3_to_list(light.position),
        "color": _vec3_to_list(light.color),
        "intensity": light.intensity,
        "radius": light.radius,
    }


def _point_light_from_dict(data: Mapping[str, Any]) -> PointLight:
    return PointLight(
        position=_vec3_from_value(data.get("position"), "point light position", Vec3()),
        color=_vec3_from_value(data.get("color"), "point light color", Vec3(1.0, 0.8, 0.5)),
        intensity=float(data.get("intensity", 1.0)),
        radius=float(data.get("radius", 10.0)),
    )


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
            "position": _vec3_to_list(scene.camera.position),
            "yaw": scene.camera.yaw,
            "pitch": scene.camera.pitch,
            "fov_y": scene.camera.fov_y,
            "near": scene.camera.near,
            "far": scene.camera.far,
        },
        "environment": {
            "ambient": _vec3_to_list(scene.ambient),
            "background": _vec3_to_list(scene.background),
            "sky": _vec3_to_list(scene.sky),
            "fog_density": scene.fog_density,
            "light": _light_to_dict(scene.light),
            "point_light": _point_light_to_dict(scene.point_light) if scene.point_light else None,
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
        scene.camera.position = _vec3_from_value(
            camera.get("position"), "camera position", scene.camera.position
        )
        scene.camera.yaw = float(camera.get("yaw", 0.0))
        scene.camera.pitch = float(camera.get("pitch", 0.0))
        scene.camera.fov_y = float(camera.get("fov_y", scene.camera.fov_y))
        scene.camera.near = float(camera.get("near", scene.camera.near))
        scene.camera.far = float(camera.get("far", scene.camera.far))
    environment = data.get("environment", {})
    if environment is not None and not isinstance(environment, Mapping):
        raise TypeError("scene snapshot environment must be a mapping")
    if isinstance(environment, Mapping):
        scene.ambient = _vec3_from_value(
            environment.get("ambient"), "environment ambient", scene.ambient
        )
        scene.background = _vec3_from_value(
            environment.get("background"), "environment background", scene.background
        )
        scene.sky = _vec3_from_value(environment.get("sky"), "environment sky", scene.sky)
        scene.fog_density = float(environment.get("fog_density", scene.fog_density))
        light = environment.get("light")
        if light is not None:
            if not isinstance(light, Mapping):
                raise TypeError("scene snapshot light must be a mapping")
            scene.light = _light_from_dict(light)
        point_light = environment.get("point_light")
        if point_light is not None:
            if not isinstance(point_light, Mapping):
                raise TypeError("scene snapshot point_light must be a mapping")
            scene.point_light = _point_light_from_dict(point_light)
    raw_nodes = data.get("nodes", [])
    if not isinstance(raw_nodes, (list, tuple)):
        raise TypeError("scene snapshot nodes must be a list")
    seen_ids: set[str] = set()
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise TypeError("scene snapshot node must be a mapping")
        node_id = str(raw.get("id", ""))
        if not node_id:
            raise ValueError("scene snapshot node id must be non-blank")
        if node_id in seen_ids:
            raise ValueError(f"scene snapshot has duplicate node id {node_id!r}")
        seen_ids.add(node_id)
    created: dict[str, Node] = {}
    for raw in raw_nodes:
        node_id = str(raw.get("id", ""))
        name = str(raw.get("name", node_id))
        layer = raw.get("layer", "default")
        if not isinstance(layer, str) or not layer:
            raise ValueError("scene snapshot node layer must be a non-empty string")
        node = Node(name, id=node_id, layer=layer)
        node.transform = _transform_from_dict(raw.get("transform", {}))
        node.visible = bool(raw.get("visible", True))
        tags = raw.get("tags", [])
        if not isinstance(tags, (list, tuple)):
            raise TypeError("scene snapshot node tags must be a list")
        for tag in tags:
            if not isinstance(tag, str):
                raise TypeError("scene snapshot node tags must be strings")
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
        if parent_id is None:
            scene.add(node)
            continue
        if not isinstance(parent_id, str):
            raise TypeError("scene snapshot parent_id must be a string or null")
        if parent_id == node_id:
            raise ValueError(f"scene snapshot node {node_id!r} cannot be its own parent")
        if parent_id not in by_id:
            raise ValueError(
                f"scene snapshot node {node_id!r} references unknown parent {parent_id!r}"
            )
        by_id[parent_id].add_child(node)
    return scene