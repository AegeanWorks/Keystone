"""Scene graph: hierarchical transforms, visibility, camera and directional light."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from keystone.camera import PerspectiveCamera
from keystone.math3d import Mat4, Quat, Vec3


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
    """A named transform node with optional renderable payload and children."""

    name: str = ""
    transform: Transform = field(default_factory=Transform)
    mesh: object | None = None
    material: object | None = None
    visible: bool = True
    parent: Node | None = field(default=None, repr=False)
    children: list[Node] = field(default_factory=list)

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


@dataclass
class Scene:
    """Root node, active camera, one directional light and atmosphere settings."""

    root: Node = field(default_factory=Node)
    camera: PerspectiveCamera = field(default_factory=PerspectiveCamera)
    light: DirectionalLight = field(default_factory=DirectionalLight)
    ambient: Vec3 = Vec3(0.16, 0.17, 0.2)
    background: Vec3 = Vec3(0.045, 0.055, 0.075)
    sky: Vec3 = Vec3(0.01, 0.015, 0.04)
    fog_density: float = 0.012

    def add(self, node: Node) -> Node:
        self.root.add_child(node)
        return node

    def traverse(self) -> Iterator[Node]:
        return self.root.traverse()
