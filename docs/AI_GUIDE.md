# Keystone AI Workflow Guide

Keystone is designed to be driven and checked by an AI client without a desktop or a GPU for logic tests.

## 1. Discover the game

```bash
python -m keystone --describe --game package.module:Factory
```

The JSON response contains:

- `game`: name;
- `actions`: the game's action schema;
- `snapshot`: the current state shape;
- `capabilities`: `simulate`, `render`, `human_ui`, `game_ui`, `web` and the versioned `report_schema`/`scene_schema`.

`capabilities.input_bind_hook` is `true` when the game implements
`bind_input(mapping)`, which is how a game binds its own live controls:

```python
class MyGame:
    name = "my-game"

    def bind_input(self, mapping):          # optional sixth capability
        mapping.bind("fire", "mouse_left")  # merged over the engine defaults
        mapping.bind("reload", "r")
        mapping.bind("slot1", "1")
```

The engine calls the hook once after building its `InputMap`, so the game's
bindings sit on top of the default movement, look, pause and quit keys. The
hook runs once per engine, its defaults survive, and a game without the hook
keeps the defaults unchanged. To catch a misleading contract, compare what the
game advertises with what can actually arrive:

```python
from keystone.input import InputMap

mapping = InputMap()
mapping.bind("fire", "mouse_left")
unreachable = mapping.unbound_buttons(["fire", "sprint", "reload"])
# ["reload"] -> declared in actions() but no binding can produce it
```

`--version` prints the release and is a standalone query; combining it with a
run mode is rejected with exit 2, like every other standalone flag.

## 1b. Create or open a project

```bash
python -m keystone --new my-game
python -m keystone --project my-game --describe
python -m keystone --project my-game --validate-project
python -m keystone --project my-game --simulate --frames 120
```

`--new` creates `keystone.json`, a five-operation game module, a README, a `.gitignore`, `prefabs/` and `scenes/` library directories, plus starter `scenes/main.kscene` and `prefabs/cube.kprefab` content. The generated game exposes `self.assets = AssetRegistry()` and `self.component_types = {}` for editor authoring. `--project` accepts the project directory or the manifest file, adds the project directory to the import path, validates the game contract and uses the manifest's `game` spec unless `--game` overrides it. `--scene NAME` opens a saved scene for `--serve`, `--simulate`, `--headless`, `--replay`, `--playtest`, `--verify-determinism` or a windowed run when `--project` or `--scene-dir` supplies the library; `--describe` is the only run it cannot accompany. Manifest schema 2 adds an optional `startup_scene`; `--project` opens it when `--scene` is omitted, while `--describe`, `--validate-project` and `--export` do not load scenes. `--project DIR --validate-project` performs a non-destructive check of game assets, manifest/glTF assets, scene files and prefab files, prints a schema-1 JSON report and exits 1 on any error. Relative `.obj`, `.png`, `.kprefab`, `.gltf` and `.glb` paths in the manifest `assets` list are imported when the game exposes `self.assets = AssetRegistry()`: regular assets use `project:<relative-path>`, glTF/GLB scenes become `<project>/prefabs/<stem>.kprefab` with `gltf.<stem>.*` mesh/material/texture ids, and prefabs import after their dependencies regardless of manifest order; bad paths fail with `Why:`/`Fix:` text. `--describe` includes a `project` object with the resolved directory and manifest when `--project` is used.

## 1c. Package a project

```bash
python -m keystone --project my-game --export build/my-game
```

`--export` validates the game, assets, scenes and prefabs, then writes a runnable bundle: the runtime project files, a vendored `keystone` package under `vendor/keystone`, `run.py`, `requirements.txt`, `EXPORT.md` and a schema-1 `BUILD.json` with every file's size and SHA-256. The bundle refuses a non-empty destination unless `--force` is passed and runs with `python run.py --simulate --frames 1` or `python run.py`; runtime dependencies still install from `requirements.txt`.

## 2. Simulate without OpenGL

```bash
python -m keystone --simulate --frames 120 --actions actions.json --out run.json
python -m keystone --replay run-log.json --out replay.json
```

Actions are a JSON list of `ActionState` objects. If the list is shorter than `frames`, the last action repeats. Each object may set movement axes, `pressed`, `held`, `pointer` and `mouse_clicked`. The result includes:

