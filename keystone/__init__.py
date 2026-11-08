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
from keystone.animation_state import (
    AnimationState,
    AnimationStateMachine,
    AnimationTransition,
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
from keystone.culling import (
    aabb_visible,
    cull_scene,
    culling_enabled,
    extract_planes,
    model_visible,
    node_visible,
    world_bounds,
)
from keystone.gltf import GltfImport, load_gltf
from keystone.gpu.instancing import group_instances, plan_instanced
from keystone.history import History
from keystone.input import ActionState, InputMap
from keystone.lifecycle import ComponentRuntime, LifecycleContext, lifecycle_hooks
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
from keystone.prefab import Prefab
from keystone.scene import (
    BloomSettings,
    ColorSettings,
    CullingSettings,
    DirectionalLight,
    Node,
    PointLight,
    PostSettings,
    Scene,
    SceneGroup,
    ShadowSettings,
    SpriteSettings,
    Transform,
)
from keystone.scene_snapshot import scene_from_dict, scene_to_dict
from keystone.skin import bone_matrices, skin_mesh, skin_point
from keystone.texture import TextureData

__version__ = "0.45.0"
__all__ = [
    "PLAYTEST_REPORT_SCHEMA",
    "SAMPLE_RATE",
    "TRANSCRIPT_SCHEMA",
    "ActionState",
    "AnimationClip",
    "AnimationController",
    "AnimationState",
    "AnimationStateMachine",
    "AnimationTransition",
    "AssetRegistry",
    "AudioClip",
    "AuditTrail",
    "BloomSettings",
    "BotPolicy",
    "ColorSettings",
    "ComponentRuntime",
    "CullingSettings",
    "DirectionalLight",
    "Emitter",
    "Engine",
    "GameModule",
    "GltfImport",
    "GreedyPolicy",
    "History",
    "InputMap",
    "LifecycleContext",
    "Mat4",
    "MaterialGraph",
    "MaterialGraphNode",
    "Mixer",
    "Node",
    "Particle",
    "ParticleSystem",
    "PointLight",
    "PostSettings",
    "Prefab",
    "Quat",
    "RandomPolicy",
    "Scene",
    "SceneGroup",
    "ScriptedPolicy",
    "ShadowSettings",
    "SpriteSettings",
    "TextureData",
    "Track",
    "Transform",
    "Vec3",
    "aabb_visible",
    "animation_report",
    "apply_pose",
    "audio_report",
    "blend_poses",
    "bone_matrices",
    "canon",
    "canon_hash",
    "cull_scene",
    "culling_enabled",
    "diff_transcripts",
    "extract_planes",
    "group_instances",
    "lifecycle_hooks",
    "load_gltf",
    "make_report",
    "merge_batches",
    "mix_clips",
    "model_visible",
    "node_visible",
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
    "skin_mesh",
    "skin_point",
    "square",
    "summarize_report",
    "to_command_log",
    "validate_fairness",
    "world_bounds",
    "write_wav",
]


def __getattr__(name: str):
    if name == "Engine":
        from keystone.app import Engine

        return Engine
    raise AttributeError(f"module 'keystone' has no attribute '{name}'")
