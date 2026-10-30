# Keystone

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/AegeanWorks/AIKit)

![Keystone expedition](assets/expedition.png)

A performance-first 3D game engine in Python with an OpenGL 3.3 renderer, deterministic procedural worlds, first-person collision, survivors-style combat and a headless AI harness.

Keystone's core loop is a **seeded expedition**: one integer seed generates an island and a dungeon, the player walks the terrain, fights escalating enemy waves, enters the crypt through a stone portal, explores a generated room-and-corridor layout, and returns to the surface. The authoritative simulation is independent of OpenGL, so the same run can be rendered, replayed from JSON actions, or hashed for regression checks.

| Overworld | Dungeon |
|---|---|
| ![Terrain and portal](assets/expedition.png) | ![Generated crypt](assets/dungeon.png) |

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10+ with the pinned `requirements.txt` stack (numpy 2.5.3, PyOpenGL 3.1.10, glfw 2.11.0, pytest 9.1.1) and an OpenGL 3.3-capable GPU driver.
- **Install**: `python -m pip install -r requirements.txt`
- **Canonical Regression Shield Gate**:
  ```bash
  python -m pytest -q
  ```
- **Run the expedition**:
  ```bash
  python -m keystone
  ```
- **Run a specific seed**:
  ```bash
  python -m keystone --seed 42
  ```
- **Original showcase scene**:
  ```bash
  python -m keystone --demo
  ```
- **Render headlessly**:
  ```bash
  python -m keystone --headless --frames 1 --size 1280x720 --out frame.png
  ```
- **Ask the AI harness for the action schema**:
  ```bash
  python -m keystone.harness catalog
  ```

### 🛠️ AIKit Commands (run from the AIKit folder)

| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status keystone` |
| Phase 4: every gate | `python aikit.py check keystone` |
| Repair memory and map, then check | `python aikit.py fix keystone` |
| Resume an interrupted task | `python aikit.py resume keystone` |

## 🎮 Controls

The window captures the mouse on start.

| Input | Action |
|---|---|
| `W` / `A` / `S` / `D` | Move forward / left / back / right |
| Mouse | Look around |
| Arrow keys | Look with the keyboard |
| `Shift` | Sprint |
| `E` | Enter the portal, or leave through the crypt exit |
| `F1` | Release or recapture the mouse |
| `Esc` | Close the window |

Weapons fire automatically at the nearest enemy in range. Keep moving to avoid contact damage; the window title shows HP, wave, kills and whether a boss is alive.

## 🧭 The Core Loop

1. `World(seed)` generates the island heightfield, the dungeon layout and the combat director from the same seed.
2. The player starts at a walkable clearing, facing the stone portal, with the opening enemy pack in the forward arc.
3. Walking uses terrain height, water and slope checks; the dungeon uses a player-radius grid collision check.
4. Enemies chase, split, explode or soak damage; the weapon auto-fires, waves escalate and a Warlord arrives every fifth wave. Death respawns the player at the last safe point with a fresh arena.
5. Interacting within range of the portal switches the world to `dungeon`, rebuilds the scene and respawns the arena around the dungeon spawn.
6. Interacting at the exit rune restores the overworld position at the portal.
7. `World.state_hash()` fingerprints seed, time, player, terrain metadata, dungeon tiles and combat state. Identical seeds and actions produce identical hashes.

The dungeon preview is generated from the same run: `assets/dungeon.png`.

## 🚀 Features

- **Deterministic simulation core**: `keystone/sim/` imports no OpenGL; a fixed-step world, seeded generation and a stable replay hash drive every view.
- **Procedural island**: deterministic integer-hash value noise and FBM, radial island falloff, water level, biome colors, a clearing and a path from spawn to portal.
- **Procedural dungeon**: seeded non-overlapping rooms, L-shaped corridors, farthest-room exit, symmetric-raycast field of view and BFS pathfinding.
- **First-person collision**: terrain walkability (water/slope), dungeon radius checks with axis-separated sliding, and portal/exit range transitions.
- **Survivors combat**: six seeded enemy archetypes (Crawler, Stalker, Bulwark, Splitter, Bomber, Warlord boss), auto-fire hitscan, contact damage, split-on-death, escalating waves, boss waves and death/respawn. The whole director is renderer-independent and included in the replay hash.
- **GPU renderer**: OpenGL 3.3 core, GLSL 330, per-vertex colors, one directional light, an optional warm point light (the crypt torch), depth testing, culling, gradient sky and distance fog.
- **Static batching**: terrain is one mesh; trees, crowns, rocks and the path are merged into four meshes, so the expedition renders in roughly ten draw calls.
- **Day/night atmosphere**: sun elevation drives daylight, warm dawn tint, ambient light, sky/horizon colors and light intensity; the dungeon overrides with its own moody palette.
- **AI harness**: `catalog`, `run` and `selftest` JSON commands reproduce a run from a seed and an action list, with no GPU and no browser.
- **Headless parity**: the same renderer runs in a hidden context for tests and screenshots.

## ⚔️ Combat

![Enemy pack on the path](assets/combat.png)

Combat follows the Dustline model: the player only moves, the weapon auto-fires, and the pressure comes from wave composition and positioning. Enemies spawn around the player, chase across terrain or dungeon corridors, and deal contact damage. Crawlers are the baseline, Stalkers are fast, Bulwarks soak damage, Splitters spawn two Stalkers on death, Bombers explode on contact, and a Warlord boss arrives every fifth wave.

The director is seeded and lives in `keystone/combat.py`; it has no OpenGL dependency. Death resets the player to the last safe point with a fresh arena, so the AI harness can replay an entire run and still stop deterministically.

## 🤖 Headless AI Harness

```bash
python -m keystone.harness catalog
python -m keystone.harness selftest
python -m keystone.harness run --seed 7 --actions actions.json --out run.json
```

`actions.json`:

```json
{
  "actions": [
    {"action": "turn", "yaw": 90},
    {"action": "move", "forward": 1.0, "seconds": 1.0, "sprint": true},
    {"action": "interact"},
    {"action": "wait", "seconds": 0.5}
  ]
}
```

The result contains the final state (`mode`, `player`, `terrain`, `dungeon`, `near_entrance`, `near_exit`, `combat`, `events`) and a `hash`. The same seed and actions always produce the same hash; `selftest` proves determinism, seed sensitivity, portal entry, exit transition and rejection of unknown actions.

## 📈 Performance

- Frame loop after construction: roughly **2 ms per frame** at 1280×720 in a local headless run (AMD Radeon RX 9060 XT, OpenGL 3.3 core).
- 120 frames at 1280×720, including process startup, terrain/dungeon construction, combat and GLFW teardown: about **3–4 s wall-clock** locally. Construction and driver teardown dominate that number, not rendering.
- The static world is uploaded once; each frame updates the camera, atmosphere, enemy transforms and a handful of uniforms. Enemies are individual primitives; a hundred-plus would need instancing.

These are measurements of this demo on one machine, not a benchmark suite.

## 📦 What's Inside

```text
keystone/
├── keystone/
│   ├── __init__.py           <- package surface and version
│   ├── __main__.py           <- CLI: expedition, showcase, headless frames
│   ├── math3d.py             <- Vec3, Mat4, Quat (column-major, OpenGL-ready)
│   ├── camera.py             <- perspective camera and fly-style movement
│   ├── scene.py              <- hierarchy, transforms, lights, sky and fog
│   ├── geometry.py           <- indexed mesh data with optional vertex colors
│   ├── mesh_builder.py       <- merge boxes, quads and meshes into one MeshData
│   ├── primitives.py         <- cube, plane, cone, cylinder and UV sphere
│   ├── obj_loader.py         <- streaming Wavefront OBJ loader
│   ├── png.py                <- dependency-free PNG screenshot writer
│   ├── atmosphere.py         <- day/night sky, ambient and light model
│   ├── combat.py             <- archetypes, waves, auto-fire, boss, death
│   ├── expedition.py         <- world-to-scene assembly and player controls
│   ├── harness.py            <- deterministic JSON action harness
│   ├── app.py                <- engine loop, input and screenshot capture
│   ├── demo.py               <- original showcase scene
│   ├── procedural/
│   │   ├── __init__.py
│   │   ├── noise.py          <- deterministic value noise and FBM
│   │   ├── terrain.py        <- island heightfield, biome colors and mesh
│   │   └── dungeon.py        <- rooms, corridors, FOV and BFS
│   ├── sim/
│   │   ├── __init__.py
│   │   └── world.py          <- deterministic state, collision, modes, hash
│   └── gpu/
│       ├── __init__.py       <- GPU adapter package marker
│       ├── context.py        <- GLFW window and OpenGL 3.3 context
│       ├── shader.py         <- GLSL compilation and uniform upload
│       ├── mesh_buffer.py    <- VAO/VBO/EBO upload and drawing
│       └── renderer.py       <- forward renderer, sky, lights, readback
├── assets/
│   ├── octahedron.obj        <- sample OBJ asset
│   ├── screenshot.png        <- showcase scene capture
│   ├── expedition.png        <- expedition overworld capture
│   ├── dungeon.png           <- generated crypt capture
│   └── combat.png            <- enemy pack capture
├── tests/
│   ├── test_math3d.py        <- math core
│   ├── test_scene.py         <- hierarchy, camera and lights
│   ├── test_geometry.py      <- meshes, primitives, builder and OBJ
│   ├── test_png.py           <- PNG writer
│   ├── test_renderer.py      <- headless OpenGL integration
│   ├── test_procedural.py    <- noise, terrain and atmosphere
│   ├── test_dungeon.py       <- dungeon, FOV and pathfinding
│   ├── test_combat.py        <- archetypes, waves, damage and boss
│   ├── test_world.py         <- deterministic state, movement and modes
│   ├── test_expedition.py    <- scene assembly and scene transitions
│   ├── test_harness.py       <- AI harness API and CLI
│   └── test_app.py           <- engine loop, demo and CLI
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

