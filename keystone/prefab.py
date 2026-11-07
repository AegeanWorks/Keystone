"""Deterministic prefabs: capture a scene subtree and instantiate reusable copies.

A prefab is a detached template. Instances get fresh, caller-prefixed or
scene-allocated IDs, while names, transforms, tags, layers, components and
mesh/material payloads are preserved. The template is never attached.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from keystone.scene import Node, Scene

__all__ = ["Prefab"]


def _clone_template(node: Node) -> Node:
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
    )
    for child in node.children:
        clone.add_child(_clone_template(child))
    return clone


def _collect_ids(node: Node) -> list[str]:
    return [item.id for item in node.traverse() if item.id]


@dataclass(frozen=True, slots=True)
class Prefab:
    """An immutable-name, detached template of one or more scene subtrees."""

    name: str
    roots: tuple[Node, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("prefab name must be a non-blank string")
        if not isinstance(self.roots, (tuple, list)) or not self.roots:
            raise ValueError("prefab needs at least one root node")
        roots = tuple(self.roots)
        ids: list[str] = []
        for root in roots:
            if not isinstance(root, Node):
                raise TypeError("prefab roots must be Node instances")
            if root.parent is not None:
                raise ValueError("prefab roots must be detached")
            ids.extend(_collect_ids(root))
        if len(ids) != len(set(ids)):
            raise ValueError("prefab node ids must be unique across roots")
        object.__setattr__(self, "roots", roots)

    @classmethod
    def from_node(cls, node: Node, name: str | None = None) -> Prefab:
        """Capture one detached subtree."""
        if not isinstance(node, Node):
            raise TypeError("prefab source must be a Node")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("prefab name must be a non-blank string")
        return cls(name if name is not None else (node.name or "prefab"), (_clone_template(node),))

    @classmethod
    def from_scene(cls, scene: Scene, name: str = "prefab") -> Prefab:
        """Capture every child of a scene root as a multi-root prefab."""
        if not isinstance(scene, Scene):
            raise TypeError("prefab source must be a Scene")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("prefab name must be a non-blank string")
        roots = tuple(_clone_template(child) for child in scene.root.children)
        return cls(name, roots)

    @property
    def node_count(self) -> int:
        return sum(1 for root in self.roots for _ in root.traverse())

    def instantiate(
        self,
        scene: Scene,
        parent: Node | None = None,
        instance: str | None = None,
    ) -> list[Node]:
        """Attach fresh copies to a scene, returning the new root nodes.

        With ``instance`` set, every ID becomes ``instance:original-id`` (or
        ``instance:node-N`` when the template node had no ID). Without it, IDs
        are left blank so the scene's deterministic allocator assigns them.
        """
        if not isinstance(scene, Scene):
            raise TypeError("prefab target must be a Scene")
        if parent is not None and not isinstance(parent, Node):
            raise TypeError("prefab parent must be a Node or None")
        if instance is not None:
            if not isinstance(instance, str) or not instance.strip():
                raise ValueError("instance prefix must be a non-blank string")
            if ":" in instance:
                raise ValueError("instance prefix must not contain ':'")
        target_parent = parent if parent is not None else scene.root
        counter = 0
        created: list[Node] = []

        def clone_for_instance(node: Node) -> Node:
            nonlocal counter
            if instance is None:
                new_id = ""
            elif node.id:
                new_id = f"{instance}:{node.id}"
            else:
                counter += 1
                new_id = f"{instance}:node-{counter}"
            clone = Node(
                node.name,
                transform=node.transform,
                mesh=node.mesh,
                material=node.material,
                visible=node.visible,
                id=new_id,
                tags=set(node.tags),
                layer=node.layer,
                components=copy.deepcopy(node.components),
            )
            for child in node.children:
                clone.add_child(clone_for_instance(child))
            return clone

        for root in self.roots:
            clone = clone_for_instance(root)
            if target_parent is scene.root:
                scene.add(clone)
            else:
                target_parent.add_child(clone)
            created.append(clone)
        return created

    def describe(self) -> dict:
        """Return a JSON-safe structural summary for AI clients and tooling."""

        def entry(node: Node) -> dict:
            return {
                "id": node.id,
                "name": node.name,
                "tags": sorted(node.tags),
                "layer": node.layer,
                "components": sorted(component_type.__name__ for component_type in node.components),
                "children": [entry(child) for child in node.children],
            }

        return {
            "schema": 1,
            "name": self.name,
            "node_count": self.node_count,
            "nodes": [entry(root) for root in self.roots],
        }
