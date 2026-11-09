# Keystone

<!-- aegean:media:start -->
<p align="center"><img src="assets/social-preview.svg" alt="Keystone social preview" width="100%"></p>
<p align="center"><a href="LICENSE"><img src="https://img.shields.io/badge/license-AL--1.1-2f9e44" alt="License"></a> <a href="https://github.com/AegeanWorks/AIKit"><img src="https://img.shields.io/badge/AIKit-integrated-6f42c1" alt="AIKit Integrated"></a></p>
<!-- aegean:media:end -->


![Keystone engine sample](assets/engine.png)

A game-agnostic 3D engine core in Python: OpenGL 3.3 PBR rendering, scene graph, meshes/OBJ, fixed-step loop, rebindable input, animation, particles, audio, collision, replay, atomic saves, batch merging and a HUD overlay.

Games plug in through one five-operation contract. Keystone ships a **cube demo** only as a smoke test; it contains no combat, puzzles, procedural worlds or genre rules. External games live outside this package and load with `--game package.module:Factory`. Games may add optional `draw_ui` and `bind_input` hooks.

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10+ with the pinned `requirements.txt` stack (numpy 2.5.3, PyOpenGL 3.1.10, glfw 2.11.0, pytest 9.1.1) and an OpenGL 3.3-capable GPU driver.
- **Install**: `python -m pip install -r requirements.txt`
- **Canonical Regression Shield Gate**:
  ```bash
  python -m pytest -q
  ```
- **Create and open a project**:
  ```bash
  python -m keystone --new my-game
  python -m keystone --project my-game
  ```
- **Package a project**:
  ```bash
  python -m keystone --project my-game --export build/my-game
  ```
- **Open the local web console and WebGL viewer**:
  ```bash
  python -m keystone --serve
  ```
- **Hide or disable the human overlay**:
  ```bash
  python -m keystone --no-ui
  ```
- **Render headlessly with the HUD**:
  ```bash
  python -m keystone --headless --frames 1 --size 960x540 --ui --out hud.png
  ```
- **Discover a game from an AI client**:
  ```bash
  python -m keystone --describe
  ```
- **Verify a scenario is deterministic**:
  ```bash
  python -m keystone --verify-determinism --frames 120
  ```
- **Pin a known result**:
  ```bash
  python -m keystone --simulate --frames 120 --expect-hash <32-hex-hash>
  ```
- **Simulate without OpenGL**:
  ```bash
  python -m keystone --simulate --frames 120 --trace
  ```
- **Emit a model-readable frame report**:
  ```bash
  python -m keystone --headless --frames 1 --size 1280x720 --out frame.png --report frame.json
  ```
### 🛠️ AIKit Commands (run from the AIKit folder)

| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status keystone` |
| Phase 4: every gate | `python aikit.py check keystone` |
| Repair memory and map, then check | `python aikit.py fix keystone` |
| Resume an interrupted task | `python aikit.py resume keystone` |

## 🧩 GameModule Contract

A game is an object with a name and five operations:

```python
from keystone.input import ActionState
from keystone.scene import Node, Scene


class MyGame:
    name = "my-game"

    def build_scene(self) -> Scene:
        scene = Scene()
        scene.add(Node("cube"))
        return scene

    def update(self, dt: float, actions: ActionState) -> None:
        ...

    def snapshot(self) -> dict[str, object]:
        return {"time": 0.0}

    def actions(self) -> dict[str, object]:
        return {"axes": ["forward", "right", "up", "look_yaw", "look_pitch"]}

    def status(self) -> str:
        return "my game"
```

The engine owns the window, OpenGL context, renderer, fixed clock, input sampling and screenshots. The game owns its state, rules and scene contents. The engine never imports a game.

### Optional live controls

A game may implement `bind_input(mapping)` to extend the engine's default
`InputMap` with its declared buttons:

```python
def bind_input(self, mapping: InputMap) -> None:
    mapping.bind("slot1", "1")
    mapping.bind("reload", "r")