### Frame flow

```text
Engine.run
  -> poll GLFW events and resize the framebuffer
  -> Expedition.handle_input: keyboard + captured mouse -> MoveIntent
  -> Expedition.update
       -> World.step: time, turn, collision, portal/exit interaction
       -> rebuild scene only when mode changes
       -> Atmosphere.at(day_fraction): sky, horizon, ambient, directional light
       -> camera follows the player eye
  -> Renderer.render
       -> sky pass (full-screen triangle, depth writes off)
       -> scene pass (terrain, water, batched trees/rocks/path, portal or crypt)
  -> swap buffers (visible window only)
```

## 🧩 Extending the Engine

Add a mesh to any scene with a transform and a material:

```python
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.obj_loader import load_obj
from keystone.scene import Node, Scene, Transform

scene = Scene()
scene.camera.position = Vec3(0.0, 2.0, 6.0)
scene.camera.look_at(Vec3(0.0, 0.5, 0.0))
scene.add(
    Node(
        "artifact",
        Transform(position=Vec3(0.0, 0.8, 0.0), scale=Vec3(0.7, 0.7, 0.7)),
        mesh=load_obj("assets/octahedron.obj"),
        material=Material(color=Vec3(0.9, 0.7, 0.2), shininess=96.0),
    )
)
```

`MeshData` carries positions, normals, optional UVs, triangle indices and optional vertex colors; the GPU uploads it once and caches it by identity. `MeshBuilder` merges static geometry, which is how the 90 trees and the path become four draw calls.

## 🧬 Lineage & Licensing

Keystone's first implementation was built in this workspace. The seeded expedition deliberately reuses **algorithms and design patterns** from sibling AegeanWorks projects:

- **Aldervale** — integer-hash value noise/FBM, island heightfield, biome color palette, day/night atmosphere model, mesh-builder primitives.
- **Crypt-Crawler** — room-and-corridor generation, symmetric-raycast FOV, BFS pathfinding and the deterministic JSON harness pattern.
- **Dustline** — streaming-world collision ideas (circle/box separation and segment blocking), enemy archetype/wave/boss structure and combat pacing.

These were reimplemented as modular Python; no AGL-licensed assets or source files were copied into this repository. See ADR-006 for the provenance decision. Keystone itself remains under the Aegean License 1.1 (AL-1.1).

## 🗺️ Roadmap

1. Shadow maps and a second point light for the crypt.
2. PBR materials, textures and sRGB color management.
3. Weather (rain/snow particles) and a wind-driven foliage animation.
4. Weapons/upgrades, champion affixes and loot using the wider Dustline tables.
5. Save/load of the seed + action log, and a rewind/debug viewer.
6. glTF/scene import and an editor with gizmos.

## 🤖 AIKit Integration

- `.aikit/project.json` declares `mechanics.core` (simulation, terrain, dungeon, combat, expedition, renderer, harness) and `mechanics.test` (`python -m keystone.harness selftest`), so an agent exercises the same headless core.
- `.aikit/task_ledger.json` records plans, checkpoints and handoff state; resume with `python aikit.py resume keystone`.
- `.aikit/decisions.md` records ADR-001 through ADR-006.
- `python aikit.py check keystone` is the Phase 4 gate: tests, lint, mechanics, hygiene, guidelines and secret scan. It never pushes; delivery is opt-in.

## 📜 License

Free for personal use under the Aegean License 1.1 (AL-1.1); see [LICENSE](LICENSE). Any commercial use needs the Aegean Commercial License 1.0 (ACL-1.0); see [COMMERCIAL.md](COMMERCIAL.md).
