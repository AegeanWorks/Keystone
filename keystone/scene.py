"""Scene graph: hierarchical transforms, identity, components, camera and light."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TypeVar

from keystone.camera import PerspectiveCamera
from keystone.math3d import Mat4, Quat, Vec3

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Transform:
    """Translation, rotation and non-uniform scale composed as T * R * S."""

    position: Vec3 = Vec3(0.0, 0.0, 0.0)
    rotation: Quat = Quat()
    scale: Vec3 = Vec3(1.0, 1.0, 1.0)

    def matrix(self) -> Mat4:
        return (
            Mat4.translation(self.position.x, self.position.y, self.position.z)
            * self.rotation.to_mat4()
            * Mat4.scale(self.scale.x, self.scale.y, self.scale.z)
        )


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

    def __post_init__(self) -> None:
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
        local = self.transform.matrix()
        return self.parent.world_matrix() * local if self.parent else local

    def world_visible(self) -> bool:
        return self.visible and (self.parent is None or self.parent.world_visible())

    def traverse(self) -> Iterator[Node]:
        yield self
        for child in self.children:
            yield from child.traverse()


@dataclass(frozen=True, slots=True)
class DirectionalLight:
    """A direction the light travels in, plus linear color and intensity."""

    direction: Vec3 = Vec3(-0.4, -1.0, -0.6)
    color: Vec3 = Vec3(1.0, 0.97, 0.9)
    intensity: float = 1.0

    def __post_init__(self) -> None:
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
    ambient: Vec3 = Vec3(0.16, 0.17, 0.2)
    background: Vec3 = Vec3(0.045, 0.055, 0.075)
    sky: Vec3 = Vec3(0.01, 0.015, 0.04)
    fog_density: float = 0.012
    _next_id: int = field(default=1, init=False, repr=False)

    def add(self, node: Node) -> Node:
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
