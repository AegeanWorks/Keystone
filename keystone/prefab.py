"""Deterministic prefabs: capture, persist and instantiate reusable subtrees.

A prefab is a detached template. Instances get fresh, caller-prefixed or
scene-allocated IDs, while names, transforms, tags, layers, components and
mesh/material payloads are preserved. Persistent prefabs reference registered
mesh/material assets by id and require an explicit component type map on load.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from keystone.component_codec import (
    ComponentTypes,
    component_from_dict,
    component_to_dict,
)
from keystone.math3d import Quat, Vec3
from keystone.scene import Node, PrefabLink, Scene, Transform
from keystone.schema import PREFAB_SCHEMA_VERSION
from keystone.serialization import read_json, write_json_atomic

__all__ = ["PREFAB_SCHEMA_VERSION", "Prefab"]


def _copy_template(node: Node) -> Node:
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
        prefab_base=None,
        scene_group=None,
    )
    for child in node.children:
        clone.add_child(_copy_template(child))
    return clone


def _normalize_template(
    node: Node,
    inherited: str | None,
    prefab_name: str,
    is_root: bool,
) -> None:
    link = node.prefab_link
    effective = link.instance if link is not None else inherited
    if effective is not None and node.id:
        node.id = node.id.removeprefix(f"{effective}:")
    if link is not None:
        if is_root:
            node.prefab_link = None
        else:
            if link.name == prefab_name:
                raise ValueError(f"prefab {prefab_name!r} cannot reference itself")
            instance = link.instance
            if inherited is not None:
                if instance == inherited:
                    raise ValueError(
                        "nested prefab instance cannot reuse its parent prefix"
                    )
                marker = f"{inherited}."
                if not instance.startswith(marker):
                    raise ValueError(
                        "nested prefab instance must be inside its parent instance"
                    )
                instance = instance[len(marker):]
            node.prefab_link = PrefabLink(link.name, instance)
    for child in node.children:
        _normalize_template(child, effective, prefab_name, False)


def _capture_template(node: Node, prefab_name: str) -> Node:
    root_prefix = node.prefab_link.instance if node.prefab_link is not None else None
    clone = _copy_template(node)
    _normalize_template(clone, root_prefix, prefab_name, True)
    return clone


def _allocate_instance_prefix(scene: Scene, base: str = "prefab") -> str:
    used_instances = {
        node.prefab_link.instance
        for node in scene.traverse()
        if node.prefab_link is not None
    }
    used_ids = {node.id for node in scene.traverse() if node.id}
    candidate = base
    counter = 2
    while candidate in used_instances or any(
        node_id.startswith(f"{candidate}:") for node_id in used_ids
    ):
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _collect_ids(node: Node) -> list[str]:
    return [item.id for item in node.traverse() if item.id]


def _asset_id(
    registry: object | None,
    payload: object | None,
    label: str,
    kind: str,
) -> str | None:
    if payload is None:
        return None
    if registry is None:
        raise ValueError(f"{label} needs an AssetRegistry")
    for record in registry:  # type: ignore[union-attr]
        if (
            getattr(record, "payload", None) is payload
            and getattr(record, "kind", None) == kind
        ):
            return str(record.id)
    raise ValueError(f"{label} is not registered as a {kind} asset")


def _transform_to_dict(transform: Transform) -> dict:
    rotation = transform.rotation
    return {
        "position": [transform.position.x, transform.position.y, transform.position.z],
        "rotation": [rotation.x, rotation.y, rotation.z, rotation.w],
        "scale": [transform.scale.x, transform.scale.y, transform.scale.z],
    }


def _transform_from_dict(value: object) -> Transform:
    if not isinstance(value, Mapping):
        raise TypeError("prefab transform must be a mapping")
    position = value.get("position", [0.0, 0.0, 0.0])
    rotation = value.get("rotation", [0.0, 0.0, 0.0, 1.0])
    scale = value.get("scale", [1.0, 1.0, 1.0])
    if not (isinstance(position, (list, tuple)) and len(position) == 3):
        raise ValueError("prefab transform position must have three values")
    if not (isinstance(rotation, (list, tuple)) and len(rotation) == 4):
        raise ValueError("prefab transform rotation must have four values")
    if not (isinstance(scale, (list, tuple)) and len(scale) == 3):
        raise ValueError("prefab transform scale must have three values")
    return Transform(
        position=Vec3(float(position[0]), float(position[1]), float(position[2])),
        rotation=Quat(float(rotation[3]), float(rotation[0]), float(rotation[1]), float(rotation[2])),
        scale=Vec3(float(scale[0]), float(scale[1]), float(scale[2])),
    )


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
            if root.prefab_link is not None:
                raise ValueError("prefab roots must not carry prefab links")
            for node in root.traverse():
                link = node.prefab_link
                if link is not None and link.name == self.name:
                    raise ValueError(f"prefab {self.name!r} cannot reference itself")
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
        selected = name if name is not None else (node.name or "prefab")
        return cls(selected, (_capture_template(node, selected),))

    @classmethod
    def from_nodes(
        cls,
        nodes: list[Node] | tuple[Node, ...],
        name: str | None = None,
    ) -> Prefab:
        """Capture several subtrees as a deterministic multi-root prefab."""
        if not isinstance(nodes, (list, tuple)) or not nodes:
            raise ValueError("prefab needs at least one source node")
        first = nodes[0]
        if not isinstance(first, Node):
            raise TypeError("prefab sources must be Node instances")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("prefab name must be a non-blank string")
        selected = name if name is not None else (first.name or "prefab")
        roots: list[Node] = []
        for node in nodes:
            if not isinstance(node, Node):
                raise TypeError("prefab sources must be Node instances")
            roots.append(_capture_template(node, selected))
        return cls(selected, tuple(roots))

    @classmethod
    def from_scene(cls, scene: Scene, name: str = "prefab") -> Prefab:
        """Capture every child of a scene root as a multi-root prefab."""
        if not isinstance(scene, Scene):
            raise TypeError("prefab source must be a Scene")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("prefab name must be a non-blank string")
        roots = tuple(
            _capture_template(child, name) for child in scene.root.children
        )
        return cls(name, roots)

    def copy(self, name: str | None = None) -> Prefab:
        """Return a detached template copy, preserving nested links and IDs."""
        selected = name if name is not None else self.name
        return Prefab(selected, tuple(_copy_template(root) for root in self.roots))

    @property
    def node_count(self) -> int:
        return sum(1 for root in self.roots for _ in root.traverse())

    def asset_ids(self, registry: object) -> tuple[str, ...]:
        """Return the mesh/material asset ids referenced by this prefab."""
        found: set[str] = set()

        def visit(node: Node) -> None:
            for label, payload in (("mesh", node.mesh), ("material", node.material)):
                asset_id = _asset_id(
                    registry, payload, f"{node.id or node.name!r} {label}", label
                )
                if asset_id is not None:
                    found.add(asset_id)
            for child in node.children:
                visit(child)

        for root in self.roots:
            visit(root)
        return tuple(sorted(found))

    def to_dict(self, registry: object | None = None) -> dict:
        """Serialize to versioned JSON; mesh/material payloads need registered assets."""

        def entry(node: Node) -> dict:
            return {
                "id": node.id,
                "name": node.name,
                "visible": node.visible,
                "tags": sorted(node.tags),
                "layer": node.layer,
                "prefab_link": (
                    node.prefab_link.to_dict() if node.prefab_link is not None else None
                ),
                "transform": _transform_to_dict(node.transform),
                "mesh": _asset_id(
                    registry, node.mesh, f"{node.id or node.name!r} mesh", "mesh"
                ),
                "material": _asset_id(
                    registry, node.material, f"{node.id or node.name!r} material", "material"
                ),
                "components": [
                    component_to_dict(component)
                    for _, component in sorted(
                        node.components.items(),
                        key=lambda item: (item[0].__module__, item[0].__qualname__),
                    )
                ],
                "children": [entry(child) for child in node.children],
            }

        return {
            "schema": PREFAB_SCHEMA_VERSION,
            "name": self.name,
            "roots": [entry(root) for root in self.roots],
        }

    @classmethod
    def from_dict(
        cls,
        data: object,
        registry: object | None = None,
        component_types: ComponentTypes | None = None,
    ) -> Prefab:
        """Load versioned JSON; asset ids resolve through the registry."""
        if not isinstance(data, Mapping):
            raise TypeError("prefab document must be a mapping")
        if "schema" not in data:
            raise ValueError("prefab document needs a schema")
        schema = data["schema"]
        if (
            isinstance(schema, bool)
            or not isinstance(schema, int)
            or schema not in (1, PREFAB_SCHEMA_VERSION)
        ):
            raise ValueError(f"unsupported prefab schema {schema}")
        name = data.get("name")
        raw_roots = data.get("roots")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("prefab name must be a non-blank string")
        if not isinstance(raw_roots, list) or not raw_roots:
            raise ValueError("prefab roots must be a non-empty list")

        def resolve(value: object, kind: str, label: str) -> object | None:
            if value is None:
                return None
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} asset id must be a non-blank string or null")
            if registry is None:
                raise ValueError(f"{label} needs an AssetRegistry")
            record = registry.require(value)  # type: ignore[union-attr]
            if getattr(record, "kind", None) != kind:
                raise ValueError(f"{label} asset {value!r} is not a {kind}")
            return getattr(record, "payload", None)

        def node(value: object) -> Node:
            if not isinstance(value, Mapping):
                raise TypeError("prefab node must be a mapping")
            node_id = value.get("id", "")
            node_name = value.get("name", "")
            visible = value.get("visible", True)
            layer = value.get("layer", "default")
            tags = value.get("tags", [])
            if not isinstance(node_id, str):
                raise TypeError("prefab node id must be a string")
            if not isinstance(node_name, str):
                raise TypeError("prefab node name must be a string")
            if not isinstance(visible, bool):
                raise TypeError("prefab node visible must be a boolean")
            if not isinstance(layer, str) or not layer:
                raise ValueError("prefab node layer must be a non-empty string")
            if not isinstance(tags, (list, tuple)) or any(not isinstance(tag, str) for tag in tags):
                raise TypeError("prefab node tags must be a list of strings")
            raw_components = value.get("components", [])
            if not isinstance(raw_components, list):
                raise TypeError("prefab node components must be a list")
            components = {}
            for item in raw_components:
                component = component_from_dict(item, component_types)
                if type(component) in components:
                    raise ValueError(
                        f"prefab node {node_id!r} has duplicate {type(component).__name__} components"
                    )
                components[type(component)] = component
            raw_link = value.get("prefab_link")
            prefab_link = (
                PrefabLink.from_dict(raw_link) if raw_link is not None else None
            )
            built = Node(
                node_name,
                transform=_transform_from_dict(value.get("transform", {})),
                mesh=resolve(value.get("mesh"), "mesh", f"{node_id!r} mesh"),
                material=resolve(value.get("material"), "material", f"{node_id!r} material"),
                visible=visible,
                id=node_id,
                tags=set(tags),
                layer=layer,
                components=components,
                prefab_link=prefab_link,
            )
            raw_children = value.get("children", [])
            if not isinstance(raw_children, list):
                raise TypeError("prefab node children must be a list")
            for child in raw_children:
                built.add_child(node(child))
            return built

        return cls(name, tuple(node(root) for root in raw_roots))

    def save(self, path: str | Path, registry: object | None = None) -> Path:
        """Write a versioned JSON prefab atomically."""
        target = Path(path)
        write_json_atomic(target, self.to_dict(registry), backup=False)
        return target

    @classmethod
    def load(
        cls,
        path: str | Path,
        registry: object | None = None,
        component_types: ComponentTypes | None = None,
    ) -> Prefab:
        """Load a versioned JSON prefab from disk."""
        source = Path(path)
        try:
            data = read_json(source)
        except (OSError, ValueError) as exc:
            raise ValueError(f"could not read prefab from {source}: {exc}") from exc
        return cls.from_dict(data, registry=registry, component_types=component_types)

    def instantiate(
        self,
        scene: Scene,
        parent: Node | None = None,
        instance: str | None = None,
    ) -> list[Node]:
        """Attach fresh copies to a scene, returning the new root nodes.

        With ``instance`` set, outer IDs use ``instance:id`` and each nested
        prefab group uses ``instance.relative:id`` while its link instance is
        rebased to the same effective prefix. Without a prefix, simple prefabs
        keep blank IDs for the scene allocator; prefabs with nested links get a
        deterministic ``prefab`` prefix so nested groups stay unique.
        """
        if not isinstance(scene, Scene):
            raise TypeError("prefab target must be a Scene")
        if parent is not None and not isinstance(parent, Node):
            raise TypeError("prefab parent must be a Node or None")
        if instance is None and any(
            node.prefab_link is not None
            for root in self.roots
            for node in root.traverse()
        ):
            instance = _allocate_instance_prefix(scene)
        if instance is not None:
            if not isinstance(instance, str) or not instance.strip():
                raise ValueError("instance prefix must be a non-blank string")
            if ":" in instance:
                raise ValueError("instance prefix must not contain ':'")
        target_parent = parent if parent is not None else scene.root
        counter = 0
        created: list[Node] = []

        def clone_for_instance(node: Node, inherited: str | None) -> Node:
            nonlocal counter
            link = node.prefab_link
            effective = inherited
            if link is not None:
                effective = (
                    f"{inherited}.{link.instance}" if inherited else link.instance
                )
            if instance is None:
                new_id = ""
            elif node.id:
                new_id = f"{effective}:{node.id}"
            else:
                counter += 1
                new_id = f"{effective}:node-{counter}"
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
                prefab_link=(
                    PrefabLink(link.name, effective)
                    if link is not None and effective is not None
                    else None
                ),
            )
            for child in node.children:
                clone.add_child(clone_for_instance(child, effective))
            return clone

        for root in self.roots:
            clone = clone_for_instance(root, instance)
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
                "prefab_link": (
                    node.prefab_link.to_dict() if node.prefab_link is not None else None
                ),
                "components": sorted(component_type.__name__ for component_type in node.components),
                "children": [entry(child) for child in node.children],
            }

        return {
            "schema": PREFAB_SCHEMA_VERSION,
            "name": self.name,
            "node_count": self.node_count,
            "nodes": [entry(root) for root in self.roots],
        }
