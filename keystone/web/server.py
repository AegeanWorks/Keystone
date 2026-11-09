"""A localhost JSON API and static web console for the game-agnostic engine."""

from __future__ import annotations

import copy
import json
import math
import sys
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from keystone.animation import AnimationClip, apply_pose
from keystone.animation_blend import BlendSpace1D
from keystone.animation_library import AnimationLibrary
from keystone.animation_state import AnimationStateMachine
from keystone.assets import AssetRegistry
from keystone.component_codec import validate_component_types
from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.lifecycle import ComponentRuntime
from keystone.material_library import MaterialLibrary, material_from_document
from keystone.plugin import GameModule, describe_game
from keystone.prefab import Prefab
from keystone.prefab_library import PrefabLibrary
from keystone.project import (
    forget_project_asset,
    import_project_asset,
    import_project_gltf,
    load_project,
    project_asset_id,
    resolve_project_target,
    set_project_startup_scene,
)
from keystone.replay import FIXED_STEP
from keystone.scene import Node, Scene
from keystone.scene_diff import diff_scene_documents
from keystone.scene_library import SceneLibrary
from keystone.scene_snapshot import restore_scene, scene_to_dict
from keystone.state_machine_library import StateMachineLibrary
from keystone.web.editor import (
    EDITOR_ACTIONS,
    EditorHistory,
    add_scene,
    apply_prefab_instance,
    apply_prefab_override,
    asset_entries,
    assign_assets,
    clear_clipboard_payloads,
    clip_key_count,
    component_schemas,
    count_prefab_payloads,
    create_node,
    delete_node,
    delete_selection,
    duplicate_node,
    editor_document,
    find_node,
    insert_prefab,
    normalize_prefab_edit_ids,
    refresh_prefab_instances,
    reload_scene_assets,
    remove_clip_key,
    remove_component,
    rename_prefab_links,
    reparent_node,
    revert_prefab_instance,
    revert_prefab_override,
    save_prefab,
    save_prefab_nodes,
    save_scene_group,
    seed_prefab_instance_baselines,
    set_clip_key,
    set_component,
    set_node_properties,
    set_scene,
    set_selection_properties,
    set_selection_transform,
    toggle_selection_visible,
    transform_from_payload,
    transform_selection,
    unload_scene,
    validate_scene,
)
from keystone.web.scene import scene_document
from keystone.web.schema import EDITOR_SCHEMA, SCENE_SCHEMA, WEB_API_VERSION

MAX_BODY = 1_000_000
MAX_FRAMES = 1_000_000
MAX_BATCH_ACTIONS = 100
PREFAB_EDIT_BLOCKED = frozenset(
    {
        "play_start",
        "play_step",
        "play_pause",
        "play_resume",
        "play_stop",
        "save_prefab",
        "import_gltf",
        "forget_asset",
        "build_project",
        "revert_scene",
        "refresh_prefab_instances",
        "apply_prefab",
        "revert_prefab",
        "rename_prefab",
        "duplicate_prefab",
        "delete_prefab",
        "restore_prefab",
        "save_scene",
        "load_scene",
        "add_scene",
        "unload_scene",
        "save_scene_group",
        "diff_scene",
        "rename_scene",
        "duplicate_scene",
        "delete_scene",
        "restore_scene",
    }
)

SCENE_CLEAN_ACTIONS = frozenset({"save_scene", "load_scene", "revert_scene"})

SCENE_NEUTRAL_ACTIONS = frozenset(
    {
        "select",
        "select_many",
        "set_layer_visible",
        "set_nodes_locked",
        "copy_selection",
        "play_start",
        "play_step",
        "play_pause",
        "play_resume",
        "play_stop",
        "save_animation",
        "delete_animation",
        "restore_animation",
        "set_animation_key",
        "remove_animation_key",
        "save_state_machine",
        "load_state_machine",
        "rename_state_machine",
        "duplicate_state_machine",
        "delete_state_machine",
        "restore_state_machine",
        "save_material",
        "delete_material",
        "restore_material",
        "save_prefab",
        "edit_prefab",
        "save_prefab_edit",
        "close_prefab_edit",
        "duplicate_prefab",
        "delete_prefab",
        "restore_prefab",
        "apply_prefab",
        "apply_prefab_override",
        "diff_scene",
        "validate_scene",
        "set_startup_scene",
        "import_asset",
        "import_gltf",
        "reload_assets",
        "forget_asset",
        "asset_usages",
        "build_project",
        "rename_scene",
        "duplicate_scene",
        "delete_scene",
        "restore_scene",
    }
)


