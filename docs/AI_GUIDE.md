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
- `capabilities`: `simulate`, `render`, `human_ui` and the versioned `report_schema`.

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

The schema-1 report contains:

- image path, dimensions and PNG/RGBA SHA-256;
- mean RGB/luminance, content pixels/ratio and bbox;
- dominant colors and an 8×8 luminance grid;
- camera parameters;
- every node's world position, visibility, triangle count, projected screen center and bounding box;
- a stable report hash.

## 5. Compare against a baseline

```bash
python -m keystone --headless --frames 1 --size 1280x720 \
  --out current.png --report current.json \
  --compare-baseline baseline.json --diff-out diff.png
```

The diff reports image/report equality, luminance and content-ratio deltas, bbox changes, and added/removed/changed nodes. `--diff-out` additionally writes a visual PNG and reports changed pixels, ratio, bbox, mean delta and max delta. Exit code 0 means the image hash matched; 1 means it changed.

## 6. Capture the human UI

Windowed runs draw the HUD by default. For an AI inspection of what a person sees, add `--ui` to a headless run:

```bash
python -m keystone --headless --frames 1 --size 960x540 --ui \
  --out hud.png --report hud.json
```

The overlay reports game/status, FPS, frame, elapsed time, resolution, controls and pause state. `P` opens an interactive `Resume` / `Hide HUD` / `Quit` menu; the cursor is released while it is open. The overlay is presentation-only: `--simulate` and `--verify-determinism` stay GPU-free, and `--no-ui` keeps captures pixel-identical to the pre-overlay behavior.

UI actions can also be driven directly, which is useful for scripted tests:

```python
engine.apply_ui_action("pause")     # open the menu
engine.apply_ui_action("resume")    # close it
engine.apply_ui_action("toggle_ui") # hide/show the HUD
engine.apply_ui_action("quit")      # request window close
```

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
