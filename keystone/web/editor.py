"""Scene-editor helpers for the local web console.

Pure functions build a hierarchy document, validate authoring commands,
capture/insert prefabs and keep bounded undo/redo snapshots. The HTTP session
owns selection, history and prefab state.
"""

from __future__ import annotations

import base64
import copy
import math
from collections.abc import Callable, Mapping
from dataclasses import MISSING, fields, is_dataclass
from typing import TypeVar

from keystone.camera import MAX_PITCH
from keystone.component_codec import (
    ComponentTypes,
    component_from_dict,
    component_to_dict,
)
from keystone.geometry import Material, MeshData
from keystone.lifecycle import lifecycle_hooks
from keystone.math3d import Quat, Vec3
from keystone.png import png_bytes
from keystone.prefab import Prefab
from keystone.scene import (
    BloomSettings,
    ColorSettings,
    CullingSettings,
    DirectionalLight,
    Node,
    PointLight,
    PostSettings,
    PrefabLink,
    Scene,
    SceneGroup,
    ShadowSettings,
    SpriteSettings,
    Transform,
)
from keystone.scene_library import SceneLibrary
from keystone.schema import EDITOR_ACTIONS, EDITOR_SCHEMA_VERSION
from keystone.texture import TextureData

__all__ = [
    "EDITOR_ACTIONS",
    "EditorHistory",
    "asset_entries",
    "assign_assets",
    "component_schemas",
    "create_node",
    "delete_node",
    "duplicate_node",
    "editor_document",
    "find_node",
    "insert_prefab",
    "remove_component",
    "reparent_node",
    "save_prefab",
    "scene_settings_document",
    "set_component",
    "set_node_properties",
    "set_scene",
    "transform_from_payload",
]

T = TypeVar("T")


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