```

The hook runs once after the engine builds its map. `describe_game()` reports
`capabilities.input_bind_hook` and `input_keys`; `Engine` exposes
`unbound_buttons` and `unknown_keys` so a dead control is visible. Mouse
buttons arrive through `ActionState.mouse_clicked`, not key bindings.

### Scene identity and components

A node carries a stable scene ID, tags, one layer and optional typed components:

```python
from dataclasses import dataclass

from keystone.scene import Node, Scene


@dataclass(frozen=True)
class Health:
    value: int


scene = Scene()
hero = scene.add(Node("hero", id="hero", tags={"player"}, layer="actors"))
hero.add_component(Health(100))

assert scene.find_by_id("hero") is hero
assert scene.query(tag="player", layer="actors") == [hero]
assert scene.query(component=Health) == [hero]
```

IDs are allocated per scene (`node-1`, `node-2`, ...) on attach or first traversal. An explicit `id` is kept, a duplicate is rejected, and reparenting preserves it. `tags` are a set of strings, `layer` is one string, and each node holds one component per type. Queries are linear scans; an index can come later.

### Physics: broadphase, characters and triggers

```python
from keystone.broadphase import SpatialGrid
from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Vec3
from keystone.physics import AABB, Ray, raycast
from keystone.triggers import TriggerTracker, TriggerVolume

grid = SpatialGrid(cell_size=4.0)
wall = AABB(Vec3(0, 0, 0), Vec3(0.5, 2, 4))
grid.insert("wall", wall)
boxes = [grid.get(key) for key in grid.query(AABB(Vec3(0, 0, 0), Vec3(1, 1, 1)))]
controller = CharacterController()
body = controller.step(
    CharacterBody(Vec3(0, 1, 0)),
    Vec3(4, 0, 0),
    1 / 60,
    [box for box in boxes if box is not None],
)
events = TriggerTracker().update(body.box(), [TriggerVolume("door", AABB(Vec3(0, 1, 0), Vec3(1, 1, 1)))])
hit = raycast(Ray(Vec3(), Vec3(0, 0, 1)), [("wall", wall)])
```

`SpatialGrid` keeps a uniform grid of AABB proxies with exact overlaps in insertion order; `cell_size` trades speed, not correctness. `CharacterController` moves an AABB body with wish velocity, gravity, wall/floor response, stair step-up, slope-limited climb and platform carry; no capsules or solvers. `TriggerTracker` reports sorted `entered`/`exited` tuples and an immutable `active` set; `raycast()` returns the nearest hit.

### Optional game UI

A game may add a `draw_ui(canvas, state)` method. It is optional; the five required operations do not change.

```python
from keystone.ui import Canvas, HudState


def draw_ui(self, canvas: Canvas, state: HudState) -> None:
    canvas.rect(16, 96, 220, 44, (0.03, 0.04, 0.06, 0.7))
    canvas.text(28, 108, f"OBJECTS {len(self.objects)}", (0.92, 0.94, 0.97, 1.0))
```

The hook runs before the engine HUD and pause menu, so engine UI stays on top. It receives the current `Canvas` and `HudState`, so games share the embedded font, clipping and pause state. `H` hides game UI too.

### Textures

```python
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.texture import TextureData

