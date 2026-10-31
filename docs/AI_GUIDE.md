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

## 2. Simulate without OpenGL

```bash
python -m keystone --simulate --frames 120 --actions actions.json --out run.json
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

## 4. Render and analyze

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out frame.png --report frame.json
```

The schema-4 report contains:

- image path, dimensions and PNG/RGBA SHA-256;
- mean RGB/luminance, content pixels/ratio and bbox;
- dominant colors and an 8×8 luminance grid;
- camera parameters;
- every node's scene ID, parent ID, tags, layer, component type names, world position, visibility, triangle count, projected screen center and bounding box;
- per-material color/specular/shininess/checker and optional texture name, dimensions and SHA-256;
- `ui` metadata (`visible`, `paused`, labels and buttons) or `null` for clean captures;
- a stable report hash.

## 5. Compare against a baseline

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out current.png --report current.json \
  --compare-baseline baseline.json --diff-out diff.png
```

The diff reports image/report equality, luminance and content-ratio deltas, bbox changes, added/removed/changed nodes (keyed by scene ID when both reports are schema 4, otherwise by name), added/removed/moved UI labels and buttons, and material/texture metadata. `--diff-out` additionally writes a visual PNG and reports changed pixels, ratio, bbox, mean delta and max delta. Exit code 0 means the image hash matched; 1 means it changed.

## 6. Capture the human UI

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

## 7. Draw a game HUD

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
- `GET /api/scene` returns scene document schema 1: camera, lights, atmosphere, node identity/tags/layers/components, world matrices, shared meshes and RGBA textures;
- `POST /api/simulate` accepts `{"frames": 60, "actions": [...], "step": 0.0167, "trace": false}` and returns the same deterministic result as `--simulate`.

All responses carry `Access-Control-Allow-Origin: *` so a local frontend or AI client can call the API directly. The server is loopback-only by default; do not expose it publicly. It does not need OpenGL. The bundled browser console drives the same endpoints and renders the scene document with WebGL2; that preview is approximate, while `--headless` remains the authoritative pixel render. `/api/scene` uses `self.scene` when the game exposes it (live state); otherwise it calls `build_scene()` for a fresh scene.

## Python helpers

```python
from keystone.analysis import compare_reports
from keystone.input import ActionState
from keystone.samples import CubeDemo
from keystone.testing import assert_deterministic, run_script

result = run_script(CubeDemo(), [ActionState(forward=1.0)], frames=60)
assert_deterministic(lambda: CubeDemo(), [ActionState(forward=1.0)], frames=60)
```

## AIKit

The project gate runs the GPU-free mechanics check:

```bash
python aikit.py check keystone --strict
```

`mechanics.test` is `python -m keystone --simulate --frames 1`. Rendered reports are still available through `--headless` and require an OpenGL 3.3 driver.
