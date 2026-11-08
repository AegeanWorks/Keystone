"""Deterministic scenario helpers for AI and CI tests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable

from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.plugin import GameModule
from keystone.replay import FIXED_STEP
from keystone.scene import Scene

SceneLoader = Callable[[GameModule, Scene], None]


def run_script(
    game: GameModule,
    actions: Iterable[ActionState],
    frames: int | None = None,
    step: float = FIXED_STEP,
    trace: bool = False,
    scene_loader: SceneLoader | None = None,
) -> dict:
    script = list(actions)
    count = len(script) if frames is None else frames
    scene = None
    if scene_loader is not None:
        if not callable(scene_loader):
            raise TypeError("scene_loader must be callable or None")
        scene = game.build_scene()
        if not isinstance(scene, Scene):
            raise TypeError("game build_scene() must return a Scene")
        scene_loader(game, scene)
    return run_simulation(
        game,
        frames=count or 1,
        actions=script,
        step=step,
        trace=trace,
        scene=scene,
    )


def verify_determinism(
    factory: Callable[[], GameModule],
    actions: Iterable[ActionState],
    frames: int | None = None,
    step: float = FIXED_STEP,
    scene_loader: SceneLoader | None = None,
) -> dict:
    """Run one scenario twice from a factory and compare final hashes."""
    script = list(actions)
    first = run_script(factory(), script, frames, step, scene_loader=scene_loader)
    second = run_script(factory(), script, frames, step, scene_loader=scene_loader)
    return {
        "ok": first["hash"] == second["hash"],
        "hash": first["hash"],
        "first": first["final"],
        "second": second["final"],
    }


def assert_deterministic(
    factory: Callable[[], GameModule],
    actions: Iterable[ActionState],
    frames: int | None = None,
    step: float = FIXED_STEP,
    scene_loader: SceneLoader | None = None,
) -> dict:
    result = verify_determinism(
        factory, actions, frames, step, scene_loader=scene_loader
    )
    if not result["ok"]:
        raise AssertionError("the scenario produced different hashes on two runs")
    return result


def scene_fingerprint(scene: Scene) -> str:
    """Return a stable digest of a scene's structure for snapshot assertions.

    Encodes each node's id, name, layer, tags, visibility, transform channels
    and mesh/material triangle counts. Node order is normalized, so the digest
    identifies content rather than traversal order. Use it to detect an
    *intentional* scene change and update the pinned value deliberately,
    instead of pinning exact node counts that churn on every presentation edit.
    """
    if not isinstance(scene, Scene):
        raise TypeError("scene_fingerprint needs a Scene")
    digest = hashlib.sha256()
    entries = []
    for node in scene.traverse():
        if node is scene.root:
            continue
        mesh = node.mesh
        entries.append(
            (
                node.id or "",
                node.name,
                node.layer,
                tuple(sorted(node.tags)),
                bool(node.visible),
                tuple(round(value, 6) for value in _vec(node.transform.position)),
                tuple(round(value, 6) for value in _quat(node.transform.rotation)),
                tuple(round(value, 6) for value in _vec(node.transform.scale)),
                mesh.triangle_count() if mesh is not None else -1,
                node.material is not None,
            )
        )
    for entry in sorted(entries):
        digest.update(repr(entry).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def assert_scene_budget(
    scene: Scene,
    max_nodes: int | None = None,
    max_triangles: int | None = None,
    max_draw_calls: int | None = None,
) -> dict:
    """Assert a scene stays within coarse budgets and return what was measured.

    Budgets are invariants (a scene should not silently grow without bound),
    unlike exact snapshot pins that fail on every unrelated addition.
    """
    if not isinstance(scene, Scene):
        raise TypeError("assert_scene_budget needs a Scene")
    limits = {}
    for label, value in (
        ("max_nodes", max_nodes),
        ("max_triangles", max_triangles),
        ("max_draw_calls", max_draw_calls),
    ):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{label} must be a non-negative integer or None")
        limits[label] = value

    nodes = 0
    triangles = 0
    for node in scene.traverse():
        if node is scene.root or not node.world_visible():
            continue
        nodes += 1
        mesh = node.mesh
        if mesh is not None:
            triangles += mesh.triangle_count()

    measured = {"nodes": nodes, "triangles": triangles, "draw_calls": nodes}
    for label, limit in limits.items():
        key = {
            "max_nodes": "nodes",
            "max_triangles": "triangles",
            "max_draw_calls": "draw_calls",
        }[label]
        actual = measured[key]
        if actual > limit:
            raise AssertionError(
                f"scene {key} budget exceeded: {actual} > {limit}"
            )
    return measured


def _vec(value: object) -> tuple[float, float, float]:
    return (float(value.x), float(value.y), float(value.z))  # type: ignore[attr-defined]


def _quat(value: object) -> tuple[float, float, float, float]:
    return (  # type: ignore[attr-defined]
        float(value.w),
        float(value.x),
        float(value.y),
        float(value.z),
    )