material = Material(
    color=Vec3(1.0, 1.0, 1.0),
    texture=TextureData.from_png("assets/floor.png"),
)
```

`TextureData.from_png()` accepts the same 8-bit RGBA PNGs as the reader. `TextureData.checker(size, dark, light, cell)` builds a deterministic texture without a file, and `TextureData.pattern(...)` adds seeded cell/grid/panel/rivets/noise presets. Textures use repeat wrapping, mipmaps and mesh UVs; the renderer caches one GPU texture per immutable payload.

## 🕹️ Sample Controls

The bundled `CubeDemo` uses the generic action map; the overlay shows it at runtime:

| Input | Action |
|---|---|
| `W` / `S` | Forward / back |
| `A` / `D` | Left / right |
| `E` / `Q` | Up / down |
| Mouse | Look; click menu items while paused |
| Arrow keys | Keyboard look |
| `P` | Pause / resume; opens the menu and releases the cursor |
| `W` / `S` or `↑` / `↓` | Move the pause-menu selection |
| `Enter` | Confirm the selected pause-menu item |
| `H` | Hide / show the HUD and help |
| `F1` | Release / recapture the mouse |
| `Esc` | Quit |

Pausing stops `GameModule.update()` while the window, renderer and overlay stay responsive. The pause menu offers `Resume`, `Hide HUD` and `Quit`; the cursor is released while it is open and recaptured on resume. The overlay never changes game state.

## 🖥️ Human UI

Windowed runs draw a HUD by default; `--no-ui` turns it off and `--ui` adds it to a headless capture:

```bash
python -m keystone --no-ui
python -m keystone --headless --frames 1 --size 960x540 --ui --out hud.png --report hud.json
python -m keystone --headless --frames 1 --size 960x540 --ui --start-paused \
  --out paused.png --report paused.json
```

`--start-paused` renders the pause menu immediately, which is useful for UI screenshots and AI UI reports.

The overlay contains:

- game name, game status, FPS, frame number, elapsed simulation time and resolution;
- a controls panel (`P` pause, `H` hide, `F1` cursor, `Esc` quit);
- an interactive pause menu with `Resume`, `Hide HUD` and `Quit`, navigable by keyboard or mouse;
- a centered pause banner.

`keystone.ui` splits into an embedded 5×7 font, a clipped `Canvas` (with `text_width`/`text_right`/`fit_text`), panel/button widgets, a pure `PauseMenu` state machine and `HumanOverlay`; `keystone.gpu.ui_renderer` uploads the canvas as one alpha-blended draw call. A game's optional `draw_ui(canvas, state)` hook draws into the same canvas, so a headless `--ui` report measures what a person sees.

## 🌐 Web Console, JSON API and WebGL Viewer

```bash
python -m keystone --serve
python -m keystone --serve --port 8899 --game package.module:Factory
```

The console binds to `127.0.0.1:8000` and serves a browser dashboard plus the same AI-facing JSON as the CLI. It uses only the standard library and vanilla JavaScript: no npm build, CDN or extra runtime dependency.

The dashboard can inspect the game contract, run the same action scripts as `--simulate`, refresh the live scene, and preview it in a WebGL2 viewer with textures, vertex colors, lights and fog. The browser viewer is approximate; the OpenGL renderer remains the pixel authority.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | `GET` | server, game and schema versions |
| `/api/describe` | `GET` | the same discovery payload as `--describe`, including `capabilities.web` |
| `/api/scene` | `GET` | scene document schema 2: camera, lights, atmosphere, node identity, world matrices, shared meshes and RGBA textures |
| `/api/inspector` | `GET` | batch plan, merge, audio/anim/particles, assets |
| `/api/simulate` | `POST` | the same deterministic result as `--simulate`; body `{"frames": 60, "actions": [...], "step": 0.0167, "trace": false}` |
| `/api` | `GET` | endpoint and schema index |

The API sends CORS headers so local AI clients can call it directly. Keep the default loopback host; pass `--host 0.0.0.0` for deliberate exposure. The server never opens a GL context.

`/api/scene` exports the game's `self.scene` when it has one, so a live simulation is visible immediately. A game without that attribute gets a fresh `build_scene()` result; put the scene on `self.scene` for live state.

## 🚀 Features

- **OpenGL 3.3 renderer**: GLSL 330, PBR, shadows, sRGB, post grade, bloom, placed sprite billboards, up to 8 point lights, and profiler stats.
- **Scene graph**: stable IDs, tags, layers, typed components, world transforms, queries and cached GPU meshes.
- **Prefabs**: capture, versioned `.kprefab` persistence, deterministic instantiation and override-preserving refresh.
- **Assets**: `MeshData`, primitives, streaming OBJ, PNG/checker `TextureData`, and an id/digest registry with hot reload plus core scene rebinding.
- **PBR materials**: specular/shininess plus metallic/roughness/emissive, wrapped/mipmapped textures and material graphs.
- **Runtime**: fixed-step clock with bounded catch-up; headless one-step-per-frame determinism.
- **Input**: rebindable `InputMap` across contexts, a game `bind_input` hook, and dead-binding diagnostics.
- **Audio**: synth, named-bus mixer, deterministic mixdown, WAV I/O and reports; no hardware output.
- **Animation**: tracks/clips, looping, crossfades, events, blend spaces, masked `apply_pose`, CPU/GPU skinning and state machines.
- **Particles and physics**: seeded emitters with swept collision; rays, AABB/sphere queries, broadphase, character movement and triggers.
- **Replay and persistence**: command logs, stable hashes, `run_log`/`verify_log`, atomic JSON with `.bak`.
- **Testing and AI**: `--describe`, `--simulate`, `--verify-determinism`, `--expect-hash`, frame reports, pixel diffs, seeded playtests and adapters.
- **Human UI and web**: overlay/pause menu, `draw_ui`, stdlib JSON API and WebGL2 console/editor.
- **Game-agnostic core**: no combat, light-lock, weave or expedition code.

## 🤖 AI Testing & Frame Analysis

### Discover the game contract

```bash
python -m keystone --describe
```

Includes game name, actions, snapshot and 32 capability keys.

### Verify determinism and visual regressions

```bash
python -m keystone --verify-determinism --frames 120 --actions actions.json
python -m keystone --headless --frames 1 --size 1280x720 \
  --out frame.png --report current.json --compare-baseline baseline.json
