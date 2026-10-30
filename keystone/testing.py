"""Deterministic scenario helpers for AI and CI tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.plugin import GameModule
from keystone.replay import FIXED_STEP


def run_script(
    game: GameModule,
    actions: Iterable[ActionState],
    frames: int | None = None,
    step: float = FIXED_STEP,
    trace: bool = False,
) -> dict:
    script = list(actions)
    count = len(script) if frames is None else frames
    return run_simulation(game, frames=count or 1, actions=script, step=step, trace=trace)


def verify_determinism(
    factory: Callable[[], GameModule],
    actions: Iterable[ActionState],
    frames: int | None = None,
    step: float = FIXED_STEP,
) -> dict:
    """Run one scenario twice from a factory and compare final hashes."""
    script = list(actions)
    first = run_script(factory(), script, frames, step)
    second = run_script(factory(), script, frames, step)
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
) -> dict:
    result = verify_determinism(factory, actions, frames, step)
    if not result["ok"]:
        raise AssertionError("the scenario produced different hashes on two runs")
    return result
