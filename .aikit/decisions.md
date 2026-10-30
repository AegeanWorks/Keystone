# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

<!-- Entry format:
### ADR-NNN: <decision in one line>
- **Date**: YYYY-MM-DD
- **Status**: Accepted
- **Context**: <what forced the decision>
- **Decision**: <what was decided>
- **Consequences**: <what follows, including what it costs>
-->

### ADR-001: Render on the GPU with OpenGL 3.3 core

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The request was a performance-first 3D engine. This machine has a working OpenGL 3.3 core driver but no Rust or C/C++ toolchain, and a CPU Python rasterizer would not meet the performance goal.
- **Decision**: Use GLFW for the window/context and PyOpenGL for a GLSL 330 pipeline. Keep the renderer behind `keystone/gpu/` so a different graphics API can be added without changing scene or geometry code.
- **Consequences**: Real GPU rasterization and interactive frame rates without a native build step. The project requires an OpenGL 3.3 driver; machines without one fail at startup with a `Why:`/`Fix:` message. GLFW and PyOpenGL are declared dependencies.

### ADR-002: Keep the engine core Python-only and column-major

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The engine must be readable, testable and fast enough for the demo without a compiler. The renderer needs matrix data in the layout OpenGL consumes.
- **Decision**: Implement math, scene, geometry and asset loading in pure Python, with `numpy` only at the GPU buffer boundary. Store `Mat4` column-major and expose `flat()` for direct uniform upload; keep vectors and transforms immutable.
- **Consequences**: No C extension or native build, and tests run with the standard Python toolchain. Per-object Python work remains the scaling limit for very large scenes; batching and instancing are future work.

### ADR-003: Verify rendering headlessly and cache GPU buffers by mesh identity

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Agents and CI cannot rely on a visible window or a human looking at the screen, yet renderer regressions must be caught. Re-uploading static meshes every frame would waste bandwidth.
- **Decision**: Create a hidden GLFW window for integration tests, read pixels with `glReadPixels`, and write PNG frames with a stdlib writer. Upload each immutable `MeshData` once into a VAO/VBO/EBO and cache it by identity in `Renderer`.
- **Consequences**: Renderer behaviour is observable in automated tests and screenshots, and static geometry has no per-frame upload cost. Tests require a machine with an OpenGL 3.3 context; the dependency is documented in the README.

### ADR-004: Make a deterministic seeded expedition the engine core

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Rendering alone did not make Keystone a game engine. Sibling projects already prove procedural worlds, seeded replay and AI-addressable simulation; the engine needed one loop that binds them and runs without a GPU.
- **Decision**: `keystone.sim.World` owns seed, time, player, terrain, dungeon, movement, mode transitions and `state_hash()`. It imports no OpenGL. `keystone.expedition.Expedition` is the view/adapter that rebuilds a `Scene` on mode changes; `keystone.harness` drives the same world from JSON actions.
- **Consequences**: The same run can be rendered, replayed headlessly or hashed in tests. Terrain, dungeon, collision and atmosphere become reusable systems rather than demo code. The simulation contract must stay stable; changing generation or movement changes replay hashes and needs an ADR.

### ADR-005: Add vertex colors, static batching and a local point light

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Procedural terrain needs per-vertex biome colors; a forest of individual nodes would cost one draw call per tree; the enclosed crypt needs a local light source.
- **Decision**: `MeshData` gains optional per-vertex RGB (11 floats per interleaved vertex). `MeshBuilder.add_mesh` merges primitives into a single indexed mesh. `Scene.point_light` adds one optional warm point light with quadratic falloff, used as the player torch in the dungeon.
- **Consequences**: The GPU layout and shader gain a color attribute and point-light uniforms; all existing meshes default to white vertex colors. The expedition renders in about ten draw calls. Only one point light is supported per scene; multiple lights need a future lighting pass.

### ADR-006: Extract algorithms, not AGL source, into the AL-1.1 engine

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Several sibling games contributed proven algorithms, but they are AGL-1.1 projects while Keystone is AL-1.1 software.
- **Decision**: Reimplement the useful algorithms as new modular Python (FBM/heightfield/atmosphere from Aldervale, room/corridor/FOV/BFS and harness shape from Crypt-Crawler, collision ideas from Dustline). Do not copy AGL source files or assets. Credit the sources in the README and record any future direct reuse in a new ADR after a license review.
- **Consequences**: Provenance is explicit and the engine stays under AL-1.1. Direct code or asset reuse remains a deliberate, reviewed action rather than an accident of porting.