```

The first command runs the scenario twice and exits 0 only when both hashes match. The second renders, writes the report, compares it with the baseline and exits non-zero when the image changed. The diff covers luminance/content deltas and added/removed/changed nodes. `--diff-out diff.png` adds a visual pixel diff. `--expect-hash <32-hex>` pins a known final hash either way.

See [`docs/AI_GUIDE.md`](docs/AI_GUIDE.md) for the complete workflow.

### Simulate without a GPU

`--simulate` imports the game and applies actions in fixed 1/60 s steps. It never creates an `Engine`, GLFW window or OpenGL context.

```bash
python -m keystone --simulate --frames 3 --actions actions.json --trace
```

`actions.json` is a list of `ActionState` objects (one per frame, or fewer repeated):

```json
[
  {"forward": 1.0, "look_yaw": 0.1},
  {"forward": 0.0, "pressed": ["toggle_capture"]}
]
```

The JSON result includes the game name, frames, step, actions used, final snapshot and a stable hash. `--trace` adds one snapshot per frame. `--out run.json` writes the result atomically.

For assertions in Python, use `keystone.testing`:

```python
from keystone.input import ActionState
from keystone.samples import CubeDemo
from keystone.testing import assert_deterministic, run_script

result = run_script(CubeDemo(), [ActionState(forward=1.0)], frames=120)
assert_deterministic(lambda: CubeDemo(), [ActionState(forward=1.0)], frames=120)
```

### Bot-playtest a game

```bash
python -m keystone --playtest --policy random --seed 7 --frames 120 --out report.json
```

Seeded `random`/`greedy`/`scripted` bots play headlessly through the five operations; `--expect-hash` pins the transcript, and an `unfair` configuration exits 1 with reasons.

### Analyze a rendered frame

`--report` writes a versioned JSON report next to the PNG:

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out frame.png --report frame.json
```

The report contains:

- `schema`, report field schema and a stable report `hash`;
- image path, dimensions, PNG and RGBA SHA-256, plus an optional pixel-diff summary;
- mean RGB/luminance, content box/ratio, dominant colors, 8×8 grid;
- camera plus per-node world/screen box, visibility and triangles;
- material color/specular/shininess/checker plus texture metadata;
- when `--ui` is active: `ui.visible`, `ui.paused`, every label's text/position/scale/color and every button's label, action, rect, selection and hover state. `ui` is `null` for clean captures.

