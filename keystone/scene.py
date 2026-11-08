"""Scene graph: hierarchical transforms, identity, components, camera and light."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

from keystone.camera import PerspectiveCamera
from keystone.math3d import Mat4, Quat, Vec3

T = TypeVar("T")


def _finite_vec3(value: object, label: str) -> Vec3:
    if not isinstance(value, Vec3):
        raise TypeError(f"{label} must be a Vec3")
    if not all(math.isfinite(component) for component in (value.x, value.y, value.z)):
        raise ValueError(f"{label} must contain finite components")
    return value


@dataclass(frozen=True, slots=True)
class Transform:
    """Translation, rotation and non-uniform scale composed as T * R * S."""

    position: Vec3 = Vec3(0.0, 0.0, 0.0)
    rotation: Quat = Quat()
    scale: Vec3 = Vec3(1.0, 1.0, 1.0)

    def __post_init__(self) -> None:
        _finite_vec3(self.position, "transform position")
        _finite_vec3(self.scale, "transform scale")
        if not isinstance(self.rotation, Quat):
            raise TypeError("transform rotation must be a Quat")
        if not all(math.isfinite(component) for component in (self.rotation.w, self.rotation.x, self.rotation.y, self.rotation.z)):
            raise ValueError("transform rotation must contain finite components")
        if self.rotation.w ** 2 + self.rotation.x ** 2 + self.rotation.y ** 2 + self.rotation.z ** 2 < 1e-12:
            raise ValueError("transform rotation must be a non-zero quaternion")

    def matrix(self) -> Mat4:
        return (
            Mat4.translation(self.position.x, self.position.y, self.position.z)
            * self.rotation.to_mat4()
            * Mat4.scale(self.scale.x, self.scale.y, self.scale.z)
        )


@dataclass(frozen=True, slots=True)
class PrefabLink:
    """Editor-facing link from a scene node to the prefab instance it came from."""

    name: str
    instance: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("prefab link name must be a non-blank string")
        if not isinstance(self.instance, str) or not self.instance.strip():
            raise ValueError("prefab link instance must be a non-blank string")
        if ":" in self.instance:
            raise ValueError("prefab link instance must not contain ':'")

    def to_dict(self) -> dict[str, str]:
        """Return the JSON-safe link document."""
        return {"name": self.name, "instance": self.instance}

    @classmethod
    def from_dict(cls, data: object) -> PrefabLink:
        """Validate one link document."""
        if not isinstance(data, Mapping):
            raise TypeError("prefab link must be a mapping")
        unknown = sorted(set(data) - {"name", "instance"})
        if unknown:
            raise ValueError(f"prefab link has unknown fields: {', '.join(unknown)}")
        return cls(data.get("name"), data.get("instance"))  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class SceneGroup:
    """Editor-facing metadata for one additively loaded scene container."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("scene group name must be a non-blank string")

    def to_dict(self) -> dict[str, str]:
        """Return the JSON-safe group document."""
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: object) -> SceneGroup:
        """Validate one scene group document."""
        if not isinstance(data, Mapping):
            raise TypeError("scene group must be a mapping")
        unknown = sorted(set(data) - {"name"})
        if unknown:
            raise ValueError(
                f"scene group has unknown fields: {', '.join(unknown)}"
            )
        return cls(data.get("name"))  # type: ignore[arg-type]


