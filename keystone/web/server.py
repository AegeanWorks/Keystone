"""A localhost JSON API and static web console for the game-agnostic engine."""

from __future__ import annotations

import json
import math
import sys
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from keystone.assets import AssetRegistry
from keystone.component_codec import validate_component_types
from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.lifecycle import ComponentRuntime
from keystone.plugin import GameModule, describe_game
from keystone.prefab import Prefab
from keystone.prefab_library import PrefabLibrary
from keystone.replay import FIXED_STEP
from keystone.scene import Node, Scene
from keystone.scene_diff import diff_scene_documents
from keystone.scene_library import SceneLibrary
from keystone.scene_snapshot import restore_scene, scene_to_dict
from keystone.web.editor import (
    EDITOR_ACTIONS,
    EditorHistory,
    add_scene,
    apply_prefab_instance,
    apply_prefab_override,
    asset_entries,
    assign_assets,
    component_schemas,
    create_node,
    delete_node,
    delete_selection,
    duplicate_node,
    editor_document,
    find_node,
    insert_prefab,
    remove_component,
    rename_prefab_links,
    reparent_node,
    revert_prefab_instance,
    revert_prefab_override,
    save_prefab,
    save_scene_group,
    set_component,
    set_node_properties,
    set_scene,
    set_selection_properties,
    set_selection_transform,
    toggle_selection_visible,
    transform_from_payload,
    transform_selection,
    unload_scene,
)
from keystone.web.scene import scene_document
from keystone.web.schema import EDITOR_SCHEMA, SCENE_SCHEMA, WEB_API_VERSION

MAX_BODY = 1_000_000
MAX_FRAMES = 1_000_000
MAX_BATCH_ACTIONS = 100
BATCH_ACTIONS = frozenset(
    {
        "transform",
        "set_node",
        "set_scene",
        "assign_asset",
        "set_component",
        "remove_component",
        "create_node",
        "delete_node",
        "duplicate_node",
        "reparent_node",
        "insert_prefab",
        "revert_prefab",
    }
)


def _enabled(value: object) -> bool:
    if value is None:
        return False
    return bool(getattr(value, "enabled", value))
STATIC_ROOT = Path(__file__).with_name("static")
STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "viewer.js": "text/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
}


class WebProblem(Exception):
    """One client-facing error with an actionable fix."""

    def __init__(self, status: int, why: str, fix: str) -> None:
        super().__init__(why)
        self.status = status
        self.why = why
        self.fix = fix


