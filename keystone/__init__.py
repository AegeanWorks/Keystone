"""Keystone: a game-agnostic 3D engine core."""

from __future__ import annotations

from keystone.assets import AssetRegistry
from keystone.gltf import GltfImport, load_gltf
from keystone.history import History
from keystone.input import ActionState
from keystone.material_graph import MaterialGraph, MaterialGraphNode
from keystone.math3d import Mat4, Quat, Vec3
from keystone.plugin import GameModule
from keystone.scene import Node, Scene, Transform
from keystone.scene_snapshot import scene_from_dict, scene_to_dict
from keystone.texture import TextureData

__version__ = "0.26.0"
__all__ = [
    "ActionState",
    "AssetRegistry",
    "Engine",
    "GameModule",
    "GltfImport",
    "History",
    "Mat4",
    "MaterialGraph",
    "MaterialGraphNode",
    "Node",
    "Quat",
    "Scene",
    "TextureData",
    "Transform",
    "Vec3",
    "load_gltf",
    "scene_from_dict",
    "scene_to_dict",
]


def __getattr__(name: str):
    if name == "Engine":
        from keystone.app import Engine

        return Engine
    raise AttributeError(f"module 'keystone' has no attribute '{name}'")
