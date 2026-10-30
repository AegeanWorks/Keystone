"""Game-agnostic module contract and loader."""

from __future__ import annotations

from importlib import import_module
from typing import Protocol, runtime_checkable

from keystone.input import ActionState
from keystone.scene import Scene


@runtime_checkable
class GameModule(Protocol):
    """The five operations an external game exposes to the engine."""

    name: str

    def build_scene(self) -> Scene: ...
    def update(self, dt: float, actions: ActionState) -> None: ...
    def snapshot(self) -> dict[str, object]: ...
    def actions(self) -> dict[str, object]: ...
    def status(self) -> str: ...


def describe_game(game: GameModule) -> dict[str, object]:
    """Return a machine-readable capability/action/snapshot description."""
    return {
        "schema": 1,
        "game": getattr(game, "name", "game"),
        "actions": game.actions(),
        "snapshot": game.snapshot(),
        "capabilities": {
            "simulate": True,
            "render": True,
            "report_schema": 1,
        },
    }


def load_game(spec: str) -> GameModule:
    """Load an external game from 'package.module:Factory'."""
    if ":" not in spec:
        raise ValueError("game spec must look like 'package.module:Factory'")
    module_name, attribute = spec.split(":", 1)
    if not module_name or not attribute:
        raise ValueError("game spec must include both a module and a factory")
    try:
        module = import_module(module_name)
    except ImportError as exc:
        raise ValueError(f"could not import game module '{module_name}': {exc}") from exc
    try:
        factory = getattr(module, attribute)
    except AttributeError as exc:
        raise ValueError(f"'{module_name}' has no attribute '{attribute}'") from exc
    game = factory()
    for method in ("build_scene", "update", "snapshot", "actions", "status"):
        if not callable(getattr(game, method, None)):
            raise TypeError(f"game '{spec}' does not implement {method}()")
    return game
