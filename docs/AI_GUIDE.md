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

## 1b. Create or open a project

```bash
python -m keystone --new my-game
python -m keystone --project my-game --describe
python -m keystone --project my-game --simulate --frames 120
```

`--new` creates `keystone.json`, a five-operation game module, a README, a `.gitignore`, `prefabs/` and `scenes/` library directories, plus starter `scenes/main.kscene` and `prefabs/cube.kprefab` content. The generated game exposes `self.assets = AssetRegistry()` and `self.component_types = {}` for editor authoring. `--project` accepts the project directory or the manifest file, adds the project directory to the import path, validates the game contract and uses the manifest's `game` spec unless `--game` overrides it. `--scene NAME` opens a saved scene for `--serve`, `--simulate`, `--headless`, `--replay`, `--playtest`, `--verify-determinism` or a windowed run when `--project` or `--scene-dir` supplies the library; `--describe` is the only run it cannot accompany. Relative `.obj`, `.png`, `.kprefab`, `.gltf` and `.glb` paths in the manifest `assets` list are imported when the game exposes `self.assets = AssetRegistry()`: regular assets use `project:<relative-path>`, glTF/GLB scenes become `<project>/prefabs/<stem>.kprefab` with `gltf.<stem>.*` mesh/material/texture ids, and prefabs import after their dependencies regardless of manifest order; bad paths fail with `Why:`/`Fix:` text. `--describe` includes a `project` object with the resolved directory and manifest when `--project` is used.

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

`GET http://127.0.0.1:8899/api` returns the endpoint and schema index. The API mirrors the CLI contract:

- `GET /api/health` returns `ok`, `game`, `api` and `scene_schema`;
- `GET /api/describe` returns the same payload as `--describe`, with `capabilities.web`;
- `GET /api/scene` returns scene document schema 2: camera, lights, atmosphere, node identity/tags/layers/components, world matrices, shared meshes and RGBA textures;
- `GET /api/editor` returns hierarchy, selection, local transforms, node mesh/material ids, registry assets with kind-specific metadata (mesh counts and bounds, material factors, texture size, prefab contents; shown in the console when a mesh/material is selected), component field schemas, saved scenes/prefabs, undo/redo depths and the active library directories;
- `--project .` serves file-backed `<project>/prefabs/*.kprefab` and `<project>/scenes/*.kscene` libraries; `--prefab-dir DIR` and `--scene-dir DIR` override them, `--scene NAME` opens a saved scene at startup, and entries report `source` plus any load `error`; the console save/load/rename/delete controls manage both libraries, and scene/prefab name fields suggest saved entries with node counts or load errors;
- `POST /api/editor` accepts `select`, `transform`, `set_node`, `batch`, `assign_asset`, `set_component`, `remove_component`, `play_start`, `play_step`, `play_stop`, `create_node`, `delete_node`, `duplicate_node`, `reparent_node`, `save_prefab`, `insert_prefab`, `rename_prefab`, `delete_prefab`, `save_scene`, `load_scene`, `rename_scene`, `delete_scene`, `undo` and `redo`; `batch` applies up to 100 mutating actions atomically as one undo entry and rolls the scene back on any failure; library rename/delete reject collisions and missing entries; create accepts `name`, `parent`, transform arrays, `tags`, `layer`, `visible` and optional registry asset ids `mesh`/`material`; `assign_asset` reassigns or clears an existing node's mesh/material and rejects missing or wrong-kind ids; component actions use the game's `component_types` name map and JSON `data`; the console renders dataclass fields as typed inputs and falls back to JSON for custom codecs; play mode snapshots the authored scene, advances `game.update()` with fixed steps (the console sends a frame count plus an actions JSON list), blocks edits, and restores the authored scene on stop;
- `POST /api/simulate` accepts `{"frames": 60, "actions": [...], "step": 0.0167, "trace": false}` and returns the same deterministic result as `--simulate`.

All responses carry `Access-Control-Allow-Origin: *` so a local frontend or AI client can call the API directly. The server is loopback-only by default; do not expose it publicly. It does not need OpenGL. The bundled browser console drives the same endpoints and renders the scene document with WebGL2; drag orbits the editor camera, shift-drag pans, the wheel zooms, Reset view returns to the scene camera framing, Focus selected centers the camera on the selected node, and the selected node gets a viewport rim highlight; clicking a node selects it, while clicking empty space clears selection. Console shortcuts: Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y redo, Delete deletes the selection, F focuses it, and Escape clears selection when no text field is focused. That preview is approximate, while `--headless` remains the authoritative pixel render. `/api/scene` uses `self.scene` when the game exposes it (live state); otherwise it calls `build_scene()` for a fresh scene.

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
