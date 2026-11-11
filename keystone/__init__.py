"""Keystone: a game-agnostic 3D engine core."""

from __future__ import annotations

from keystone._version import __version__
from keystone.agents import AuditTrail, observe, parse_actions, summarize_report
from keystone.animation import (
    AnimationClip,
    AnimationController,
    Track,
    animation_report,
    apply_pose,
    blend_poses,
)
from keystone.animation_blend import (
    BlendSample,
    BlendSample2D,
    BlendSpace1D,
    BlendSpace2D,
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
from keystone.audio_spatial import (
    SoundSource,
    distance_gain,
    spatial_mix,
    spatial_report,
)
from keystone.batch import merge_batches, plan_batches
from keystone.camera_rig import CameraRig
from keystone.culling import (
    aabb_visible,
    cull_scene,
    culling_enabled,
    extract_planes,
    model_visible,
    node_visible,
    world_bounds,
)
from keystone.evidence import (
    Checkpoint,
    Route,
    capture_route,
    diff_evidence,
    write_evidence,
)
from keystone.gltf import GltfImport, load_gltf
from keystone.gpu.instancing import group_instances, plan_instanced
from keystone.history import History
from keystone.input import ActionState, InputMap
from keystone.lifecycle import ComponentRuntime, LifecycleContext, lifecycle_hooks
from keystone.material_graph import MaterialGraph, MaterialGraphNode
from keystone.math3d import Mat4, Quat, Vec3
from keystone.nav_authoring import (
    grid_from_boxes,
    read_navgrid,
    scene_boxes,
    write_navgrid,
)
from keystone.navigation import PathFollower, grid_path_points, navigation_report
from keystone.particles import Emitter, Particle, ParticleSystem, particles_report
from keystone.pathfinding import (
    NavGrid,
    PathResult,
    find_path,
    line_of_sight,
    path_report,
    smooth_path,
)
from keystone.picking import (
    SceneHit,
    SceneOverlap,
    hit_report,
    overlap_report,
    overlap_scene,
    raycast_scene,
)
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
from keystone.rng import RandomStream, RandomStreamState
from keystone.scene import (
    OVERLAY_LAYER,
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

__all__ = [
    "OVERLAY_LAYER",
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
    "BlendSample",
    "BlendSample2D",
    "BlendSpace1D",
    "BlendSpace2D",
    "BloomSettings",
    "BotPolicy",
    "CameraRig",
    "Checkpoint",
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
    "NavGrid",
    "Node",
    "Particle",
    "ParticleSystem",
    "PathFollower",
    "PathResult",
    "PointLight",
    "PostSettings",
    "Prefab",
    "Quat",
    "RandomPolicy",
    "RandomStream",
    "RandomStreamState",
    "Route",
    "Scene",
    "SceneGroup",
    "SceneHit",
    "SceneOverlap",
    "ScriptedPolicy",
    "ShadowSettings",
    "SoundSource",
    "SpriteSettings",
    "TextureData",
    "Track",
    "Transform",
    "Vec3",
    "__version__",
    "aabb_visible",
    "animation_report",
    "apply_pose",
    "audio_report",
    "blend_poses",
    "bone_matrices",
    "canon",
    "canon_hash",
    "capture_route",
    "cull_scene",
    "culling_enabled",
    "diff_evidence",
    "diff_transcripts",
    "distance_gain",
    "extract_planes",
    "find_path",
    "grid_from_boxes",
    "grid_path_points",
    "group_instances",
    "hit_report",
    "lifecycle_hooks",
    "line_of_sight",
    "load_gltf",
    "make_report",
    "merge_batches",
    "mix_clips",
    "model_visible",
    "navigation_report",
    "node_visible",
    "noise",
    "observe",
    "overlap_report",
    "overlap_scene",
    "parse_actions",
    "particles_report",
    "path_report",
    "plan_batches",
    "plan_instanced",
    "raycast_scene",
    "read_navgrid",
    "read_wav",
    "run_bot",
    "scene_boxes",
    "scene_from_dict",
    "scene_to_dict",
    "sine",
    "skin_mesh",
    "skin_point",
    "smooth_path",
    "spatial_mix",
    "spatial_report",
    "square",
    "summarize_report",
    "to_command_log",
    "validate_fairness",
    "world_bounds",
    "write_evidence",
    "write_navgrid",
    "write_wav",
]


def __getattr__(name: str):
    if name == "Engine":
        from keystone.app import Engine

        return Engine
    raise AttributeError(f"module 'keystone' has no attribute '{name}'")
