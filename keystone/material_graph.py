"""Declarative, deterministic material graphs that evaluate to a Material."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.texture import TextureData

NODE_KINDS = ("color", "float", "checker", "texture", "mix", "material", "pbr")
_JSON_VALUE = (str, int, float, bool, type(None))


def _json_value(value: Any) -> Any:
    if isinstance(value, Vec3):
        return [value.x, value.y, value.z]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, _JSON_VALUE):
        return value
    raise TypeError(f"material graph parameter {value!r} is not JSON serializable")


def _from_json_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_from_json_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _from_json_value(item)) for key, item in value.items()))
    return value


@dataclass(frozen=True, slots=True)
class MaterialGraphNode:
    """One node in a material graph: a kind, parameters and input node ids."""

    id: str
    kind: str
    params: tuple[tuple[str, Any], ...] = ()
    inputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("material graph node id must be a non-blank string")
        if self.kind not in NODE_KINDS:
            raise ValueError(f"material graph node kind must be one of {', '.join(NODE_KINDS)}")
        cleaned: list[tuple[str, Any]] = []
        for item in self.params:
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                raise TypeError("material graph parameters must be (name, value) pairs")
            cleaned.append((str(item[0]), item[1]))
        object.__setattr__(self, "params", tuple(sorted(cleaned, key=lambda pair: pair[0])))
        object.__setattr__(self, "inputs", tuple(str(value) for value in self.inputs))

    def param(self, name: str, default: Any = None) -> Any:
        """Return one parameter value, or default when it is absent."""
        for key, value in self.params:
            if key == name:
                return value
        return default

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "params": {key: _json_value(value) for key, value in self.params},
            "inputs": list(self.inputs),
        }


@dataclass(frozen=True, slots=True)
class MaterialGraph:
    """An immutable, serializable graph that evaluates to one Material."""

    nodes: tuple[MaterialGraphNode, ...] = ()
    output: str = ""

    def __post_init__(self) -> None:
        normalized: list[MaterialGraphNode] = []
        for node in self.nodes:
            if not isinstance(node, MaterialGraphNode):
                raise TypeError("material graph nodes must be MaterialGraphNode instances")
            normalized.append(node)
        object.__setattr__(self, "nodes", tuple(sorted(normalized, key=lambda node: node.id)))
        if not isinstance(self.output, str):
            raise TypeError("material graph output must be a string")

    def node(self, node_id: str) -> MaterialGraphNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(f"material graph has no node {node_id!r}")

    def validate(self) -> None:
        if not self.nodes:
            raise ValueError("material graph must contain at least one node")
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("material graph node ids must be unique")
        index = {node.id: node for node in self.nodes}
        for node in self.nodes:
            if node.kind not in NODE_KINDS:
                raise ValueError(f"unknown material graph node kind {node.kind!r}")
            for input_id in node.inputs:
                if input_id not in index:
                    raise ValueError(f"node {node.id!r} references unknown input {input_id!r}")
            if node.kind == "mix" and len(node.inputs) < 2:
                raise ValueError(f"mix node {node.id!r} needs at least two inputs")
            if node.kind == "texture" and node.param("asset") is None and node.param("name") is None:
                raise ValueError(f"texture node {node.id!r} needs an asset or name parameter")
        if not self.output or self.output not in index:
            raise ValueError("material graph output must name an existing node")
        if index[self.output].kind not in ("material", "pbr"):
            raise ValueError("material graph output must be a material or pbr node")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": 1,
            "output": self.output,
            "nodes": [node.to_dict() for node in self.nodes],
        }

    @classmethod
    def from_dict(cls, data: object) -> MaterialGraph:
        if not isinstance(data, Mapping):
            raise TypeError("material graph document must be a mapping")
        schema = data.get("schema", 1)
        if schema != 1:
            raise ValueError(f"unsupported material graph schema {schema}")
        raw_nodes = data.get("nodes", ())
        if not isinstance(raw_nodes, (list, tuple)):
            raise TypeError("material graph nodes must be a list")
        nodes: list[MaterialGraphNode] = []
        for raw in raw_nodes:
            if not isinstance(raw, Mapping):
                raise TypeError("material graph node must be a mapping")
            node_id = raw.get("id")
            kind = raw.get("kind")
            if not isinstance(node_id, str) or not isinstance(kind, str):
                raise TypeError("material graph node id and kind must be strings")
            params_raw = raw.get("params", {})
            if not isinstance(params_raw, Mapping):
                raise TypeError("material graph params must be a mapping")
            params = tuple(sorted(
                (str(key), _from_json_value(value)) for key, value in params_raw.items()
            ))
            inputs_raw = raw.get("inputs", ())
            if not isinstance(inputs_raw, (list, tuple)):
                raise TypeError("material graph inputs must be a list")
            nodes.append(MaterialGraphNode(node_id, kind, params, tuple(str(value) for value in inputs_raw)))
        output = data.get("output", "")
        if not isinstance(output, str):
            raise TypeError("material graph output must be a string")
        return cls(tuple(nodes), output)

    def evaluate(
        self,
        *,
        textures: Mapping[str, TextureData] | None = None,
        registry: Any = None,
    ) -> Material:
        """Evaluate the graph and return its Material."""
        self.validate()
        index = {node.id: node for node in self.nodes}
        state: dict[str, int] = {}
        order: list[str] = []

        def visit(node_id: str) -> None:
            if state.get(node_id) == 2:
                return
            if state.get(node_id) == 1:
                raise ValueError("material graph contains a cycle")
            state[node_id] = 1
            for input_id in index[node_id].inputs:
                visit(input_id)
            state[node_id] = 2
            order.append(node_id)

        for node in self.nodes:
            visit(node.id)

        values: dict[str, Any] = {}
        for node_id in order:
            values[node_id] = _evaluate_node(index[node_id], values, textures, registry)
        result = values[self.output]
        if not isinstance(result, Material):
            raise TypeError("material graph output must be a Material")
        return result


def _evaluate_node(
    node: MaterialGraphNode,
    values: dict[str, Any],
    textures: Mapping[str, TextureData] | None,
    registry: Any,
) -> Any:
    if node.kind == "color":
        if node.param("color") is not None:
            raw = node.param("color")
            if not isinstance(raw, (tuple, list)) or len(raw) != 3:
                raise TypeError("color node needs a three-element color parameter")
            return Vec3(float(raw[0]), float(raw[1]), float(raw[2]))
        return Vec3(
            float(node.param("r", 0.78)),
            float(node.param("g", 0.78)),
            float(node.param("b", 0.78)),
        )

    if node.kind == "float":
        return float(node.param("value", 0.0))

    if node.kind == "checker":
        size = int(node.param("size", 64))
        cell = int(node.param("cell", 8))
        dark_raw = node.param("dark", (0.10, 0.12, 0.16))
        light_raw = node.param("light", (0.18, 0.20, 0.25))
        if not (isinstance(dark_raw, (tuple, list)) and len(dark_raw) == 3):
            raise TypeError("checker dark color must have three channels")
        if not (isinstance(light_raw, (tuple, list)) and len(light_raw) == 3):
            raise TypeError("checker light color must have three channels")
        dark = tuple(float(channel) for channel in dark_raw)
        light = tuple(float(channel) for channel in light_raw)
        name = str(node.param("name", "checker"))
        return TextureData.checker(size, dark, light, cell, name=name)

    if node.kind == "texture":
        asset = node.param("asset")
        if asset is not None:
            if registry is None:
                raise ValueError("texture node with an asset requires a registry")
            record = registry.require(str(asset))
            if record.kind != "texture" or not isinstance(record.payload, TextureData):
                raise TypeError(f"asset {asset!r} is not a texture")
            return record.payload
        name = node.param("name")
        if name is not None:
            if textures is None or name not in textures:
                raise ValueError(f"texture node references unknown texture {name!r}")
            return textures[name]
        raise ValueError("texture node needs an asset or name parameter")

    if node.kind == "mix":
        if len(node.inputs) < 2:
            raise ValueError("mix node needs at least two inputs")
        a = values[node.inputs[0]]
        b = values[node.inputs[1]]
        if not isinstance(a, Vec3) or not isinstance(b, Vec3):
            raise TypeError("mix inputs must evaluate to colors")
        factor = float(node.param("factor", 0.5))
        if len(node.inputs) >= 3:
            third = values[node.inputs[2]]
            if isinstance(third, (int, float, bool)):
                factor = float(third)
        factor = max(0.0, min(1.0, factor))
        return Vec3(
            a.x * (1.0 - factor) + b.x * factor,
            a.y * (1.0 - factor) + b.y * factor,
            a.z * (1.0 - factor) + b.z * factor,
        )

    if node.kind in ("material", "pbr"):
        color: Vec3 | None = None
        texture: TextureData | None = None
        floats: list[float] = []
        emissive: Vec3 | None = None
        for input_id in node.inputs:
            value = values[input_id]
            if isinstance(value, Vec3) and color is None:
                color = value
            elif isinstance(value, Vec3) and node.kind == "pbr" and emissive is None:
                emissive = value
            elif isinstance(value, TextureData) and texture is None:
                texture = value
            elif isinstance(value, (int, float, bool)):
                floats.append(float(value))
        if color is None:
            raw_color = node.param("color", (0.78, 0.78, 0.82))
            if isinstance(raw_color, (tuple, list)) and len(raw_color) == 3:
                color = Vec3(float(raw_color[0]), float(raw_color[1]), float(raw_color[2]))
            else:
                color = Vec3(
                    float(node.param("r", 0.78)),
                    float(node.param("g", 0.78)),
                    float(node.param("b", 0.78)),
                )
        if texture is None:
            asset = node.param("texture")
            if asset is not None:
                if registry is None:
                    raise ValueError("material texture asset requires a registry")
                record = registry.require(str(asset))
                if record.kind != "texture" or not isinstance(record.payload, TextureData):
                    raise TypeError(f"asset {asset!r} is not a texture")
                texture = record.payload
            texture_name = node.param("texture_name")
            if texture_name is not None:
                if textures is None or texture_name not in textures:
                    raise ValueError(
                        f"material node references unknown texture {texture_name!r}"
                    )
                texture = textures[texture_name]
        if emissive is None:
            raw_emissive = node.param("emissive", (0.0, 0.0, 0.0))
            if isinstance(raw_emissive, (tuple, list)) and len(raw_emissive) == 3:
                emissive = Vec3(float(raw_emissive[0]), float(raw_emissive[1]), float(raw_emissive[2]))
            else:
                emissive = Vec3(0.0, 0.0, 0.0)
        specular = float(node.param("specular", 0.35))
        if floats:
            specular = float(floats[0])
        metallic = float(node.param("metallic", 0.0))
        roughness = float(node.param("roughness", 0.7))
        if len(floats) >= 2:
            metallic = float(floats[1])
        if len(floats) >= 3:
            roughness = float(floats[2])
        metallic = min(1.0, max(0.0, metallic))
        roughness = min(1.0, max(0.0, roughness))
        shininess = float(node.param("shininess", max(1.0, (1.0 - roughness) * 128.0)))
        checker_scale = float(node.param("checker_scale", 0.0))
        return Material(
            color=color,
            specular=specular,
            shininess=shininess,
            checker_scale=checker_scale,
            texture=texture,
            metallic=metallic,
            roughness=roughness,
            emissive=emissive,
        )

    raise ValueError(f"unknown material graph node kind {node.kind!r}")