AI clients diff frames/scenes/sim/UI via `compare_reports(before, after)` (image/report equality, stat/node/label deltas; no visual-quality claim).

## 📦 What's Inside

```text
keystone/
├── keystone/
│   ├── __init__.py           <- public API and version
│   ├── _version.py           <- single-source release version
│   ├── __main__.py           <- CLI: --game, headless frames, PNG
│   ├── agents.py             <- AI adapters and audit trail
│   ├── animation.py          <- clips, controller and pose reports
│   ├── animation_blend.py    <- blend spaces
│   ├── animation_state.py    <- parameter-driven state machine transitions
│   ├── animation_library.py  <- file-backed .kanim clip library
│   ├── state_machine_library.py <- file-backed .kstate machine library
│   ├── app.py                <- Engine loop
│   ├── audio.py              <- synth clips, mixer and WAV I/O
│   ├── batch.py              <- static batch planning, world-space and rig merge
│   ├── clock.py              <- fixed-step clock
│   ├── culling.py            <- frustum culling
│   ├── input.py              <- ActionState and InputMap
│   ├── lifecycle.py          <- deterministic component start/update/stop
│   ├── plugin.py             <- GameModule protocol and loader
│   ├── playtest.py           <- seeded bot policies and fairness
│   ├── replay.py             <- command log and stable hash
│   ├── history.py            <- bounded undo/redo snapshots
│   ├── scene_snapshot.py     <- versioned scene save/load
│   ├── scene_library.py      <- file-backed scene library
│   ├── scene_diff.py         <- structured saved-scene diffs
│   ├── serialization.py      <- atomic JSON persistence
│   ├── headless.py           <- no-GL simulation and action scripts
│   ├── analysis.py           <- frame stats, projection and report diff
│   ├── testing.py            <- deterministic scenario helpers
│   ├── physics.py            <- rays, AABB, sphere queries, pushout and raycasts
│   ├── particles.py          <- deterministic CPU emitters and systems
│   ├── broadphase.py         <- deterministic spatial-grid broadphase
│   ├── character.py          <- AABB movement and ground detection
│   ├── triggers.py           <- trigger volumes and tracking
│   ├── assets.py             <- mesh, material and texture asset registry
│   ├── asset_io.py           <- file-backed sources, loaders and hot reload
│   ├── component_codec.py    <- shared JSON codec for typed components
│   ├── gltf_import.py        <- glTF/GLB scene to prefab import
│   ├── schema.py             <- versioned core schema constants
│   ├── math3d.py             <- Vec3, Mat4, Quat (column-major, OpenGL-ready)
│   ├── camera.py             <- perspective camera
│   ├── project.py           <- manifests, scaffolding and --project loading
│   ├── export.py            <- deterministic runnable project bundles
│   ├── prefab.py            <- deterministic subtree templates
│   ├── prefab_library.py    <- file-backed prefab library
│   ├── library_trash.py      <- recoverable library deletes
│   ├── scene.py              <- hierarchy, identity, components, transforms and lights
│   ├── geometry.py           <- MeshData, Material
│   ├── skin.py               <- bone palettes, CPU skinning
│   ├── mesh_builder.py       <- merge boxes, quads, meshes, skinned rigs
│   ├── material_graph.py     <- node graphs evaluating to Material
│   ├── material_library.py   <- file-backed .kmaterial library
│   ├── primitives.py         <- cube, plane, cone, cylinder and sphere
│   ├── obj_loader.py         <- Wavefront OBJ loader
│   ├── png.py                <- dependency-free PNG writer and reader
│   ├── texture.py            <- immutable RGBA textures, PNG and checker sources
│   ├── samples.py            <- CubeDemo smoke test
│   ├── gltf/
│   │   ├── __init__.py       <- glTF package exports
│   │   ├── io.py             <- source, buffer and accessor decoding
│   │   ├── textures.py       <- image and texture decoding
│   │   ├── materials.py      <- PBR to Material conversion
│   │   ├── meshes.py         <- primitive, mesh, skin decoding
│   │   ├── skins.py          <- joints and inverse binds
│   │   ├── scene.py          <- node, skin and scene construction
│   │   └── loader.py         <- top-level import orchestration
│   ├── ui/
│   │   ├── __init__.py       <- UI package exports
│   │   ├── font.py           <- embedded 5x7 bitmap font
│   │   ├── canvas.py         <- clipped screen-space quads and text
│   │   ├── widgets.py        <- panels and menu buttons
│   │   ├── menu.py           <- pure pause-menu selection state
│   │   ├── report.py         <- UI labels/buttons for AI reports
│   │   └── overlay.py        <- HUD, controls help and pause menu
│   ├── web/
│   │   ├── __init__.py       <- web package exports
│   │   ├── editor.py         <- hierarchy, transform and prefab edits
│   │   ├── schema.py         <- web API and scene document schemas
│   │   ├── scene.py          <- scene-to-JSON export for the viewer
│   │   ├── server.py         <- stdlib JSON API and static server
│   │   └── static/
│   │       ├── index.html    <- console shell
│   │       ├── app.js        <- console controls and API client
│   │       ├── viewer.js     <- WebGL2 scene renderer
│   │       └── style.css     <- console layout and tokens
│   └── gpu/
│       ├── __init__.py       <- GPU adapter package marker
│       ├── context.py        <- GLFW window and OpenGL 3.3 context
│       ├── shader.py         <- GLSL compilation and uniforms
│       ├── mesh_buffer.py    <- VAO/VBO/EBO upload and drawing
│       ├── skinned_buffer.py <- skinned mesh upload
│       ├── sprites.py        <- deterministic sprite math
│       ├── instancing.py     <- deterministic instancing groups
│       ├── shadow.py         <- shadow map
│       ├── post.py           <- post grade math
│       ├── bloom.py          <- bloom glow
│       ├── bloom_fbo.py      <- bloom diffusion FBO
│       ├── texture_buffer.py <- 2D texture upload, mipmaps and cleanup
│       ├── ui_renderer.py    <- screen-space alpha-blended UI draw
│       └── renderer.py       <- forward renderer, sky, lights, shadows, post, bloom, sprites
├── assets/
│   ├── octahedron.obj        <- generic sample OBJ
│   ├── engine.png            <- sample frame
│   ├── engine.json           <- sample frame report
│   ├── logo.svg              <- project logo
│   ├── social-preview.svg    <- social preview
│   └── screenshots/          <- approved HUD + console keepers
├── docs/
│   ├── ARCHITECTURE.md       <- core layers and contract
│   ├── AI_GUIDE.md           <- discover, simulate and verify
│   └── IMPLICIT_STATE_AUDIT.md <- state-machine audit
├── tests/
│   ├── test_math3d.py        <- math core
│   ├── test_scene.py         <- hierarchy, camera and lights
│   ├── test_geometry.py      <- meshes, primitives, builder and OBJ
│   ├── test_png.py           <- PNG writer and reader
│   ├── test_texture.py       <- texture data, checker and PNG loading
│   ├── test_ui.py            <- font, canvas, menu and overlay
│   ├── test_renderer.py      <- headless OpenGL integration
│   ├── test_input.py         <- action mapping and ActionState
│   ├── test_input_keys.py    <- GL key table and dead bindings
│   ├── test_lifecycle.py     <- component start/update/stop lifecycle
│   ├── test_clock.py         <- fixed-step clock
│   ├── test_physics.py       <- rays, AABB, sphere queries and raycasts
│   ├── test_broadphase.py    <- spatial-grid queries, updates and pairs
│   ├── test_project.py      <- manifest, scaffold and --project workflow
│   ├── test_export.py       <- export bundle structure, hashes and launcher
│   ├── test_prefab.py       <- prefab capture, IDs and isolation
│   ├── test_prefab_library.py <- prefab library save, load and errors
│   ├── test_particles.py     <- seeded emitters, forces and reports
│   ├── test_pbr.py           <- metallic/roughness/emissive shading
│   ├── test_character.py     <- floor, wall, jump and validation behavior
│   ├── test_triggers.py      <- enter/exit tracking and multiple volumes
│   ├── test_agents.py        <- AI adapters, validation and audit trail
│   ├── test_animation.py     <- clips, blending and timed events
│   ├── test_animation_blend.py <- blend spaces
│   ├── test_animation_state.py <- state transitions, triggers and round trips
│   ├── test_animation_library.py <- clip library save, load, delete and restore
│   ├── test_state_machine_library.py <- .kstate library save/delete/restore
│   ├── test_material_library.py <- material library save, load, register and textures
│   ├── test_skinning.py      <- skin math, GPU path, glTF
│   ├── test_sprites.py       <- sprite math, report, sample fixture
│   ├── test_sprite_nodes.py  <- placed sprite nodes and billboards
│   ├── test_merge_skin.py    <- skin-aware merge
│   ├── test_assets.py          <- registry ids, digests, dependencies and reload
│   ├── test_audio.py         <- synth, mixer buses and WAV I/O
│   ├── test_batch.py         <- batch planning and world-space merge
│   ├── test_material_graph.py <- declarative material graph evaluation
│   ├── test_gltf.py           <- glTF/GLB import and texture loading
│   ├── test_gltf_import.py    <- glTF/GLB prefab import coverage
│   ├── test_history.py        <- bounded undo/redo history
│   ├── test_instancing.py     <- hardware-instancing groups and draws
│   ├── test_shadows.py        <- shadow map
│   ├── test_srgb.py           <- sRGB pipeline
│   ├── test_post.py           <- post color-grade
│   ├── test_bloom.py          <- bloom
│   ├── test_culling.py        <- frustum culling
│   ├── test_scene_snapshot.py <- versioned scene save/load
│   ├── test_round_trip_stability.py <- idempotent save/load
│   ├── test_scene_library.py <- scene library save, load and restore
│   ├── test_scene_diff.py   <- structured scene diff coverage
│   ├── test_plugin.py        <- GameModule contract and loader
│   ├── test_replay.py        <- command log and hashes
│   ├── test_serialization.py <- atomic JSON persistence
│   ├── test_component_codec.py <- typed component JSON codec
│   ├── test_library_trash.py <- recoverable library deletes
│   ├── test_version.py       <- version single-source drift guard
│   ├── test_headless.py      <- no-GL simulation and action scripts
│   ├── test_analysis.py      <- frame stats, projection, report diff
│   ├── test_projected_bbox.py <- near-plane silhouette clipping
│   ├── test_testing.py       <- deterministic helpers
│   ├── test_samples.py       <- CubeDemo smoke test
│   ├── test_boundary.py      <- no game modules/imports
│   ├── test_cli_failure_advice.py <- post-start errors name the step
│   ├── test_web.py           <- scene export, JSON API, assets
│   ├── test_app.py           <- engine loop, CLI, simulate and reports
│   ├── test_playtest.py      <- seeded bots and fairness
│   ├── test_swarm_fixes.py   <- swarm pins
│   ├── support_maze_game.py  <- deterministic grid fixture
│   └── support_policy.py     <- external policy fixture
├── requirements.txt          <- pinned runtime and test dependencies
├── pyproject.toml            <- package metadata, pytest and ruff configuration
├── .gitignore                <- transient AIKit state excluded
├── LICENSE                   <- Aegean License 1.1 (AL-1.1): free personal use
├── COMMERCIAL.md             <- Commercial licensing terms
├── LICENSES/                 <- REUSE license texts
├── REUSE.toml                <- Machine-readable SPDX metadata
├── CHANGELOG.md              <- release history
├── README.md
└── .aikit/                   <- this project's memory: record, ledger, decisions
```

