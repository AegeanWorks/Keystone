# Keystone

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/AegeanWorks/AIKit)

![Keystone engine sample](assets/engine.png)

A small, game-agnostic 3D engine core in Python: OpenGL 3.3 rendering, scene graph, meshes and OBJ loading, fixed-step loop, action input, collision primitives, deterministic replay, atomic serialization, and a human HUD/help overlay rendered with an embedded bitmap font.

Games plug in through one five-operation contract. Keystone ships a **cube demo** only as a smoke test; it contains no combat, puzzles, procedural worlds or other genre rules. External game modules live outside this package and load with `--game package.module:Factory`. Games may also add an optional `draw_ui(canvas, state)` hook for their own HUD.

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10+ with the pinned `requirements.txt` stack (numpy 2.5.3, PyOpenGL 3.1.10, glfw 2.11.0, pytest 9.1.1) and an OpenGL 3.3-capable GPU driver.
- **Install**: `python -m pip install -r requirements.txt`
- **Canonical Regression Shield Gate**:
  ```bash
  python -m pytest -q
  ```
- **Run the engine sample**:
  ```bash
  python -m keystone
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
- **Run an external game module**:
  ```bash
  python -m keystone --game my_game:MyGame
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

### Optional game UI

A game may add a `draw_ui(canvas, state)` method. It is optional; the five required operations do not change.

```python
from keystone.ui import Canvas, HudState


def draw_ui(self, canvas: Canvas, state: HudState) -> None:
    canvas.rect(16, 96, 220, 44, (0.03, 0.04, 0.06, 0.7))
    canvas.text(28, 108, f"OBJECTS {len(self.objects)}", (0.92, 0.94, 0.97, 1.0))
```

The hook runs before the engine HUD and pause menu, so engine UI stays on top. It receives the current `Canvas` and `HudState`, so games use the same embedded font, clipping and pause state as the engine. Hiding the overlay (`H`) hides game UI too.

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

Pausing stops `GameModule.update()` while the window, renderer and overlay stay responsive. The pause menu offers `Resume`, `Hide HUD` and `Quit`; the cursor is released while it is open so items can be clicked, and recaptured on resume. The overlay is presentation-only: it never mutates game state.

## 🖥️ Human UI

Windowed runs draw a HUD by default; `--no-ui` turns it off and `--ui` adds it to a headless capture:

```bash
python -m keystone --no-ui
python -m keystone --headless --frames 1 --size 960x540 --ui --out hud.png --report hud.json
```

The overlay contains:

- game name, game status, FPS, frame number, elapsed simulation time and resolution;
- a controls panel (`P` pause, `H` hide, `F1` cursor, `Esc` quit);
- an interactive pause menu with `Resume`, `Hide HUD` and `Quit`, navigable by keyboard or mouse;
- a centered pause banner.

`keystone.ui` is split into an embedded 5×7 font, a clipped screen-space `Canvas`, small panel/button widgets, a pure `PauseMenu` state machine and `HumanOverlay`; `keystone.gpu.ui_renderer` uploads the canvas as one alpha-blended draw call. A game's optional `draw_ui(canvas, state)` hook draws into the same canvas. A headless report that includes `--ui` measures the same pixels a person sees.

## 🚀 Features