def _node_name(value: object, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError("node name must be a non-blank string")
    return value


def _node_id(value: object) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise TypeError("node id must be a string or null")
    if not value.strip():
        raise ValueError("node id must be non-blank or null")
    return value


def _node_tags(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise TypeError("node tags must be a list of strings")
    tags: set[str] = set()
    for tag in value:
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError("node tags must be non-empty strings")
        tags.add(tag)
    return tags


def _transform_from_payload(payload: Mapping[str, object], current: Transform | None) -> Transform:
    fields = [name for name in ("position", "rotation", "scale") if name in payload]
    if not fields:
        if current is None:
            return Transform()
        raise ValueError("transform needs position, rotation or scale")
    base = current or Transform()
    position = (
        Vec3(*_finite_array(payload["position"], 3, "position"))
        if "position" in payload
        else base.position
    )
    scale = (
        Vec3(*_finite_array(payload["scale"], 3, "scale"))
        if "scale" in payload
        else base.scale
    )
    if "rotation" in payload:
        x, y, z, w = _finite_array(payload["rotation"], 4, "rotation")
        rotation = Quat(w, x, y, z)
    else:
        rotation = base.rotation
    return Transform(position=position, rotation=rotation, scale=scale)


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _payload_vec3(value: object, label: str) -> Vec3:
    x, y, z = _finite_array(value, 3, label)
    return Vec3(x, y, z)


def _unknown_keys(
    payload: Mapping[str, object], allowed: set[str], label: str
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{label} has unknown keys: {unknown}")


def _vec3_list(value: Vec3) -> list[float]:
    return [value.x, value.y, value.z]


def scene_settings_document(scene: Scene) -> dict[str, object]:
    """Return JSON-safe camera and environment settings for the editor."""
    camera = scene.camera
    light = scene.light
    point = scene.point_light
    return {
        "camera": {
            "position": _vec3_list(camera.position),
            "yaw": camera.yaw,
            "pitch": camera.pitch,
            "fov_y": camera.fov_y,
            "near": camera.near,
            "far": camera.far,
        },
        "environment": {
            "ambient": _vec3_list(scene.ambient),
            "background": _vec3_list(scene.background),
            "sky": _vec3_list(scene.sky),
            "fog_density": scene.fog_density,
            "light": {
                "direction": _vec3_list(light.direction),
                "color": _vec3_list(light.color),
                "intensity": light.intensity,
            },
            "point_light": (
                {
                    "position": _vec3_list(point.position),
                    "color": _vec3_list(point.color),
                    "intensity": point.intensity,
                    "radius": point.radius,
                }
                if point is not None
                else None
            ),
            "shadow": bool(scene.shadow.enabled),
            "color": bool(scene.color.enabled),
            "post": bool(scene.post.enabled),
            "bloom": bool(scene.bloom.enabled),
            "sprites": bool(scene.sprite.enabled),
            "culling": bool(scene.culling.enabled),
        },
    }


def set_scene(scene: Scene, payload: Mapping[str, object]) -> Scene:
    """Update camera and/or environment settings after full validation."""
    if not isinstance(scene, Scene):
        raise TypeError("set_scene target must be a Scene")
    if not isinstance(payload, Mapping):
        raise TypeError("set_scene payload must be a mapping")
    _unknown_keys(
        payload, {"action", "camera", "environment"}, "set_scene payload"
    )
    if "camera" not in payload and "environment" not in payload:
        raise ValueError("set_scene needs camera or environment")
    camera_payload = payload.get("camera")
    environment_payload = payload.get("environment")
    if camera_payload is not None and not isinstance(camera_payload, Mapping):
        raise TypeError("camera must be a mapping or null")
    if environment_payload is not None and not isinstance(
        environment_payload, Mapping
    ):
        raise TypeError("environment must be a mapping or null")
    if camera_payload is None and environment_payload is None:
        raise ValueError("set_scene needs camera or environment data")
    if camera_payload == {}:
        raise ValueError("camera needs at least one field")
    if environment_payload == {}:
        raise ValueError("environment needs at least one field")

    camera = scene.camera
    position = camera.position
    yaw = camera.yaw
    pitch = camera.pitch
    fov_y = camera.fov_y
    near = camera.near
    far = camera.far
    if isinstance(camera_payload, Mapping):
        _unknown_keys(
            camera_payload,
            {"position", "yaw", "pitch", "fov_y", "near", "far"},
            "camera",
        )
        if "position" in camera_payload:
            position = _payload_vec3(camera_payload["position"], "camera position")
        if "yaw" in camera_payload:
            yaw = _finite_number(camera_payload["yaw"], "camera yaw")
        if "pitch" in camera_payload:
            pitch = _finite_number(camera_payload["pitch"], "camera pitch")
        if "fov_y" in camera_payload:
            fov_y = _finite_number(camera_payload["fov_y"], "camera fov_y")
            if not 0.0 < fov_y < 180.0:
                raise ValueError("camera fov_y must be between 0 and 180")
        if "near" in camera_payload:
            near = _finite_number(camera_payload["near"], "camera near")
            if near <= 0.0:
                raise ValueError("camera near must be positive")
        if "far" in camera_payload:
            far = _finite_number(camera_payload["far"], "camera far")
        if far <= near:
            raise ValueError("camera far must be greater than near")
        pitch = max(-MAX_PITCH, min(MAX_PITCH, pitch))

    ambient = scene.ambient
    background = scene.background
    sky = scene.sky
    fog_density = scene.fog_density
    light = scene.light
    point_light = scene.point_light
    shadow = scene.shadow.enabled
    color = scene.color.enabled
    post = scene.post.enabled
    bloom = scene.bloom.enabled
    sprites = scene.sprite.enabled
    culling = scene.culling.enabled
    if isinstance(environment_payload, Mapping):
        _unknown_keys(
            environment_payload,
            {
                "ambient",
                "background",
                "sky",
                "fog_density",
                "light",
                "point_light",
                "shadow",
                "color",
                "post",
                "bloom",
                "sprites",
                "culling",
            },
            "environment",
        )
        for key, label in (
            ("ambient", "environment ambient"),
            ("background", "environment background"),
            ("sky", "environment sky"),
        ):
            if key in environment_payload:
                value = _payload_vec3(environment_payload[key], label)
                if key == "ambient":
                    ambient = value
                elif key == "background":
                    background = value
                else:
                    sky = value
        if "fog_density" in environment_payload:
            fog_density = _finite_number(
                environment_payload["fog_density"], "environment fog_density"
            )
            if fog_density < 0.0:
                raise ValueError("environment fog_density must be non-negative")
        if "light" in environment_payload:
            raw = environment_payload["light"]
            if not isinstance(raw, Mapping):
                raise TypeError("environment light must be a mapping")
            _unknown_keys(raw, {"direction", "color", "intensity"}, "environment light")
            direction = light.direction
            light_color = light.color
            intensity = light.intensity
            if "direction" in raw:
                direction = _payload_vec3(raw["direction"], "light direction")
            if "color" in raw:
                light_color = _payload_vec3(raw["color"], "light color")
            if "intensity" in raw:
                intensity = _finite_number(raw["intensity"], "light intensity")
            light = DirectionalLight(
                direction=direction, color=light_color, intensity=intensity
            )
        if "point_light" in environment_payload:
            raw = environment_payload["point_light"]
            if raw is None:
                point_light = None
            elif isinstance(raw, Mapping):
                _unknown_keys(
                    raw,
                    {"position", "color", "intensity", "radius"},
                    "environment point_light",
                )
                base = point_light or PointLight()
                point_position = base.position
                point_color = base.color
                point_intensity = base.intensity
                radius = base.radius
                if "position" in raw:
                    point_position = _payload_vec3(
                        raw["position"], "point light position"
                    )
                if "color" in raw:
                    point_color = _payload_vec3(raw["color"], "point light color")
                if "intensity" in raw:
                    point_intensity = _finite_number(
                        raw["intensity"], "point light intensity"
                    )
                if "radius" in raw:
                    radius = _finite_number(raw["radius"], "point light radius")
                point_light = PointLight(
                    position=point_position,
                    color=point_color,
                    intensity=point_intensity,
                    radius=radius,
                )
            else:
                raise TypeError("environment point_light must be a mapping or null")
        toggles = {
            "shadow": (shadow, "shadow"),
            "color": (color, "color"),
            "post": (post, "post"),
            "bloom": (bloom, "bloom"),
            "sprites": (sprites, "sprites"),
            "culling": (culling, "culling"),
        }
        values: dict[str, bool] = {}
        for key, (_, label) in toggles.items():
            if key in environment_payload:
                value = environment_payload[key]
                if not isinstance(value, bool):
                    raise TypeError(f"environment {label} must be a boolean")
                values[key] = value
        shadow = values.get("shadow", shadow)
        color = values.get("color", color)
        post = values.get("post", post)
        bloom = values.get("bloom", bloom)
        sprites = values.get("sprites", sprites)
        culling = values.get("culling", culling)

    scene.camera.position = position
    scene.camera.yaw = yaw
    scene.camera.pitch = pitch
    scene.camera.fov_y = fov_y
    scene.camera.near = near
    scene.camera.far = far
    scene.ambient = ambient
    scene.background = background
    scene.sky = sky
    scene.fog_density = fog_density
    scene.light = light
    scene.point_light = point_light
    scene.shadow = ShadowSettings(enabled=shadow)
    scene.color = ColorSettings(enabled=color)
    scene.post = PostSettings(enabled=post)
    scene.bloom = BloomSettings(enabled=bloom)
    scene.sprite = SpriteSettings(enabled=sprites)
    scene.culling = CullingSettings(enabled=culling)
    return scene


def _type_name(value: object) -> str:
    return value.__name__ if isinstance(value, type) else str(value)


def component_schemas(
    component_types: ComponentTypes | None,
) -> dict[str, dict[str, object]]:
    """Return JSON-safe field hints for every game component type."""
    if not component_types:
        return {}
    schemas: dict[str, dict[str, object]] = {}
    for name in sorted(component_types):
        component_type = component_types[name]
        if not is_dataclass(component_type):
            schemas[name] = {
                "fields": [],
                "note": "custom to_dict/from_dict codec",
                "lifecycle": list(lifecycle_hooks(component_type)),
            }
            continue
        fields_list: list[dict[str, object]] = []
        for item in fields(component_type):
            required = item.default is MISSING and item.default_factory is MISSING
            default: object = None
            if item.default is not MISSING:
                default = (
                    item.default
                    if isinstance(item.default, (str, int, float, bool, type(None)))
                    else repr(item.default)
                )
            elif item.default_factory is not MISSING:
                default = "<factory>"
            fields_list.append(
                {
                    "name": item.name,
                    "type": _type_name(item.type),
                    "required": required,
                    "default": default if not required else None,
                }
            )
        schemas[name] = {
            "fields": fields_list,
            "lifecycle": list(lifecycle_hooks(component_type)),
        }
    return schemas


def _texture_preview(texture: TextureData, max_size: int = 64) -> str:
    scale = max(1, math.ceil(max(texture.width, texture.height) / max_size))
    thumb_width = max(1, texture.width // scale)
    thumb_height = max(1, texture.height // scale)
    pixels = bytearray()
    for y in range(thumb_height):
        source_y = min(texture.height - 1, (y * texture.height) // thumb_height)
        for x in range(thumb_width):
            source_x = min(texture.width - 1, (x * texture.width) // thumb_width)
            offset = (source_y * texture.width + source_x) * 4
            pixels.extend(texture.rgba[offset : offset + 4])
    encoded = png_bytes(thumb_width, thumb_height, bytes(pixels), flip_vertical=False)
    return "data:image/png;base64," + base64.b64encode(encoded).decode("ascii")


def _texture_metadata(texture: TextureData) -> dict:
    return {
        "name": texture.name,
        "width": texture.width,
        "height": texture.height,
        "preview": _texture_preview(texture),
    }


def _asset_metadata(registry: object | None, kind: object, payload: object) -> dict:
    if kind == "mesh" and isinstance(payload, MeshData):
        if payload.positions:
            xs, ys, zs = zip(*payload.positions)
            minimum = [min(xs), min(ys), min(zs)]
            maximum = [max(xs), max(ys), max(zs)]
        else:
            minimum = [0.0, 0.0, 0.0]
            maximum = [0.0, 0.0, 0.0]
        return {
            "vertices": len(payload.positions),
            "triangles": len(payload.indices) // 3,
            "has_uvs": bool(payload.uvs),
            "has_colors": bool(payload.colors),
            "skin_joints": len(payload.skin_joints),
            "bounds": {"min": minimum, "max": maximum},
        }
    if kind == "material" and isinstance(payload, Material):
        texture = (
            _texture_metadata(payload.texture)
            if isinstance(payload.texture, TextureData)
            else None
        )
        return {
            "color": [payload.color.x, payload.color.y, payload.color.z],
            "specular": payload.specular,
            "shininess": payload.shininess,
            "metallic": payload.metallic,
            "roughness": payload.roughness,
            "emissive": [payload.emissive.x, payload.emissive.y, payload.emissive.z],
            "has_texture": texture is not None,
            "texture": texture,
        }
    if kind == "texture" and isinstance(payload, TextureData):
        return _texture_metadata(payload)
    if kind == "prefab" and isinstance(payload, Prefab):
        try:
            dependencies = list(payload.asset_ids(registry))
        except (TypeError, ValueError):
            dependencies = []
        return {"node_count": payload.node_count, "asset_dependencies": dependencies}
    return {}


def asset_entries(registry: object | None) -> list[dict[str, object]]:
    """Return the registry's JSON-safe asset inventory for the editor."""
    if registry is None:
        return []
    try:
        records = list(registry)
    except TypeError:
        records = []
    if records:
        entries: list[dict[str, object]] = []
        for record in records:
            describe = getattr(record, "describe", None)
            if not callable(describe):
                continue
            try:
                entry = describe()
            except (TypeError, ValueError):
                continue
            if not isinstance(entry, dict):
                continue
            entry = dict(entry)
            entry["metadata"] = _asset_metadata(
                registry,
                getattr(record, "kind", None),
                getattr(record, "payload", None),
            )
            entries.append(entry)
        return sorted(entries, key=lambda item: str(item.get("id", "")))
    describe = getattr(registry, "describe", None)
    if not callable(describe):
        return []
    try:
        document = describe()
    except (TypeError, ValueError):
        return []
    if not isinstance(document, Mapping):
        return []
    assets = document.get("assets", [])
    if not isinstance(assets, list):
        return []
    return [item for item in assets if isinstance(item, Mapping)]


def _payload_id(registry: object | None, payload: object | None, kind: str) -> str | None:
    if payload is None or registry is None:
        return None
    for record in registry:  # type: ignore[union-attr]
        if getattr(record, "payload", None) is payload and getattr(record, "kind", None) == kind:
            return str(record.id)
    return None


def _asset_payload(
    registry: object | None,
    value: object,
    kind: str,
    label: str,
) -> object | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label} asset id must be a string or null")
    if not value.strip():
        raise ValueError(f"{label} asset id must be non-blank or null")
    if registry is None:
        raise ValueError(f"{label} needs an AssetRegistry")
    try:
        record = registry.require(value)  # type: ignore[union-attr]
    except KeyError as exc:
        raise ValueError(f"{label} asset {value!r} is not registered") from exc
    if record.kind != kind:
        raise ValueError(f"{label} asset {value!r} is not a {kind}")
    return record.payload


def _node_snapshot(node: Node) -> dict[str, object]:
    return {
        "name": node.name,
        "transform": node.transform,
        "mesh": node.mesh,
        "material": node.material,
        "visible": node.visible,
        "id": node.id,
        "tags": set(node.tags),
        "layer": node.layer,
        "components": copy.deepcopy(node.components),
        "prefab_link": node.prefab_link,
        "scene_group": node.scene_group,
        "children": [_node_snapshot(child) for child in node.children],
    }


def _snapshot_nodes(scene: Scene) -> list[dict[str, object]]:
    list(scene.traverse())
    return [_node_snapshot(child) for child in scene.root.children]


def _node_from_snapshot(data: Mapping[str, object]) -> Node:
    children = data["children"]
    if not isinstance(children, list):
        raise TypeError("editor snapshot children must be a list")
    node = Node(
        data["name"],
        transform=data["transform"],
        mesh=data["mesh"],
        material=data["material"],
        visible=data["visible"],
        id=data["id"],
        tags=set(data["tags"]),
        layer=data["layer"],
        components=copy.deepcopy(data["components"]),
        prefab_link=data.get("prefab_link"),
        scene_group=data.get("scene_group"),
    )
    for child in children:
        node.add_child(_node_from_snapshot(child))
    return node


def _restore_nodes(scene: Scene, snapshot: list[dict[str, object]]) -> None:
    for child in list(scene.root.children):
        scene.root.remove_child(child)
    for item in snapshot:
        scene.root.add_child(_node_from_snapshot(item))
    list(scene.traverse())


def _scene_snapshot(scene: Scene) -> dict[str, object]:
    return {
        "nodes": _snapshot_nodes(scene),
        "camera": {
            "position": scene.camera.position,
            "yaw": scene.camera.yaw,
            "pitch": scene.camera.pitch,
            "fov_y": scene.camera.fov_y,
            "near": scene.camera.near,
            "far": scene.camera.far,
        },
        "light": scene.light,
        "point_light": scene.point_light,
        "shadow": scene.shadow,
        "color": scene.color,
        "post": scene.post,
        "bloom": scene.bloom,
        "sprite": scene.sprite,
        "culling": scene.culling,
        "ambient": scene.ambient,
        "background": scene.background,
        "sky": scene.sky,
        "fog_density": scene.fog_density,
    }


def _restore_scene_state(scene: Scene, snapshot: dict[str, object]) -> None:
    _restore_nodes(scene, snapshot["nodes"])  # type: ignore[arg-type]
    camera = snapshot["camera"]
    if not isinstance(camera, Mapping):
        raise TypeError("editor camera snapshot must be a mapping")
    scene.camera.position = camera["position"]  # type: ignore[assignment]
    scene.camera.yaw = camera["yaw"]  # type: ignore[assignment]
    scene.camera.pitch = camera["pitch"]  # type: ignore[assignment]
    scene.camera.fov_y = camera["fov_y"]  # type: ignore[assignment]
    scene.camera.near = camera["near"]  # type: ignore[assignment]
    scene.camera.far = camera["far"]  # type: ignore[assignment]
    scene.light = snapshot["light"]  # type: ignore[assignment]
    scene.point_light = snapshot["point_light"]  # type: ignore[assignment]
    scene.shadow = snapshot["shadow"]  # type: ignore[assignment]
    scene.color = snapshot["color"]  # type: ignore[assignment]
    scene.post = snapshot["post"]  # type: ignore[assignment]
    scene.bloom = snapshot["bloom"]  # type: ignore[assignment]
    scene.sprite = snapshot["sprite"]  # type: ignore[assignment]
    scene.culling = snapshot["culling"]  # type: ignore[assignment]
    scene.ambient = snapshot["ambient"]  # type: ignore[assignment]
    scene.background = snapshot["background"]  # type: ignore[assignment]
    scene.sky = snapshot["sky"]  # type: ignore[assignment]
    scene.fog_density = snapshot["fog_density"]  # type: ignore[assignment]


class EditorHistory:
    """Bounded in-memory undo/redo for scene and environment edits."""

    def __init__(self, limit: int = 50) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("history limit must be a positive integer")
        self._limit = limit
        self._undo: list[dict[str, object]] = []
        self._redo: list[dict[str, object]] = []

    def describe(self) -> dict[str, int]:
        return {"undo": len(self._undo), "redo": len(self._redo), "limit": self._limit}

    def apply(self, scene: Scene, operation: Callable[[], T]) -> T:
        """Run one scene mutation and push its pre-edit snapshot."""
        before = _scene_snapshot(scene)
        try:
            result = operation()
        except Exception:
            _restore_scene_state(scene, before)
            raise
        self._push(before)
        return result

    def undo(self, scene: Scene) -> bool:
        if not self._undo:
            return False
        current = _scene_snapshot(scene)
        _restore_scene_state(scene, self._undo.pop())
        self._redo.append(current)
        return True

    def redo(self, scene: Scene) -> bool:
        if not self._redo:
            return False
        current = _scene_snapshot(scene)
        _restore_scene_state(scene, self._redo.pop())
        self._push(current)
        return True

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def _push(self, snapshot: dict[str, object]) -> None:
        self._undo.append(snapshot)
        if len(self._undo) > self._limit:
            self._undo.pop(0)
        self._redo.clear()


def _component_documents(node: Node) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    for component_type, component in sorted(
        node.components.items(),
        key=lambda item: (item[0].__module__, item[0].__qualname__),
    ):
        try:
            documents.append(component_to_dict(component))
        except (TypeError, ValueError) as exc:
            documents.append({"type": component_type.__name__, "error": str(exc)})
    return documents


def node_document(
    node: Node,
    selected_id: str | None,
    registry: object | None = None,
    selected_ids: set[str] | None = None,
) -> dict:
    transform = node.transform
    rotation = transform.rotation
    selected = (
        selected_ids
        if selected_ids is not None
        else ({selected_id} if selected_id is not None else set())
    )
    return {
        "id": node.id,
        "name": node.name,
        "parent_id": node.parent.id if node.parent is not None and node.parent.id else None,
        "children": [child.id for child in node.children],
        "visible": node.visible,
        "selected": node.id in selected,
        "tags": sorted(node.tags),
        "layer": node.layer,
        "components": sorted(component_type.__name__ for component_type in node.components),
        "component_data": _component_documents(node),
        "mesh": _payload_id(registry, node.mesh, "mesh"),
        "material": _payload_id(registry, node.material, "material"),
        "prefab_link": (
            node.prefab_link.to_dict() if node.prefab_link is not None else None
        ),
        "scene_group": (
            node.scene_group.to_dict() if node.scene_group is not None else None
        ),
        "transform": {
            "position": [transform.position.x, transform.position.y, transform.position.z],
            "rotation": [rotation.x, rotation.y, rotation.z, rotation.w],
            "scale": [transform.scale.x, transform.scale.y, transform.scale.z],
        },
        "world": list(node.world_matrix().flat()),
    }


def editor_document(
    scene: Scene,
    selected_id: str | None,
    prefabs: dict[str, Prefab],
    history: EditorHistory | None = None,
    prefab_entries: list[dict[str, object]] | None = None,
    scene_entries: list[dict[str, object]] | None = None,
    registry: object | None = None,
    assets: list[dict[str, object]] | None = None,
    component_types: list[str] | None = None,
    component_schema_documents: dict[str, dict[str, object]] | None = None,
    play_state: dict[str, object] | None = None,
    diff: dict[str, object] | None = None,
    trash: dict[str, list[dict[str, str]]] | None = None,
    selected_ids: list[str] | None = None,
) -> dict:
    ordered_ids = list(
        dict.fromkeys(
            selected_ids
            if selected_ids is not None
            else ([selected_id] if selected_id is not None else [])
        )
    )
    selected_set = set(ordered_ids)
    selection_details = selection_summary(scene, ordered_ids)
    nodes = [
        node_document(node, selected_id, registry, selected_set)
        for node in scene.traverse()
    ]
    selection = next((node for node in nodes if node["id"] == selected_id), None)
    prefab_instances = [
        {"id": node.id, **node.prefab_link.to_dict()}
        for node in scene.traverse()
        if node.prefab_link is not None
    ]
    prefab_instance_count = len(
        {
            (node.prefab_link.name, node.prefab_link.instance)
            for node in scene.traverse()
            if node.prefab_link is not None
        }
    )
    prefab_overrides = prefab_override_document(scene, prefabs, registry)
    prefab_override_count = sum(
        len(node["fields"])
        for group in prefab_overrides
        for node in group["nodes"]
    )
    scene_groups = scene_group_document(scene)
    return {
        "schema": EDITOR_SCHEMA_VERSION,
        "game": None,
        "roots": [node.id for node in scene.root.children],
        "selection": selection,
        "selected_ids": ordered_ids,
        "selection_count": len(ordered_ids),
        "selection_summary": selection_details,
        "nodes": nodes,
        "prefab_instances": prefab_instances,
        "prefab_instance_count": prefab_instance_count,
        "prefab_overrides": prefab_overrides,
        "prefab_override_count": prefab_override_count,
        "scene_groups": scene_groups,
        "scene_group_count": len(scene_groups),
        "scene_settings": scene_settings_document(scene),
        "prefabs": (
            prefab_entries
            if prefab_entries is not None
            else [
                {"name": name, "node_count": prefabs[name].node_count}
                for name in sorted(prefabs)
            ]
        ),
        "scenes": scene_entries if scene_entries is not None else [],
        "assets": assets if assets is not None else asset_entries(registry),
        "component_types": component_types if component_types is not None else [],
        "component_schemas": (
            component_schema_documents if component_schema_documents is not None else {}
        ),
        "play": (
            play_state
            if play_state is not None
            else {"active": False, "frames": 0, "step": 0.0}
        ),
        "diff": diff,
        "trash": trash if trash is not None else {"prefabs": [], "scenes": []},
        "actions": list(EDITOR_ACTIONS),
        "history": (
            history.describe()
            if history is not None
            else {"undo": 0, "redo": 0, "limit": 0}
        ),
    }


def find_node(scene: Scene, node_id: str) -> Node:
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("node id must be a non-blank string")
    node = scene.find_by_id(node_id)
    if node is None:
        raise KeyError(f"no scene node {node_id!r}")
    return node


def create_node(
    scene: Scene,
    payload: Mapping[str, object],
    parent: Node | None = None,
    registry: object | None = None,
) -> Node:
    """Create, validate and attach one node from an editor payload."""
    if not isinstance(scene, Scene):
        raise TypeError("create_node target must be a Scene")
    if not isinstance(payload, Mapping):
        raise TypeError("create_node payload must be a mapping")
    if parent is not None and not isinstance(parent, Node):
        raise TypeError("create_node parent must be a Node or None")
    visible = payload.get("visible", True)
    if not isinstance(visible, bool):
        raise TypeError("node visible must be a boolean")
    layer = payload.get("layer", "default")
    if not isinstance(layer, str) or not layer:
        raise ValueError("node layer must be a non-empty string")
    node = Node(
        _node_name(payload.get("name"), "node"),
        transform=_transform_from_payload(payload, None),
        mesh=_asset_payload(registry, payload.get("mesh"), "mesh", "node mesh"),
        material=_asset_payload(registry, payload.get("material"), "material", "node material"),
        visible=visible,
        id=_node_id(payload.get("id")),
        tags=_node_tags(payload.get("tags")),
        layer=layer,
    )
    if parent is None:
        scene.add(node)
    else:
        parent.add_child(node)
    list(scene.traverse())
    return node


def delete_node(scene: Scene, node: Node) -> Node:
    """Detach one node subtree or its whole prefab instance and return the parent."""
    if not isinstance(scene, Scene):
        raise TypeError("delete_node target must be a Scene")
    if node is scene.root:
        raise ValueError("cannot delete the scene root")
    if node.parent is None:
        raise ValueError("node is not attached to this scene")
    link = node.prefab_link
    if link is not None:
        roots = _prefab_instance_roots(scene, link)
        parent = roots[0].parent
        if parent is None:
            raise ValueError("prefab instance root is detached")
        for root in roots:
            parent.remove_child(root)
        return parent
    parent = node.parent
    parent.remove_child(node)
    return parent


def duplicate_node(scene: Scene, node: Node, name: str | None = None) -> Node:
    """Clone one node subtree as a sibling with fresh scene-allocated ids."""
    if not isinstance(scene, Scene):
        raise TypeError("duplicate_node target must be a Scene")
    if node is scene.root or node.parent is None:
        raise ValueError("cannot duplicate a detached node")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise ValueError("duplicate name must be a non-blank string or null")
    roots = Prefab.from_node(node, name="duplicate").instantiate(scene, parent=node.parent)
    list(scene.traverse())
    clone = roots[0]
    clone.name = name if name is not None else (f"{node.name} copy" if node.name else "copy")
    return clone


def reparent_node(scene: Scene, node: Node, parent: Node | None) -> Node:
    """Move one node subtree or its whole prefab instance below a new parent."""
    if not isinstance(scene, Scene):
        raise TypeError("reparent_node target must be a Scene")
    if node is scene.root or node.parent is None:
        raise ValueError("cannot reparent a detached node")
    if parent is not None and not isinstance(parent, Node):
        raise TypeError("reparent parent must be a Node or None")
    target = scene.root if parent is None else parent
    link = node.prefab_link
    roots = _prefab_instance_roots(scene, link) if link is not None else [node]
    for root in roots:
        if target is root or root.is_ancestor_of(target):
            raise ValueError("cannot move a prefab instance into itself")
    for root in roots:
        target.add_child(root)
    list(scene.traverse())
    return node


def transform_from_payload(node: Node, payload: dict) -> Transform:
    if not isinstance(payload, Mapping):
        raise TypeError("transform payload must be a mapping")
    return _transform_from_payload(payload, node.transform)


def set_node_properties(node: Node, payload: Mapping[str, object]) -> Node:
    """Update a node's name, visibility, tags or layer atomically."""
    if not isinstance(node, Node):
        raise TypeError("set_node target must be a Node")
    if not isinstance(payload, Mapping):
        raise TypeError("set_node payload must be a mapping")
    fields = [name for name in ("name", "visible", "tags", "layer") if name in payload]
    if not fields:
        raise ValueError("set_node needs name, visible, tags or layer")
    name = node.name
    visible = node.visible
    tags = set(node.tags)
    layer = node.layer
    if "name" in payload:
        value = payload.get("name")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("node name must be a non-blank string")
        name = value
    if "visible" in payload:
        value = payload.get("visible")
        if not isinstance(value, bool):
            raise TypeError("node visible must be a boolean")
        visible = value
    if "tags" in payload:
        tags = _node_tags(payload.get("tags"))
    if "layer" in payload:
        value = payload.get("layer")
        if not isinstance(value, str) or not value:
            raise ValueError("node layer must be a non-empty string")
        layer = value
    node.name = name
    node.visible = visible
    node.tags = tags
    node.layer = layer
    return node


def set_component(
    node: Node,
    type_name: object,
    data: object,
    component_types: ComponentTypes | None,
) -> object:
    """Decode and add/replace one component on a node."""
    if not isinstance(node, Node):
        raise TypeError("set_component target must be a Node")
    if not isinstance(type_name, str) or not type_name.strip():
        raise ValueError("component type must be a non-blank string")
    if component_types is None:
        raise ValueError("the game does not expose component_types")
    if type_name not in component_types:
        raise ValueError(f"unknown component type {type_name!r}")
    component = component_from_dict(
        {"type": type_name, "data": data}, component_types
    )
    node.components[type(component)] = component
    return component


def remove_component(
    node: Node,
    type_name: object,
    component_types: ComponentTypes | None,
) -> object:
    """Remove one named component from a node."""
    if not isinstance(node, Node):
        raise TypeError("remove_component target must be a Node")
    if not isinstance(type_name, str) or not type_name.strip():
        raise ValueError("component type must be a non-blank string")
    if component_types is None or type_name not in component_types:
        raise ValueError(f"unknown component type {type_name!r}")
    component_type = component_types[type_name]
    component = node.components.pop(component_type, None)
    if component is None:
        raise ValueError(f"node {node.id or node.name!r} has no {type_name} component")
    return component


def assign_assets(
    node: Node,
    payload: Mapping[str, object],
    registry: object | None,
) -> Node:
    """Assign or clear a node's mesh/material through registry asset ids."""
    if not isinstance(node, Node):
        raise TypeError("assign_assets target must be a Node")
    if not isinstance(payload, Mapping):
        raise TypeError("assign_assets payload must be a mapping")
    fields = [name for name in ("mesh", "material") if name in payload]
    if not fields:
        raise ValueError("assign_assets needs a mesh or material field")
    if "mesh" in payload:
        node.mesh = _asset_payload(registry, payload.get("mesh"), "mesh", "node mesh")
    if "material" in payload:
        node.material = _asset_payload(
            registry, payload.get("material"), "material", "node material"
        )
    return node


def save_prefab(scene: Scene, node: Node, name: str, prefabs: dict[str, Prefab]) -> Prefab:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("prefab name must be a non-blank string")
    prefab = Prefab.from_node(node, name=name)
    prefabs[name] = prefab
    return prefab


def _next_instance_prefix(scene: Scene, name: str) -> str:
    used = {
        node.prefab_link.instance
        for node in scene.traverse()
        if node.prefab_link is not None
    }
    candidate = name
    counter = 2
    while candidate in used:
        candidate = f"{name}-{counter}"
        counter += 1
    return candidate


def _prefab_instance_roots(scene: Scene, link: PrefabLink) -> list[Node]:
    roots = [node for node in scene.traverse() if node.prefab_link == link]
    if not roots:
        raise KeyError(f"no prefab instance {link.instance!r} in the scene")
    parent = roots[0].parent
    if parent is None:
        raise ValueError("prefab instance root is detached")
    if any(node.parent is not parent for node in roots):
        raise ValueError("prefab instance roots must share a parent")
    return [node for node in parent.children if node in roots]


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
    prefab = prefabs[name]
    prefix = instance if instance is not None else _next_instance_prefix(scene, name)
    roots = prefab.instantiate(scene, parent=parent, instance=prefix)
    link = PrefabLink(name, prefix)
    for root in roots:
        root.prefab_link = link
    # Materialize IDs for instances attached below a non-root parent.
    list(scene.traverse())
    return roots


def revert_prefab_instance(
    scene: Scene,
    node: Node,
    prefabs: dict[str, Prefab],
) -> list[Node]:
    """Replace the linked instance group with a fresh prefab template."""
    link = node.prefab_link
    if link is None:
        raise ValueError("node is not a prefab instance")
    prefab = prefabs.get(link.name)
    if prefab is None:
        raise KeyError(f"no saved prefab {link.name!r}")
    roots = _prefab_instance_roots(scene, link)
    parent = roots[0].parent
    if parent is None:
        raise ValueError("prefab instance root is detached")
    index = min(parent.children.index(root) for root in roots)
    for root in roots:
        parent.remove_child(root)
    created = prefab.instantiate(scene, parent=parent, instance=link.instance)
    for root in created:
        root.prefab_link = link
    for offset, root in enumerate(created):
        parent.children.remove(root)
        parent.children.insert(index + offset, root)
        root.parent = parent
    list(scene.traverse())
    return created


def apply_prefab_instance(
    scene: Scene,
    node: Node,
    prefabs: dict[str, Prefab],
) -> Prefab:
    """Capture the linked instance group as the new prefab definition."""
    link = node.prefab_link
    if link is None:
        raise ValueError("node is not a prefab instance")
    roots = _prefab_instance_roots(scene, link)
    prefab = Prefab.from_nodes(roots, name=link.name)
    prefabs[link.name] = prefab
    return prefab


def rename_prefab_links(scene: Scene, old: str, new: str) -> int:
    """Point every instance link at a renamed prefab; return the updates made."""
    updated = 0
    for node in scene.traverse():
        link = node.prefab_link
        if link is not None and link.name == old:
            node.prefab_link = PrefabLink(new, link.instance)
            updated += 1
    return updated


def _instance_groups(scene: Scene) -> dict[PrefabLink, list[Node]]:
    groups: dict[PrefabLink, list[Node]] = {}
    for node in scene.traverse():
        link = node.prefab_link
        if link is not None:
            groups.setdefault(link, []).append(node)
    ordered: dict[PrefabLink, list[Node]] = {}
    for link, roots in groups.items():
        parent = roots[0].parent
        if parent is not None and all(root.parent is parent for root in roots):
            ordered[link] = [node for node in parent.children if node in roots]
        else:
            ordered[link] = roots
    return ordered


def _containing_instance_link(node: Node) -> PrefabLink | None:
    current: Node | None = node
    while current is not None:
        if current.prefab_link is not None:
            return current.prefab_link
        current = current.parent
    return None


def _map_prefab_nodes(
    prefab: Prefab, roots: list[Node]
) -> list[tuple[Node, Node]]:
    pairs: list[tuple[Node, Node]] = []
    if len(prefab.roots) != len(roots):
        return pairs

    def walk(template: Node, instance: Node) -> None:
        pairs.append((template, instance))
        if len(template.children) != len(instance.children):
            return
        for template_child, instance_child in zip(
            template.children, instance.children
        ):
            if (
                template_child.prefab_link is not None
                or instance_child.prefab_link is not None
            ):
                continue
            walk(template_child, instance_child)

    for template_root, instance_root in zip(prefab.roots, roots):
        walk(template_root, instance_root)
    return pairs


def _node_override_values(
    node: Node, registry: object | None
) -> dict[str, object]:
    transform = node.transform
    values: dict[str, object] = {
        "name": node.name,
        "visible": node.visible,
        "tags": sorted(node.tags),
        "layer": node.layer,
        "transform.position": [
            transform.position.x,
            transform.position.y,
            transform.position.z,
        ],
        "transform.rotation": [
            transform.rotation.x,
            transform.rotation.y,
            transform.rotation.z,
            transform.rotation.w,
        ],
        "transform.scale": [
            transform.scale.x,
            transform.scale.y,
            transform.scale.z,
        ],
    }
    if registry is not None:
        values["mesh"] = _payload_id(registry, node.mesh, "mesh")
        values["material"] = _payload_id(registry, node.material, "material")
    for component_type, component in sorted(
        node.components.items(),
        key=lambda item: (item[0].__module__, item[0].__qualname__),
    ):
        name = component_type.__name__
        try:
            values[f"components.{name}"] = component_to_dict(component)["data"]
        except (TypeError, ValueError) as exc:
            values[f"components.{name}"] = {"error": str(exc)}
    return values


def prefab_override_document(
    scene: Scene,
    prefabs: dict[str, Prefab],
    registry: object | None = None,
) -> list[dict[str, object]]:
    """Return field-level diffs for every linked scene instance group."""
    reports: list[dict[str, object]] = []
    groups = _instance_groups(scene)
    for link, roots in sorted(
        groups.items(), key=lambda item: (item[0].name, item[0].instance)
    ):
        report: dict[str, object] = {
            "prefab": link.name,
            "instance": link.instance,
            "roots": [root.id for root in roots],
            "nodes": [],
        }
        prefab = prefabs.get(link.name)
        if prefab is None:
            report["error"] = f"no saved prefab {link.name!r}"
            reports.append(report)
            continue
        if roots[0].parent is None or any(
            root.parent is not roots[0].parent for root in roots
        ):
            report["error"] = "prefab instance roots must share a parent"
            reports.append(report)
            continue
        if len(prefab.roots) != len(roots):
            report["error"] = "prefab instance root count does not match prefab"
            reports.append(report)
            continue
        node_reports: list[dict[str, object]] = []
        for template, instance in _map_prefab_nodes(prefab, roots):
            before = _node_override_values(template, registry)
            after = _node_override_values(instance, registry)
            fields: dict[str, dict[str, object]] = {}
            for field in sorted(set(before) | set(after)):
                if (
                    field not in before
                    or field not in after
                    or before[field] != after[field]
                ):
                    fields[field] = {
                        "template": before.get(field),
                        "instance": after.get(field),
                    }
            if fields:
                node_reports.append(
                    {
                        "id": instance.id,
                        "template_id": template.id,
                        "fields": fields,
                    }
                )
        report["nodes"] = node_reports
        if node_reports:
            reports.append(report)
    return reports


def _node_path(
    roots: tuple[Node, ...], target: Node
) -> tuple[int, ...] | None:
    def find(node: Node, path: tuple[int, ...]) -> tuple[int, ...] | None:
        if node is target:
            return path
        for index, child in enumerate(node.children):
            found = find(child, path + (index,))
            if found is not None:
                return found
        return None

    for root_index, root in enumerate(roots):
        found = find(root, (root_index,))
        if found is not None:
            return found
    return None


def _follow_path(roots: tuple[Node, ...], path: tuple[int, ...]) -> Node:
    node = roots[path[0]]
    for index in path[1:]:
        node = node.children[index]
    return node


def _resolve_prefab_override(
    scene: Scene,
    node_id: str,
    field: object,
    prefabs: dict[str, Prefab],
    registry: object | None,
) -> tuple[Prefab, Node, Node]:
    if not isinstance(field, str) or not field.strip():
        raise ValueError("override field must be a non-blank string")
    node = find_node(scene, node_id)
    link = _containing_instance_link(node)
    if link is None:
        raise ValueError("node is not part of a prefab instance")
    prefab = prefabs.get(link.name)
    if prefab is None:
        raise KeyError(f"no saved prefab {link.name!r}")
    roots = _prefab_instance_roots(scene, link)
    pairs = _map_prefab_nodes(prefab, roots)
    pair = next(
        (
            (template, instance)
            for template, instance in pairs
            if instance is node
        ),
        None,
    )
    if pair is None:
        raise ValueError("node is not mapped to the prefab template")
    template, instance = pair
    before = _node_override_values(template, registry)
    after = _node_override_values(instance, registry)
    if field not in before and field not in after:
        raise ValueError(f"unknown override field {field!r}")
    if field in before and field in after and before[field] == after[field]:
        raise ValueError(f"field {field!r} has no prefab override")
    return prefab, template, instance


def _copy_node_field(source: Node, target: Node, field: str) -> None:
    if field == "name":
        target.name = source.name
    elif field == "visible":
        target.visible = source.visible
    elif field == "tags":
        target.tags = set(source.tags)
    elif field == "layer":
        target.layer = source.layer
    elif field == "transform.position":
        target.transform = Transform(
            position=source.transform.position,
            rotation=target.transform.rotation,
            scale=target.transform.scale,
        )
    elif field == "transform.rotation":
        target.transform = Transform(
            position=target.transform.position,
            rotation=source.transform.rotation,
            scale=target.transform.scale,
        )
    elif field == "transform.scale":
        target.transform = Transform(
            position=target.transform.position,
            rotation=target.transform.rotation,
            scale=source.transform.scale,
        )
    elif field == "mesh":
        target.mesh = source.mesh
    elif field == "material":
        target.material = source.material
    elif field.startswith("components."):
        type_name = field.split(".", 1)[1]
        found = False
        source_component: object | None = None
        for component_type, component in source.components.items():
            if component_type.__name__ == type_name:
                found = True
                source_component = component
                break
        for existing_type in list(target.components):
            if existing_type.__name__ == type_name:
                target.components.pop(existing_type)
        if found:
            target.components[type(source_component)] = copy.deepcopy(
                source_component
            )
    else:
        raise ValueError(f"unknown override field {field!r}")


def revert_prefab_override(
    scene: Scene,
    node_id: str,
    field: object,
    prefabs: dict[str, Prefab],
    registry: object | None = None,
) -> Node:
    """Restore one field on a linked instance from its prefab template."""
    _, template, instance = _resolve_prefab_override(
        scene, node_id, field, prefabs, registry
    )
    _copy_node_field(template, instance, field)  # type: ignore[arg-type]
    return instance


def apply_prefab_override(
    scene: Scene,
    node_id: str,
    field: object,
    prefabs: dict[str, Prefab],
    registry: object | None = None,
) -> Prefab:
    """Return a template copy with one instance field applied to it."""
    prefab, template, instance = _resolve_prefab_override(
        scene, node_id, field, prefabs, registry
    )
    path = _node_path(prefab.roots, template)
    if path is None:
        raise ValueError("prefab template node is not reachable")
    updated = prefab.copy()
    _copy_node_field(
        instance,
        _follow_path(updated.roots, path),
        field,  # type: ignore[arg-type]
    )
    return updated


def _clone_scene_node(node: Node) -> Node:
    clone = Node(
        node.name,
        transform=node.transform,
        mesh=node.mesh,
        material=node.material,
        visible=node.visible,
        id=node.id,
        tags=set(node.tags),
        layer=node.layer,
        components=copy.deepcopy(node.components),
        prefab_link=node.prefab_link,
        scene_group=node.scene_group,
    )
    for child in node.children:
        clone.add_child(_clone_scene_node(child))
    return clone


def scene_group_document(scene: Scene) -> list[dict[str, object]]:
    """Return one JSON-safe entry for every additive scene group container."""
    groups: list[dict[str, object]] = []
    for node in scene.traverse():
        group = node.scene_group
        if group is None:
            continue
        parent = node.parent
        groups.append(
            {
                "id": node.id,
                "name": group.name,
                "parent_id": (
                    parent.id
                    if parent is not None and parent is not scene.root
                    else None
                ),
                "node_count": max(0, sum(1 for _ in node.traverse()) - 1),
                "roots": [child.id for child in node.children],
            }
        )
    return groups


def _rename_colliding_ids(node: Node, used: set[str]) -> None:
    if node.id:
        base = node.id
        candidate = base
        counter = 2
        while candidate in used:
            candidate = f"{base}-{counter}"
            counter += 1
        node.id = candidate
        used.add(candidate)
    for child in node.children:
        _rename_colliding_ids(child, used)


def add_scene(
    scene: Scene,
    name: str,
    library: SceneLibrary,
    parent: Node | None = None,
) -> Node:
    """Add one saved scene as a named child group of the current scene."""
    if not isinstance(scene, Scene):
        raise TypeError("add_scene target must be a Scene")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("scene name must be a non-blank string")
    if not isinstance(library, SceneLibrary):
        raise TypeError("add_scene needs a SceneLibrary")
    if parent is not None and not isinstance(parent, Node):
        raise TypeError("scene group parent must be a Node or None")
    loaded = library.load(name)
    container = Node(name, scene_group=SceneGroup(name))
    used = {node.id for node in scene.traverse() if node.id}
    for root in loaded.root.children:
        clone = _clone_scene_node(root)
        _rename_colliding_ids(clone, used)
        container.add_child(clone)
    target = scene.root if parent is None else parent
    if target is scene.root:
        scene.add(container)
    else:
        target.add_child(container)
    list(scene.traverse())
    return container


def unload_scene(scene: Scene, node: Node) -> Node:
    """Remove one scene group container and return its former parent."""
    if not isinstance(scene, Scene):
        raise TypeError("unload_scene target must be a Scene")
    if node is scene.root or node.parent is None:
        raise ValueError("cannot unload a detached node")
    if node.scene_group is None:
        raise ValueError("node is not a scene group")
    parent = node.parent
    parent.remove_child(node)
    return parent


def _copy_scene_settings(source: Scene, target: Scene) -> None:
    target.camera.position = source.camera.position
    target.camera.yaw = source.camera.yaw
    target.camera.pitch = source.camera.pitch
    target.camera.fov_y = source.camera.fov_y
    target.camera.near = source.camera.near
    target.camera.far = source.camera.far
    target.light = source.light
    target.point_light = source.point_light
    target.shadow = source.shadow
    target.color = source.color
    target.post = source.post
    target.bloom = source.bloom
    target.sprite = source.sprite
    target.culling = source.culling
    target.ambient = source.ambient
    target.background = source.background
    target.sky = source.sky
    target.fog_density = source.fog_density


def save_scene_group(scene: Scene, node: Node, library: SceneLibrary) -> str:
    """Write one scene group's children back to its library scene in place."""
    if not isinstance(scene, Scene):
        raise TypeError("save_scene_group target must be a Scene")
    if not isinstance(library, SceneLibrary):
        raise TypeError("save_scene_group needs a SceneLibrary")
    group = node.scene_group
    if group is None:
        raise ValueError("node is not a scene group")
    temp = Scene()
    _copy_scene_settings(scene, temp)
    for child in node.children:
        temp.add(_clone_scene_node(child))
    library.save(group.name, temp)
    return group.name


def _top_level_selected(scene: Scene, ids: list[str]) -> list[Node]:
    wanted = set(ids)
    selected_nodes: list[Node] = []
    seen: set[str] = set()
    for node_id in ids:
        if node_id in seen:
            continue
        seen.add(node_id)
        node = scene.find_by_id(node_id)
        if node is None:
            raise KeyError(f"no node {node_id!r}")
        if node is scene.root:
            raise ValueError("cannot edit the scene root")
        selected_ancestor = False
        ancestor = node.parent
        while ancestor is not None and ancestor is not scene.root:
            if ancestor.id in wanted:
                selected_ancestor = True
                break
            ancestor = ancestor.parent
        if not selected_ancestor:
            selected_nodes.append(node)
    return selected_nodes


def _parent_linear_inverse(node: Node) -> tuple[tuple[float, ...], ...]:
    if node.parent is None:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    matrix = list(node.parent.world_matrix().flat())
    a, b, c = matrix[0], matrix[4], matrix[8]
    d, e, f = matrix[1], matrix[5], matrix[9]
    g, h, i = matrix[2], matrix[6], matrix[10]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(determinant) < 1e-12:
        raise ValueError("cannot move a node below a zero-scale parent")
    inverse = 1.0 / determinant
    return (
        (
            (e * i - f * h) * inverse,
            (c * h - b * i) * inverse,
            (b * f - c * e) * inverse,
        ),
        (
            (f * g - d * i) * inverse,
            (a * i - c * g) * inverse,
            (c * d - a * f) * inverse,
        ),
        (
            (d * h - e * g) * inverse,
            (b * g - a * h) * inverse,
            (a * e - b * d) * inverse,
        ),
    )


def _world_position(node: Node) -> Vec3:
    matrix = list(node.world_matrix().flat())
    return Vec3(matrix[12], matrix[13], matrix[14])


def _quat_from_basis(x: Vec3, y: Vec3, z: Vec3) -> Quat:
    m00, m01, m02 = x.x, y.x, z.x
    m10, m11, m12 = x.y, y.y, z.y
    m20, m21, m22 = x.z, y.z, z.z
    trace = m00 + m11 + m22
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        return Quat(
            0.25 * scale,
            (m21 - m12) / scale,
            (m02 - m20) / scale,
            (m10 - m01) / scale,
        ).normalized()
    if m00 > m11 and m00 > m22:
        scale = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        return Quat(
            (m21 - m12) / scale,
            0.25 * scale,
            (m01 + m10) / scale,
            (m02 + m20) / scale,
        ).normalized()
    if m11 > m22:
        scale = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        return Quat(
            (m02 - m20) / scale,
            (m01 + m10) / scale,
            0.25 * scale,
            (m12 + m21) / scale,
        ).normalized()
    scale = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
    return Quat(
        (m10 - m01) / scale,
        (m02 + m20) / scale,
        (m12 + m21) / scale,
        0.25 * scale,
    ).normalized()


def _parent_rotation(node: Node) -> Quat:
    if node.parent is None:
        return Quat()
    matrix = list(node.parent.world_matrix().flat())
    x = Vec3(matrix[0], matrix[1], matrix[2]).normalized()
    raw_y = Vec3(matrix[4], matrix[5], matrix[6])
    y = (raw_y - x * x.dot(raw_y)).normalized()
    z = x.cross(y).normalized()
    return _quat_from_basis(x, y, z)


def _world_to_local_position(node: Node, position: Vec3) -> Vec3:
    if node.parent is None:
        return position
    matrix = list(node.parent.world_matrix().flat())
    offset = [
        position.x - matrix[12],
        position.y - matrix[13],
        position.z - matrix[14],
    ]
    inverse = _parent_linear_inverse(node)
    return Vec3(
        inverse[0][0] * offset[0]
        + inverse[0][1] * offset[1]
        + inverse[0][2] * offset[2],
        inverse[1][0] * offset[0]
        + inverse[1][1] * offset[1]
        + inverse[1][2] * offset[2],
        inverse[2][0] * offset[0]
        + inverse[2][1] * offset[1]
        + inverse[2][2] * offset[2],
    )


def _apply_group_transform(
    node: Node,
    pivot: Vec3,
    rotation: Quat | None,
    scale: float | None,
) -> None:
    world = _world_position(node)
    offset = world - pivot
    if rotation is not None:
        offset = rotation.rotate(offset)
    if scale is not None:
        offset = offset * scale
    new_world = pivot + offset
    transform = node.transform
    rotation_value = transform.rotation
    if rotation is not None:
        parent_rotation = _parent_rotation(node)
        rotation_value = (
            parent_rotation.conjugate()
            * rotation
            * parent_rotation
            * transform.rotation
        ).normalized()
    scale_value = transform.scale
    if scale is not None:
        scale_value = Vec3(
            scale_value.x * scale,
            scale_value.y * scale,
            scale_value.z * scale,
        )
    node.transform = Transform(
        _world_to_local_position(node, new_world),
        rotation_value,
        scale_value,
    )


def transform_selection(
    scene: Scene,
    ids: list[str],
    payload: Mapping[str, object],
) -> list[Node]:
    """Apply world position delta, local deltas, or a centroid group transform."""
    if not isinstance(scene, Scene):
        raise TypeError("transform_selection target must be a Scene")
    if not ids:
        raise ValueError("select at least one node")
    if not isinstance(payload, Mapping):
        raise TypeError("transform_selection payload must be a mapping")
    unknown = sorted(
        set(payload)
        - {
            "action",
            "position",
            "rotation",
            "scale",
            "pivot",
            "group_rotation",
            "group_scale",
        }
    )
    if unknown:
        raise ValueError(
            f"transform_selection has unknown fields: {', '.join(unknown)}"
        )
    if {"pivot", "group_rotation", "group_scale"} & set(payload):
        if "pivot" not in payload:
            raise ValueError("group transform_selection needs pivot")
        if any(name in payload for name in ("position", "rotation", "scale")):
            raise ValueError(
                "group transform_selection cannot mix position/rotation/scale"
            )
        pivot = Vec3(*_finite_array(payload["pivot"], 3, "group pivot"))
        group_rotation = None
        if "group_rotation" in payload:
            x, y, z, w = _finite_array(
                payload["group_rotation"], 4, "group rotation"
            )
            group_rotation = Quat(w, x, y, z).normalized()
        group_scale = None
        if "group_scale" in payload:
            group_scale = _finite_number(payload["group_scale"], "group scale")
            if group_scale <= 0.0:
                raise ValueError("group scale must be positive")
        if group_rotation is None and group_scale is None:
            raise ValueError(
                "group transform_selection needs group_rotation or group_scale"
            )
        nodes = _top_level_selected(scene, ids)
        for node in nodes:
            _apply_group_transform(node, pivot, group_rotation, group_scale)
        return nodes
    fields = [name for name in ("position", "rotation", "scale") if name in payload]
    if not fields:
        raise ValueError("transform_selection needs position, rotation or scale")
    position = (
        _finite_array(payload["position"], 3, "selection position")
        if "position" in payload
        else None
    )
    rotation = (
        _finite_array(payload["rotation"], 4, "selection rotation")
        if "rotation" in payload
        else None
    )
    scale = (
        _finite_array(payload["scale"], 3, "selection scale")
        if "scale" in payload
        else None
    )
    rotation_delta = (
        Quat(rotation[3], rotation[0], rotation[1], rotation[2]).normalized()
        if rotation is not None
        else None
    )
    nodes = _top_level_selected(scene, ids)
    for node in nodes:
        transform = node.transform
        position_value = transform.position
        rotation_value = transform.rotation
        scale_value = transform.scale
        if position is not None:
            inverse = _parent_linear_inverse(node)
            local = [
                inverse[0][0] * position[0]
                + inverse[0][1] * position[1]
                + inverse[0][2] * position[2],
                inverse[1][0] * position[0]
                + inverse[1][1] * position[1]
                + inverse[1][2] * position[2],
                inverse[2][0] * position[0]
                + inverse[2][1] * position[1]
                + inverse[2][2] * position[2],
            ]
            position_value = Vec3(
                position_value.x + local[0],
                position_value.y + local[1],
                position_value.z + local[2],
            )
        if rotation_delta is not None:
            rotation_value = (rotation_value * rotation_delta).normalized()
        if scale is not None:
            scale_value = Vec3(
                scale_value.x * scale[0],
                scale_value.y * scale[1],
                scale_value.z * scale[2],
            )
        node.transform = Transform(position_value, rotation_value, scale_value)
    return nodes


def toggle_selection_visible(scene: Scene, ids: list[str]) -> list[Node]:
    """Flip the visibility of every selected node in one operation."""
    if not isinstance(scene, Scene):
        raise TypeError("toggle_selection_visible target must be a Scene")
    if not ids:
        raise ValueError("select at least one node")
    nodes: list[Node] = []
    seen: set[str] = set()
    for node_id in ids:
        if node_id in seen:
            continue
        seen.add(node_id)
        node = scene.find_by_id(node_id)
        if node is None:
            raise KeyError(f"no node {node_id!r}")
        if node is scene.root:
            raise ValueError("cannot edit the scene root")
        nodes.append(node)
    for node in nodes:
        node.visible = not node.visible
    return nodes


def delete_selection(scene: Scene, ids: list[str]) -> Node:
    """Delete all top-level selected nodes and return a surviving parent."""
    if not isinstance(scene, Scene):
        raise TypeError("delete_selection target must be a Scene")
    if not ids:
        raise ValueError("select at least one node")
    roots = _top_level_selected(scene, ids)
    deleted_parent: Node | None = None
    seen_links: set[PrefabLink] = set()
    for node in roots:
        if node.parent is None:
            continue
        link = node.prefab_link
        if link is not None:
            if link in seen_links:
                continue
            seen_links.add(link)
        deleted_parent = delete_node(scene, node)
    return deleted_parent if deleted_parent is not None else scene.root


def _selected_nodes(scene: Scene, ids: list[str]) -> list[Node]:
    if not ids:
        raise ValueError("select at least one node")
    nodes: list[Node] = []
    seen: set[str] = set()
    for node_id in ids:
        if node_id in seen:
            continue
        seen.add(node_id)
        node = scene.find_by_id(node_id)
        if node is None:
            raise KeyError(f"no node {node_id!r}")
        if node is scene.root:
            raise ValueError("cannot edit the scene root")
        nodes.append(node)
    return nodes


def set_selection_properties(
    scene: Scene,
    ids: list[str],
    payload: Mapping[str, object],
) -> list[Node]:
    """Apply the same name/visible/tags/layer values to every selected node."""
    if not isinstance(scene, Scene):
        raise TypeError("set_selection_properties target must be a Scene")
    nodes = _selected_nodes(scene, ids)
    for node in nodes:
        set_node_properties(node, payload)
    return nodes


def set_selection_transform(
    scene: Scene,
    ids: list[str],
    payload: Mapping[str, object],
) -> list[Node]:
    """Apply the same absolute local transform values to every selected node."""
    if not isinstance(scene, Scene):
        raise TypeError("set_selection_transform target must be a Scene")
    nodes = _selected_nodes(scene, ids)
    for node in nodes:
        node.transform = transform_from_payload(node, dict(payload))
    return nodes


def _shared_field(values: list[object]) -> dict[str, object]:
    shared = bool(values) and all(value == values[0] for value in values[1:])
    return {"shared": shared, "value": values[0] if shared else None}


def selection_summary(scene: Scene, ids: list[str]) -> dict[str, object]:
    """Return shared versus mixed inspector values for the selection set."""
    nodes: list[Node] = []
    for node_id in ids:
        node = scene.find_by_id(node_id)
        if node is not None and node is not scene.root:
            nodes.append(node)
    if not nodes:
        empty = {"shared": False, "value": None}
        return {
            "count": 0,
            "mixed": [],
            "name": dict(empty),
            "visible": dict(empty),
            "tags": dict(empty),
            "layer": dict(empty),
            "transform": {
                "position": dict(empty),
                "rotation": dict(empty),
                "scale": dict(empty),
            },
        }
    fields = {
        "name": _shared_field([node.name for node in nodes]),
        "visible": _shared_field([node.visible for node in nodes]),
        "tags": _shared_field([sorted(node.tags) for node in nodes]),
        "layer": _shared_field([node.layer for node in nodes]),
        "transform": {
            "position": _shared_field(
                [
                    [
                        node.transform.position.x,
                        node.transform.position.y,
                        node.transform.position.z,
                    ]
                    for node in nodes
                ]
            ),
            "rotation": _shared_field(
                [
                    [
                        node.transform.rotation.x,
                        node.transform.rotation.y,
                        node.transform.rotation.z,
                        node.transform.rotation.w,
                    ]
                    for node in nodes
                ]
            ),
            "scale": _shared_field(
                [
                    [
                        node.transform.scale.x,
                        node.transform.scale.y,
                        node.transform.scale.z,
                    ]
                    for node in nodes
                ]
            ),
        },
    }
    mixed = [
        name
        for name in ("name", "visible", "tags", "layer")
        if not fields[name]["shared"]
    ]
    for name in ("position", "rotation", "scale"):
        if not fields["transform"][name]["shared"]:
            mixed.append(f"transform.{name}")
    return {"count": len(nodes), "mixed": mixed, **fields}