def _copy_scene_settings(source: Scene, target: Scene) -> None:
    """Copy camera and environment settings without copying scene nodes."""
    target.camera = copy.deepcopy(source.camera)
    target.light = copy.deepcopy(source.light)
    target.point_light = copy.deepcopy(source.point_light)
    target.shadow = copy.deepcopy(source.shadow)
    target.color = copy.deepcopy(source.color)
    target.post = copy.deepcopy(source.post)
    target.bloom = copy.deepcopy(source.bloom)
    target.sprite = copy.deepcopy(source.sprite)
    target.culling = copy.deepcopy(source.culling)
    target.ambient = copy.deepcopy(source.ambient)
    target.background = copy.deepcopy(source.background)
    target.sky = copy.deepcopy(source.sky)
    target.fog_density = source.fog_density
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
        animation_dir: str | Path | None = None,
        material_dir: str | Path | None = None,
        initial_scene: str | None = None,
        project_dir: str | Path | None = None,
    ) -> None:
        self.game = game
        self.lock = threading.RLock()
        self._batch_depth = 0
        self._built = False
        self.selected_id: str | None = None
        self.selected_ids: list[str] = []
        self.hidden_layers: set[str] = set()
        self.locked_ids: set[str] = set()
        self.prefabs: dict[str, Prefab] = {}
        self.clipboard: Prefab | None = None
        self.history = EditorHistory()
        self._history_label = "edit"
        component_types = validate_component_types(getattr(game, "component_types", None))
        self.component_types = component_types
        self.project_dir = None
        self.startup_scene: str | None = None
        self.project_assets: tuple[str, ...] = ()
        if project_dir is not None:
            project_context = load_project(project_dir)
            self.project_dir = project_context.directory
            self.startup_scene = project_context.manifest.startup_scene
            self.project_assets = project_context.manifest.assets
        self.playing = False
        self.play_frames = 0
        self.play_paused = False
        self.prefab_edit: dict[str, object] | None = None
        self._prefab_edit_dirty = False
        self.last_prefab_refresh: dict[str, int] | None = None
        self.last_animation_preview: dict[str, object] | None = None
        self.last_blend_space_preview: dict[str, object] | None = None
        self.last_animation_key: dict[str, object] | None = None
        self.last_validation: dict[str, object] | None = None
        self.last_import: dict[str, object] | None = None
        self.last_gltf_import: dict[str, object] | None = None
        self.last_asset_reload: dict[str, object] | None = None
        self.last_forgotten_asset: dict[str, object] | None = None
        self.last_asset_usages: dict[str, object] | None = None
        self.last_revert: dict[str, object] | None = None
        self.last_build: dict[str, object] | None = None
        self.last_state_machine_preview: dict[str, object] | None = None
        self.last_state_machine_document: dict[str, object] | None = None
        self.scene_dirty = False
        self.saved_scene = initial_scene
        self._prefab_edit_original_history: EditorHistory | None = None
        self._prefab_edit_original_selection: list[str] = []
        self._scene_override: Scene | None = None
        self._scene_before_prefab: Scene | None = None
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
        self.animation_library: AnimationLibrary | None = None
        if animation_dir is not None:
            self.animation_library = AnimationLibrary(animation_dir)
        self.state_machine_library: StateMachineLibrary | None = None
        if animation_dir is not None:
            self.state_machine_library = StateMachineLibrary(animation_dir)
        self.material_library: MaterialLibrary | None = None
        if material_dir is not None:
            self.material_library = MaterialLibrary(
                material_dir, registry=self._registry_locked()
            )
        self._materials_registered = False
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
        scene = self._scene_override
        if scene is None:
            scene = self._scene_before_prefab
        if scene is None:
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
        if self.material_library is not None:
            self.material_library.registry = registry
            if not self._materials_registered:
                self.material_library.register_all()
                self._materials_registered = True
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

    def _node_locked_locked(self, node: Node) -> bool:
        current: Node | None = node
        while current is not None:
            if current.id in self.locked_ids:
                return True
            current = current.parent
        return False

    def _ensure_unlocked_locked(self, nodes: list[Node]) -> None:
        locked = [
            node.id for node in nodes if self._node_locked_locked(node)
        ]
        if locked:
            raise ValueError(
                "locked nodes cannot be edited: "
                + ", ".join(sorted(set(locked)))
            )

    def _ensure_subtree_unlocked_locked(self, nodes: list[Node]) -> None:
        locked: set[str] = set()
        for root in nodes:
            for node in root.traverse():
                if self._node_locked_locked(node):
                    locked.add(node.id)
        if locked:
            raise ValueError(
                "locked nodes cannot be deleted: "
                + ", ".join(sorted(locked))
            )

    @staticmethod
    def _document_asset_ids(value: object, ids: set[str]) -> None:
        """Collect mesh/material/texture ids from one scene document."""
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("mesh", "material", "texture") and isinstance(item, str):
                    ids.add(item)
                else:
                    GameSession._document_asset_ids(item, ids)
        elif isinstance(value, list):
            for item in value:
                GameSession._document_asset_ids(item, ids)

    @staticmethod
    def _format_asset_usage(report: dict[str, object]) -> str:
        parts: list[str] = []
        for item in report.get("scene_nodes", []):
            parts.append(f"node {item.get('node')!r} {item.get('field')}")
        for item in report.get("registry", []):
            parts.append(f"asset {item.get('asset')!r} {item.get('field')}")
        for name in report.get("prefabs", []):
            parts.append(f"prefab {name!r}")
        for name in report.get("scenes", []):
            parts.append(f"scene file {name!r}")
        return ", ".join(parts)

    def _asset_usage_report_locked(
        self,
        scene: Scene,
        registry: AssetRegistry,
        asset_id: str,
    ) -> dict[str, object]:
        """Return structured references to one asset across live and saved content."""
        record = registry.get(asset_id)
        payload = record.payload if record is not None else None
        scene_nodes: list[dict[str, str]] = []
        if payload is not None:
            for node in scene.traverse():
                if node.mesh is payload:
                    scene_nodes.append({"node": node.id, "field": "mesh"})
                if node.material is payload:
                    scene_nodes.append({"node": node.id, "field": "material"})
                if getattr(node.material, "texture", None) is payload:
                    scene_nodes.append({"node": node.id, "field": "texture"})
        registry_refs: list[dict[str, str]] = []
        for item in registry:
            if item.id == asset_id:
                continue
            if asset_id in item.dependencies:
                registry_refs.append({"asset": item.id, "field": "dependency"})
            if payload is not None and getattr(item.payload, "texture", None) is payload:
                registry_refs.append({"asset": item.id, "field": "texture"})
        prefabs: set[str] = set()
        for prefab in self.prefabs.values():
            try:
                references = prefab.asset_ids(registry)
            except (KeyError, TypeError, ValueError):
                continue
            if asset_id in references:
                prefabs.add(prefab.name)
        if self.prefab_library is not None:
            for entry in self.prefab_library.entries():
                if entry.error is not None:
                    continue
                try:
                    prefab = self.prefab_library.load(entry.name)
                    references = prefab.asset_ids(registry)
                except (KeyError, TypeError, ValueError):
                    continue
                if asset_id in references:
                    prefabs.add(entry.name)
        scenes: set[str] = set()
        if self.scene_library is not None:
            for entry in self.scene_library.entries():
                if entry.error is not None:
                    continue
                try:
                    document = self.scene_library.document(entry.name)
                except (KeyError, TypeError, ValueError):
                    continue
                ids: set[str] = set()
                self._document_asset_ids(document, ids)
                if asset_id in ids:
                    scenes.add(entry.name)
        project_asset = None
        if asset_id.startswith("project:") and self.project_dir is not None:
            path = asset_id.removeprefix("project:")
            project_asset = path in {
                Path(item).as_posix() for item in self.project_assets
            }
        history_references = (
            self.history.count_payloads({id(payload)})
            if payload is not None
            else 0
        )
        clipboard_references = (
            count_prefab_payloads(self.clipboard, {id(payload)})
            if payload is not None
            else 0
        )
        references = (
            len(scene_nodes) + len(registry_refs) + len(prefabs) + len(scenes)
        )
        return {
            "schema": 1,
            "asset": asset_id,
            "registered": record is not None,
            "kind": record.kind if record is not None else None,
            "scene_nodes": scene_nodes,
            "registry": registry_refs,
            "prefabs": sorted(prefabs),
            "scenes": sorted(scenes),
            "history_references": history_references,
            "clipboard_references": clipboard_references,
            "project_asset": project_asset,
            "references": references,
            "found": references > 0,
        }

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

    def _history_label_for(self, action: str, payload: dict) -> str:
        target = payload.get("id") or payload.get("name")
        if isinstance(target, str) and target.strip():
            return f"{action} {target.strip()}"[:120]
        return action

    def _apply_history(self, scene: Scene, operation: Callable[[], object]) -> object:
        if self._batch_depth:
            result = operation()
        else:
            result = self.history.apply(
                scene, operation, label=self._history_label
            )
        if self.prefab_edit is not None:
            self._prefab_edit_dirty = True
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
                label=f"batch {len(actions)} actions",
            )
        except Exception:
            self._set_selected_ids(before)
            raise
        finally:
            self._batch_depth -= 1
        if self.prefab_edit is not None:
            self._prefab_edit_dirty = True

    def _prefab_edit_document(self) -> dict[str, object] | None:
        if self.prefab_edit is None:
            return None
        roots = self.prefab_edit.get("roots")
        root_ids = list(roots) if isinstance(roots, list) else []
        return {
            "name": str(self.prefab_edit.get("name", "")),
            "roots": root_ids,
            "root_count": len(root_ids),
            "dirty": self._prefab_edit_dirty,
        }

    def _edit_prefab_locked(self, name: object) -> Scene:
        if self.prefab_edit is not None:
            raise ValueError("prefab edit mode is already active")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("prefab name must be a non-blank string")
        self._ensure_prefab_locked(name)
        original_scene = self._scene_locked()
        isolated = Scene()
        _copy_scene_settings(original_scene, isolated)
        roots = insert_prefab(
            isolated,
            self.prefabs,
            name,
            None,
            "edit",
            self._registry_locked(),
        )
        if not roots:
            raise ValueError("prefab has no roots")
        self._scene_before_prefab = original_scene
        self._scene_override = isolated
        self.prefab_edit = {
            "name": name,
            "roots": [root.id for root in roots],
        }
        self._prefab_edit_original_history = self.history
        self._prefab_edit_original_selection = self.selected_ids
        self._prefab_edit_dirty = False
        self.history = EditorHistory()
        self._set_selected_ids([roots[0].id])
        self.last_diff = None
        return isolated

    def _save_prefab_edit_locked(self, scene: Scene) -> Prefab:
        if self.prefab_edit is None:
            raise ValueError("prefab edit mode is not active")
        roots = self.prefab_edit.get("roots")
        if not isinstance(roots, list) or not roots:
            raise ValueError("prefab edit scene has no roots")
        node = scene.find_by_id(roots[0])
        if node is None:
            raise KeyError("prefab edit root is missing")
        name = str(self.prefab_edit.get("name", ""))
        link = node.prefab_link
        if link is None or link.name != name:
            raise ValueError(
                "prefab edit root is no longer linked to the edited prefab"
            )
        normalize_prefab_edit_ids(scene, link)
        previous = self.prefabs.get(name)
        prefab = apply_prefab_instance(
            scene, node, self.prefabs, self._registry_locked()
        )
        try:
            if self.prefab_library is not None:
                self.prefab_library.save(prefab.name, prefab)
        except Exception:
            if previous is None:
                self.prefabs.pop(name, None)
            else:
                self.prefabs[name] = previous
            raise
        self.prefabs[prefab.name] = prefab
        seed_prefab_instance_baselines(
            scene, node, self._registry_locked()
        )
        self._prefab_edit_dirty = False
        return prefab

    def _close_prefab_edit_locked(self, scene: Scene, save: bool) -> Scene:
        if self.prefab_edit is None:
            raise ValueError("prefab edit mode is not active")
        if save:
            self._save_prefab_edit_locked(scene)
        original_history = self._prefab_edit_original_history
        original_selection = list(self._prefab_edit_original_selection)
        self._scene_override = None
        self._scene_before_prefab = None
        self.prefab_edit = None
        self._prefab_edit_original_history = None
        self._prefab_edit_original_selection = []
        self._prefab_edit_dirty = False
        self.history = (
            original_history if original_history is not None else EditorHistory()
        )
        self._set_selected_ids(original_selection)
        self.last_diff = None
        return self._scene_locked()

    def _persist_prefab_locked(
        self, name: str, prefab: Prefab, previous: Prefab | None
    ) -> None:
        if self.prefab_library is None:
            return
        try:
            self.prefab_library.save(name, prefab)
        except Exception:
            if previous is None:
                self.prefabs.pop(name, None)
            else:
                self.prefabs[name] = previous
            raise

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

    def _play_state_locked(self) -> dict[str, object]:
        state: dict[str, object] = {
            "active": self.playing,
            "paused": self.play_paused,
            "frames": self.play_frames,
            "step": FIXED_STEP,
            "lifecycle": self._lifecycle_state(),
            "status": None,
            "snapshot": None,
        }
        if not self.playing:
            return state
        try:
            status = self.game.status()
            state["status"] = status if isinstance(status, str) else str(status)
        # hygiene: allow game hooks are foreign code
        except Exception as exc:  # noqa: BLE001
            state["status_error"] = str(exc)
        try:
            snapshot = self.game.snapshot()
            json.dumps(snapshot)
            state["snapshot"] = snapshot
        # hygiene: allow game hooks are foreign code
        except Exception as exc:  # noqa: BLE001
            state["snapshot_error"] = str(exc)
        return state

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
            play_state=self._play_state_locked(),
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
            prefab_edit=self._prefab_edit_document(),
            locked_ids=self.locked_ids,
        )
        document["game"] = self.name
        document["prefab_refresh"] = self.last_prefab_refresh
        document["animation_preview"] = self.last_animation_preview
        document["blend_space_preview"] = self.last_blend_space_preview
        document["animation_key"] = self.last_animation_key
        document["validation"] = self.last_validation
        document["imported_asset"] = self.last_import
        document["imported_gltf"] = self.last_gltf_import
        document["forgotten_asset"] = self.last_forgotten_asset
        document["asset_usages"] = self.last_asset_usages
        document["asset_reload"] = self.last_asset_reload
        document["startup_scene"] = self.startup_scene
        layer_counts: dict[str, int] = {}
        for node in scene.traverse():
            if node is scene.root:
                continue
            layer_name = node.layer or "default"
            layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
        document["layers"] = [
            {"name": name, "count": count}
            for name, count in sorted(layer_counts.items())
        ]
        document["hidden_layers"] = sorted(self.hidden_layers)
        document["clipboard"] = (
            {
                "count": len(self.clipboard.roots),
                "names": [root.name for root in self.clipboard.roots],
            }
            if self.clipboard is not None
            else None
        )
        document["project_assets"] = list(self.project_assets)
        document["saved_scene"] = self.saved_scene
        document["scene_dirty"] = self.scene_dirty
        document["revert"] = self.last_revert
        document["build"] = self.last_build
        document["animations"] = (
            [entry.describe() for entry in self.animation_library.entries()]
            if self.animation_library is not None
            else []
        )
        document["trash"]["animations"] = (
            self.animation_library.trash()
            if self.animation_library is not None
            else []
        )
        document["state_machines"] = (
            [
                entry.describe()
                for entry in self.state_machine_library.entries()
            ]
            if self.state_machine_library is not None
            else []
        )
        document["trash"]["state_machines"] = (
            self.state_machine_library.trash()
            if self.state_machine_library is not None
            else []
        )
        document["state_machine_preview"] = self.last_state_machine_preview
        document["state_machine_document"] = self.last_state_machine_document
        document["trash"]["materials"] = (
            self.material_library.trash()
            if self.material_library is not None
            else []
        )
        document["materials"] = (
            [entry.describe() for entry in self.material_library.entries()]
            if self.material_library is not None
            else []
        )
        document["workspace"] = {
            "project_dir": (
                self.project_dir.as_posix() if self.project_dir is not None else None
            ),
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
            "animation_dir": (
                self.animation_library.directory.as_posix()
                if self.animation_library is not None
                else None
            ),
            "material_dir": (
                self.material_library.directory.as_posix()
                if self.material_library is not None
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
        self._history_label = self._history_label_for(action, payload)
        self.last_prefab_refresh = None
        self.last_animation_preview = None
        self.last_blend_space_preview = None
        self.last_animation_key = None
        self.last_validation = None
        self.last_import = None
        self.last_gltf_import = None
        self.last_asset_reload = None
        self.last_forgotten_asset = None
        self.last_asset_usages = None
        self.last_revert = None
        self.last_build = None
        self.last_state_machine_preview = None
        self.last_state_machine_document = None
        with self.lock:
            scene = self._scene_locked()
            try:
                if self.playing and action not in (
                    "select",
                    "select_many",
                    "play_step",
                    "play_pause",
                    "play_resume",
                    "play_stop",
                ):
                    raise ValueError("play mode is active; stop it before editing")
                if self.prefab_edit is not None and action in PREFAB_EDIT_BLOCKED:
                    raise ValueError(
                        f"{action} is not available while editing a prefab; "
                        "close prefab edit first"
                    )
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
                elif action == "set_layer_visible":
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "layer name must be a non-blank string"
                        )
                    visible = payload.get("visible")
                    if not isinstance(visible, bool):
                        raise TypeError(
                            "layer visible must be a boolean"
                        )
                    if visible:
                        self.hidden_layers.discard(name)
                    else:
                        self.hidden_layers.add(name)
                        self._set_selected_ids(
                            [
                                node_id
                                for node_id in self.selected_ids
                                if (
                                    (node := scene.find_by_id(node_id))
                                    is not None
                                    and node.layer not in self.hidden_layers
                                )
                            ]
                        )
                elif action == "set_nodes_locked":
                    ids = payload.get("ids")
                    if ids is None:
                        ids = self.selected_ids
                    if not isinstance(ids, list) or not ids:
                        raise ValueError(
                            "select at least one node before changing locks"
                        )
                    if any(
                        not isinstance(item, str) or not item.strip()
                        for item in ids
                    ):
                        raise ValueError(
                            "locked node ids must be non-blank strings"
                        )
                    nodes = [find_node(scene, node_id) for node_id in ids]
                    locked = payload.get("locked")
                    if not isinstance(locked, bool):
                        raise TypeError("node locked must be a boolean")
                    for node in nodes:
                        if locked:
                            self.locked_ids.add(node.id)
                        else:
                            self.locked_ids.discard(node.id)
                elif action == "transform":
                    node = find_node(scene, payload.get("id"))
                    self._ensure_unlocked_locked([node])

                    def apply_transform() -> None:
                        node.transform = transform_from_payload(node, payload)

                    self._apply_history(scene, apply_transform)
                    self.selected_id = node.id
                elif action == "transform_selection":
                    nodes = [
                        find_node(scene, node_id)
                        for node_id in self.selected_ids
                    ]
                    self._ensure_unlocked_locked(nodes)
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
                    nodes = [
                        find_node(scene, node_id)
                        for node_id in self.selected_ids
                    ]
                    self._ensure_subtree_unlocked_locked(nodes)
                    parent = self._apply_history(
                        scene,
                        lambda: delete_selection(scene, self.selected_ids),
                    )
                    self.selected_id = None if parent is scene.root else parent.id
                elif action == "set_node":
                    node = find_node(scene, payload.get("id"))
                    self._ensure_unlocked_locked([node])
                    self._apply_history(
                        scene, lambda: set_node_properties(node, payload)
                    )
                    self.selected_id = node.id
                elif action == "set_selection_properties":
                    nodes = [
                        find_node(scene, node_id)
                        for node_id in self.selected_ids
                    ]
                    self._ensure_unlocked_locked(nodes)
                    self._apply_history(
                        scene,
                        lambda: set_selection_properties(
                            scene, self.selected_ids, payload
                        ),
                    )
                elif action == "set_selection_transform":
                    nodes = [
                        find_node(scene, node_id)
                        for node_id in self.selected_ids
                    ]
                    self._ensure_unlocked_locked(nodes)
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
                    self._ensure_unlocked_locked([node])
                    self._apply_history(
                        scene,
                        lambda: assign_assets(node, payload, self._registry_locked()),
                    )
                    self.selected_id = node.id
                elif action == "assign_asset_selection":
                    if not self.selected_ids:
                        raise ValueError(
                            "select at least one node before assigning assets"
                        )
                    nodes = [
                        find_node(scene, node_id)
                        for node_id in self.selected_ids
                    ]
                    self._ensure_unlocked_locked(nodes)
                    registry = self._registry_locked()
                    self._apply_history(
                        scene,
                        lambda: [
                            assign_assets(node, payload, registry)
                            for node in nodes
                        ],
                    )
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
                    self.play_paused = False
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
                elif action == "play_pause":
                    if not self.playing:
                        raise ValueError("play mode is not active")
                    self.play_paused = True
                elif action == "play_resume":
                    if not self.playing:
                        raise ValueError("play mode is not active")
                    self.play_paused = False
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
                        self.play_paused = False
                        self._play_snapshot = None
                        self.history.clear()
                        self.selected_id = None
                elif action == "preview_animation":
                    name = payload.get("name")
                    clip_payload = payload.get("clip")
                    if name is not None and clip_payload is not None:
                        raise ValueError(
                            "preview_animation needs name or clip, not both"
                        )
                    if name is not None:
                        if self.animation_library is None:
                            raise ValueError(
                                "no animation library is configured"
                            )
                        clip = self.animation_library.load(name)
                        source = "library"
                    else:
                        if not isinstance(clip_payload, dict):
                            raise TypeError(
                                "preview_animation clip must be a JSON object"
                            )
                        clip = AnimationClip.from_dict(clip_payload)
                        source = "inline"
                    time = payload.get("time", 0.0)
                    if (
                        isinstance(time, bool)
                        or not isinstance(time, (int, float))
                        or not math.isfinite(time)
                    ):
                        raise ValueError(
                            "preview_animation time must be a finite number"
                        )
                    if time < 0.0:
                        raise ValueError(
                            "preview_animation time must be non-negative"
                        )
                    record = payload.get("record", True)
                    if not isinstance(record, bool):
                        raise TypeError(
                            "preview_animation record must be a boolean"
                        )
                    if record:
                        updated = self._apply_history(
                            scene,
                            lambda: apply_pose(
                                scene, clip.sample(float(time))
                            ),
                        )
                    else:
                        updated = apply_pose(scene, clip.sample(float(time)))
                        self.last_diff = None
                    self.last_animation_preview = {
                        "name": clip.name,
                        "time": round(float(time), 6),
                        "updated": list(updated),
                        "track_count": len(clip.position_tracks)
                        + len(clip.rotation_tracks)
                        + len(clip.scale_tracks),
                        "source": source,
                        "record": record,
                    }
                elif action == "preview_blend_space":
                    data = payload.get("blend_space")
                    if not isinstance(data, dict):
                        raise TypeError(
                            "preview_blend_space blend_space must be a JSON object"
                        )
                    space = BlendSpace1D.from_dict(data)
                    parameter = payload.get("parameter", 0.0)
                    if (
                        isinstance(parameter, bool)
                        or not isinstance(parameter, (int, float))
                        or not math.isfinite(parameter)
                    ):
                        raise ValueError(
                            "preview_blend_space parameter must be a finite number"
                        )
                    time = payload.get("time", 0.0)
                    if (
                        isinstance(time, bool)
                        or not isinstance(time, (int, float))
                        or not math.isfinite(time)
                    ):
                        raise ValueError(
                            "preview_blend_space time must be a finite number"
                        )
                    if time < 0.0:
                        raise ValueError(
                            "preview_blend_space time must be non-negative"
                        )
                    record = payload.get("record", True)
                    if not isinstance(record, bool):
                        raise TypeError(
                            "preview_blend_space record must be a boolean"
                        )
                    pose = space.sample(float(parameter), float(time))
                    if record:
                        updated = self._apply_history(
                            scene, lambda: apply_pose(scene, pose)
                        )
                    else:
                        updated = apply_pose(scene, pose)
                        self.last_diff = None
                    self.last_blend_space_preview = {
                        "parameter": round(float(parameter), 6),
                        "time": round(float(time), 6),
                        "updated": list(updated),
                        "record": record,
                        "report": space.report(),
                    }
                elif action == "save_animation":
                    if self.animation_library is None:
                        raise ValueError("no animation library is configured")
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "animation name must be a non-blank string"
                        )
                    clip_payload = payload.get("clip")
                    if not isinstance(clip_payload, dict):
                        raise TypeError("save_animation clip must be a JSON object")
                    data = dict(clip_payload)
                    data["name"] = name
                    clip = AnimationClip.from_dict(data)
                    self.animation_library.save(name, clip)
                elif action == "delete_animation":
                    if self.animation_library is None:
                        raise ValueError("no animation library is configured")
                    self.animation_library.delete(payload.get("name"))
                elif action == "restore_animation":
                    if self.animation_library is None:
                        raise ValueError("no animation library is configured")
                    self.animation_library.restore(payload.get("trash"))
                elif action in ("set_animation_key", "remove_animation_key"):
                    if self.animation_library is None:
                        raise ValueError("no animation library is configured")
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "animation name must be a non-blank string"
                        )
                    node_id = payload.get("id") or self.selected_id
                    if node_id is None:
                        raise ValueError(
                            "select a node before editing animation keys"
                        )
                    node = find_node(scene, node_id)
                    channel = payload.get("channel")
                    if channel not in ("position", "rotation", "scale"):
                        raise ValueError(
                            "animation channel must be position, rotation or scale"
                        )
                    time = payload.get("time")
                    if (
                        isinstance(time, bool)
                        or not isinstance(time, (int, float))
                        or not math.isfinite(time)
                        or time < 0.0
                    ):
                        raise ValueError(
                            "animation key time must be a finite non-negative number"
                        )
                    clip = self.animation_library.load(name)
                    if action == "set_animation_key":
                        value = payload.get("value")
                        if value is None:
                            value = getattr(node.transform, channel)
                        updated = set_clip_key(
                            clip, node.id, channel, float(time), value
                        )
                        removed = 0
                    else:
                        updated, removed = remove_clip_key(
                            clip, node.id, channel, float(time)
                        )
                    self.animation_library.save(name, updated)
                    self.last_animation_key = {
                        "action": action,
                        "name": name,
                        "node": node.id,
                        "channel": channel,
                        "time": round(float(time), 6),
                        "keys": clip_key_count(updated, node.id, channel),
                        "removed": removed,
                    }
                elif action == "save_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "state machine name must be a non-blank string"
                        )
                    data = payload.get("machine")
                    if not isinstance(data, dict):
                        raise TypeError(
                            "save_state_machine machine must be a JSON object"
                        )
                    machine = AnimationStateMachine.from_dict(data)
                    self.state_machine_library.save(name, machine)
                elif action == "load_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "state machine name must be a non-blank string"
                        )
                    machine = self.state_machine_library.load(name)
                    self.last_state_machine_document = {
                        "name": name,
                        "machine": machine.to_dict(),
                    }
                elif action == "rename_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    try:
                        self.state_machine_library.rename(
                            payload.get("name"), payload.get("new_name")
                        )
                    except FileExistsError as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "choose a state machine name that does not exist",
                        ) from exc
                elif action == "duplicate_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    try:
                        self.state_machine_library.duplicate(
                            payload.get("name"), payload.get("new_name")
                        )
                    except FileExistsError as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "choose a state machine name that does not exist",
                        ) from exc
                elif action == "delete_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    self.state_machine_library.delete(payload.get("name"))
                elif action == "restore_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    try:
                        self.state_machine_library.restore(
                            payload.get("trash")
                        )
                    except FileExistsError as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "rename or delete the live state machine before restoring",
                        ) from exc
                elif action == "preview_state_machine":
                    if self.state_machine_library is None:
                        raise ValueError(
                            "no state machine library is configured"
                        )
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "preview_state_machine name must be a non-blank string"
                        )
                    machine = self.state_machine_library.load(name)
                    parameters = payload.get("parameters", {})
                    if not isinstance(parameters, dict):
                        raise TypeError(
                            "preview_state_machine parameters must be a JSON object"
                        )
                    for key, value in parameters.items():
                        machine.set_parameter(key, value)
                    triggers = payload.get("triggers", [])
                    if not isinstance(triggers, list) or any(
                        not isinstance(item, str) or not item.strip()
                        for item in triggers
                    ):
                        raise ValueError(
                            "preview_state_machine triggers must be a list of non-blank strings"
                        )
                    for trigger in triggers:
                        machine.set_trigger(trigger)
                    frames = payload.get("frames", 1)
                    if (
                        isinstance(frames, bool)
                        or not isinstance(frames, int)
                        or not 1 <= frames <= 10_000
                    ):
                        raise ValueError(
                            "preview_state_machine frames must be an integer between 1 and 10000"
                        )
                    step = payload.get("step", 1.0 / 60.0)
                    if (
                        isinstance(step, bool)
                        or not isinstance(step, (int, float))
                        or not math.isfinite(step)
                        or step <= 0.0
                    ):
                        raise ValueError(
                            "preview_state_machine step must be a positive finite number"
                        )
                    record = payload.get("record", True)
                    if not isinstance(record, bool):
                        raise TypeError(
                            "preview_state_machine record must be a boolean"
                        )
                    pose: dict = {}
                    for _ in range(frames):
                        pose = machine.advance(float(step))
                    if record:
                        updated = self._apply_history(
                            scene, lambda: apply_pose(scene, pose)
                        )
                    else:
                        updated = apply_pose(scene, pose)
                        self.last_diff = None
                    self.last_state_machine_preview = {
                        "name": name,
                        "frames": frames,
                        "step": round(float(step), 6),
                        "current": machine.current,
                        "parameters": dict(
                            sorted(machine.parameters.items())
                        ),
                        "events": list(machine.events),
                        "updated": list(updated),
                        "record": record,
                        "report": machine.report(),
                    }
                elif action == "save_material":
                    if self.material_library is None:
                        raise ValueError("no material library is configured")
                    registry = self._registry_locked()
                    if registry is None:
                        raise ValueError("save_material needs an AssetRegistry")
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "material name must be a non-blank string"
                        )
                    data = dict(payload)
                    data.pop("action", None)
                    data["name"] = name
                    material = material_from_document(data, registry)
                    entry = self.material_library.save(name, material)
                    registry.register(
                        self.material_library.asset_id(name),
                        material,
                        kind="material",
                        source=entry.path,
                        replace=True,
                    )
                elif action == "assign_material":
                    node_id = payload.get("id") or self.selected_id
                    if node_id is None:
                        raise ValueError(
                            "select a node before assigning a material"
                        )
                    node = find_node(scene, node_id)
                    name = payload.get("name")

                    def apply_material() -> None:
                        if name in (None, ""):
                            node.material = None
                            return
                        if self.material_library is None:
                            raise ValueError(
                                "no material library is configured"
                            )
                        registry = self._registry_locked()
                        if registry is None:
                            raise ValueError(
                                "assign_material needs an AssetRegistry"
                            )
                        record = registry.require(
                            self.material_library.asset_id(name)
                        )
                        if record.kind != "material":
                            raise ValueError(
                                f"asset {record.id!r} is not a material"
                            )
                        node.material = record.payload

                    self._apply_history(scene, apply_material)
                    self.selected_id = node.id
                elif action == "delete_material":
                    if self.material_library is None:
                        raise ValueError("no material library is configured")
                    name = payload.get("name")
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError(
                            "material name must be a non-blank string"
                        )
                    asset_id = self.material_library.asset_id(name)
                    registry = self._registry_locked()
                    used_by: list[str] = []
                    if registry is not None:
                        record = registry.get(asset_id)
                        if record is not None:
                            used_by = [
                                node.id
                                for node in scene.traverse()
                                if node.material is record.payload
                            ]
                    if used_by:
                        raise ValueError(
                            f"material {name!r} is used by nodes: "
                            + ", ".join(used_by)
                        )
                    self.material_library.delete(name)
                    if registry is not None:
                        try:
                            registry.remove(asset_id)
                        # hygiene: allow registry may already be absent
                        except KeyError:
                            pass
                elif action == "restore_material":
                    if self.material_library is None:
                        raise ValueError("no material library is configured")
                    entry = self.material_library.restore(payload.get("trash"))
                    registry = self._registry_locked()
                    if registry is not None:
                        material = self.material_library.load(entry.name)
                        registry.register(
                            self.material_library.asset_id(entry.name),
                            material,
                            kind="material",
                            source=entry.path,
                            replace=True,
                        )
                elif action == "set_component":
                    node = find_node(scene, payload.get("id"))
                    self._ensure_unlocked_locked([node])
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
                    self._ensure_unlocked_locked([node])
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
                    self._ensure_subtree_unlocked_locked([node])
                    parent = self._apply_history(scene, lambda: delete_node(scene, node))
                    self.selected_id = None if parent is scene.root else parent.id
                elif action == "duplicate_node":
                    node = find_node(scene, payload.get("id"))
                    clone = self._apply_history(
                        scene, lambda: duplicate_node(scene, node, payload.get("name"))
                    )
                    self.selected_id = clone.id
                elif action == "copy_selection":
                    if not self.selected_ids:
                        raise ValueError(
                            "select at least one node before copying"
                        )
                    nodes = [
                        find_node(scene, node_id)
                        for node_id in self.selected_ids
                    ]
                    clipboard, _ = save_prefab_nodes(
                        nodes, "clipboard", {}
                    )
                    self.clipboard = clipboard
                elif action == "paste_nodes":
                    if self.clipboard is None:
                        raise ValueError(
                            "clipboard is empty; copy a selection first"
                        )
                    if "parent" in payload:
                        parent = self._parent_locked(
                            scene, payload.get("parent")
                        )
                    elif len(self.selected_ids) == 1:
                        parent = find_node(scene, self.selected_ids[0])
                    else:
                        parent = None
                    clipboard = self.clipboard
                    roots = self._apply_history(
                        scene,
                        lambda: clipboard.instantiate(scene, parent=parent),
                    )
                    list(scene.traverse())
                    self._set_selected_ids([root.id for root in roots])
                elif action == "reparent_node":
                    node = find_node(scene, payload.get("id"))
                    self._ensure_unlocked_locked([node])
                    parent = self._parent_locked(scene, payload.get("parent"))
                    self._apply_history(scene, lambda: reparent_node(scene, node, parent))
                    self.selected_id = node.id
                elif action == "save_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    name = payload.get("name") or "scene"
                    self.scene_library.save(name, scene)
                    self.saved_scene = name
                    self.scene_dirty = False
                elif action == "load_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    name = payload.get("name")
                    self.scene_library.load_into(name, scene)
                    self.history.clear()
                    self.selected_id = None
                    self.last_diff = None
                    self.saved_scene = name
                    self.scene_dirty = False
                elif action == "revert_scene":
                    name = self.saved_scene or self.startup_scene
                    if name is None:
                        raise ValueError(
                            "no saved scene to revert to; save the scene first"
                        )
                    if self.scene_library is None:
                        raise WebProblem(
                            400,
                            "revert needs a scene library",
                            "start with --project or pass --scene-dir <dir>",
                        )
                    try:
                        self.scene_library.load_into(name, scene)
                    except (KeyError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            f"could not revert to scene {name!r}: {exc}",
                            "save the scene again or choose an existing startup scene",
                        ) from exc
                    self.history.clear()
                    self.selected_id = None
                    self.last_diff = None
                    self.saved_scene = name
                    self.scene_dirty = False
                    self.last_revert = {
                        "name": name,
                        "node_count": len(list(scene.traverse())),
                        "cleared_history": True,
                    }
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
                    old = payload.get("name")
                    old_saved = self.saved_scene
                    entry = self.scene_library.rename(
                        old, payload.get("new_name")
                    )
                    if self.saved_scene == old:
                        self.saved_scene = entry.name
                    if (
                        self.startup_scene == old
                        and self.project_dir is not None
                    ):
                        try:
                            context = load_project(self.project_dir)
                            manifest = set_project_startup_scene(
                                context, entry.name
                            )
                        except (OSError, TypeError, ValueError):
                            self.saved_scene = old_saved
                            try:
                                self.scene_library.rename(
                                    entry.name, old
                                )
                            # hygiene: allow best-effort rollback; the original error is re-raised
                            except (KeyError, OSError, TypeError, ValueError):
                                pass
                            raise
                        self.startup_scene = manifest.startup_scene
                elif action == "duplicate_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.duplicate(
                        payload.get("name"), payload.get("new_name")
                    )
                elif action == "delete_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    name = payload.get("name")
                    old_startup = self.startup_scene
                    if old_startup == name and self.project_dir is not None:
                        context = load_project(self.project_dir)
                        manifest = set_project_startup_scene(context, None)
                        self.startup_scene = manifest.startup_scene
                    try:
                        self.scene_library.delete(name)
                    except Exception:
                        if (
                            old_startup == name
                            and self.project_dir is not None
                        ):
                            try:
                                context = load_project(self.project_dir)
                                manifest = set_project_startup_scene(
                                    context, old_startup
                                )
                                self.startup_scene = manifest.startup_scene
                            # hygiene: allow best-effort rollback; the original error is re-raised
                            except (OSError, TypeError, ValueError):
                                pass
                        raise
                    if self.saved_scene == name:
                        self.saved_scene = None
                        self.scene_dirty = True
                elif action == "restore_scene":
                    if self.scene_library is None:
                        raise ValueError("no scene library is configured")
                    self.scene_library.restore(payload.get("trash"))
                elif action == "edit_prefab":
                    scene = self._edit_prefab_locked(payload.get("name"))
                elif action == "save_prefab_edit":
                    self._save_prefab_edit_locked(scene)
                elif action == "close_prefab_edit":
                    save = payload.get("save", False)
                    if not isinstance(save, bool):
                        raise TypeError("close_prefab_edit save must be a boolean")
                    scene = self._close_prefab_edit_locked(scene, save)
                elif action == "refresh_prefab_instances":
                    name = payload.get("name")
                    keep_overrides = payload.get("keep_overrides", False)
                    if not isinstance(keep_overrides, bool):
                        raise TypeError(
                            "refresh_prefab_instances keep_overrides must be a boolean"
                        )
                    self._ensure_prefab_locked(name)
                    result = self._apply_history(
                        scene,
                        lambda: refresh_prefab_instances(
                            scene,
                            self.prefabs,
                            name,
                            self._registry_locked(),
                            keep_overrides=keep_overrides,
                            is_locked=self._node_locked_locked,
                        ),
                    )
                    self.last_prefab_refresh = result
                elif action == "save_prefab":
                    ids = payload.get("ids")
                    if ids is not None:
                        if not isinstance(ids, list) or not ids:
                            raise ValueError(
                                "save_prefab ids must be a non-empty list"
                            )
                        if any(
                            not isinstance(item, str) or not item.strip()
                            for item in ids
                        ):
                            raise ValueError(
                                "save_prefab ids must be non-blank strings"
                            )
                        nodes: list[Node] = []
                        seen: set[str] = set()
                        for node_id in ids:
                            node = find_node(scene, node_id)
                            if node.id not in seen:
                                seen.add(node.id)
                                nodes.append(node)
                        name = payload.get("name") or nodes[0].id or nodes[0].name
                        previous = (
                            self.prefabs.get(name)
                            if isinstance(name, str)
                            else None
                        )
                        prefab, roots = save_prefab_nodes(
                            nodes, name, self.prefabs
                        )
                        self._persist_prefab_locked(name, prefab, previous)
                        self._set_selected_ids([root.id for root in roots])
                    else:
                        node_id = payload.get("id") or self.selected_id
                        if node_id is None:
                            raise ValueError(
                                "select a node before saving a prefab"
                            )
                        node = find_node(scene, node_id)
                        name = payload.get("name") or node.id or node.name
                        previous = (
                            self.prefabs.get(name)
                            if isinstance(name, str)
                            else None
                        )
                        prefab = save_prefab(scene, node, name, self.prefabs)
                        self._persist_prefab_locked(name, prefab, previous)
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
                            scene,
                            self.prefabs,
                            name,
                            parent,
                            payload.get("instance"),
                            self._registry_locked(),
                        ),
                    )
                    if roots:
                        self.selected_id = roots[0].id
                elif action == "revert_prefab":
                    node = find_node(scene, payload.get("id") or self.selected_id)
                    self._ensure_subtree_unlocked_locked([node])
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
                        lambda: revert_prefab_instance(
                            scene, node, self.prefabs, self._registry_locked()
                        ),
                    )
                    if root:
                        self.selected_id = root[0].id
                elif action == "apply_prefab":
                    node = find_node(scene, payload.get("id") or self.selected_id)
                    self._ensure_subtree_unlocked_locked([node])
                    link = node.prefab_link
                    if link is None:
                        raise ValueError("node is not a prefab instance")
                    previous = self.prefabs.get(link.name)
                    prefab = apply_prefab_instance(
                        scene, node, self.prefabs, self._registry_locked()
                    )
                    if self.prefab_library is not None:
                        try:
                            self.prefab_library.save(link.name, prefab)
                        except Exception:
                            if previous is None:
                                self.prefabs.pop(link.name, None)
                            else:
                                self.prefabs[link.name] = previous
                            raise
                    seed_prefab_instance_baselines(
                        scene, node, self._registry_locked()
                    )
                    self.selected_id = node.id
                elif action == "revert_prefab_override":
                    node_id = payload.get("id") or self.selected_id
                    if node_id is None:
                        raise ValueError("select a node before reverting an override")
                    node = find_node(scene, node_id)
                    self._ensure_unlocked_locked([node])
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
                    self._ensure_unlocked_locked([node])
                    baselines = {
                        item.id: copy.deepcopy(item.prefab_base)
                        for item in scene.traverse()
                        if item.prefab_base is not None
                    }
                    try:
                        updated = apply_prefab_override(
                            scene,
                            node_id,
                            payload.get("field"),
                            self.prefabs,
                            self._registry_locked(),
                        )
                        if self.prefab_library is not None:
                            self.prefab_library.save(updated.name, updated)
                    except Exception:
                        for item in scene.traverse():
                            if item.id in baselines:
                                item.prefab_base = copy.deepcopy(
                                    baselines[item.id]
                                )
                        raise
                    self.prefabs[updated.name] = updated
                    self.selected_id = node.id
                elif action == "validate_scene":
                    self.last_validation = validate_scene(
                        scene, self.prefabs, self._registry_locked()
                    )
                elif action == "set_startup_scene":
                    if self.project_dir is None:
                        raise WebProblem(
                            400,
                            "startup scene needs a project directory",
                            "start the console with python -m keystone --project <dir> --serve",
                        )
                    name = payload.get("name")
                    if name is not None and (
                        not isinstance(name, str) or not name.strip()
                    ):
                        raise ValueError(
                            "startup scene name must be a non-blank string or null"
                        )
                    if name is not None:
                        if self.scene_library is None:
                            raise WebProblem(
                                400,
                                "startup scene needs a scene library",
                                "start with --project or pass --scene-dir <dir>",
                            )
                        try:
                            path = self.scene_library.path_for(name)
                        except ValueError as exc:
                            raise WebProblem(
                                400,
                                str(exc),
                                "use letters, digits, '.', '_' and '-' only",
                            ) from exc
                        if not path.is_file():
                            raise WebProblem(
                                400,
                                f"scene {name!r} is not saved",
                                "save the scene before setting it as startup",
                            )
                    try:
                        context = load_project(self.project_dir)
                    except (OSError, TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            f"could not load the project manifest: {exc}",
                            "check keystone.json and restore a valid manifest",
                        ) from exc
                    manifest = set_project_startup_scene(context, name)
                    self.startup_scene = manifest.startup_scene
                elif action == "import_asset":
                    if self.project_dir is None:
                        raise WebProblem(
                            400,
                            "asset import needs a project directory",
                            "start the console with python -m keystone --project <dir> --serve",
                        )
                    registry = self._registry_locked()
                    if registry is None:
                        raise WebProblem(
                            400,
                            "asset import needs an AssetRegistry",
                            "expose self.assets = AssetRegistry() in the game module",
                        )
                    value = payload.get("path")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            "import path must be a non-blank project-relative string"
                        )
                    try:
                        context = load_project(self.project_dir)
                    except (OSError, TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            f"could not load the project manifest: {exc}",
                            "check keystone.json and restore a valid manifest",
                        ) from exc
                    try:
                        self.last_import = import_project_asset(
                            context,
                            registry,
                            value,
                            self.component_types,
                        )
                    except FileNotFoundError as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "choose a file that exists inside the project directory",
                        ) from exc
                    if not self.last_import["duplicate"]:
                        self.project_assets = (
                            *self.project_assets,
                            str(self.last_import["path"]),
                        )
                elif action == "import_gltf":
                    if self.project_dir is None:
                        raise WebProblem(
                            400,
                            "glTF import needs a project directory",
                            "start the console with python -m keystone --project <dir> --serve",
                        )
                    registry = self._registry_locked()
                    if registry is None:
                        raise WebProblem(
                            400,
                            "glTF import needs an AssetRegistry",
                            "expose self.assets = AssetRegistry() in the game module",
                        )
                    if self.prefab_library is None:
                        raise WebProblem(
                            400,
                            "glTF import needs a prefab library",
                            "start with --project or pass --prefab-dir <dir>",
                        )
                    value = payload.get("path")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            "glTF path must be a non-blank project-relative string"
                        )
                    name = payload.get("name")
                    if name is not None and (
                        not isinstance(name, str) or not name.strip()
                    ):
                        raise ValueError(
                            "glTF prefab name must be a non-blank string or null"
                        )
                    try:
                        context = load_project(self.project_dir)
                    except (OSError, TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            f"could not load the project manifest: {exc}",
                            "check keystone.json and restore a valid manifest",
                        ) from exc
                    try:
                        report = import_project_gltf(
                            context,
                            registry,
                            self.prefab_library,
                            value,
                            name,
                        )
                    except FileNotFoundError as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "choose a file that exists inside the project directory",
                        ) from exc
                    self.last_gltf_import = report
                    self.prefabs.pop(str(report["prefab"]), None)
                    if not report["duplicate"]:
                        self.project_assets = (
                            *self.project_assets,
                            str(report["path"]),
                        )
                elif action == "reload_assets":
                    registry = self._registry_locked()
                    if registry is None:
                        raise WebProblem(
                            400,
                            "asset reload needs an AssetRegistry",
                            "expose self.assets = AssetRegistry() in the game module",
                        )
                    self.last_asset_reload = reload_scene_assets(
                        scene,
                        registry,
                        self.history,
                        self.prefabs,
                        self.clipboard,
                    )
                elif action == "forget_asset":
                    if self.project_dir is None:
                        raise WebProblem(
                            400,
                            "asset removal needs a project directory",
                            "start the console with python -m keystone --project <dir> --serve",
                        )
                    registry = self._registry_locked()
                    if registry is None:
                        raise WebProblem(
                            400,
                            "asset removal needs an AssetRegistry",
                            "expose self.assets = AssetRegistry() in the game module",
                        )
                    value = payload.get("path")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            "forget path must be a non-blank project-relative string"
                        )
                    try:
                        identifier = project_asset_id(value)
                    except (TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "use a project-relative asset path",
                        ) from exc
                    usage = self._format_asset_usage(
                        self._asset_usage_report_locked(
                            scene, registry, identifier
                        )
                    )
                    if usage:
                        raise WebProblem(
                            400,
                            "asset is still used by: " + usage,
                            "remove or reassign those references before forgetting the asset",
                        )
                    try:
                        context = load_project(self.project_dir)
                    except (OSError, TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            f"could not load the project manifest: {exc}",
                            "check keystone.json and restore a valid manifest",
                        ) from exc
                    record = registry.get(identifier)
                    self.last_forgotten_asset = forget_project_asset(
                        context, registry, value
                    )
                    self.last_forgotten_asset["history_cleared"] = (
                        self.history.clear_payloads({id(record.payload)})
                        if record is not None
                        else 0
                    )
                    self.last_forgotten_asset["clipboard_cleared"] = (
                        clear_clipboard_payloads(
                            self.clipboard, {id(record.payload)}
                        )
                        if record is not None
                        else 0
                    )
                    updated = load_project(self.project_dir)
                    self.project_assets = updated.manifest.assets
                    self.startup_scene = updated.manifest.startup_scene
                elif action == "asset_usages":
                    registry = self._registry_locked()
                    if registry is None:
                        raise WebProblem(
                            400,
                            "asset usages need an AssetRegistry",
                            "expose self.assets = AssetRegistry() in the game module",
                        )
                    asset = payload.get("asset")
                    path = payload.get("path")
                    if (asset is None) == (path is None):
                        raise ValueError(
                            "asset_usages needs exactly one of asset or path"
                        )
                    if asset is not None:
                        if not isinstance(asset, str) or not asset.strip():
                            raise ValueError(
                                "asset_usages asset must be a non-blank string"
                            )
                        asset_id = asset
                    else:
                        if self.project_dir is None:
                            raise WebProblem(
                                400,
                                "asset path lookup needs a project directory",
                                "start the console with python -m keystone --project <dir> --serve",
                            )
                        if not isinstance(path, str) or not path.strip():
                            raise ValueError(
                                "asset_usages path must be a non-blank project-relative string"
                            )
                        try:
                            asset_id = project_asset_id(path)
                        except (TypeError, ValueError) as exc:
                            raise WebProblem(
                                400,
                                str(exc),
                                "use a project-relative asset path",
                            ) from exc
                    self.last_asset_usages = self._asset_usage_report_locked(
                        scene, registry, asset_id
                    )
                elif action == "build_project":
                    if self.project_dir is None:
                        raise WebProblem(
                            400,
                            "build needs a project directory",
                            "start the console with python -m keystone --project <dir> --serve",
                        )
                    target = payload.get("target", "build")
                    if not isinstance(target, str) or not target.strip():
                        raise ValueError(
                            "build target must be a non-blank project-relative string"
                        )
                    force = payload.get("force", False)
                    if not isinstance(force, bool):
                        raise TypeError("build force must be a boolean")
                    try:
                        context = load_project(self.project_dir)
                        destination = resolve_project_target(context, target)
                    except (OSError, TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "use a project-relative build target such as 'build'",
                        ) from exc
                    from keystone.export import export_project

                    try:
                        manifest = export_project(
                            context.directory, destination, force=force
                        )
                    except FileExistsError as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "pass force=true or choose an empty target",
                        ) from exc
                    except (OSError, TypeError, ValueError) as exc:
                        raise WebProblem(
                            400,
                            str(exc),
                            "fix project validation errors or choose another target",
                        ) from exc
                    relative_target = destination.relative_to(
                        context.directory.resolve()
                    ).as_posix()
                    self.last_build = {
                        "schema": manifest["schema"],
                        "target": relative_target,
                        "manifest": f"{relative_target}/BUILD.json",
                        "summary": manifest["summary"],
                    }
                elif action == "undo":
                    steps = payload.get("steps", 1)
                    if (
                        isinstance(steps, bool)
                        or not isinstance(steps, int)
                        or not 1 <= steps <= 100
                    ):
                        raise ValueError(
                            "undo steps must be an integer between 1 and 100"
                        )
                    self.history.undo(scene, steps)
                    self.last_diff = None
                elif action == "redo":
                    steps = payload.get("steps", 1)
                    if (
                        isinstance(steps, bool)
                        or not isinstance(steps, int)
                        or not 1 <= steps <= 100
                    ):
                        raise ValueError(
                            "redo steps must be an integer between 1 and 100"
                        )
                    self.history.redo(scene, steps)
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
            if (
                action not in SCENE_CLEAN_ACTIONS
                and action not in SCENE_NEUTRAL_ACTIONS
            ):
                self.scene_dirty = True
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
    animation_dir: str | Path | None = None,
    material_dir: str | Path | None = None,
    initial_scene: str | None = None,
    project_dir: str | Path | None = None,
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
            animation_dir=animation_dir,
            material_dir=material_dir,
            initial_scene=initial_scene,
            project_dir=project_dir,
        ),
    )


def serve(
    game: GameModule,
    host: str = "127.0.0.1",
    port: int = 8000,
    prefab_dir: str | Path | None = None,
    scene_dir: str | Path | None = None,
    animation_dir: str | Path | None = None,
    material_dir: str | Path | None = None,
    initial_scene: str | None = None,
    project_dir: str | Path | None = None,
) -> int:
    """Run the local console until interrupted."""
    try:
        server = create_server(
            game,
            host=host,
            port=port,
            prefab_dir=prefab_dir,
            scene_dir=scene_dir,
            animation_dir=animation_dir,
            material_dir=material_dir,
            initial_scene=initial_scene,
            project_dir=project_dir,
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