## 🏗️ Architecture

The engine core is layered so games depend on it, never the reverse:

```text
GameModule (external)
  -> update(dt, ActionState)
  -> build_scene() -> Scene
Engine
  -> GLContext / InputMap / FixedStepClock
  -> Renderer.render(scene)
  -> UiRenderer.draw(HumanOverlay.build(state))
```

- `keystone.*` uses stdlib plus declared deps only.
- Games use the public API and never reach into another game.
- `GameModule` is a five-method Protocol; `ActionState`/`HudState` are frozen DTOs.
- `CommandLog`/`stable_hash()` fingerprint deterministic frames; `write_json_atomic()` uses temp+fsync+replace.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for dependency rules and roadmap; [`docs/IMPLICIT_STATE_AUDIT.md`](docs/IMPLICIT_STATE_AUDIT.md) records the state-machine audit.

## 📦 Asset Registry and Hot Reload

Keystone keeps meshes, materials and textures in a caller-owned `AssetRegistry`:

```python
from keystone.assets import AssetRegistry
assets = AssetRegistry()
assets.register_file("texture.logo", "assets/logo.png")
assets.refresh()  # sync reload; keeps last good payload on failure
```

Each asset has a stable id, kind, digest and dependencies. `refresh()` returns a `ReloadReport` (reloaded/unchanged/failed/missing) without crashing; it is synchronous with no thread.

