"""Keystone: a game-agnostic 3D engine core."""

from __future__ import annotations

from keystone.input import ActionState
from keystone.math3d import Mat4, Quat, Vec3
from keystone.plugin import GameModule
from keystone.scene import Node, Scene, Transform

__version__ = "0.10.0"
__all__ = ["ActionState", "Engine", "GameModule", "Mat4", "Node", "Quat", "Scene", "Transform", "Vec3"]


def __getattr__(name: str):
    if name == "Engine":
        from keystone.app import Engine

        return Engine
    raise AttributeError(f"module 'keystone' has no attribute '{name}'")