class GameSession:
    """One in-memory game guarded by a lock for concurrent HTTP requests."""

    def __init__(
        self,
        game: GameModule,
        prefab_dir: str | Path | None = None,
        scene_dir: str | Path | None = None,
        initial_scene: str | None = None,
    ) -> None:
        self.game = game
        self.lock = threading.RLock()
        self._batch_depth = 0
        self._built = False
        self.selected_id: str | None = None
        self.selected_ids: list[str] = []
        self.prefabs: dict[str, Prefab] = {}
        self.history = EditorHistory()
        component_types = validate_component_types(getattr(game, "component_types", None))
        self.component_types = component_types
        self.playing = False
        self.play_frames = 0
        self.lifecycle: ComponentRuntime | None = None
        self._play_snapshot: dict | None = None
        self.last_diff: dict[str, object] | None = None
        self.prefab_library: PrefabLibrary | None = None
        if prefab_dir is not None:
            self.prefab_library = PrefabLibrary(
                prefab_dir,
                registry=self._registry_locked(),
                component_types=component_types,
            )
        self.scene_library: SceneLibrary | None = None
        if scene_dir is not None:
            self.scene_library = SceneLibrary(
                scene_dir,
                registry=self._registry_locked(),
                component_types=component_types,
            )
        self.initial_scene = initial_scene
        self._initial_scene_loaded = False
        if initial_scene is not None:
            if self.scene_library is None:
                raise ValueError("a scene library is required to open a saved scene")
            self._scene_locked()

    @property
    def name(self) -> str:
        return getattr(self.game, "name", "game")

    @property
    def selected_ids(self) -> list[str]:
        return list(self._selected_ids)

    @selected_ids.setter
    def selected_ids(self, value: list[str]) -> None:
        self._set_selected_ids(value)

    def _set_selected_ids(self, ids: list[str]) -> None:
        seen: set[str] = set()
        ordered: list[str] = []
        for node_id in ids:
            if node_id not in seen:
                seen.add(node_id)
                ordered.append(node_id)
        self._selected_ids = ordered
        self._selected_id = ordered[0] if ordered else None

    @property
    def selected_id(self) -> str | None:
        return self._selected_id

    @selected_id.setter
    def selected_id(self, value: str | None) -> None:
        self._selected_id = value
        self._selected_ids = [] if value is None else [value]

    def describe(self) -> dict:
        with self.lock:
            return describe_game(self.game)

    def simulate(self, frames: int, actions: list, step: float, trace: bool) -> dict:
        if isinstance(frames, bool) or not isinstance(frames, int) or frames < 0:
            raise WebProblem(400, "frames must be a non-negative integer", 'send {"frames": 1}')
        if frames > MAX_FRAMES:
            raise WebProblem(400, f"frames must be at most {MAX_FRAMES}", "send a smaller frame count")
        if isinstance(step, bool) or not isinstance(step, (int, float)):
            raise WebProblem(400, "step must be a positive number", 'send {"frames": 1, "step": 0.0167}')
        try:
            step_value = float(step)
        except (OverflowError, ValueError) as exc:
            raise WebProblem(400, "step must be a positive number", 'send {"frames": 1, "step": 0.0167}') from exc
        if step_value <= 0.0 or not math.isfinite(step_value):
            raise WebProblem(400, "step must be a positive number", 'send {"frames": 1, "step": 0.0167}')
        if not isinstance(trace, bool):
            raise WebProblem(400, "trace must be a boolean", 'send {"frames": 1, "trace": false}')
        if not isinstance(actions, list):
            raise WebProblem(400, "actions must be a JSON list", 'send {"frames": 1, "actions": [{"forward": 1.0}]}')
        try:
            script = [ActionState.from_dict(item) for item in actions]
        except (AttributeError, TypeError, ValueError) as exc:
            raise WebProblem(400, f"invalid action item: {exc}", "each action must be a JSON object") from exc
        with self.lock:
            if self.playing:
                raise WebProblem(400, "play mode is active", "send play_stop before simulating")
            result = run_simulation(self.game, frames, script, step=step_value, trace=bool(trace))
            self._built = True
            return result

    def _scene_locked(self) -> Scene:
        scene = getattr(self.game, "scene", None)
        if not isinstance(scene, Scene) or (not self._built and not scene.root.children):
            scene = self.game.build_scene()
            self._built = True
        if not isinstance(scene, Scene):
            raise TypeError("GameModule.build_scene() must return a Scene")
        registry = self._registry_locked()
        if self.prefab_library is not None:
            self.prefab_library.registry = registry
        if self.scene_library is not None:
            self.scene_library.registry = registry
        if self.initial_scene is not None and not self._initial_scene_loaded:
            self.scene_library.load_into(self.initial_scene, scene)
            self._initial_scene_loaded = True
        return scene

    def scene(self) -> dict:
        with self.lock:
            return scene_document(self._scene_locked(), game=self.name)

    def _registry_locked(self) -> AssetRegistry | None:
        registry = getattr(self.game, "assets", None)
        return registry if isinstance(registry, AssetRegistry) else None

    def _parent_locked(self, scene: Scene, value: object) -> Node | None:
        if value in (None, "", "root"):
            return None
        return find_node(scene, value)

    def _prefab_entries_locked(self) -> list[dict[str, object]] | None:
        if self.prefab_library is None:
            return None
        entries = [entry.describe() for entry in self.prefab_library.entries()]
        listed = {str(entry["name"]) for entry in entries}
        for name in sorted(set(self.prefabs) - listed):
            entries.append(
                {
                    "name": name,
                    "node_count": self.prefabs[name].node_count,
                    "source": None,
                    "error": None,
                }
            )
        entries.sort(key=lambda entry: str(entry["name"]))
        return entries

    def _apply_history(self, scene: Scene, operation: Callable[[], object]) -> object:
        if self._batch_depth:
            result = operation()
        else:
            result = self.history.apply(scene, operation)
        self.last_diff = None
        return result

    def _batch_locked(self, scene: Scene, payload: dict) -> None:
        actions = payload.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError("batch actions must be a non-empty list")
        if len(actions) > MAX_BATCH_ACTIONS:
            raise ValueError(f"batch actions must contain at most {MAX_BATCH_ACTIONS} entries")
        for index, item in enumerate(actions):
            if not isinstance(item, dict):
                raise TypeError(f"batch actions[{index}] must be a JSON object")
            action = item.get("action")
            if action not in BATCH_ACTIONS:
                raise ValueError(
                    f"batch actions[{index}] {action!r} is not allowed; "
                    f"use {', '.join(sorted(BATCH_ACTIONS))}"
                )
        before = self.selected_ids
        self._batch_depth += 1
        try:
            self.history.apply(
                scene,
                lambda: [self.editor_action(item) for item in actions],
            )
        except Exception:
            self._set_selected_ids(before)
            raise
        finally:
            self._batch_depth -= 1

    def _ensure_prefab_locked(self, name: object) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("prefab name must be a non-blank string")
        if name in self.prefabs:
            return
        if self.prefab_library is None:
            raise KeyError(f"no saved prefab {name!r}")
        self.prefabs[name] = self.prefab_library.load(name)

    def _lifecycle_state(self) -> dict[str, object]:
        if self.lifecycle is not None:
            return self.lifecycle.describe()
        return {"active": False, "frame": 0, "started": 0, "hooks": []}

    def _editor_locked(self, scene: Scene) -> dict:
        existing = [
            node_id
            for node_id in self._selected_ids
            if scene.find_by_id(node_id) is not None
        ]
        if (
            not existing
            and self._selected_id is not None
            and scene.find_by_id(self._selected_id) is not None
        ):
            existing = [self._selected_id]
        self._set_selected_ids(existing)
        scene_entries = (
            self.scene_library.describe() if self.scene_library is not None else None
        )
        registry = self._registry_locked()
        for node in scene.traverse():
            link = node.prefab_link
            if link is not None and link.name not in self.prefabs:
                try:
                    self._ensure_prefab_locked(link.name)
                except (KeyError, ValueError):  # hygiene: allow missing prefabs stay in prefab_overrides errors
                    pass
        document = editor_document(
            scene,
            self.selected_id,
            self.prefabs,
            self.history,
            prefab_entries=self._prefab_entries_locked(),
            scene_entries=scene_entries,
            registry=registry,
            assets=asset_entries(registry),
            component_types=sorted(self.component_types or {}),
            component_schema_documents=component_schemas(self.component_types),
            play_state={
                "active": self.playing,
                "frames": self.play_frames,
                "step": FIXED_STEP,
                "lifecycle": self._lifecycle_state(),
            },
            diff=self.last_diff,
            trash={
                "prefabs": (
                    self.prefab_library.trash()
                    if self.prefab_library is not None
                    else []
                ),
                "scenes": (
                    self.scene_library.trash()
                    if self.scene_library is not None
                    else []
                ),
            },
            selected_ids=self.selected_ids,
        )
        document["game"] = self.name
        document["workspace"] = {
            "prefab_dir": (
                self.prefab_library.directory.as_posix()
                if self.prefab_library is not None
                else None
            ),
            "scene_dir": (
                self.scene_library.directory.as_posix()
                if self.scene_library is not None
                else None
            ),
        }
        return document

    def editor(self) -> dict:
        with self.lock:
            return self._editor_locked(self._scene_locked())

    def editor_action(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            raise WebProblem(400, "editor request must be a JSON object", 'send {"action": "select", "id": "cube"}')
        action = payload.get("action")
        if not isinstance(action, str) or not action.strip():
            raise WebProblem(
                400,
                "editor action must be a non-blank string",
                "use " + ", ".join(EDITOR_ACTIONS),
            )
        with self.lock:
            scene = self._scene_locked()
            try:
                if self.playing and action not in (
                    "select",
                    "select_many",
                    "play_step",
                    "play_stop",
                ):
                    raise ValueError("play mode is active; stop it before editing")
                if action == "batch":
                    self._batch_locked(scene, payload)
                elif action == "select":
                    node_id = payload.get("id")
                    if node_id is None:
                        self.selected_id = None
                    elif isinstance(node_id, str):
                        find_node(scene, node_id)
                        self.selected_id = node_id
                    else:
                        raise ValueError("select id must be a string or null")
                elif action == "select_many":
                    ids = payload.get("ids")
                    mode = payload.get("mode", "replace")
                    if not isinstance(ids, list) or any(
                        not isinstance(item, str) or not item.strip()
                        for item in ids
                    ):
                        raise ValueError(
                            "select_many ids must be a list of non-blank strings"
                        )
                    if mode not in ("replace", "add", "remove", "toggle"):
                        raise ValueError(
                            "select_many mode must be replace, add, remove or toggle"
                        )
                    for node_id in ids:
                        find_node(scene, node_id)
                    current = self.selected_ids
                    if mode == "replace":
                        result = list(ids)
                    elif mode == "add":
                        result = current + [
                            node_id for node_id in ids if node_id not in current
                        ]
                    elif mode == "remove":
                        removed = set(ids)
                        result = [
                            node_id for node_id in current if node_id not in removed
                        ]
                    else:
                        result = list(current)
                        for node_id in ids:
                            if node_id in result:
                                result.remove(node_id)
                            else:
                                result.append(node_id)
                    self._set_selected_ids(result)
                elif action == "transform":
                    node = find_node(scene, payload.get("id"))

                    def apply_transform() -> None:
                        node.transform = transform_from_payload(node, payload)

                    self._apply_history(scene, apply_transform)
                    self.selected_id = node.id
                elif action == "transform_selection":
                    self._apply_history(
                        scene,
                        lambda: transform_selection(
                            scene, self.selected_ids, payload
                        ),
                    )
                elif action == "toggle_selection_visible":
                    self._apply_history(
                        scene,
                        lambda: toggle_selection_visible(
                            scene, self.selected_ids
                        ),
                    )
                elif action == "delete_selection":
                    parent = self._apply_history(
                        scene,
                        lambda: delete_selection(scene, self.selected_ids),
                    )
                    self.selected_id = None if parent is scene.root else parent.id
                elif action == "set_node":
                    node = find_node(scene, payload.get("id"))
                    self._apply_history(
                        scene, lambda: set_node_properties(node, payload)
                    )
                    self.selected_id = node.id
                elif action == "set_selection_properties":
                    self._apply_history(
                        scene,
                        lambda: set_selection_properties(
                            scene, self.selected_ids, payload
                        ),
                    )
                elif action == "set_selection_transform":
                    self._apply_history(
                        scene,
                        lambda: set_selection_transform(
                            scene, self.selected_ids, payload
                        ),
                    )
                elif action == "set_scene":
                    self._apply_history(scene, lambda: set_scene(scene, payload))
                elif action == "assign_asset":
                    node = find_node(scene, payload.get("id"))
                    self._apply_history(
                        scene,
                        lambda: assign_assets(node, payload, self._registry_locked()),
                    )
                    self.selected_id = node.id
                elif action == "play_start":
                    if self.playing:
                        raise ValueError("play mode is already active")
                    registry = self._registry_locked()
                    snapshot = scene_to_dict(scene, registry)
                    lifecycle = ComponentRuntime(scene)
                    try:
                        lifecycle.start()
                    except Exception:
                        restore_scene(
                            scene, snapshot, registry, self.component_types
                        )
                        raise
                    self._play_snapshot = snapshot
                    self.lifecycle = lifecycle
                    self.playing = True
                    self.play_frames = 0
                    self.history.clear()
                elif action == "play_step":
                    if not self.playing:
                        raise ValueError("play mode is not active")
                    frames = payload.get("frames", 1)
                    if (
                        isinstance(frames, bool)
                        or not isinstance(frames, int)
                        or frames < 1
                        or frames > 10_000
                    ):
                        raise ValueError("play frames must be an integer between 1 and 10000")
                    actions = payload.get("actions", [])
                    if not isinstance(actions, list):
                        raise TypeError("play actions must be a list")
                    script = [ActionState.from_dict(item) for item in actions]
                    for index in range(frames):
                        if script:
                            state = (
                                script[index]
                                if index < len(script)
                                else script[-1].without_pressed()
                            )
                        else:
                            state = ActionState()
                        if self.lifecycle is not None:
                            self.lifecycle.update(FIXED_STEP)
                        self.game.update(FIXED_STEP, state)
                    self.play_frames += frames
                elif action == "play_stop":
                    if not self.playing:
                        raise ValueError("play mode is not active")
                    lifecycle = self.lifecycle
                    self.lifecycle = None
                    try:
                        if lifecycle is not None:
                            lifecycle.stop()
                    finally:
                        if self._play_snapshot is not None:
                            restore_scene(
                                scene,
                                self._play_snapshot,
                                self._registry_locked(),
                                self.component_types,
                            )
                        self.playing = False
                        self.play_frames = 0
                        self._play_snapshot = None
                        self.history.clear()
                        self.selected_id = None
                elif action == "set_component":
                    node = find_node(scene, payload.get("id"))
                    self._apply_history(
                        scene,
                        lambda: set_component(
                            node,
                            payload.get("type"),
                            payload.get("data"),
                            self.component_types,
                        ),
                    )
                    self.selected_id = node.id
                elif action == "remove_component":
                    node = find_node(scene, payload.get("id"))
                    self._apply_history(
                        scene,
                        lambda: remove_component(
                            node, payload.get("type"), self.component_types
                        ),
                    )
                    self.selected_id = node.id
                elif action == "create_node":
                    parent = self._parent_locked(scene, payload.get("parent"))
                    node = self._apply_history(
                        scene,
                        lambda: create_node(
                            scene,
                            payload,
                            parent=parent,
                            registry=self._registry_locked(),
                        ),
                    )
                    self.selected_id = node.id
                elif action == "delete_node":
                    node = find_node(scene, payload.get("id"))
                    parent = self._apply_history(scene, lambda: delete_node(scene, node))
                    self.selected_id = None if parent is scene.root else parent.id
                elif action == "duplicate_node":
                    node = find_node(scene, payload.get("id"))
                    clone = self._apply_history(
                        scene, lambda: duplicate_node(scene, node, payload.get("name"))
                    )
                    self.selected_id = clone.id
                elif action == "reparent_node":
                    node = find_node(scene, payload.get("id"))
                    parent = self._parent_locked(scene, payload.get("parent"))
                    self._apply_history(scene, lambda: reparent_node(scene, node, parent))
                    self.selected_id = node.id
                elif action == "save_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    name = payload.get("name") or "scene"
                    self.scene_library.save(name, scene)
                elif action == "load_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.load_into(payload.get("name"), scene)
                    self.history.clear()
                    self.selected_id = None
                    self.last_diff = None
                elif action == "add_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    parent = self._parent_locked(scene, payload.get("parent"))
                    node = self._apply_history(
                        scene,
                        lambda: add_scene(
                            scene,
                            payload.get("name"),
                            self.scene_library,
                            parent,
                        ),
                    )
                    self.selected_id = node.id
                elif action == "unload_scene":
                    node = find_node(scene, payload.get("id"))
                    parent = self._apply_history(
                        scene, lambda: unload_scene(scene, node)
                    )
                    self.selected_id = None if parent is scene.root else parent.id
                elif action == "save_scene_group":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    node = find_node(scene, payload.get("id"))
                    group = node.scene_group
                    if group is None:
                        raise ValueError("node is not a scene group")
                    requested = payload.get("name")
                    if requested is None or requested == group.name:
                        save_scene_group(scene, node, self.scene_library)
                    else:
                        self._apply_history(
                            scene,
                            lambda: save_scene_group(
                                scene,
                                node,
                                self.scene_library,
                                requested,
                            ),
                        )
                    self.selected_id = node.id
                elif action == "diff_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    saved = self.scene_library.document(payload.get("name"))
                    current = scene_to_dict(scene, self._registry_locked())
                    self.last_diff = diff_scene_documents(saved, current)
                elif action == "rename_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.rename(
                        payload.get("name"), payload.get("new_name")
                    )
                elif action == "duplicate_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.duplicate(
                        payload.get("name"), payload.get("new_name")
                    )
                elif action == "delete_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.delete(payload.get("name"))
                elif action == "restore_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.restore(payload.get("trash"))
                elif action == "save_prefab":
                    node_id = payload.get("id") or self.selected_id
                    if node_id is None:
                        raise ValueError("select a node before saving a prefab")
                    node = find_node(scene, node_id)
                    name = payload.get("name") or node.id or node.name
                    previous = self.prefabs.get(name) if isinstance(name, str) else None
                    prefab = save_prefab(scene, node, name, self.prefabs)
                    if self.prefab_library is not None:
                        try:
                            self.prefab_library.save(name, prefab)
                        except Exception:
                            if previous is None:
                                self.prefabs.pop(name, None)
                            else:
                                self.prefabs[name] = previous
                            raise
                    self.selected_id = node.id
                elif action == "rename_prefab":
                    if self.prefab_library is None:
                        raise ValueError("no prefab library is configured")
                    old = payload.get("name")
                    entry = self.prefab_library.rename(old, payload.get("new_name"))
                    self.prefabs.pop(old, None)
                    self.prefabs.pop(entry.name, None)
                    self.prefabs[entry.name] = self.prefab_library.load(entry.name)
                    rename_prefab_links(scene, old, entry.name)
                elif action == "duplicate_prefab":
                    if self.prefab_library is None:
                        raise ValueError("no prefab library is configured")
                    entry = self.prefab_library.duplicate(
                        payload.get("name"), payload.get("new_name")
                    )
                    self.prefabs.pop(entry.name, None)
                    self.prefabs[entry.name] = self.prefab_library.load(entry.name)
                elif action == "delete_prefab":
                    if self.prefab_library is None:
                        raise ValueError("no prefab library is configured")
                    name = payload.get("name")
                    self.prefab_library.delete(name)
                    self.prefabs.pop(name, None)
                elif action == "restore_prefab":
                    if self.prefab_library is None:
                        raise ValueError("no prefab library is configured")
                    entry = self.prefab_library.restore(payload.get("trash"))
                    self.prefabs.pop(entry.name, None)
                    self.prefabs[entry.name] = self.prefab_library.load(entry.name)
                elif action == "insert_prefab":
                    name = payload.get("name")
                    self._ensure_prefab_locked(name)
                    parent = self._parent_locked(scene, payload.get("parent"))
                    roots = self._apply_history(
                        scene,
                        lambda: insert_prefab(
                            scene, self.prefabs, name, parent, payload.get("instance")
                        ),
                    )
                    if roots:
                        self.selected_id = roots[0].id
                elif action == "revert_prefab":
                    node = find_node(scene, payload.get("id") or self.selected_id)
                    link = node.prefab_link
                    if link is None:
                        raise ValueError("node is not a prefab instance")
                    if self.prefab_library is not None:
                        try:
                            self.prefabs[link.name] = self.prefab_library.load(link.name)
                        except KeyError:
                            self._ensure_prefab_locked(link.name)
                    else:
                        self._ensure_prefab_locked(link.name)
                    root = self._apply_history(
                        scene,
                        lambda: revert_prefab_instance(scene, node, self.prefabs),
                    )
                    if root:
                        self.selected_id = root[0].id
                elif action == "apply_prefab":
                    node = find_node(scene, payload.get("id") or self.selected_id)
                    link = node.prefab_link
                    if link is None:
                        raise ValueError("node is not a prefab instance")
                    previous = self.prefabs.get(link.name)
                    prefab = apply_prefab_instance(scene, node, self.prefabs)
                    if self.prefab_library is not None:
                        try:
                            self.prefab_library.save(link.name, prefab)
                        except Exception:
                            if previous is None:
                                self.prefabs.pop(link.name, None)
                            else:
                                self.prefabs[link.name] = previous
                            raise
                    self.selected_id = node.id
                elif action == "revert_prefab_override":
                    node_id = payload.get("id") or self.selected_id
                    if node_id is None:
                        raise ValueError("select a node before reverting an override")
                    node = self._apply_history(
                        scene,
                        lambda: revert_prefab_override(
                            scene,
                            node_id,
                            payload.get("field"),
                            self.prefabs,
                            self._registry_locked(),
                        ),
                    )
                    self.selected_id = node.id
                elif action == "apply_prefab_override":
                    node_id = payload.get("id") or self.selected_id
                    if node_id is None:
                        raise ValueError("select a node before applying an override")
                    node = find_node(scene, node_id)
                    updated = apply_prefab_override(
                        scene,
                        node_id,
                        payload.get("field"),
                        self.prefabs,
                        self._registry_locked(),
                    )
                    if self.prefab_library is not None:
                        self.prefab_library.save(updated.name, updated)
                    self.prefabs[updated.name] = updated
                    self.selected_id = node.id
                elif action == "undo":
                    self.history.undo(scene)
                    self.last_diff = None
                elif action == "redo":
                    self.history.redo(scene)
                    self.last_diff = None
                else:
                    raise ValueError(f"unknown editor action {action!r}")
            except KeyError as exc:
                raise WebProblem(
                    404,
                    str(exc),
                    "refresh /api/editor and choose an existing node or prefab",
                ) from exc
            except (TypeError, ValueError) as exc:
                raise WebProblem(
                    400,
                    str(exc),
                    "send a valid editor action with finite transform values",
                ) from exc
            return self._editor_locked(scene)

    def inspector(self) -> dict:
        from keystone.batch import merge_batches, plan_batches

        with self.lock:
            scene = self._scene_locked()
            document = scene_document(scene, game=self.name)
            try:
                batches = plan_batches(scene)
            except (AttributeError, TypeError, ValueError):
                batches = {"schema": 1, "groups": 0, "draw_calls": 0, "batched_calls": 0, "saved_calls": 0, "triangles": 0, "batches": []}
            try:
                merged = merge_batches(scene)
                merged_summary = {
                    "groups": merged["groups"],
                    "merged_calls": merged["merged_calls"],
                    "saved_calls": merged["saved_calls"],
                    "triangles": merged["triangles"],
                    "skin_merged_calls": merged["skin_merged_calls"],
                    "skin_saved_calls": merged["skin_saved_calls"],
                }
            except (AttributeError, TypeError, ValueError):
                merged_summary = None
            try:
                from keystone.gpu.instancing import plan_instanced

                instanced = plan_instanced(scene)
                instancing_summary = {
                    "groups": instanced["groups"],
                    "instanced_calls": instanced["instanced_calls"],
                    "saved_calls": instanced["saved_calls"],
                    "instances": instanced["instances"],
                    "triangles": instanced["triangles"],
                }
            except (AttributeError, TypeError, ValueError):
                instancing_summary = None
            mixer = getattr(self.game, "mixer", None)
            audio = None
            if mixer is not None and hasattr(mixer, "voice_count"):
                try:
                    from keystone.audio import audio_report

                    clip = mixer.render() if hasattr(mixer, "render") else None
                    voices = mixer.voice_count() if callable(mixer.voice_count) else 0
                    buses = dict(mixer.buses) if isinstance(getattr(mixer, "buses", None), dict) else {}
                    audio = audio_report(clip, voices=voices, buses=buses) if clip is not None else {"voices": voices, "buses": buses}
                except (AttributeError, TypeError, ValueError):
                    audio = None
            animation = None
            for attribute in ("animations", "animator", "controller"):
                try:
                    controller = getattr(self.game, attribute, None)
                    clips = getattr(controller, "clips", None) if controller is not None else None
                    if not isinstance(clips, dict):
                        continue
                    from keystone.animation import animation_report

                    animation = animation_report(controller)
                except (AttributeError, TypeError, ValueError, KeyError):
                    animation = None
                    continue
                break
            particles = None
            for attribute in ("particles", "fx", "particle_system"):
                try:
                    system = getattr(self.game, attribute, None)
                    if system is None or not hasattr(system, "alive_count"):
                        continue
                    from keystone.particles import particles_report

                    particles = particles_report(system)
                except (AttributeError, TypeError, ValueError):
                    particles = None
                    continue
                break
            assets = None
            registry = getattr(self.game, "assets", None)
            if registry is not None and hasattr(registry, "describe"):
                try:
                    inventory = registry.describe()
                    counts = inventory.get("stats", {}) if isinstance(inventory, dict) else {}
                    items = inventory.get("assets", []) if isinstance(inventory, dict) else []
                    assets = {
                        "total": counts.get("total", len(items) if isinstance(items, list) else 0),
                        "kinds": counts.get("kinds", {}),
                        "ids": sorted(item.get("id", "") for item in items if isinstance(item, dict))[:64],
                        "truncated": isinstance(items, list) and len(items) > 64,
                    }
                except (AttributeError, TypeError, ValueError):
                    assets = None
            shadow = getattr(scene, "shadow", None)
            color = getattr(scene, "color", None)
            post = getattr(scene, "post", None)
            bloom = getattr(scene, "bloom", None)
            sprite = getattr(scene, "sprite", None)
            culling = getattr(scene, "culling", None)
            return {
                "schema": 1,
                "game": self.name,
                "node_count": document["node_count"],
                "mesh_count": document["mesh_count"],
                "texture_count": document["texture_count"],
                "batches": batches,
                "merged": merged_summary,
                "instancing": instancing_summary,
                "shadows": {"enabled": _enabled(shadow), "size": 1024 if _enabled(shadow) else 0},
                "color": {"enabled": _enabled(color)},
                "post": {"enabled": _enabled(post)},
                "bloom": {"enabled": _enabled(bloom)},
                "sprites": {"enabled": _enabled(sprite)},
                "culling": {"enabled": _enabled(culling)},
                "audio": audio,
                "animation": animation,
                "particles": particles,
                "assets": assets,
                "scene_schema": SCENE_SCHEMA["version"],
            }