@dataclass(eq=False)
class Node:
    """A named transform node with identity, tags, components and children."""

    name: str = ""
    transform: Transform = field(default_factory=Transform)
    mesh: object | None = None
    material: object | None = None
    visible: bool = True
    parent: Node | None = field(default=None, repr=False)
    children: list[Node] = field(default_factory=list)
    id: str = ""
    tags: set[str] = field(default_factory=set)
    layer: str = "default"
    components: dict[type, object] = field(default_factory=dict)
    prefab_link: PrefabLink | None = None
    scene_group: SceneGroup | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("node name must be a string")
        if not isinstance(self.transform, Transform):
            raise TypeError("node transform must be a Transform")
        if not isinstance(self.visible, bool):
            raise TypeError("node visible must be a boolean")
        if self.parent is not None and not isinstance(self.parent, Node):
            raise TypeError("node parent must be a Node or None")
        if isinstance(self.children, (str, bytes)) or not isinstance(self.children, (list, tuple)):
            raise TypeError("node children must be a list of Node instances")
        children = list(self.children)
        for child in children:
            if not isinstance(child, Node):
                raise TypeError("node children must be a list of Node instances")
        self.children = children
        if not isinstance(self.id, str):
            raise TypeError("node id must be a string")
        if self.id and not self.id.strip():
            raise ValueError("node id must not be blank")
        if not isinstance(self.layer, str) or not self.layer:
            raise ValueError("node layer must be a non-empty string")
        if isinstance(self.tags, str):
            raise TypeError("tags must be a collection of strings, not a string")
        self.tags = set(self.tags)
        for tag in self.tags:
            if not isinstance(tag, str) or not tag:
                raise ValueError("tags must be non-empty strings")
        self.components = dict(self.components)
        for component_type, component_value in self.components.items():
            if not isinstance(component_type, type):
                raise TypeError("component keys must be types")
            if not isinstance(component_value, component_type):
                raise TypeError("component value must match its key type")
        if self.prefab_link is not None and not isinstance(self.prefab_link, PrefabLink):
            raise TypeError("node prefab_link must be a PrefabLink or None")
        if self.scene_group is not None and not isinstance(self.scene_group, SceneGroup):
            raise TypeError("node scene_group must be a SceneGroup or None")
        if self.parent is not None:
            if self.parent is self:
                raise ValueError("a node cannot be its own parent")
            ancestor = self.parent
            while ancestor is not None:
                if ancestor is self:
                    raise ValueError("node parent chain would create a cycle")
                ancestor = ancestor.parent
            if self not in self.parent.children:
                self.parent.children.append(self)
        for child in self.children:
            if child is self:
                raise ValueError("a node cannot be its own child")
            if child.parent is not None and child.parent is not self:
                raise ValueError("child node already has a different parent")
            child.parent = self

    def add_tag(self, tag: str) -> None:
        if not isinstance(tag, str) or not tag:
            raise ValueError("tags must be non-empty strings")
        self.tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        self.tags.discard(tag)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def add_component(self, component: T) -> T:
        if component is None:
            raise TypeError("component must not be None")
        self.components[type(component)] = component
        return component

    def get_component(self, component_type: type[T]) -> T | None:
        value = self.components.get(component_type)
        return value if isinstance(value, component_type) else None

    def require_component(self, component_type: type[T]) -> T:
        value = self.get_component(component_type)
        if value is None:
            raise KeyError(f"node {self.id or self.name!r} has no {component_type.__name__}")
        return value

    def has_component(self, component_type: type) -> bool:
        return component_type in self.components

    def remove_component(self, component_type: type[T]) -> T | None:
        value = self.components.pop(component_type, None)
        return value if isinstance(value, component_type) else None

    def add_child(self, child: Node) -> None:
        if child is self or child.is_ancestor_of(self):
            raise ValueError("adding this child would create a cycle")
        if child.parent is self:
            return
        new_ids = [node.id for node in child.traverse() if node.id]
        if len(set(new_ids)) != len(new_ids):
            raise ValueError("child subtree has a duplicate node id")
        if new_ids:
            wanted = set(new_ids)
            ancestor = self
            while ancestor.parent is not None:
                ancestor = ancestor.parent
            subtree_ids = {id(node) for node in child.traverse()}
            for node in ancestor.traverse():
                if id(node) in subtree_ids:
                    continue
                if node.id and node.id in wanted:
                    raise ValueError(f"duplicate node id: {node.id!r}")
        if child.parent is not None:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: Node) -> None:
        if child not in self.children:
            raise ValueError("node is not a child of this parent")
        self.children.remove(child)
        child.parent = None

    def is_ancestor_of(self, other: Node) -> bool:
        node = other.parent
        while node is not None:
            if node is self:
                return True
            node = node.parent
        return False

    def world_matrix(self) -> Mat4:
        chain: list[Node] = []
        node: Node | None = self
        while node is not None:
            chain.append(node)
            node = node.parent
        matrix = Mat4.identity()
        for item in reversed(chain):
            matrix = matrix * item.transform.matrix()
        return matrix

    def world_visible(self) -> bool:
        node: Node | None = self
        while node is not None:
            if not node.visible:
                return False
            node = node.parent
        return True

    def traverse(self) -> Iterator[Node]:
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(list(node.children)))


@dataclass(frozen=True, slots=True)
class DirectionalLight:
    """A direction the light travels in, plus linear color and intensity."""

    direction: Vec3 = Vec3(-0.4, -1.0, -0.6)
    color: Vec3 = Vec3(1.0, 0.97, 0.9)
    intensity: float = 1.0

    def __post_init__(self) -> None:
        _finite_vec3(self.direction, "directional light direction")
        _finite_vec3(self.color, "directional light color")
        if not isinstance(self.intensity, (int, float)) or isinstance(self.intensity, bool):
            raise TypeError("directional light intensity must be a number")
        if not math.isfinite(self.intensity):
            raise ValueError("directional light intensity must be finite")
        if self.intensity < 0.0:
            raise ValueError("directional light intensity must be non-negative")
        if self.direction.length_squared() < 1e-12:
            raise ValueError("directional light needs a non-zero direction")

    def unit_direction(self) -> Vec3:
        return self.direction.normalized()

    def radiance(self) -> Vec3:
        return self.color * self.intensity


