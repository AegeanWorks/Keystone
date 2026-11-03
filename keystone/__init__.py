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
from keystone.playtest import (
    PLAYTEST_REPORT_SCHEMA,
    TRANSCRIPT_SCHEMA,
    BotPolicy,
    GreedyPolicy,
    RandomPolicy,
    ScriptedPolicy,
    canon,
    canon_hash,
    diff_transcripts,
    make_report,
    run_bot,
    to_command_log,
    validate_fairness,
)
from keystone.plugin import GameModule
from keystone.scene import (
    BloomSettings,
    ColorSettings,
    DirectionalLight,
    Node,
    PointLight,
    PostSettings,
    Scene,
    ShadowSettings,
    Transform,
)
from keystone.scene_snapshot import scene_from_dict, scene_to_dict

__version__ = "0.40.0"
__all__ = [
    "PLAYTEST_REPORT_SCHEMA",
    "SAMPLE_RATE",
    "TRANSCRIPT_SCHEMA",
    "ActionState",
    "AnimationClip",
    "AnimationController",
    "AssetRegistry",
    "AudioClip",
    "AuditTrail",
    "BloomSettings",
    "BotPolicy",
    "ColorSettings",
    "DirectionalLight",
    "Emitter",
    "Engine",
    "GameModule",
    "GltfImport",
    "GreedyPolicy",
    "History",
    "InputMap",
    "Mat4",
    "MaterialGraph",
    "MaterialGraphNode",
    "Mixer",
    "Node",
    "Particle",
    "ParticleSystem",
    "PointLight",
    "PostSettings",
    "Quat",
    "RandomPolicy",
    "Scene",
    "ScriptedPolicy",
    "ShadowSettings",
    "TextureData",
    "Track",
    "Transform",
    "Vec3",
    "animation_report",
    "apply_pose",
    "audio_report",
    "blend_poses",
    "canon",
    "canon_hash",
    "diff_transcripts",
    "group_instances",
    "load_gltf",
    "make_report",
    "merge_batches",
    "mix_clips",
    "noise",
    "observe",
    "parse_actions",
    "particles_report",
    "plan_batches",
    "plan_instanced",
    "read_wav",
    "run_bot",
    "scene_from_dict",
    "scene_to_dict",
    "sine",
    "square",
    "summarize_report",
    "to_command_log",
    "validate_fairness",
    "write_wav",
]


def __getattr__(name: str):
    if name == "Engine":
        from keystone.app import Engine

        return Engine
    raise AttributeError(f"module 'keystone' has no attribute '{name}'")
