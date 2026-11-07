"""Deterministic scenario helpers for AI and CI tests."""

from __future__ import annotations

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