- `ok`, `game`, `frames`, `step`;
- actions used, final snapshot and `hash`;
- optional `trace` with one snapshot per frame.

No `Engine`, GLFW window or OpenGL context is created.

## 3. Pin a deterministic hash

```bash
python -m keystone --simulate --frames 120 --actions actions.json \
  --expect-hash 1210b1adef6e3578b2368955eeb9f98c
```

Exit code 0 means the final hash matched; 1 means drift. `--verify-determinism` runs the same scenario twice and can also take `--expect-hash`.

## 4. Bot-playtest a game

```bash
python -m keystone --playtest --policy random --seed 7 --frames 120 \
  --transcript-out run.json --out report.json
python -m keystone --playtest --policy scripted --script solution.json --frames 120
```

`--playtest` runs a seeded bot policy (`random`, `greedy`, `scripted`) headlessly through the same five operations as `--simulate`. The transcript wraps the exact `CommandLog` shape, so its hash pins with `--expect-hash` and replays with `--replay` like any simulation; `diff_transcripts()` reports the first divergent frame between two traced runs. The schema-1 report (`game`, `policy`, `seed`, `outcome`, `final`, `hash`, `coverage`, `fairness`) is the same JSON a thin web adapter emits from `POST /api/simulate` — browser driving stays out. Exit code is 1 when the validator rejects the configuration as `unfair` (spawn-terminal, nondeterministic, no witnessed win, or reference longer than the time limit), with reasons in `report.fairness.reasons`. Games opt into win/lose judgments with `outcome`/`score` snapshot keys; without them the verdict is `unknown`, never a false `fair`.

## 5. Render and analyze

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out frame.png --report frame.json
```

The schema-11 report contains:

- image path, dimensions and PNG/RGBA SHA-256;
- mean RGB/luminance, content pixels/ratio and bbox;
- dominant colors and an 8×8 luminance grid;
- camera parameters;
- every node's scene ID, parent ID, tags, layer, component type names, world position, visibility, triangle count, projected screen center and bounding box;
- per-material color/specular/shininess/checker and optional texture name, dimensions and SHA-256;
- `ui` metadata (`visible`, `paused`, labels and buttons) or `null` for clean captures;
- a stable report hash.

## 6. Compare against a baseline

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out current.png --report current.json \
  --compare-baseline baseline.json --diff-out diff.png
```

The diff reports image/report equality, luminance and content-ratio deltas, bbox changes, added/removed/changed nodes (keyed by scene ID when both reports are schema 4 or newer, otherwise by name), added/removed/moved UI labels and buttons, and PBR material/texture metadata. `--diff-out` additionally writes a visual PNG and reports changed pixels, ratio, bbox, mean delta and max delta. Exit code 0 means the image hash matched; 1 means it changed.

## 7. Capture the human UI

Windowed runs draw the HUD by default. For an AI inspection of what a person sees, add `--ui` to a headless run:

```bash
python -m keystone --headless --frames 1 --size 960x540 --ui \
  --out hud.png --report hud.json
python -m keystone --headless --frames 1 --size 960x540 --ui --start-paused \
  --out paused.png --report paused.json
```

The overlay reports game/status, FPS, frame, elapsed time, resolution, controls and pause state. `P` opens an interactive `Resume` / `Hide HUD` / `Quit` menu; the cursor is released while it is open. `--start-paused` makes the menu the first rendered frame. In the report, `ui.labels` gives text/position/scale/color and `ui.buttons` gives label/action/rect/selected/hovered, so an AI can review the interface structurally. The overlay is presentation-only: `--simulate` and `--verify-determinism` stay GPU-free, and `--no-ui` keeps captures pixel-identical to the pre-overlay behavior.

UI actions can also be driven directly, which is useful for scripted tests:

```python
engine.apply_ui_action("pause")     # open the menu
engine.apply_ui_action("resume")    # close it
engine.apply_ui_action("toggle_ui") # hide/show the HUD
engine.apply_ui_action("quit")      # request window close
```

## 8. Draw a game HUD

A game can implement an optional `draw_ui(canvas, state)` hook. It runs before the engine HUD and uses the same clipped canvas, bitmap font and pause state:

```python
from keystone.ui import Canvas, HudState


def draw_ui(self, canvas: Canvas, state: HudState) -> None:
    canvas.text(24, 96, "GAME HUD", (0.92, 0.94, 0.97, 1.0))
```

