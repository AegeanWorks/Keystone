"""Versioned, asset-aware snapshots of a Keystone scene."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from keystone.camera import MAX_PITCH
from keystone.component_codec import (
    ComponentTypes,
    component_from_dict,
    component_to_dict,
)
from keystone.math3d import Quat, Vec3
from keystone.scene import (
    BloomSettings,
    ColorSettings,
    CullingSettings,
    DirectionalLight,
    Node,
    PointLight,
    PostSettings,
    Scene,
    ShadowSettings,
    SpriteSettings,
    Transform,
)

SCENE_SNAPSHOT_VERSION = 2


def _vec3_to_list(value: Vec3) -> list[float]:
    return [value.x, value.y, value.z]


def _vec3_from_value(value: Any, label: str, default: Vec3) -> Vec3:
    if value is None:
        return default
    if not (isinstance(value, (list, tuple)) and len(value) == 3):
        raise ValueError(f"{label} must have three values")
    vector = Vec3(float(value[0]), float(value[1]), float(value[2]))
    if not all(math.isfinite(component) for component in (vector.x, vector.y, vector.z)):
        raise ValueError(f"{label} must contain finite values")
    return vector


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
    if not isinstance(transform, Transform):
        raise TypeError("node transform must be a Transform")
    Transform(transform.position, transform.rotation, transform.scale)
    rotation = transform.rotation
    return {
        "position": [transform.position.x, transform.position.y, transform.position.z],
        "rotation": [rotation.x, rotation.y, rotation.z, rotation.w],
        "scale": [transform.scale.x, transform.scale.y, transform.scale.z],
    }


def _transform_from_dict(data: Any) -> Any:
    from keystone.scene import Transform

    if data is None:
        data = {}
    if not isinstance(data, Mapping):
        raise TypeError("snapshot transform must be a mapping")
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


def _payload_asset_ids(registry: Any) -> dict[int, str]:
    if registry is None:
        return {}
    index: dict[int, str] = {}
    for record in registry:
        index.setdefault(id(record.payload), record.id)
    return index


def _required_node_id(raw: Mapping[str, Any]) -> str:
    node_id = raw.get("id")
    if not isinstance(node_id, str):
        raise TypeError("scene snapshot node id must be a string")
    if not node_id.strip():
        raise ValueError("scene snapshot node id must be non-blank")
    return node_id


def _restore_asset(
    registry: Any,
    asset_id: Any,
    expected_kind: str,
    label: str,
) -> Any:
    if asset_id is None:
        return None
    if not isinstance(asset_id, str):
        raise TypeError(f"scene snapshot node {label} must be an asset id string or null")
    if registry is None:
        return None
    try:
        record = registry.require(asset_id)
    except KeyError:
        return None
    payload = getattr(record, "payload", None)
    if payload is None:
        return None
    kind = getattr(record, "kind", None)
    if kind is not None and kind != expected_kind:
        raise ValueError(
            f"scene snapshot node {label} {asset_id!r} is a {kind}, not a {expected_kind}"
        )
    return payload


def scene_to_dict(scene: Scene, registry: Any = None) -> dict[str, Any]:
    """Serialize a scene to a versioned, JSON-safe dictionary."""
    nodes: list[dict[str, Any]] = []
    asset_ids = _payload_asset_ids(registry)
    mesh_ids: dict[int, str | None] = {}
    material_ids: dict[int, str | None] = {}
    if registry is not None:
        for node in scene.traverse():
            if node.mesh is not None and id(node.mesh) not in mesh_ids:
                mesh_ids[id(node.mesh)] = asset_ids.get(id(node.mesh))
            if node.material is not None and id(node.material) not in material_ids:
                material_ids[id(node.material)] = asset_ids.get(id(node.material))
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
                "components": [
                    component_to_dict(component)
                    for _, component in sorted(
                        node.components.items(),
                        key=lambda item: (item[0].__module__, item[0].__qualname__),
                    )
                ],
            }
        )
    return {
        "schema": SCENE_SNAPSHOT_VERSION,
        "root": {
            "transform": _transform_to_dict(scene.root.transform),
            "visible": scene.root.visible,
        },
        "next_id": scene._next_id,
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
            "shadow": {"enabled": bool(getattr(scene.shadow, "enabled", True))},
            "color": {"enabled": bool(getattr(scene.color, "enabled", True))},
            "post": {"enabled": bool(getattr(scene.post, "enabled", True))},
            "bloom": {"enabled": bool(getattr(scene.bloom, "enabled", True))},
            "sprites": {"enabled": bool(getattr(scene.sprite, "enabled", True))},
            "culling": {"enabled": bool(getattr(scene.culling, "enabled", True))},
        },
        "nodes": nodes,
    }


def scene_from_dict(
    data: Mapping[str, Any],
    registry: Any = None,
    component_types: ComponentTypes | None = None,
) -> Scene:
    """Rebuild a scene from a versioned snapshot."""
    if not isinstance(data, Mapping):
        raise TypeError("scene snapshot must be a mapping")
    version = data.get("schema", data.get("version", SCENE_SNAPSHOT_VERSION))
    if isinstance(version, bool) or not isinstance(version, int) or version not in (1, SCENE_SNAPSHOT_VERSION):
        raise ValueError(f"unsupported scene snapshot version {version}")
    if "nodes" not in data:
        raise ValueError("scene snapshot must contain a nodes list")
    scene = Scene()
    root = data.get("root", {})
    if root is not None:
        if not isinstance(root, Mapping):
            raise TypeError("scene snapshot root must be a mapping")
        if "transform" in root:
            scene.root.transform = _transform_from_dict(root["transform"])
        if "visible" in root:
            if not isinstance(root["visible"], bool):
                raise TypeError("scene snapshot root visible must be a boolean")
            scene.root.visible = root["visible"]
    camera = data.get("camera", {})
    if camera is not None and not isinstance(camera, Mapping):
        raise TypeError("scene snapshot camera must be a mapping")
    if isinstance(camera, Mapping):
        scene.camera.position = _vec3_from_value(
            camera.get("position"), "camera position", scene.camera.position
        )
        scene.camera.yaw = float(camera.get("yaw", 0.0))
        scene.camera.pitch = float(camera.get("pitch", 0.0))
        scene.camera.fov_y = float(camera.get("fov_y", scene.camera.fov_y))
        scene.camera.near = float(camera.get("near", scene.camera.near))
        scene.camera.far = float(camera.get("far", scene.camera.far))
        if not all(
            math.isfinite(value)
            for value in (scene.camera.yaw, scene.camera.pitch, scene.camera.fov_y, scene.camera.near, scene.camera.far)
        ):
            raise ValueError("scene snapshot camera values must be finite")
        scene.camera.pitch = max(-MAX_PITCH, min(MAX_PITCH, scene.camera.pitch))
        scene.camera.projection_matrix(1.0)
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
        if not math.isfinite(scene.fog_density) or scene.fog_density < 0.0:
            raise ValueError("environment fog_density must be finite and non-negative")
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
        shadow = environment.get("shadow")
        if shadow is not None:
            if not isinstance(shadow, Mapping):
                raise TypeError("scene snapshot shadow must be a mapping")
            scene.shadow = ShadowSettings(enabled=bool(shadow.get("enabled", True)))
        color = environment.get("color")
        if color is not None:
            if not isinstance(color, Mapping):
                raise TypeError("scene snapshot color must be a mapping")
            scene.color = ColorSettings(enabled=bool(color.get("enabled", True)))
        post = environment.get("post")
        if post is not None:
            if not isinstance(post, Mapping):
                raise TypeError("scene snapshot post must be a mapping")
            scene.post = PostSettings(enabled=bool(post.get("enabled", True)))
        bloom = environment.get("bloom")
        if bloom is not None:
            if not isinstance(bloom, Mapping):
                raise TypeError("scene snapshot bloom must be a mapping")
            scene.bloom = BloomSettings(enabled=bool(bloom.get("enabled", True)))
        sprites = environment.get("sprites")
        if sprites is not None:
            if not isinstance(sprites, Mapping):
                raise TypeError("scene snapshot sprites must be a mapping")
            scene.sprite = SpriteSettings(enabled=bool(sprites.get("enabled", True)))
        culling = environment.get("culling")
        if culling is not None:
            if not isinstance(culling, Mapping):
                raise TypeError("scene snapshot culling must be a mapping")
            scene.culling = CullingSettings(enabled=bool(culling.get("enabled", True)))
    raw_nodes = data.get("nodes", [])
    if not isinstance(raw_nodes, (list, tuple)):
        raise TypeError("scene snapshot nodes must be a list")
    next_id = data.get("next_id")
    if next_id is not None and (isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < 1):
        raise ValueError("scene snapshot next_id must be a positive integer")
    seen_ids: set[str] = set()
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise TypeError("scene snapshot node must be a mapping")
        node_id = _required_node_id(raw)
        if node_id in seen_ids:
            raise ValueError(f"scene snapshot has duplicate node id {node_id!r}")
        seen_ids.add(node_id)
    created: dict[str, Node] = {}
    for raw in raw_nodes:
        node_id = _required_node_id(raw)
        raw_name = raw.get("name", node_id)
        if not isinstance(raw_name, str):
            raise TypeError("scene snapshot node name must be a string")
        name = raw_name
        layer = raw.get("layer", "default")
        if not isinstance(layer, str) or not layer:
            raise ValueError("scene snapshot node layer must be a non-empty string")
        raw_components = raw.get("components", [])
        if not isinstance(raw_components, (list, tuple)):
            raise TypeError("scene snapshot node components must be a list")
        components: dict[type, object] = {}
        for item in raw_components:
            component = component_from_dict(item, component_types)
            if type(component) in components:
                raise ValueError(
                    f"scene snapshot node {node_id!r} has duplicate "
                    f"{type(component).__name__} components"
                )
            components[type(component)] = component
        node = Node(name, id=node_id, layer=layer, components=components)
        node.transform = _transform_from_dict(raw.get("transform", {}))
        visible = raw.get("visible", True)
        if not isinstance(visible, bool):
            raise TypeError("scene snapshot node visible must be a boolean")
        node.visible = visible
        tags = raw.get("tags", [])
        if not isinstance(tags, (list, tuple)):
            raise TypeError("scene snapshot node tags must be a list")
        for tag in tags:
            if not isinstance(tag, str):
                raise TypeError("scene snapshot node tags must be strings")
            node.add_tag(tag)
        node.mesh = _restore_asset(registry, raw.get("mesh"), "mesh", f"{node_id!r} mesh")
        node.material = _restore_asset(
            registry, raw.get("material"), "material", f"{node_id!r} material"
        )
        created[node_id] = node
    # Link parents.
    by_id = {node.id: node for node in created.values()}
    for raw in raw_nodes:
        node_id = _required_node_id(raw)
        node = by_id[node_id]
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
    if next_id is not None:
        scene.restore_next_id(next_id)
    return scene