### ADR-007: Combat is a deterministic core mechanic, not a separate mode

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The seeded expedition had exploration and collision but no threat, fail state or reason to move. Dustline already proves an archetype/wave/boss model that suits the existing auto-render loop.
- **Decision**: Add `keystone.combat.Combat` to `World`: seeded enemy spawns, six archetypes, contact damage, split-on-death, bomber detonation, auto-fire hitscan, escalating waves, a Warlord every fifth wave, player death and safe-point respawn. Combat is GL-free and included in `World.snapshot()` and `state_hash()`. Enemies are rendered as primitive nodes; HP/wave/kills appear in the window title.
- **Consequences**: The core loop gains a fail state and combat state becomes part of replay hashes. Balance edits that change spawns or damage change hashes and need the harness selftest updated. No HUD yet, and only one weapon; weapons, upgrades, affixes and loot remain future work.

### ADR-008: Gate the crypt with a deterministic light lock

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The portal opened unconditionally, so the new world had no spatial puzzle and Iris's beam mechanic was unused. A full 3D light simulation would be larger than the core loop needs.
- **Decision**: Add `keystone.beams.LightLock`: a seeded 2D circuit at the portal with a red emitter, green dye, two `/` or `\` mirrors, a yellow (red+green) receiver, additive color masks, cycle-safe tracing and a solved state. `World` gates portal entry on it, rotates the nearest mirror with `E`, and includes its snapshot in the replay hash. `Expedition` renders the circuit and rebuilds it when the mirror version changes.
- **Consequences**: The crypt is now locked by a solvable puzzle; the harness gains a `rotate` action and `light_lock` state. The puzzle is local to the portal and not yet a full chamber system; lenses, movable emitters and in-dungeon locks are future work. Changing the layout or initial orientations changes replay hashes.

### ADR-009: Add a Weft-style Hamiltonian room-chain layout

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The crypt's rooms-and-corridors layout was the only dungeon topology. Weft's Hamiltonian route generator guarantees full coverage and offers a visibly different, deterministic layout that fits the existing `Dungeon` interface.
- **Decision**: Add `keystone.procedural.weave.WeaveLayout`: a 4×3 Hamiltonian room path with Warnsdorff ordering and connectivity checks, cut into three colored thread segments, expanded into 7×7 rooms joined by corridors. `World(layout=auto)` chooses weave for even seeds and crypt for odd seeds; `crypt`/`weave` force one. Room floors carry the thread color and `World.snapshot()` includes the weave path/segments.
- **Consequences**: The engine now has two deterministic dungeon topologies and the CLI/harness expose `--layout`. Changing the grid, room size or path changes hashes and screenshots. The weave is a chain, not a loop or branch graph; those remain future work.

### ADR-010: Make the cyber network the dungeon objective

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The dungeon exit opened unconditionally once the light lock was solved, so the crypt had no infiltration objective and Cyberpulse's network/living-alert model was unused.
- **Decision**: Add `keystone.procedural.network.Network`: a seeded graph of four terminal rooms selected from reachable non-spawn/non-exit rooms, a deterministic link tree plus one extra link, four-step hacks, alert gain/decay and a hunter response at 50+ alert. The exit is sealed until every terminal is hacked. Terminals and links render in the dungeon; network state is included in `World.snapshot()` and `state_hash()`.
- **Consequences**: A dungeon run now has an objective beyond survival and navigation; hacking creates risk and combat pressure. Terminal count/link topology changes hashes and screenshots. The current hack is a progress counter, not Cyberpulse's frequency/buffer/hash puzzle variants; those remain future work.

### ADR-011: Add a free-flight space survey as the second playable mode

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Keystone only had the ground expedition. VoidFarer already proves procedural systems, orbiting bodies, hyperlane connectivity and a scan/survey loop; a self-contained mode would prove the engine is not tied to one game.
- **Decision**: Add `keystone.procedural.space` for deterministic six-system galaxies, `keystone.space.SpaceWorld` for free flight, body scans, survey completion and gate jumps, and `keystone.space_expedition.SpaceExpedition` for the starfield/planet/gate scene and controls. `--space` selects the mode; `keystone.space_harness` exposes catalog/run/selftest without a GPU.
- **Consequences**: Keystone has two independent playable modes and two headless harnesses. Space has no combat, trade or multi-ship systems yet; those are future work. Orbit phases, scan state, ship position and system links are part of the space replay hash.

### ADR-012: Separate the engine core from game modules and freeze genre work

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Combat, light locks, weave layouts, cyber networks and the space survey were built beside the renderer and math but treated as engine mechanics. They are games built on the engine, and the core still lacks a game-agnostic module contract, generic input/replay, physics, assets, audio and serialization.
- **Decision**: Freeze genre feature work. Define `keystone/` as core only and `games/` as optional examples/modules. Introduce a five-operation `GameModule` protocol, `ActionState`, a game registry and a game-agnostic `Engine`; core must never import `games.*`. Preserve the current features by moving them to `games/expedition`, `games/space` and `games/showcase` after this document is reviewed. The full boundary, inventory, dependency rules, module roadmap and staged refactor sequence are in `docs/ARCHITECTURE.md`.
- **Consequences**: No new genre modules until the core split is accepted. The current v0.7.0 tree keeps running during review; the next work is the boundary refactor, then real core systems (physics, assets/serialization, scene/ECS, renderer, input/audio, tooling). Existing replay hashes and screenshots may change when modules move.

### ADR-013: Remove the genre prototypes and ship a core-only engine

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The user rejected the game mechanics as engine core and directed a game-agnostic engine with the prototypes removed. ADR-012 described the split; this ADR executes it.
- **Decision**: Delete the expedition, combat, light-lock, weave, network, space and showcase modules, their tests and screenshots. Keep a game-agnostic core with a five-operation `GameModule` protocol, a generic `Engine`, `ActionState`/`InputMap`, `FixedStepClock`, collision primitives, `CommandLog`/`stable_hash`, atomic JSON persistence and the `CubeDemo` smoke test. External games load through `--game package.module:Factory`.
- **Consequences**: v0.8.0 is much smaller and contains no genre rules. The deleted prototypes remain in git history but are not part of the package. The engine now has a real core API to extend; physics, assets, audio, ECS and tooling remain roadmap items.

### ADR-014: Add a no-OpenGL simulation path and machine-readable frame reports

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: AIKit, CI and AI model tooling need to drive and inspect the engine without a desktop window or GPU. A PNG alone is not enough for a model to reason about scene layout, and creating an OpenGL context on every test host is fragile.
- **Decision**: Add `keystone.headless.run_simulation()` and `load_actions()` to apply JSON action scripts directly to a `GameModule` with no GL context. Add `keystone.analysis.analyze_frame()` and `Engine.capture()` to emit a schema-1 JSON report beside a PNG: image hashes, mean/luminance statistics, content bounding box, dominant colors, an 8×8 luminance grid, projected screen positions and mesh bounding boxes for every scene node. CLI gains `--simulate`, `--actions`, `--trace`, and `--report`.
- **Consequences**: CI and AI tests can run game logic on GPU-less hosts through `--simulate`; rendered reports still require OpenGL. The report schema is versioned (`schema: 1`) and stable action/snapshot hashes make model-driven regressions reproducible. Pixel statistics are descriptive, not a visual-quality metric.

### ADR-015: Add discovery, deterministic test helpers and report comparison

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: A headless command and a single frame report are not enough for an AI client: it must discover the action/snapshot contract, assert a scenario is deterministic, and compare a baseline against a new frame. Without a stable contract those steps become ad-hoc scripts.
- **Decision**: Add `describe_game()` and `--describe` for capability/action/snapshot discovery; `keystone.testing.run_script()`, `verify_determinism()` and `assert_deterministic()` for deterministic scenarios; and `analysis.compare_reports()` for image/report/stat/node diffs. All are core, GL-free where possible, and versioned separately from a game's own actions.
- **Consequences**: AI clients have a discovery → simulate → verify → render → compare loop with JSON evidence. Reports remain descriptive rather than aesthetic judgments, and games still own their action semantics.

### ADR-016: Make verification and baseline comparison first-class CLI workflows

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: `keystone.testing` and `compare_reports()` were library-only, forcing an AI client to write Python wrappers for the two most common checks: repeat a scenario deterministically and gate a frame against a baseline.
- **Decision**: Add `--verify-determinism` (no GL, two runs, exit 0 only on matching hashes) and `--compare-baseline` (requires `--headless` and `--report`, prints image/stat/node diff, exits non-zero on image change). Publish `REPORT_SCHEMA` through `describe_game()`/`--describe`.
- **Consequences**: AI/CI clients get direct exit-code gates and schema discovery. Visual comparison is image-hash first; descriptive statistics and node changes are evidence, not aesthetic judgment.

### ADR-017: Support explicit expected-hash gates and an AI workflow guide

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Determinism was checkable by running twice, but an AI client also needs to pin a known-good result and fail on drift in one command. The workflow was spread across README sections.
- **Decision**: Add `--expect-hash <32-hex>` to `--simulate` and `--verify-determinism`; mismatches return 1 and include `expected_hash`. Add `docs/AI_GUIDE.md` covering discovery, simulation, hash pinning, rendering, reports and baseline comparison.
- **Consequences**: A model can gate a known outcome directly. Expected hashes are explicit operator input, never silently refreshed; changing game behavior requires updating the pin deliberately.

### ADR-018: Add a dependency-free PNG reader and visual pixel diff

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The report comparison could say that an image changed, but an AI or human reviewer had no pixel-level artifact or changed-region evidence.
- **Decision**: Add `png.read_png()` for 8-bit RGBA non-interlaced PNGs (all PNG filters), and `analysis.diff_images()` to compare two PNGs, write a visual diff, and report changed pixels/ratio, bbox, mean/max channel delta. Wire `--diff-out` into `--compare-baseline`.
- **Consequences**: Baseline checks now produce both JSON and a diff image without third-party imaging libraries. The reader intentionally supports only RGBA 8-bit non-interlaced files; other PNG variants fail with a clear error.

### ADR-019: Give the human runtime a first-class, game-agnostic HUD

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The engine had become excellent for AI clients but a person launching the window had no in-engine HUD, control reference or pause feedback; the title bar was the only status surface.
- **Decision**: Add `keystone.ui` (embedded 5×7 bitmap font, clipped `Canvas`, `HumanOverlay`/`HudState`) and `gpu.ui_renderer.UiRenderer` for one alpha-blended screen-space draw. The Engine draws the overlay after the 3D scene, toggles it with `H`, pauses gameplay with `P` without stopping rendering, and exposes `--ui`/`--no-ui`. Windowed runs default to UI on; headless captures default to off so existing report hashes and baselines stay stable.
- **Consequences**: People get a readable HUD, controls help and pause banner with no font/asset dependency. The overlay is presentation-only and never mutates game state. UI pixels are included in `--ui` reports, so UI screenshots can be reviewed by the same report/diff workflow; `--no-ui` preserves clean scene captures.

### ADR-020: Make the pause menu interactive with mouse and keyboard

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The human overlay displayed a pause banner but offered no actions; a person still had to remember `P` to resume and `Esc` to quit, and there was no clickable UI or reusable menu state for games.
- **Decision**: Add a pure `PauseMenu` (Resume / Hide HUD / Quit), draw hit-testable buttons with selected and hover states, add a one-frame `ActionState.mouse_clicked` edge, bind `Enter` to `confirm`, release the cursor while paused, and expose `Engine.apply_ui_action()` for scripted use. `W`/`S` or arrows move the selection.
- **Consequences**: Pausing now opens a real menu that works by mouse or keyboard; resuming recaptures the cursor. `mouse_clicked` defaults to false so existing action scripts stay valid. Menu selection and hitboxes are presentation state only; games remain unaware of the overlay.

### ADR-021: Let games contribute HUD pixels through an optional hook

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The human overlay showed engine/runtime information, but an external game had no supported way to draw its own health, score or panels; it would have needed to fork the engine or draw 3D proxies.
- **Decision**: If a game exposes a callable `draw_ui(canvas, state)`, the Engine passes it to the overlay builder, which calls it before drawing the engine HUD and pause menu. The hook receives the same `Canvas` and `HudState` used by the HUD and is skipped when the overlay is hidden or UI is disabled. `describe_game()` reports `capabilities.game_ui`.
- **Consequences**: Games can add HUD pixels with the dependency-free font/canvas toolkit while the required five-operation contract stays unchanged. The hook is presentation-only and receives no input dispatch; game UI participates in `--ui` captures and report/diff workflows like any other pixel.

### ADR-022: Capture structured UI metadata in schema-2 frame reports

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The human UI was visible in PNGs, but an AI reading a frame report could not tell which labels and buttons were on screen, which menu item was selected, or whether the game was paused; UI regressions were only pixel diffs.
- **Decision**: Record `TextElement`/`ButtonElement` metadata on the `Canvas`, add `ui.report.describe_canvas()`, and include an optional `ui` object in the frame report: visibility, pause state, labels with text/position/scale/color and buttons with label/action/rect/selected/hovered. Bump the report schema to 2; include `ui` in the report hash only when present; diff UI labels/buttons in `compare_reports()`; accept schema-1 reports as baselines. Add `--start-paused` so the pause menu can be captured headlessly.
- **Consequences**: AI and human reviewers get structural UI evidence alongside pixels. `--no-ui` reports keep `ui: null` and their old hash behavior; schema-1 baselines remain comparable. UI metadata is presentation-only, and volatile labels (FPS/time) make deterministic headless captures the reliable baseline.