`--describe` reports `capabilities.game_ui` as true when the hook exists. The hook is skipped with `--no-ui` and when the person hides the overlay. `--start-paused` is also useful here: the game's HUD renders under the pause menu.

## Web API and browser console

```bash
python -m keystone --serve --port 8899
```

`GET http://127.0.0.1:8899/api` returns the endpoint and schema index, including `endpoints.editor.schema.examples` with one ready-to-send payload for every editor action. The API mirrors the CLI contract:

- `GET /api/health` returns `ok`, `game`, `api` and `scene_schema`;
- `GET /api/describe` returns the same payload as `--describe`, with `capabilities.web`;
- `GET /api/scene` returns scene document schema 2: camera, lights, atmosphere, node identity/tags/layers/components, world matrices, shared meshes and RGBA textures;
- `GET /api/editor` returns hierarchy, selection, the ordered `selected_ids` set plus `selection_count`, a `selection_summary` of shared versus mixed inspector values, local transforms, node mesh/material ids, a `prefab_instances` inventory of linked roots plus a distinct `prefab_instance_count`, a `prefab_overrides` field-diff report plus `prefab_override_count`, a `scene_groups` additive-scene inventory (source camera/environment and container roots included) plus `scene_group_count`, registry assets with kind-specific metadata (mesh counts and bounds, material factors, texture size and 64px preview data URIs, prefab contents; shown in the console when a mesh/material is selected), component field schemas and lifecycle hooks, saved scenes/prefabs, named undo/redo stacks (counts, newest-first labels and limit) and the active library directories;
- `--project .` serves file-backed `<project>/prefabs/*.kprefab` and `<project>/scenes/*.kscene` libraries; `--prefab-dir DIR` and `--scene-dir DIR` override them, `--scene NAME` opens a saved scene at startup, and entries report `source` plus any load `error`; the console save/load/rename/duplicate/delete controls manage both libraries, scene/prefab name fields suggest saved entries with node counts or load errors, and hierarchy/asset filter inputs narrow large scenes and registries;
- `POST /api/editor` accepts `select`, `select_many`, `set_layer_visible`, `set_nodes_locked`, `transform`, `transform_selection`, `toggle_selection_visible`, `delete_selection`, `set_node`, `set_selection_properties`, `set_selection_transform`, `set_scene`, `batch`, `assign_asset`, `assign_asset_selection`, `set_component`, `remove_component`, `play_start`, `play_step`, `play_pause`, `play_resume`, `play_stop`, `preview_animation`, `preview_blend_space`, `save_animation`, `delete_animation`, `restore_animation`, `set_animation_key`, `remove_animation_key`, `save_state_machine`, `load_state_machine`, `rename_state_machine`, `duplicate_state_machine`, `delete_state_machine`, `restore_state_machine`, `preview_state_machine`, `save_material`, `assign_material`, `delete_material`, `restore_material`, `create_node`, `delete_node`, `duplicate_node`, `copy_selection`, `paste_nodes`, `reparent_node`, `save_prefab`, `edit_prefab`, `save_prefab_edit`, `close_prefab_edit`, `refresh_prefab_instances`, `insert_prefab`, `revert_prefab`, `apply_prefab`, `revert_prefab_override`, `apply_prefab_override`, `rename_prefab`, `duplicate_prefab`, `delete_prefab`, `restore_prefab`, `save_scene`, `load_scene`, `revert_scene`, `add_scene`, `unload_scene`, `save_scene_group`, `diff_scene`, `validate_scene`, `set_startup_scene`, `import_asset`, `import_gltf`, `reload_assets`, `forget_asset`, `asset_usages`, `build_project`, `rename_scene`, `duplicate_scene`, `delete_scene`, `restore_scene`, `undo` and `redo` (each accepts an optional `steps` count from 1 to 100); `select_many` replaces, adds, removes or toggles an ordered selection set; `transform_selection` applies a world position delta plus optional local rotation/scale deltas, or a `pivot` with `group_rotation`/`group_scale` around the selection centroid, to the top-level selected nodes in one undo entry (selected descendants follow their parents); `group_scale` is a positive scalar for uniform scaling or three positive X/Y/Z factors for axis-local centroid scaling; `set_selection_properties` writes name/visible/tags/layer and `set_selection_transform` writes absolute local transforms to every selected node in one undo entry; `selection_summary` reports shared values and mixed fields; `toggle_selection_visible` flips the visibility of the selection; `delete_selection` removes the top-level selection and deduplicates prefab instance groups; deletes move entries to the library `.trash` directory and `restore_*` takes the reported `trash` file name; `save_prefab` captures one `id` subtree, or an ordered `ids` list of top-level roots that share a parent, as a multi-root template (selected descendants are folded into their selected ancestors); inserted prefabs carry an editor-only `prefab_link` (`name`, `instance`) on every root; `edit_prefab` opens an isolated scene containing that prefab, normalizes new edit-node ids before save so they survive template normalization, `save_prefab_edit` captures and writes the template, and `close_prefab_edit` restores the authored scene and its undo history (`save` writes first); `refresh_prefab_instances` replaces top-level authored instances of one prefab with the current template in one undo entry; with `keep_overrides: true` (the console default) it reapplies field values that differ from each node's stored instance baseline, so template-owned changes propagate while authored overrides survive, and reports `refreshed`, `preserved_overrides`, `dropped_overrides`, `skipped_nested`, `skipped_invalid`, `skipped_locked` and `total`; instance groups containing a locked node are skipped; instance baselines persist in scene snapshot schema 6; nested links are persisted in prefab schema 2, rebased under the outer prefix on instantiation, and can be reverted or applied independently; `revert_prefab` replaces the linked instance group with a fresh copy of its prefab (discarding overrides), and `apply_prefab` captures the whole group back into the prefab definition and its file library, rebasing only the applied group after a successful write so nested overrides survive; per-field overrides are reported for name, visibility, tags, layer, transform position/rotation/scale, registry mesh/material ids and whole components, `revert_prefab_override` restores one `field` on a scene node with undo, and `apply_prefab_override` writes one field into a cloned prefab and its file library, restoring instance baselines if that write fails (asset writes are not scene-undoable); `add_scene` loads a saved `.kscene` as a named child group, preserving its source camera/environment metadata and root transform while renaming only colliding node IDs; `unload_scene` removes a group with undo; `save_scene_group` writes the group's children, source camera/environment and container root transform back to its library scene, with optional `name` for save-as (the metadata rename is undoable; the new file remains); `diff_scene` compares the current scene with a saved `.kscene` and reports added/removed/changed node ids plus camera/environment/root changes and per-node prefab-link changes; `set_scene` accepts `camera` and/or `environment` objects (camera position/yaw/pitch/fov/near/far; environment vectors, fog, directional/point lights and render toggles), and the console exposes labeled camera, environment and render-toggle controls plus an advanced JSON fallback; `batch` applies up to 100 mutating actions (including `revert_prefab`) atomically as one undo entry and rolls the scene back on any failure; library rename/delete reject collisions and missing entries; create accepts `name`, `parent`, transform arrays, `tags`, `layer`, `visible` and optional registry asset ids `mesh`/`material`; `assign_asset` reassigns or clears an existing node's mesh/material and rejects missing or wrong-kind ids; component actions use the game's `component_types` name map and JSON `data`; the console renders dataclass fields as typed inputs and falls back to JSON for custom codecs; `preview_animation` accepts an inline `clip` document or a library `name` plus a non-negative `time` and a `record` flag, samples the clip, applies its pose to matching nodes, and exposes `animation_preview` with name/time/updated/track_count/source/record; recording frames add one undo entry, while `record: false` frames drive real-time playback without flooding history; `preview_blend_space` accepts an inline schema-1 `blend_space`, a finite `parameter`, non-negative `time` and `record`, samples the blended pose and exposes `blend_space_preview` with parameter, time, updated nodes, record flag and report; `save_animation`, `delete_animation` and `restore_animation` manage `.kanim` clips in the editor animation library, and the console can sample a clip from the selected node, save it, scrub it, preview it by name, play/pause it, or restore a trashed clip; `save_material` writes `.kmaterial` files and registers `material.<name>` for rendering, `assign_material` applies or clears a node material with undo, `delete_material` moves an unused material to the recoverable trash and unregisters it, `restore_material` restores and re-registers it, and the console edits color, metallic, roughness, emissive, specular, shininess, checker and texture fields; `validate_scene` returns a schema-1 report with errors and warnings for unregistered mesh/material references, dangling prefab links, blank or duplicate names and empty scene groups, and the console shows the counts; play mode snapshots the authored scene, advances `game.update()` with fixed steps, blocks edits, exposes a `paused` flag, accepts `play_pause`/`play_resume`, and restores the authored scene on stop; the console Play button drives a real-time loop, Pause/Resume toggle it, and Step pauses and advances the requested frame count with the actions JSON list; authored components can implement `start(context)`, `update(context)` and `stop(context)` hooks and run through `ComponentRuntime` before each fixed game update, with `LifecycleContext` carrying the scene, node, component, fixed `dt` and frame; play state reports the runtime active/frame/started/hooks summary, and while active the game's `status` and JSON `snapshot` with `status_error`/`snapshot_error` when a hook fails, and stop hooks run before the scene restore;
- `POST /api/simulate` accepts `{"frames": 60, "actions": [...], "step": 0.0167, "trace": false}` and returns the same deterministic result as `--simulate`.
- `import_asset` requires `--project`, accepts a non-blank project-relative `.obj`, `.png` or `.kprefab` path, appends it to `keystone.json` atomically, registers it as `project:<path>` with `replace=True`, and returns an `imported_asset` report (`path`, `asset`, `kind`, `duplicate`, `count`); re-importing a listed path refreshes the registry record without duplicating the manifest entry, traversal/missing files and unsupported formats fail with actionable guidance, and the console exposes a path input, Import asset button and readout (`workspace.project_dir` shows whether import is available).
- `import_gltf` requires `--project` and a prefab library, accepts a project-relative `.gltf`/`.glb` path plus an optional prefab `name`, imports the scene into `<prefabs>/<name>.kprefab`, registers `gltf.<name>.texture.*`, `.material.*` and `.mesh.*` assets, appends the source to `keystone.json`, and returns an `imported_gltf` report (`path`, `prefab`, `assets`, `asset_count`, `duplicate`, `replaced_prefab`, `count`); re-import refreshes the derived prefab/assets, failures restore the manifest, previously registered derived records and removed newly added assets, and the console routes `.gltf`/`.glb` paths through this action automatically.
- `reload_assets` calls `AssetRegistry.refresh()` with meshes/textures ahead of materials and prefabs last, rebinds scene mesh/material payloads and inline material textures plus undo/redo snapshots, cached prefab templates, the clipboard and registry material payloads to changed records, keeps last-good payloads when a file fails or disappears, and returns an `asset_reload` report (`ok`, `checked`, `reloaded`, `unchanged`, `failed`, `missing`, `rebound`, `history_rebound`, `prefab_rebound`, `clipboard_rebound`, `registry_rebound`); the console Reload assets button shows the counts.
- Plain (non-editor) consumers use the core rule directly: `AssetRegistry.reload(scene)` refreshes sources and then rebinds that scene's nodes, registered materials and inline textures, returning `rebound` and `registry_rebound` on the `ReloadReport`. `refresh()` alone still only replaces records, so a live scene keeps stale payloads until either call. The web editor delegates to the same core helpers, so there is one rebinding rule rather than two.
- `forget_asset` requires `--project` and an AssetRegistry, accepts a project-relative `.obj`, `.png` or `.kprefab` path, rejects glTF/GLB and unsupported paths, blocks while scene nodes, material textures, registry dependencies, in-memory/saved prefabs or saved scenes reference the payload, clears forgotten payloads from undo/redo snapshots and the clipboard, then removes the manifest entry atomically and unregisters the record while keeping the source file; the document exposes `project_assets` and a `forgotten_asset` report (`path`, `asset`, `removed`, `history_cleared`, `clipboard_cleared`, `count`), and the console lists project paths with a Forget asset control.
- `asset_usages` accepts exactly one of `asset` (exact id) or `path` (project-relative) and returns `registered`, `kind`, `scene_nodes`, `registry`, `prefabs`, `scenes`, `history_references`, `clipboard_references`, `project_asset`, `references` and `found`; it scans the live scene, registry dependencies/textures, in-memory and saved prefabs, saved scenes, undo/redo snapshots and the clipboard; `history_references` and `clipboard_references` are reported separately and do not raise `references` or block forgetting. The console Find usages button accepts a path or asset id.
- `assign_asset_selection` applies validated `mesh`/`material` ids to every selected node in one undo entry; the console Assign to selection button sends only non-empty fields. Single-node `assign_asset` remains available for per-node replacement or clearing.
- `copy_selection` captures the top-level selected nodes as a detached clipboard prefab; `paste_nodes` instantiates fresh IDs under the selected node (or an explicit `parent`) in one undo entry; the console exposes Copy and Paste buttons.
- `set_layer_visible` accepts a layer name and boolean and updates the session-only `hidden_layers` list; `layers` reports per-layer node counts. Hidden layers remain in the scene document but are filtered from scene-view rendering, picking and pivots, hiding a layer removes its nodes from the current selection, and the console renders layer checkboxes.
- `set_nodes_locked` toggles editor-only locks for an `ids` list or the current selection. Locked nodes and their descendants reject transform/transform_selection/set_selection_transform, delete selection/node, reparent, asset assignment, component edits and prefab revert/apply; deleting, reverting or applying an unlocked ancestor whose subtree contains a locked node is also rejected; nodes report `locked` and the document reports `locked_ids`/`locked_count`. The console exposes Lock/Unlock selection controls.
- The console stores named scene-view camera bookmarks (target, distance, yaw, pitch) per game in `localStorage`; Save view, Go to view and Delete view are client-only and do not change the scene.
- `save_state_machine`, `load_state_machine`, `rename_state_machine`, `duplicate_state_machine`, `delete_state_machine` and `restore_state_machine` manage `.kstate` machine documents in the animation directory; rename/duplicate reject collisions and restore returns 400 when the live name is occupied; `load_state_machine` returns `state_machine_document` (`name`, `machine`) for console JSON editing; `preview_state_machine` applies `parameters` and `triggers`, advances `frames` by `step` (default 1/60s), applies the final pose and returns `state_machine_preview` with the current state, parameters, events, updated nodes, record flag and report; previews record one undo entry unless `record: false`. The console's blend-space panel previews an inline blend space and saves it as a blend state inside the state-machine JSON field: it merges one state by name, keeps other states/transitions/parameters, and adopts the state as `current` only when the existing current state is missing, so loading a saved machine mirrors its blend state back into the panel for editing.
- `set_animation_key` inserts or replaces one selected-node position/rotation/scale key at a non-negative `time` in a library clip (`value` defaults to the node's current transform) and saves the `.kanim`; `remove_animation_key` removes a key within epsilon and drops empty tracks. Both return an `animation_key` report with action, node, channel, time, key count and removed count; the console exposes a channel selector plus Set key/Remove key controls.
- The material panel selects textures from registry texture assets, previews the chosen texture, and preserves unregistered texture ids as missing entries; `save_material` still accepts a texture id or null.
- `build_project` requires `--project`, accepts a project-relative target (default `build`) and `force`, runs the validated export pipeline, and returns a `build` report (`schema`, `target`, `manifest`, `summary`); traversal/absolute targets and validation failures return 400, non-empty targets fail with force guidance, and the console has target/force controls plus a files/bytes readout.
- `set_startup_scene` requires `--project` and a scene library, accepts a saved scene name or null, writes `startup_scene` to `keystone.json` atomically, and returns the updated top-level `startup_scene` document field; the console sets it from the Scene name field or clears it.
- The editor tracks `saved_scene` and `scene_dirty`: selects, play, validation, library-only actions and asset import/reload leave the flag unchanged, scene edits mark it dirty, and save/load clear it. `revert_scene` reloads the saved scene (falling back to `startup_scene`), clears history and selection, and returns a `revert` report (`name`, `node_count`, `cleared_history`); the console shows Saved/Unsaved state and enables Revert only for a dirty saved scene.

All responses carry `Access-Control-Allow-Origin: *` so a local frontend or AI client can call the API directly. The server is loopback-only by default; do not expose it publicly. It does not need OpenGL. The bundled browser console drives the same endpoints and renders the scene document with WebGL2; drag orbits the editor camera, shift-drag pans, the wheel zooms, Reset view returns to the scene camera framing, Focus selected centers the camera on the selected node, the Scene/Game button switches to a game-camera view that follows the live scene camera and suppresses editing, a projection button cycles Perspective/Top/Front/Side orthographic Scene views (O), and Play switches to Game view automatically; clicking a node selects it, while clicking empty space clears selection; meshless nodes draw small pivot crosses in Scene view, tinted green when selected. A selected node gets Move/Rotate/Scale gizmos (console buttons or W/E/R): translate handles follow world axes by default and local axes after X or the Space button, while rotate rings and scale handles always follow the node's local axes; drag for a live world-space preview (children follow), hold Ctrl/Cmd to snap to 0.25 units, 15 degrees or 0.1 scale, and release to send one validated `transform` action and one undo entry; the gizmos are hidden in play mode. Inserted prefabs show their `prefab_link` under the prefab controls, with Revert instance (restore the authored prefab template) and Apply instance (write the current group back to the prefab and its `.kprefab` library) buttons; Edit prefab opens the template in an isolated scene, Save prefab edit writes it, and Save & close or Discard & close returns to the authored scene; the Prefab overrides panel lists each diverging field with Revert (scene undo) and Apply (writes the prefab) buttons; multi-root instances are linked, reverted, applied, deleted and reparented as one group; nested instances keep parent-relative links and are rebased under their outer prefix; the hierarchy marks linked roots with `[prefab:name/instance]`. The hierarchy is a draggable tree; click selects, Ctrl/Cmd-click toggles, dragging a row onto another node reparents it, and dropping on empty space moves it to the scene root; nodes with children have collapse toggles, filtered searches reveal matching rows, and selecting a hidden node expands its ancestors; the selected nodes share a centroid translate/rotate/axis-local-scale gizmo, and Toggle selected/Delete/F act on the whole set. Box select (button or B) draws a marquee over projected node bounds, including hidden mesh nodes and world-position proxies for meshless nodes; AABBs are clipped against the near plane. No modifier replaces, Shift adds and Ctrl/Cmd toggles the hit set. When multiple nodes are selected, the inspector summary reports mixed fields and Apply transform/Apply node properties write the same values to every selected node. Console shortcuts: Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y redo, Delete deletes the selection, F focuses it, Escape clears selection, G toggles the Scene-view ground grid, S toggles persistent snapping (Ctrl/Cmd still snaps temporarily), and arrow/PageUp/PageDown nudge the selection by 0.1 units (Shift for 1.0) when no text field is focused. The console's Snap move/rotate/scale fields set positive increments persisted with the workspace layout; Reset layout restores 0.25 units, 15 degrees and 0.1 scale. The editor stores the Scene camera, view mode, projection, grid and snap in browser storage per game and restores them on reload; Reset layout clears that record. The Undo/Redo buttons apply the console's History steps count, and the history readout lists the newest-first undo and redo labels. That preview is approximate, while `--headless` remains the authoritative pixel render. `/api/scene` uses `self.scene` when the game exposes it (live state); otherwise it calls `build_scene()` for a fresh scene.

## Python helpers

```python
from keystone.agents import AuditTrail, observe, parse_actions, summarize_report
from keystone.analysis import compare_reports
from keystone.input import ActionState, InputMap
from keystone.samples import CubeDemo
from keystone.testing import assert_deterministic, run_script

result = run_script(CubeDemo(), [ActionState(forward=1.0)], frames=60)
assert_deterministic(lambda: CubeDemo(), [ActionState(forward=1.0)], frames=60)

# Bot playtesting: seeded policies, transcript reports, fairness verdicts.
from keystone.playtest import RandomPolicy, make_report, run_bot, validate_fairness

transcript = run_bot(CubeDemo, RandomPolicy(), frames=60, seed=7, trace=True)
print(make_report(transcript, validate_fairness(CubeDemo, frames=60, seeds=(7,)))["fairness"])

# AI-first workflow: validate LLM JSON, fuse discovery + simulation, audit it.
actions = parse_actions([{"forward": 1.0}])
observation = observe(CubeDemo(), frames=60, actions=actions)
trail = AuditTrail()
trail.record("observe", {"hash": observation["hash"]})

# Persist rebindable input with contexts for human + AI clients.
bindings = InputMap()
bindings.bind("dash", "left_shift")
bindings.bind("confirm", "enter", context="menu")
bindings.save_bindings("bindings.json")

# Prefabs: capture, persist through the asset registry, then instantiate copies.
from keystone import Prefab
from keystone.scene import Scene

demo = CubeDemo()
source = demo.build_scene().find_by_id("cube-0")
prefab = Prefab.from_node(source, name="cube")
prefab.save("cube.kprefab", demo.assets)
loaded = Prefab.load("cube.kprefab", demo.assets)
scene = Scene()
loaded.instantiate(scene, instance="a")
demo.assets.register_file("prefab.cube", "cube.kprefab")
print(loaded.describe())

# Custom components need an explicit type map on load; mesh/material ids must
# already be registered. `register_file(..., component_types={...})` does both.
# Prefabs are the fourth asset kind: their digests and dependencies update on refresh.

# Scene snapshots keep typed components; pass component_types when present.
from keystone.scene_snapshot import scene_from_dict, scene_to_dict

snapshot = scene_to_dict(demo.scene, demo.assets)
restored_scene = scene_from_dict(snapshot, demo.assets, {})
print(restored_scene.find_by_id("cube-0").name)

# Deterministic audio: synth, mix, audit, export.
from keystone.audio import Mixer, audio_report, sine, write_wav

mixer = Mixer()
mixer.play(sine(440.0, 0.2), bus="sfx")
clip = mixer.render()
write_wav("mix.wav", clip)
print(audio_report(clip, voices=mixer.voice_count(), buses=mixer.buses))

# Static batching + inspector for humans and AI.
from keystone.batch import merge_batches, plan_batches

print(plan_batches(CubeDemo().build_scene()))
print(merge_batches(CubeDemo().build_scene())["saved_calls"])

# Deterministic animation: author clips, drive nodes, audit state.
from keystone.animation import AnimationClip, AnimationController, Track, apply_pose
from keystone.math3d import Vec3

clip = AnimationClip(
    name="bob",
    position_tracks=(("cube-0", Track(times=(0.0, 1.0), values=(Vec3(0, 0, 0), Vec3(0, 2, 0)))),),
)
controller = AnimationController()
controller.add(clip)
controller.play("bob")
apply_pose(CubeDemo().build_scene(), controller.advance(0.016))

# Timed events, crossfade blending and file-based replay for audit trails.
from keystone.animation import blend_poses

eventful = AnimationClip(name="fx", events=((0.5, "hit"),))
print(eventful.events_in_range(0.0, 0.75))
controller.crossfade("bob", 0.25)
pose, fired = controller.advance_with_events(0.016)

# Parameter-driven state machine with transitions, triggers and crossfades.
from keystone import (
    AnimationState,
    AnimationStateMachine,
    AnimationTransition,
)

idle = AnimationState("idle", clip)
run = AnimationState("run", eventful, speed=1.5)
machine = AnimationStateMachine(
    [idle, run],
    [
        AnimationTransition(
            source="idle",
            target="run",
            parameter="speed",
            operator="greater",
            value=0.5,
            duration=0.2,
        )
    ],
    {"speed": 0.0},
)
machine.set_parameter("speed", 1.0)
apply_pose(CubeDemo().build_scene(), machine.advance(0.016))
print(machine.report())

# One-dimensional blend space: ordered clips blended by one scalar.
from keystone import BlendSample, BlendSpace1D

space = BlendSpace1D(
    (BlendSample(clip, 0.0), BlendSample(eventful, 1.0))
)
print(space.sample(0.5, 0.0))
print(space.report())

from keystone.input import ActionState
from keystone.replay import CommandLog, run_log

log = CommandLog(seed=11)
log.record(ActionState(forward=1.0))
print(run_log(CubeDemo, log)["hash"])

# Deterministic particles: seeded emitters, HUD/inspector/AI reports.
from keystone.particles import Emitter, ParticleSystem, particles_report
from keystone.physics import AABB
from keystone.math3d import Vec3

fx = ParticleSystem()
fx.add(Emitter(name="sparks", rate=60.0, seed=5))
fx.burst("sparks", 8)
fx.step(0.016)
floor = AABB(Vec3(0, -0.05, 0), Vec3(10, 0.05, 10))
fx.step(0.016, [floor], restitution=0.45, friction=0.1)
print(particles_report(fx))
```

## AIKit

The project gate runs the GPU-free mechanics check:

```bash
python aikit.py check keystone --strict
```

`mechanics.test` is `python -m keystone --simulate --frames 1`. Rendered reports are still available through `--headless` and require an OpenGL 3.3 driver.
