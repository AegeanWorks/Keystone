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
    Scene,
    ShadowSettings,
    SpriteSettings,
    Transform,
)
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
            schemas[name] = {"fields": [], "note": "custom to_dict/from_dict codec"}
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
        schemas[name] = {"fields": fields_list}
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
) -> dict:
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
        "component_data": _component_documents(node),
        "mesh": _payload_id(registry, node.mesh, "mesh"),
        "material": _payload_id(registry, node.material, "material"),
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
) -> dict:
    nodes = [node_document(node, selected_id, registry) for node in scene.traverse()]
    selection = next((node for node in nodes if node["id"] == selected_id), None)
    return {
        "schema": EDITOR_SCHEMA_VERSION,
        "game": None,
        "roots": [node.id for node in scene.root.children],
        "selection": selection,
        "nodes": nodes,
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
    """Detach one node subtree and return its former parent."""
    if not isinstance(scene, Scene):
        raise TypeError("delete_node target must be a Scene")
    if node is scene.root:
        raise ValueError("cannot delete the scene root")
    if node.parent is None:
        raise ValueError("node is not attached to this scene")
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
    """Move one node subtree below a new parent, or the scene root."""
    if not isinstance(scene, Scene):
        raise TypeError("reparent_node target must be a Scene")
    if node is scene.root or node.parent is None:
        raise ValueError("cannot reparent a detached node")
    if parent is not None and not isinstance(parent, Node):
        raise TypeError("reparent parent must be a Node or None")
    target = scene.root if parent is None else parent
    if target is node:
        raise ValueError("cannot parent a node to itself")
    target.add_child(node)
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