- **OpenGL 3.3 core renderer**: GLSL 330, indexed meshes, depth testing, back-face culling, Blinn-Phong lighting, vertex colors, fog, gradient sky and an optional point light.
- **Scene graph**: named nodes, local/world transforms, visibility, cycle-safe parenting and cached static GPU meshes.
- **Assets**: immutable `MeshData` with optional UVs and vertex colors, cube/plane/cone/cylinder/sphere primitives, a streaming OBJ loader and a dependency-free PNG writer.
- **Fixed-step runtime**: `FixedStepClock` releases whole simulation steps with a bounded catch-up budget; the headless path advances exactly one step per rendered frame for deterministic tests.
- **Action input**: `InputMap` maps keys and pointer motion to `forward`, `right`, `up`, `look_yaw`, `look_pitch`, `pressed` and `held`; games never read GLFW directly.
- **Physics primitives**: rays, AABBs and spheres with ray queries, overlap tests and sphere/AABB resolution.
- **Replay and persistence**: `ActionState` command logs, stable hashes and atomic JSON writes with a `.bak` snapshot.
- **Plugin loading**: `load_game("package.module:Factory")` validates the five-operation contract before the engine starts.
- **No-GL simulation**: `run_simulation()` and `--simulate` drive `GameModule.update()` directly, with JSON action scripts and deterministic hashes, no window or driver required.
- **AI discovery and testing**: `--describe`/`describe_game()` expose actions, capabilities, report schema and the current snapshot; `--verify-determinism` runs a script twice; `--expect-hash` pins a result; `keystone.testing` provides the same evidence as Python helpers; `compare_reports()` diffs two frame reports.
- **Visual regression gate**: `--compare-baseline baseline.json` renders a new report, compares image/report hashes, stats and projected nodes, prints the diff and exits non-zero on image change. `--diff-out diff.png` writes a changed-pixel diff image.
- **PNG reader and pixel diff**: `keystone.png.read_png()` and `keystone.analysis.diff_images()` provide round-trip image loading, changed-pixel counts, bbox and a visual diff without third-party imaging libraries.
- **Frame reports for AI analysis**: `--report` writes a schema-1 JSON document with image hashes, pixel/luminance statistics, content bbox, dominant colors, an 8×8 luminance grid, camera data and projected screen bounds for every scene node.
- **Human overlay**: a game-agnostic HUD with game/status, FPS, frame, elapsed time and resolution, plus controls help and an interactive pause menu; drawn with an embedded 5×7 bitmap font, no font asset or imaging library. Games can add their own HUD through the optional `draw_ui(canvas, state)` hook.
- **Game-agnostic core**: no combat, light-lock, weave, network, space or expedition code in the package.

## 🤖 AI Testing & Frame Analysis

### Discover the game contract

```bash
python -m keystone --describe
```

The JSON response contains the game name, `actions()` schema, current `snapshot()`, capabilities (`simulate`, `render`, `human_ui`) and the versioned report schema. It is the first call an AI client should make.

### Verify determinism and visual regressions

```bash
python -m keystone --verify-determinism --frames 120 --actions actions.json
python -m keystone --headless --frames 1 --size 1280x720 \
  --out frame.png --report current.json --compare-baseline baseline.json
```

The first command runs the scenario twice and exits 0 only when both hashes match. The second renders, writes the current report, compares it with the baseline and exits non-zero when the image changed. The diff includes luminance/content deltas and changed/added/removed nodes. Add `--diff-out diff.png` for a visual pixel diff with changed-pixel count, ratio, bbox and mean/max delta. `--expect-hash <32-hex>` pins a known final hash for either simulation mode.

See [`docs/AI_GUIDE.md`](docs/AI_GUIDE.md) for the complete discover → simulate → verify → render → compare workflow.

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

### Analyze a rendered frame