@dataclass(frozen=True, slots=True)
class PointLight:
    """A local light with quadratic falloff, used for torches and lamps."""

    position: Vec3 = Vec3(0.0, 0.0, 0.0)
    color: Vec3 = Vec3(1.0, 0.8, 0.5)
    intensity: float = 1.0
    radius: float = 10.0

    def __post_init__(self) -> None:
        _finite_vec3(self.position, "point light position")
        _finite_vec3(self.color, "point light color")
        if not isinstance(self.radius, (int, float)) or isinstance(self.radius, bool):
            raise TypeError("point light radius must be a number")
        if not isinstance(self.intensity, (int, float)) or isinstance(self.intensity, bool):
            raise TypeError("point light intensity must be a number")
        if not math.isfinite(self.radius) or not math.isfinite(self.intensity):
            raise ValueError("point light radius and intensity must be finite")
        if self.radius <= 0.0:
            raise ValueError("point light radius must be positive")
        if self.intensity < 0.0:
            raise ValueError("point light intensity must be non-negative")


@dataclass(frozen=True, slots=True)
class ShadowSettings:
    """Deterministic directional shadow-map toggle (fixed 1024 map, bias 0.005)."""

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ColorSettings:
    """Deterministic sRGB-correct linear pipeline toggle (in-shader, pow 2.2)."""

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class PostSettings:
    """Deterministic post color-grade toggle (in-shader exposure + vignette)."""

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BloomSettings:
    """Deterministic bloom glow toggle (in-shader luminance threshold)."""

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class SpriteSettings:
    """Deterministic GPU point-sprite toggle (one instanced quad per particle)."""

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class CullingSettings:
    """Deterministic CPU view-frustum culling toggle (color pass only)."""

    enabled: bool = True


def _root_node() -> Node:
    return Node("", id="root")


@dataclass
class Scene:
    """Root node, identity allocation, queries, camera, lights and atmosphere."""

    root: Node = field(default_factory=_root_node)
    camera: PerspectiveCamera = field(default_factory=PerspectiveCamera)
    light: DirectionalLight = field(default_factory=DirectionalLight)
    point_light: PointLight | None = None
    shadow: ShadowSettings = field(default_factory=ShadowSettings)
    color: ColorSettings = field(default_factory=ColorSettings)
    post: PostSettings = field(default_factory=PostSettings)
    bloom: BloomSettings = field(default_factory=BloomSettings)
    sprite: SpriteSettings = field(default_factory=SpriteSettings)
    culling: CullingSettings = field(default_factory=CullingSettings)
    ambient: Vec3 = Vec3(0.16, 0.17, 0.2)
    background: Vec3 = Vec3(0.045, 0.055, 0.075)
    sky: Vec3 = Vec3(0.01, 0.015, 0.04)
    fog_density: float = 0.012
    _next_id: int = field(default=1, init=False, repr=False)

    def add(self, node: Node) -> Node:
        if node.parent is not None:
            raise ValueError("node is already attached; remove it from its parent first")
        self._prepare(node)
        self.root.add_child(node)
        return node

    def traverse(self) -> Iterator[Node]:
        self._prepare(self.root)
        return self.root.traverse()

    def query(
        self,
        *,
        name: str | None = None,
        tag: str | None = None,
        layer: str | None = None,
        component: type | None = None,
    ) -> list[Node]:
        """Return every node matching all supplied filters."""
        matches = []
        for node in self.traverse():
            if name is not None and node.name != name:
                continue
            if tag is not None and tag not in node.tags:
                continue
            if layer is not None and node.layer != layer:
                continue
            if component is not None and component not in node.components:
                continue
            matches.append(node)
        return matches

    def find(
        self,
        *,
        name: str | None = None,
        tag: str | None = None,
        layer: str | None = None,
        component: type | None = None,
    ) -> Node | None:
        """Return the first node matching all supplied filters."""
        matches = self.query(name=name, tag=tag, layer=layer, component=component)
        return matches[0] if matches else None

    def find_by_id(self, node_id: str) -> Node | None:
        for node in self.traverse():
            if node.id == node_id:
                return node
        return None

    def _used_ids(self, exclude: Node | None = None) -> set[str]:
        if exclude is self.root:
            return set()
        detached = exclude is not None and exclude.parent is None
        used = set()
        for node in self.root.traverse():
            if not detached and exclude is not None and (node is exclude or exclude.is_ancestor_of(node)):
                continue
            if node.id:
                used.add(node.id)
        return used

    def restore_next_id(self, value: int) -> None:
        """Advance the deterministic ID counter after loading a snapshot."""
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("next id must be a positive integer")
        self._next_id = max(self._next_id, value)

    def _prepare(self, node: Node) -> None:
        used = self._used_ids(exclude=node)
        subtree = list(node.traverse())
        for item in subtree:
            if item.id:
                if item.id in used:
                    raise ValueError(f"duplicate node id: {item.id!r}")
                used.add(item.id)
        for item in subtree:
            if item.id:
                continue
            while True:
                candidate = f"node-{self._next_id}"
                self._next_id += 1
                if candidate not in used:
                    break
            item.id = candidate
            used.add(candidate)