## 🧱 glTF and GLB Import

`load_gltf()` accepts a `.gltf`/`.glb` path, JSON text or a parsed document:

```python
from keystone.gltf import load_gltf
imported = load_gltf("assets/robot.glb", registry=assets)
```

It decodes external/base64/GLB buffers, typed accessors, indexed triangles, PBR materials, PNG textures and TRS/matrix hierarchies. Bad modes/offsets/cycles raise.

## 💾 Scene Snapshots and Undo/Redo

`scene_to_dict()`/`scene_from_dict()` round-trip versioned snapshots (camera, environment, hierarchy, metadata, asset ids). Bad ids/parents/kinds/cycles are rejected.

```python
from keystone.history import History
from keystone.scene_snapshot import scene_from_dict, scene_to_dict

history = History(capacity=32)
history.push(scene_to_dict(scene))
snapshot = history.undo()
```

`History` deep-copies snapshots; schema 6 persists prefab-instance baselines; schema 1-5 stay compatible.

## 🗺️ Core Roadmap

Scene identity, physics, assets, PBR, batching, animation, particles, replay and AI adapters shipped through v0.45.0; the remaining renderer work is the full post chain, and editor hooks continue.

Games are external modules; they are not added to this repository.

## 🧪 Verification

```bash
python -m pytest -q
python -m keystone --simulate --frames 1
python -m keystone --headless --frames 1 --size 64x48
python aikit.py check keystone --strict
```

The project gate covers tests, lint, mechanics, hygiene, guidelines and secrets.

<!-- aegean:brand-assets:start -->
## 🎨 Brand Assets

> **AI-Generated Brand Artwork.** The banner and logo are **AI-generated brand assets**. They are illustrative and may not literally depict every feature or the full project scope.
<!-- aegean:brand-assets:end -->

## 📜 License

Free for personal use under the Aegean License 1.1 (AL-1.1); see [LICENSE](LICENSE). Any commercial use needs the Aegean Commercial License 1.0 (ACL-1.0); see [COMMERCIAL.md](COMMERCIAL.md).

<!-- aegean:screenshots:start -->
## Screenshots

<a href="https://github.com/AegeanWorks/Keystone/commit/e6c6318"><img src="assets/screenshots/2026-11-03-hud.png" alt="Keystone headless HUD render at 2026-11-03"></a>

<a href="https://github.com/AegeanWorks/Keystone/commit/e6c6318"><img src="assets/screenshots/2026-11-03-console.png" alt="Keystone web console at 2026-11-03"></a>

*`e6c6318` · 2026-11-03 · 960x540 headless + 1440x900 console; `engine.png` is legacy art*
<!-- aegean:screenshots:end -->