`--report` writes a versioned JSON report next to the PNG:

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out frame.png --report frame.json
```

The report contains:

- `schema`, report field schema and a stable report `hash`;
- image path, dimensions, PNG and RGBA SHA-256, plus an optional pixel-diff summary;
- mean RGB/luminance, content pixels/ratio, content bounding box, dominant colors and an 8×8 luminance grid;
- camera parameters;
- every scene node's world position, visibility, triangle count and projected screen center/bounding box.

This lets an AI model compare a frame, a scene graph and a deterministic simulation without guessing from pixels alone. `keystone.analysis.compare_reports(before, after)` returns image/report equality, luminance and content-ratio deltas, bbox changes, and added/removed/changed nodes. It does not claim to measure visual quality.

## 📦 What's Inside

```text
keystone/
├── keystone/
│   ├── __init__.py           <- public API and version
│   ├── __main__.py           <- CLI: --game, headless frames, PNG
│   ├── app.py                <- game-agnostic Engine loop
│   ├── clock.py              <- fixed-step clock
│   ├── input.py              <- ActionState and InputMap
│   ├── plugin.py             <- GameModule protocol and loader
│   ├── replay.py             <- command log and stable hash
│   ├── serialization.py      <- atomic JSON persistence
│   ├── headless.py           <- no-GL simulation and JSON action scripts
│   ├── analysis.py           <- frame statistics, projected scene and report diff
│   ├── testing.py            <- deterministic AI/CI scenario helpers
│   ├── physics.py            <- rays, AABB, sphere queries and pushout
│   ├── math3d.py             <- Vec3, Mat4, Quat (column-major, OpenGL-ready)
│   ├── camera.py             <- perspective camera
│   ├── scene.py              <- hierarchy, transforms and lights
│   ├── geometry.py           <- MeshData and Material
│   ├── mesh_builder.py       <- merge boxes, quads and meshes
│   ├── primitives.py         <- cube, plane, cone, cylinder and sphere
│   ├── obj_loader.py         <- streaming Wavefront OBJ loader
│   ├── png.py                <- dependency-free PNG writer and reader
│   ├── samples.py            <- CubeDemo smoke test
│   ├── ui/
│   │   ├── __init__.py       <- UI package exports
│   │   ├── font.py           <- embedded 5x7 bitmap font
│   │   ├── canvas.py         <- clipped screen-space quads and text
│   │   ├── widgets.py        <- panels and menu buttons
│   │   ├── menu.py           <- pure pause-menu selection state
│   │   └── overlay.py        <- HUD, controls help and pause menu
│   └── gpu/
│       ├── __init__.py       <- GPU adapter package marker
│       ├── context.py        <- GLFW window and OpenGL 3.3 context
│       ├── shader.py         <- GLSL compilation and uniforms
│       ├── mesh_buffer.py    <- VAO/VBO/EBO upload and drawing
│       ├── ui_renderer.py    <- screen-space alpha-blended UI draw
│       └── renderer.py       <- forward renderer, sky, lights, readback
├── assets/
│   ├── octahedron.obj        <- generic sample OBJ
│   ├── engine.png            <- sample frame
│   └── engine.json           <- schema-1 sample frame report
├── docs/
│   ├── ARCHITECTURE.md       <- core layers, contract and roadmap
│   └── AI_GUIDE.md           <- discover, simulate, verify, render and compare
├── tests/
│   ├── test_math3d.py        <- math core
│   ├── test_scene.py         <- hierarchy, camera and lights
│   ├── test_geometry.py      <- meshes, primitives, builder and OBJ
│   ├── test_png.py           <- PNG writer and reader
│   ├── test_ui.py            <- font, canvas, menu and overlay
│   ├── test_renderer.py      <- headless OpenGL integration
│   ├── test_input.py         <- action mapping and ActionState
│   ├── test_clock.py         <- fixed-step clock
│   ├── test_physics.py       <- rays, AABB and sphere queries
│   ├── test_plugin.py        <- GameModule contract and loader
│   ├── test_replay.py        <- command log and hashes
│   ├── test_serialization.py <- atomic JSON persistence
│   ├── test_headless.py      <- no-GL simulation and action scripts
│   ├── test_analysis.py      <- frame statistics, projection and report diff
│   ├── test_testing.py       <- deterministic scenario helpers
│   ├── test_samples.py       <- CubeDemo smoke test
│   ├── test_boundary.py      <- core has no game modules/imports
│   └── test_app.py           <- engine loop, CLI, simulate and reports
├── requirements.txt          <- pinned runtime and test dependencies
├── pyproject.toml            <- package metadata, pytest and ruff configuration
├── .gitignore                <- transient AIKit state excluded
├── LICENSE                   <- Aegean License 1.1 (AL-1.1): free personal use
├── COMMERCIAL.md             <- Commercial licensing terms
├── LICENSES/                 <- REUSE license texts
├── REUSE.toml                <- Machine-readable SPDX metadata
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

- `keystone.*` imports only the standard library, declared dependencies and other core modules.
- A game imports the public `keystone` API; it never reaches into another game.
- `GameModule` is a five-method Protocol, not an inheritance tree.
- `ActionState` is a frozen DTO; bindings live in `InputMap`.
- `HudState` is a frozen DTO; the overlay reads it and never writes game state.
- `CommandLog` records deterministic action frames; `stable_hash()` fingerprints snapshots.
- `write_json_atomic()` replaces state with a temp file, fsync, `.bak` and `os.replace`.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the dependency rules, module responsibilities, acceptance criteria and core roadmap.

## 🗺️ Core Roadmap

1. Scene identity and optional ECS/component queries.
2. Broadphase physics, character controller and trigger volumes.
3. Asset registry, materials/textures, glTF import and hot reload.
4. Renderer instancing, shadows, PBR and post-processing.
5. Input rebinding, audio mixer and buses.
6. Scene/save schema versioning and replay/undo tooling.
7. Editor/inspector, asset browser and profiler.
8. AI observation/action adapters that consume the frame report and command log.

Games are external modules; they are not added to this repository.

## 🧪 Verification

```bash
python -m pytest -q
python -m keystone --simulate --frames 1
python -m keystone --headless --frames 1 --size 64x48
python aikit.py check keystone --strict
```

The project gate covers tests, lint, mechanics, hygiene, guidelines and secrets.

## 📜 License

Free for personal use under the Aegean License 1.1 (AL-1.1); see [LICENSE](LICENSE). Any commercial use needs the Aegean Commercial License 1.0 (ACL-1.0); see [COMMERCIAL.md](COMMERCIAL.md).