class KeystoneHTTPServer(ThreadingHTTPServer):
    """Threaded server carrying one game session for the request handler."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], session: GameSession) -> None:
        self.session = session
        super().__init__(address, ConsoleHandler)

    def handle_error(self, request: object, client_address: tuple[str, int]) -> None:
        error = sys.exc_info()[1]
        if isinstance(error, (ConnectionError, BrokenPipeError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


class ConsoleHandler(BaseHTTPRequestHandler):
    """Serve the API and the bundled static console."""

    protocol_version = "HTTP/1.1"
    server_version = "KeystoneWeb/1"

    def log_message(self, format: str, *args: object) -> None:
        return

    _GET_PATHS: ClassVar[frozenset[str]] = frozenset(
        {"/", "/index.html", "/app.js", "/viewer.js", "/style.css", "/api", "/api/health", "/api/describe", "/api/scene", "/api/inspector", "/api/editor"}
    )

    def do_OPTIONS(self) -> None:
        self._send(204, b"", None)

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path in self._GET_PATHS:
            content_type = "application/json; charset=utf-8" if path.startswith("/api") else STATIC_FILES.get(path.lstrip("/"))
            self._send(200, b"", content_type)
        else:
            self._send_problem(WebProblem(404, f"no route for {path}", "use /, /api, /api/health or /api/scene"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/" or path == "/index.html":
                self._send_file("index.html")
            elif path in ("/app.js", "/viewer.js", "/style.css"):
                self._send_file(path.lstrip("/"))
            elif path == "/api":
                self._send_json(200, self._index())
            elif path == "/api/health":
                self._send_json(200, self._health())
            elif path == "/api/describe":
                self._send_json(200, self.session.describe())
            elif path == "/api/scene":
                self._send_json(200, self.session.scene())
            elif path == "/api/inspector":
                self._send_json(200, self.session.inspector())
            elif path == "/api/editor":
                self._send_json(200, self.session.editor())
            elif path == "/api/simulate":
                raise WebProblem(405, "method not allowed", "use POST /api/simulate")
            else:
                raise WebProblem(404, f"no route for {path}", "use /, /api, /api/describe, /api/scene, /api/inspector or /api/simulate")
        except WebProblem as exc:
            self._send_problem(exc)
        except Exception as exc:  # noqa: BLE001 - HTTP must never leak a traceback
            self._send_problem(WebProblem(500, str(exc), "check the server log and retry the request"))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/simulate":
                payload = self._read_json()
                if not isinstance(payload, dict):
                    raise WebProblem(400, "request body must be a JSON object", 'send {"frames": 1}')
                actions = payload.get("actions", [])
                frames = payload.get("frames")
                if frames is None:
                    frames = len(actions) if isinstance(actions, list) and actions else 1
                step = payload.get("step", FIXED_STEP)
                trace = payload.get("trace", False)
                self._send_json(200, self.session.simulate(frames, actions, step, trace))
            elif path == "/api/editor":
                self._send_json(200, self.session.editor_action(self._read_json()))
            else:
                status = 405 if path in self._GET_PATHS else 404
                raise WebProblem(status, f"method not allowed for {path}" if status == 405 else f"no route for {path}", "POST /api/simulate or /api/editor")
        except WebProblem as exc:
            self._send_problem(exc)
        except Exception as exc:  # noqa: BLE001 - HTTP must never leak a traceback
            self._send_problem(WebProblem(500, str(exc), "check the server log and retry the request"))

    def do_PUT(self) -> None:
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._method_not_allowed()

    def do_DELETE(self) -> None:
        self._method_not_allowed()

    @property
    def session(self) -> GameSession:
        return self.server.session

    def _index(self) -> dict:
        return {
            "ok": True,
            "api": WEB_API_VERSION,
            "game": self.session.name,
            "scene_schema": SCENE_SCHEMA,
            "endpoints": {
                "health": {"method": "GET", "path": "/api/health"},
                "describe": {"method": "GET", "path": "/api/describe"},
                "scene": {"method": "GET", "path": "/api/scene"},
                "inspector": {"method": "GET", "path": "/api/inspector"},
                "editor": {"method": "GET/POST", "path": "/api/editor", "schema": EDITOR_SCHEMA},
                "simulate": {
                    "method": "POST",
                    "path": "/api/simulate",
                    "body": {"frames": 1, "actions": [], "step": FIXED_STEP, "trace": False},
                },
            },
        }

    def _health(self) -> dict:
        return {
            "ok": True,
            "api": WEB_API_VERSION,
            "scene_schema": SCENE_SCHEMA["version"],
            "editor_schema": EDITOR_SCHEMA["version"],
            "game": self.session.name,
        }

    def _read_json(self) -> object:
        header = self.headers.get("Content-Length")
        if header is None:
            raise WebProblem(411, "Content-Length is required", "send a JSON body with Content-Type: application/json")
        try:
            length = int(header)
        except ValueError as exc:
            raise WebProblem(400, "Content-Length must be an integer", "send a valid byte length") from exc
        if length < 0:
            raise WebProblem(400, "Content-Length cannot be negative", "send a valid byte length")
        if length > MAX_BODY:
            raise WebProblem(413, f"request body exceeds {MAX_BODY} bytes", "send a smaller action list")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise WebProblem(400, "request body was truncated", "resend the complete JSON body")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WebProblem(400, "request body must be UTF-8", "encode the JSON body as UTF-8") from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise WebProblem(400, f"invalid JSON: {exc.msg}", "send a valid JSON object") from exc
        except (ValueError, RecursionError) as exc:
            raise WebProblem(400, f"invalid JSON: {exc}", "send a smaller, valid JSON object") from exc

    def _send_file(self, name: str) -> None:
        content_type = STATIC_FILES.get(name)
        if content_type is None:
            raise WebProblem(404, f"no static asset named {name}", "use /, /app.js, /viewer.js or /style.css")
        try:
            body = (STATIC_ROOT / name).read_bytes()
        except OSError as exc:
            raise WebProblem(500, f"could not read {name}: {exc}", "reinstall the Keystone package") from exc
        self._send(200, body, content_type)

    def _send_problem(self, problem: WebProblem) -> None:
        headers = {"Allow": "GET, POST, HEAD, OPTIONS"} if problem.status == 405 else None
        self._send_json(
            problem.status,
            {"ok": False, "error": problem.why, "fix": problem.fix},
            extra_headers=headers,
        )

    def _method_not_allowed(self) -> None:
        self._send_json(
            405,
            {"ok": False, "error": "method not allowed", "fix": "use GET, POST, HEAD or OPTIONS"},
            extra_headers={"Allow": "GET, POST, HEAD, OPTIONS"},
        )

    def _send_json(self, status: int, payload: dict, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra_headers)

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str | None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        if status >= 400:
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        if body:
            self.wfile.write(body)


def create_server(
    game: GameModule,
    host: str = "127.0.0.1",
    port: int = 0,
    prefab_dir: str | Path | None = None,
    scene_dir: str | Path | None = None,
    initial_scene: str | None = None,
) -> KeystoneHTTPServer:
    """Create a bound server; port 0 asks the OS for a free port."""
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return KeystoneHTTPServer(
        (host, port),
        GameSession(
            game,
            prefab_dir=prefab_dir,
            scene_dir=scene_dir,
            initial_scene=initial_scene,
        ),
    )


def serve(
    game: GameModule,
    host: str = "127.0.0.1",
    port: int = 8000,
    prefab_dir: str | Path | None = None,
    scene_dir: str | Path | None = None,
    initial_scene: str | None = None,
) -> int:
    """Run the local console until interrupted."""
    try:
        server = create_server(
            game,
            host=host,
            port=port,
            prefab_dir=prefab_dir,
            scene_dir=scene_dir,
            initial_scene=initial_scene,
        )
    except OSError as exc:
        raise ValueError(
            f"web console could not bind {host}:{port}.\n"
            f"Why: {exc}\n"
            "Fix: pass --port with a free port, or stop the process using it."
        ) from exc
    actual_port = server.server_address[1]
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("Warning: the console has no authentication; prefer the loopback host.", flush=True)
    print(f"Keystone web console: http://{display_host}:{actual_port}/", flush=True)
    print("Serving the JSON API and WebGL viewer. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.", flush=True)
    finally:
        server.server_close()
    return 0
