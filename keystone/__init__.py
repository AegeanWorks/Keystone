"""Keystone: a game-agnostic 3D engine core."""

from __future__ import annotations

from keystone.agents import AuditTrail, observe, parse_actions, summarize_report
from keystone.animation import (
    AnimationClip,
    AnimationController,
    Track,
    animation_report,
    apply_pose,
    blend_poses,
)
from keystone.assets import AssetRegistry
from keystone.audio import (
    SAMPLE_RATE,
    AudioClip,
    Mixer,
    audio_report,
    mix_clips,
    noise,
    read_wav,
    sine,
    square,
    write_wav,
)
from keystone.batch import merge_batches, plan_batches
from keystone.gltf import GltfImport, load_gltf
from keystone.gpu.instancing import group_instances, plan_instanced
from keystone.history import History
from keystone.input import ActionState, InputMap
from keystone.material_graph import MaterialGraph, MaterialGraphNode
from keystone.math3d import Mat4, Quat, Vec3
from keystone.particles import Emitter, Particle, ParticleSystem, particles_report
from keystone.plugin import GameModule
from keystone.scene import Node, Scene, Transform
from keystone.scene_snapshot import scene_from_dict, scene_to_dict
from keystone.texture import TextureData

__version__ = "0.32.0"
__all__ = [
    "SAMPLE_RATE",
    "ActionState",
    "AnimationClip",
    "AnimationController",
    "AssetRegistry",
    "AudioClip",
    "AuditTrail",
    "Emitter",
    "Engine",
    "GameModule",
    "GltfImport",
    "History",
    "InputMap",
    "Mat4",
    "MaterialGraph",
    "MaterialGraphNode",
    "Mixer",
    "Node",
    "Particle",
    "ParticleSystem",
    "Quat",
    "Scene",
    "TextureData",
    "Track",
    "Transform",
    "Vec3",
    "animation_report",
    "apply_pose",
    "audio_report",
    "blend_poses",
    "group_instances",
    "load_gltf",
    "merge_batches",
    "mix_clips",
    "noise",
    "observe",
    "parse_actions",
    "particles_report",
    "plan_batches",
    "plan_instanced",
    "read_wav",
    "scene_from_dict",
    "scene_to_dict",
    "sine",
    "square",
    "summarize_report",
    "write_wav",
]


def __getattr__(name: str):
    if name == "Engine":
        from keystone.app import Engine

        return Engine
    raise AttributeError(f"module 'keystone' has no attribute '{name}'")
