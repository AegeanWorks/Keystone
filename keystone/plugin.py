"""Game-agnostic module contract and loader."""

from __future__ import annotations

from importlib import import_module
from typing import Protocol, runtime_checkable

from keystone.input import ActionState
from keystone.scene import Scene
from keystone.schema import (
    EDITOR_ACTIONS,
    EDITOR_SCHEMA_VERSION,
    SCENE_SCHEMA_VERSION,
    WEB_API_VERSION,
)


@runtime_checkable
class GameModule(Protocol):
    """The five operations an external game exposes to the engine."""

    name: str

    def build_scene(self) -> Scene: ...
    def update(self, dt: float, actions: ActionState) -> None: ...
    def snapshot(self) -> dict[str, object]: ...
    def actions(self) -> dict[str, object]: ...
    def status(self) -> str: ...

    # Optional: extend the engine's default bindings with the game's own
    # actions. The engine calls it once, after building its InputMap.
    # def bind_input(self, mapping: InputMap) -> None: ...


def describe_game(game: GameModule) -> dict[str, object]:
    """Return a machine-readable capability/action/snapshot description."""
    from keystone.analysis import REPORT_SCHEMA
    from keystone.gpu.context import key_names

    name = getattr(game, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise TypeError("GameModule.name must be a non-blank string")
    return {
        "schema": 1,
        "game": name,
        "actions": game.actions(),
        "snapshot": game.snapshot(),
        "capabilities": {
            "simulate": True,
            "render": True,
            "shadows": True,
            "srgb": True,
            "post": True,
            "bloom": True,
            "sprites": True,
            "culling": True,
            "skin": True,
            "pbr": True,
            "agents": True,
            "profiler": True,
            "input_bindings": True,
            "input_contexts": True,
            "input_bind_hook": callable(getattr(game, "bind_input", None)),
            "input_keys": list(key_names()),
            "audio": True,
            "batching": True,
            "prefabs": True,
            "static_merge": True,
            "instancing": True,
            "animation": True,
            "animation_events": True,
            "animation_blend": True,
            "replay": True,
            "asset_inventory": True,
            "particles": True,
            "inspector": True,
            "editor": {
                "schema": EDITOR_SCHEMA_VERSION,
                "actions": list(EDITOR_ACTIONS),
            },
            "playtest": True,
            "human_ui": {"overlay": "on", "toggle": "h", "pause": "p", "menu": ["resume", "toggle_ui", "quit"]},
            "game_ui": callable(getattr(game, "draw_ui", None)),
            "report_schema": REPORT_SCHEMA,
            "web": {
                "api_version": WEB_API_VERSION,
                "scene_schema": SCENE_SCHEMA_VERSION,
                "endpoints": ["/api", "/api/health", "/api/describe", "/api/scene", "/api/inspector", "/api/editor", "/api/simulate"],
                "notes": ["replay a CommandLog with --replay <log.json>, or translate log.frames into the actions array of POST /api/simulate"],
            },
        },
    }


def load_game(spec: str) -> GameModule:
    """Load an external game from 'package.module:Factory'."""
    if not isinstance(spec, str) or spec.count(":") != 1:
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
    if not callable(factory):
        raise TypeError(f"game '{spec}' factory '{attribute}' is not callable")
    try:
        game = factory()
    except TypeError as exc:
        raise TypeError(f"game '{spec}' factory failed: {exc}") from exc
    name = getattr(game, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"game '{spec}' must expose a non-blank string name")
    for method in ("build_scene", "update", "snapshot", "actions", "status"):
        if not callable(getattr(game, method, None)):
            raise TypeError(f"game '{spec}' does not implement {method}()")
    return game
