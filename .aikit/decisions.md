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

### ADR-023: Add immutable RGBA textures and material texture metadata

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: `MeshData` carried UVs and primitives filled them, but the renderer ignored them; materials had only a flat color and a world-space checker. Textured surfaces are a basic 3D engine capability, and AI graphics reports could not identify which texture a node used.
- **Decision**: Add immutable `TextureData` (RGBA8, PNG and procedural checker sources), `Material.texture`, a renderer-owned `GpuTexture` cache with repeat wrapping and mipmaps, and GLSL texture sampling multiplied into the base color. Use a checker texture on the sample floor. Report material color/specular/shininess/checker and texture name/dimensions/SHA-256; bump the report schema to 3 and accept schema 1/2 baselines.
- **Consequences**: Games get textured materials with no new dependency beyond the existing PNG reader and PyOpenGL. Textures are opaque (alpha is not blended), one sampler per material, and color management stays linear/untagged. The renderer releases cached textures with meshes; `compare_reports()` flags material changes on a node.

### ADR-024: Give scene nodes stable IDs, tags, layers and typed components

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Nodes were addressable only by name, so two nodes with the same name could not be distinguished, and the engine had no game-agnostic way to attach behaviour or query entities. AI frame reports keyed nodes by that colliding name.
- **Decision**: Add optional `Node.id`, `tags`, `layer` and typed `components` with add/get/require/remove helpers. `Scene` allocates deterministic per-scene IDs (`node-1`, `node-2`, ...) on attach or first traversal, preserves explicit IDs, rejects duplicates, and keeps an ID across reparenting. Add `Scene.query()`, `Scene.find()` and `Scene.find_by_id()`. Bump the frame report schema to 4 with `id`, `parent_id`, `tags`, `layer` and component names; `compare_reports()` keys nodes by ID only when both reports are schema 4, and keeps name keying for older baselines. The sample uses explicit IDs.
- **Consequences**: Games can address, tag and query nodes without a name collision, and AI diffs can distinguish duplicate names. Auto IDs depend on attach/traversal order and are scene-local, not a cross-process save format; a future serialized scene must persist assigned IDs. Queries are linear scans, and the report hash changes for schema 4.

### ADR-025: Add a local web console, JSON API and WebGL2 scene viewer

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: The AI surface was CLI-only and the human surface was a desktop window. AI clients and browser users could not inspect the same game contract, scene state or deterministic simulation over a local interface.
- **Decision**: Add `keystone.web` with a versioned scene document (schema 1), a stdlib `ThreadingHTTPServer` and a vanilla web console. Endpoints are `GET /api`, `GET /api/health`, `GET /api/describe`, `GET /api/scene` and `POST /api/simulate`; responses reuse `describe_game()`, `run_simulation()` and the scene export. Add `--serve`, `--host` and `--port`. The console has a WebGL2 viewer for shared meshes, RGBA textures, camera, lights and fog, and CORS headers for local clients.
- **Consequences**: AI clients and the bundled browser UI share one JSON contract without a new runtime dependency or a server GPU requirement. The server binds to loopback by default and is not an internet service; simulation mutates one in-memory game behind a lock. The WebGL preview is approximate, while the OpenGL renderer remains the pixel authority. The static assets are package data, so a source checkout and an installed wheel both serve the console.

### ADR-026: Add broadphase, character movement, triggers and filtered raycasts

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Physics stopped at individual ray and overlap queries. Games had to scan every collider, reimplement character movement, and hand-roll trigger state; none of those are genre rules, so they belong in the core.
- **Decision**: Add `keystone.broadphase.SpatialGrid` (uniform grid, exact overlap filtering, insertion-order results), `keystone.character.CharacterBody`/`CharacterController` (AABB body, horizontal wish velocity, gravity, swept axis resolution, ground state), `keystone.triggers.TriggerVolume`/`TriggerTracker` (sorted enter/exit/active events), and `AABB.low/high/contains/overlaps` plus `RayHit`/`raycast()` with an optional key/box predicate. Keep all state caller-owned and GL-free.
- **Consequences**: Games get deterministic nearby-body queries, reusable character movement and trigger reactions without a genre contract. The controller covers axis-aligned static colliders only; slopes, step-up, moving platforms, capsules and a physics solver remain future work. Cell size controls broadphase performance, never correctness, and trigger tracker state is mutable by design.

### ADR-027: Add the asset registry and hot reload

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Meshes, materials and textures were anonymous objects passed straight to nodes, so games could not address, deduplicate, inspect or refresh them. The roadmap's asset step needed a game-agnostic registry and a deterministic hot-reload path before material graphs and glTF import.
- **Decision**:
  1. Add `keystone.assets` with `AssetRegistry`, `AssetRecord` and `ASSET_KINDS`. Kinds are inferred from `MeshData`, `Material` and `TextureData`, with explicit kind validation, id and dependency validation, stable content digests, duplicate groups, missing-dependency reports and a JSON-safe `describe()`.
  2. Add `keystone.asset_io` with `AssetSource`, `Fingerprint`, `ReloadReport`, default PNG and OBJ loaders, suffix-based kind inference, `load_asset` and `fingerprint`. `register_file` loads a source and binds it; `refresh()` re-reads changed files, keeps the last good payload on a loader failure or a missing file, reports persistent errors, and preserves dependencies.
  3. Export `AssetRegistry` from the package and wire `CubeDemo` through the registry so the smoke test proves asset identity.
- **Consequences**: Games get stable asset ids, content hashes, dependency tracking and synchronous hot reload with no new dependencies or background thread. Broken or missing files surface in `ReloadReport` instead of crashing the render loop. Material graphs and glTF import remain future work.

### ADR-028: Add declarative material graphs

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Materials were literal `Material` values, so reusable procedural surfaces, texture references and mixes had to be rebuilt by hand in every game and could not be serialized or inspected by AI clients.
- **Decision**:
  1. Add `keystone.material_graph` with `MaterialGraphNode` and `MaterialGraph`. Node kinds are `color`, `float`, `checker`, `texture`, `mix` and `material`; inputs form a directed graph evaluated in topological order with cycle detection.
  2. Parameters are frozen `(name, value)` pairs and graphs serialize to schema-1 JSON with `to_dict()`/`from_dict()`, keeping `Vec3` as channel arrays and parameters as JSON values.
  3. `evaluate(textures=..., registry=...)` resolves color, checker and texture nodes, including asset ids through an `AssetRegistry`, and returns one `Material`.
- **Consequences**: Games and AI clients can build, serialize, inspect and evaluate materials without OpenGL. Graphs are immutable and deterministic; texture payloads are referenced by asset id or name rather than embedded. Material graphs do not change the report schema or the renderer contract.

### ADR-029: Add dependency-free glTF 2.0 import

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Keystone could load OBJ and PNG assets but had no path for modern glTF scenes, so AI and game authors had to convert assets or hand-build meshes. A glTF importer must not add a runtime dependency or require OpenGL.
- **Decision**:
  1. Add `keystone.gltf` as a package with `io`, `textures`, `materials`, `meshes`, `scene` and `loader` modules. `load_gltf(source, registry=None)` accepts a path, JSON text, bytes or an already-parsed mapping and returns a `GltfImport`.
  2. Decode external and embedded base64 buffers, typed accessors (SCALAR/VEC2/VEC3/VEC4/MAT4), meshes with optional normals/UVs/colors/indices, PBR materials (base color, roughness to specular/shininess, base color texture), PNG images and node/scene hierarchies with TRS or matrix transforms.
  3. Reuse `TextureData.from_png_bytes`, `MeshData`, `Material` and `Scene`, and optionally register imported assets in an `AssetRegistry`.
- **Consequences**: Games and AI clients can import glTF 2.0 scenes without new dependencies or a GPU. JPEG images, animations, skins, morph targets and multi-primitive mesh splitting beyond the first primitive remain future work. Matrix decomposition assumes affine transforms with non-zero scale.

### ADR-030: Add versioned scene snapshots and undo/redo history

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: The engine had no way to save, restore or roll back a scene graph without OpenGL or a game-specific serializer, and replay/inspection workflows need deterministic state checkpoints.
- **Decision**:
  1. Add `keystone.history.History`, a bounded undo/redo stack that deep-copies snapshots and reports `can_undo`/`can_redo`.
  2. Add `keystone.scene_snapshot` with `SCENE_SNAPSHOT_VERSION = 1`, `scene_to_dict` and `scene_from_dict`. Snapshots store node identity, hierarchy, tags, layer, visibility, transforms and camera state, plus mesh/material asset ids when an `AssetRegistry` is supplied.
  3. Rebuild parents through `Node.add_child`, validate the snapshot version and reattach assets from the registry on load.
- **Consequences**: Games and AI clients can save, restore and roll back scene graphs without OpenGL or a GPU. Mesh and material payloads are referenced by asset id rather than embedded, so a snapshot is small and a missing asset leaves the node without that payload. Undo/redo state is caller-owned and in memory.

### ADR-031: Harden glTF import and scene snapshot correctness

- **Date**: 2026-11-01
- **Status**: Accepted
- **Context**: Review of the v0.23-v0.25 additions found silent correctness failures. Generated glTF normals followed vertex order instead of triangle indices, non-triangle primitive modes were treated as triangles, cyclic node hierarchies recursed until `RecursionError`, normalized integer accessors returned raw byte values, sparse accessors decoded as zeros, snapshots dropped lighting and atmosphere, and snapshot loaders accepted duplicate ids and dangling parents.
- **Decision**:
  1. Decode indices before normals and generate normals from the actual triangle list; reject primitive modes other than TRIANGLES and reject unknown material indices.
  2. Apply glTF normalization rules to signed and unsigned integer accessors and refuse sparse accessors with a clear error instead of returning base or zero data.
  3. Track visiting nodes during hierarchy construction so a cycle raises `ValueError`.
  4. Extend scene snapshot schema 1 with optional camera lens and environment fields (ambient, background, sky, fog, directional and point lights) and reject duplicate ids, unknown parents and self-parenting. Older schema-1 documents still load with engine defaults.
  5. Make a material graph's `texture_name` fail when it cannot resolve, matching texture nodes.
- **Consequences**: Malformed or unsupported glTF and snapshot documents fail early with actionable errors instead of producing wrong geometry or state. Snapshots round-trip the visible environment, and schema 1 stays backwards compatible because every new field is optional.

### ADR-032: Add GLB containers and tighten glTF and snapshot validation

- **Date**: 2026-11-01
- **Status**: Accepted
- **Context**: A second review of the v0.25.1 format work found that binary `.glb` files failed as invalid UTF-8 JSON, out-of-range material texture indices were silently ignored, accessor offsets and bufferView bounds were not checked, snapshots could attach a material asset as a node mesh, non-string ids were coerced, and asset lookup scanned the whole registry once per distinct payload.
- **Decision**:
  1. Parse GLB version 2 headers and chunks in `keystone.gltf.io`, feed the first buffer without a uri from the BIN chunk, and reject truncated containers, wrong versions, duplicate JSON chunks and invalid buffer lengths.
  2. Validate accessor and bufferView offsets against the declared bufferView byteLength and reject material texture indices that do not resolve.
  3. Require string snapshot node ids, reject non-mapping camera and transform fields, validate asset kinds on reattachment, and build one payload-to-id index per snapshot instead of scanning the registry per node.
- **Consequences**: Standard GLB bundles import through the same path as JSON glTF. Malformed glTF and snapshot documents fail with precise errors instead of silently losing textures or attaching the wrong payload. Snapshot schema 1 is unchanged; only validation is stricter and serialization is linear in registry size.

### ADR-033: Add GPU hardware instancing for repeated static geometry

- **Date**: 2026-11-02
- **Status**: Accepted
- **Context**: Static batch merging baked still geometry into one mesh, but repeated rigid nodes (including moving ones sharing a mesh/material) still cost one GL draw call each. Draw-call count limited scene scale while pixels stayed identical.
- **Decision**: Add `keystone/gpu/instancing.py` with deterministic `group_instances()`/`plan_instanced()` grouping by identical mesh/material payloads, an instanced vertex shader with per-instance model/normal divisor attributes, and a renderer path issuing one `glDrawElementsInstanced` per multi-node group. Single-node groups keep the uniform path. Expose counts via `last_stats`, `/api/inspector` and `capabilities.instancing`. Frame report schema stays at 5.
- **Consequences**: Repeated meshes render with fewer draw calls and identical pixels; CubeDemo keeps 5 plain draws while a 200-cube test scene collapses to 1 call. Single-instance fallback avoids divisor state leaks. Report hashes and simulation hashes are unchanged. Shadows, post-processing, skinning and editor work remain future.

### ADR-034: Add the seeded bot playtester as first-class engine tooling

- **Date**: 2026-11-02
- **Status**: Accepted
- **Context**: `--simulate` replayed fixed action scripts, so an AI client could not bot-play a game end to end, diff a bot run against a pinned baseline, or ask the engine whether a configuration is winnable at all. Each check was an ad-hoc script with its own hash semantics.
- **Decision**:
  1. Add `keystone.playtest` with a `BotPolicy` protocol (`reset`/`select` over snapshots, action specs and a private `random.Random`) plus `RandomPolicy`, lookahead-free bandit `GreedyPolicy` and `ScriptedPolicy`. `run_bot()` records a schema-1 transcript wrapping the exact `CommandLog` shape, so `--expect-hash` pins it and `--replay`/`run_log` replay it with the same `stable_hash(final)`.
  2. Add `diff_transcripts()` (hash fast-path, first-divergent-frame walk on traced runs), frozen schema-1 `make_report()` shared byte-identically with thin web adapters (`POST /api/simulate` plus the same policy/seed envelope; no browser driving), and canonical `canon()` projection (drops `time`, rounds floats) for visited-sets.
  3. Add `validate_fairness()` with a defined rejection predicate: `unfair` only for spawn-terminal, nondeterministic, no-witnessed-win-with-reference, or reference-longer-than-time-limit runs; `fair` requires a deterministic witnessed win; anything else (no outcome signal, no reference, exhausted state budget) is `unknown`, never a false `fair`. Games opt in via `outcome`/`score` snapshot keys; the five-operation contract is unchanged and `describe_game()` gains only the additive `capabilities.playtest` flag.
  4. Add `--playtest --policy {random,greedy,scripted} --seed --script --transcript-out` to the CLI (standalone no-GL command, wall-clock capped, unfair verdict exits 1). The proving stub is `tests/support_maze_game.py`, a deterministic grid fixture outside `keystone/` so the boundary test stays green; maze-exact BFS ground truth lives fixture-side, the core stays sampling-based.
- **Consequences**: Bot runs are deterministic first-class artifacts next to `--simulate`; unfair configurations are rejected with machine-readable reasons. Cost ceilings (`frames`, `max_wall_seconds`, `max_states`) bound every search; greedy lookahead and exhaustive game-tree search are explicitly deferred. Bumps version to 0.33.0.

### ADR-035: First screenshot keepers are the scripted HUD render and the live web console
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Keystone had approved cube/KE brand (6/6) but `assets/screenshots/` did not exist and `media.json screenshots: []`; the legacy `assets/engine.png` sample predates the bitmap-font HUD/profiler and carries no commit record.
- **Decision**: Keep `engine.png` as legacy art; register `2026-11-03-hud.png` (scripted `python -m keystone --headless --frames 1 --size 960x540 --ui --out`, commit `e6c6318`, deterministic) and `2026-11-03-console.png` (`python -m keystone --serve`, WebGL viewer, viewport 1440x900) in `.aikit/media.json` and the README `aegean:screenshots` block.
- **Consequences**: README proves both the headless and the served workflows against the documented cube-demo smoke test; the HUD render re-renders byte-identical on demand. Reproduce with the two commands above.

### ADR-036: Add deterministic directional shadow mapping to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer roadmap listed shadows as remaining; every game needs depth cueing but no game should implement its own light pass. The change must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.shadow` (`ShadowSettings.enabled`, default on) plus `keystone/gpu/shadow.py` (fixed 1024 depth FBO, ortho extent 12, near 1, far 40, bias 0.005, deterministic light VP). Render a depth-only pass reusing `group_instances()` ordering (one depth draw per instance; instanced divisor path deferred), then a PCF 3x3 lit pass. Gate with `--shadows/--no-shadows`; `--no-shadows` preserves legacy pixels. Bump frame report schema 5 to 6 with `scene.shadows`, add `capabilities.shadows`, persist optional `environment.shadow` in snapshot schema 1, export `shadows` in the web scene/inspector, and extend `last_stats` with `shadow_calls/shadow_map_size/shadows_enabled` plus a HUD `SHADOW N PASS` line.
- **Consequences**: CubeDemo renders with shadows by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because shadows never enter `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: scene draw calls unchanged, `shadow_calls <= 5` on CubeDemo, wall time `<=1.3x` no-shadow baseline. Post-processing, sRGB, skinning and GPU sprite work remain future.

### ADR-037: Add an sRGB-correct linear lighting pipeline to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer shaded and fogged raw sRGB bytes as if linear, so mid-tones were systematically dark; every game pays that error but no game should implement its own color pipeline. The fix must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.color` (`ColorSettings.enabled`, default on) plus in-shader `pow 2.2` decode/encode (no driver `GL_SRGB` dependency). Decode the combined `base_color`, ambient, light/point radiances, emissive and fog color, shade linear, fog in linear, encode the final color and the sky gradient; the UI overlay stays display-referred and unencoded. Gate with `--srgb/--no-srgb`; `--no-srgb` preserves legacy pixels. Bump frame report schema 6 to 7 with `scene.color`, add `capabilities.srgb`, persist optional `environment.color` in snapshot schema 1, export `color` in the web scene/inspector, and extend `last_stats` with `srgb_enabled`.
- **Consequences**: CubeDemo renders sRGB-correct by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because color never enters `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new draws or triangles, wall time `<=1.05x` no-sRGB baseline. Post-processing, skinning and GPU sprite work remain future.

### ADR-038: Add a deterministic post color-grade to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer stopped at sRGB encode, so every game shipped ungraded linear output with no vignette control; each game would otherwise hand-roll its own grade. The change must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.post` (`PostSettings.enabled`, default on) plus `keystone/gpu/post.py` (fixed exposure 1.12, vignette 0.28, GL-free `grade_color`/`vignette_factor`). Apply the grade in-shader after the sRGB encode (main pass via `gl_FragCoord`/`u_resolution`, sky via `v_uv`), before the UI overlay; no FBO, no new draws. Gate with `--post/--no-post`; `--no-post` preserves legacy pixels. Bump frame report schema 7 to 8 with `scene.post`, add `capabilities.post`, persist optional `environment.post` in snapshot schema 1, export `post` in the web scene/inspector, and extend `last_stats` with `post_enabled` plus a HUD `POST GRADE` line.
- **Consequences**: CubeDemo renders graded by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because post never enters `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new draws or triangles, wall time `<=1.02x` no-post baseline. Bloom, full post chain, skinning and GPU sprite work remain future.

### ADR-039: Add a deterministic bloom glow to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer stopped at exposure/vignette, so bright surfaces and emissive highlights had no glow and every game would hand-roll its own bloom; the change must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.bloom` (`BloomSettings.enabled`, default on) plus `keystone/gpu/bloom.py` (fixed threshold 0.72, knee 0.12, intensity 0.35, GL-free `bloom_factor`/`bloom_color` on display-referred luma). Apply the glow in-shader after the sRGB encode and before the post grade (main pass and sky via `v_uv`), before the UI overlay; no FBO, no blur pass, no new draws. Gate with `--bloom/--no-bloom`; `--no-bloom` preserves legacy pixels. Bump frame report schema 8 to 9 with `scene.bloom`, add `capabilities.bloom`, persist optional `environment.bloom` in snapshot schema 1, export `bloom` in the web scene/inspector, and extend `last_stats` with `bloom_enabled` plus a HUD `BLOOM GLOW` line.
- **Consequences**: CubeDemo renders with glow by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because bloom never enters `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new draws or triangles, wall time `<=1.05x` no-bloom baseline. Full blur/mip-chain bloom, skinning and GPU sprite work remain future.

### ADR-040: Add deterministic bloom diffusion to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The v0.37.0 threshold glow adds sparkle but no diffusion, so bright surfaces still lack Unity-class spread and games would hand-roll blur FBOs with divergent hashes.
- **Decision**: Keep `Scene.bloom.enabled` unchanged and add frozen diffusion in `gpu/bloom.py` (5-tap weights summing to 1.0, half-res `floor(w/2)` min 1, `bloom_composite`) plus `gpu/bloom_fbo.py` (RGBA8, NEAREST, CLAMP_TO_EDGE, completeness `Why:/Fix: --no-bloom`). When bloom is on, render the scene to a full-res FBO, run bright-pass downsample + separable H/V blur + composite to the default framebuffer; when off, keep the exact legacy direct-to-screen path. No CLI, snapshot, report-schema, web, or HUD changes; `last_stats` shape unchanged.
- **Consequences**: CubeDemo diffuses bright orb/cubes with `--no-bloom` byte-identical legacy; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged because diffusion never enters `snapshot()`. Perf budget: no new scene draws, wall `<=1.35x` no-bloom median; miss falls back to threshold-only. Skinning, GPU sprites, editor remain future.

### ADR-041: Add deterministic character slopes, step-up and platform carry
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The controller stopped at axis-aligned walls, so stairs blocked movement and platforms could not carry bodies without per-game teleports that bypass swept pushout and fork determinism.
- **Decision**: Extend frozen `CharacterController` with `slope_rise 0.55`, `slope_run 1.0`, `step_height 0.45` and `step(..., platform_velocity=None→zero)` (defaults preserve all 4-arg call sites). Fixed order: swept platform carry, X, Z, swept step-up probe (headroom, horizontal retry, settle, rise within `slope_rise*(run/slope_run+1)`), gravity Y. No new collider types (stairs, not ramps), no snapshot/report/CLI/web/GPU changes; character stays runtime-only and GL-free.
- **Consequences**: Low stairs climb, tall walls stop, carry respects walls and ledges; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged (CubeDemo never calls `step`). Perf budget: no-hit path unchanged, hit path ≤2 extra sweeps, `<=1.10x` over 10k steps/32 AABBs manual. Capsules, solvers, ladders remain future.

### ADR-042: Add deterministic particle-vs-AABB collision
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Particles fell through floors and tunneled walls, so every game hand-rolled FX collision with divergent results.
- **Decision**: Extend `ParticleSystem.step` with `step(dt, colliders=())` and a swept point-vs-AABB pass (X→Z→Y, caller list order, `POINT_SKIN 1e-9`), response stop-at-surface with hit-axis velocity zeroed and lifetime continuing; zero colliders runs the legacy code verbatim. No `Emitter`/`Particle`/`particles_report` changes (both schema 1 frozen), no snapshot/CLI/web/GPU changes; colliders are per-step args, never state.
- **Consequences**: Sparks rest on floors, fast shots stop at walls without tunneling; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged (CubeDemo uses no particles). Perf budget (measured, steady-state medians): `<=2.0x` stress (1k particles × 8 AABBs, observed ~1.8x) and `<=1.8x` typical (200 × 2, observed ~1.7x); zero-collider path is byte-identical legacy code. Bounce, friction, kill modes, GPU sprites and broadphase acceleration remain future.

### ADR-043: Add deterministic linear-blend skinning
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Every rigged character needs deformation, but the mesh core stopped at rigid bind poses, so games would hand-roll CPU skinning with divergent poses, hashes, and batching.
- **Decision**: Add optional skin data to `MeshData` (per-vertex joints/weights up to 4, joint names, inverse bind matrices; defaults preserve all legacy constructors and `interleaved()` bytes) plus `keystone/skin.py` (`bone_matrices` id-or-name resolution in joint order, `skin_point`/`skin_mesh` CPU oracle mirroring the vertex shader). GPU path: new `SkinnedGpuMesh` (19-float stride, attribs 11/12) + skinned vertex/depth programs (`u_bones[64]`, `vec4` joints) + per-model single draws; unskinned VAO/program/stride untouched. glTF: `JOINTS_0`/`WEIGHTS_0` + `skins` import with normalization and rejection rules. `plan_batches`/`merge_batches` auto-skip skinned meshes (like animated via `exclude`); `describe` gains `capabilities.skin`. No snapshot/report/CLI/web-schema changes: skin rides mesh assets, pose rides node transforms.
- **Consequences**: Rigged meshes deform deterministically on CPU and GPU with identical math; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged (CubeDemo unskinned). Perf budget: unskinned `<=1.02x` baseline, skinned `<=1.15x` equivalent verts. IK, dual quaternions, per-instance palettes, and skin-aware merging remain future. Deviations from Stage 2 mechanics: `batch.py` gained auto-skip (no `app.py` call site exists — `web/server.py` calls `merge_batches` without `exclude`); `set_mat4_array` added to `ShaderProgram` (array base location `u_bones[0]`).


### ADR-044: Add deterministic GPU point-sprite particle rendering
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: CPU particles simulated deterministically but had no GPU path, so every game would hand-roll FX quads with divergent blending, depth handling, and report hashes.
- **Decision**: Add frozen `Scene.sprite` (`SpriteSettings.enabled`, default on) plus `keystone/gpu/sprites.py` (fixed atten 180.0, size clamp 1-64px, GL-free `sprite_scale`/`soft_alpha`/`sprite_alpha`/`billboard_corners`) and a renderer instanced-quad path (per-instance offset/scale/fade-alpha, camera-right/up billboards, depth-test on with depth-write off, SRC_ALPHA blending, display-referred sprite tint with shared bloom/post grade). Engine supplies the game-owned `ParticleSystem` via the existing duck-typed `particles|fx|particle_system` channel (five-op contract unchanged). Gate with `--sprites/--no-sprites`; `--no-sprites` preserves legacy pixels. Bump frame report schema 9 to 10 with `scene.sprites` + top-level `fx`, add `capabilities.sprites`, persist optional `environment.sprites` in snapshot schema 1, export `sprites` in the web scene/inspector, and extend `last_stats` with `sprite_calls/sprites/sprites_enabled` plus a HUD `SPRITE N DRAWN` line. CubeDemo gains a seeded 64-particle fountain fixture stepped in `update()` but excluded from `snapshot()`.
- **Consequences**: CubeDemo renders soft FX sprites by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged because sprites never enter `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new scene draws, `sprite_calls <= 1`, CubeDemo wall `<=1.10x` no-sprite baseline, 1k-sprite stress `<=1.25x`; shadow pass skips sprites. Bounce, per-particle color/texture, and skin-aware merging remain future.


### ADR-045: Fix four reproduced swarm defects with minimal contract-preserving patches
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Parallel analysis swarms (6 modules) returned 40+ claims; main session reproduced 6/6 sampled claims (cone-base scope reduced after sampling: cone-side normals need deeper winding-mode decision, deferred). Four minimal true defects fixed: TextureData missing from public API, CubeDemo time not reset on rebuild, ActionState string/pointer shredding, camera pitch construction/look_at crash.
- **Decision**: Import TextureData in keystone/__init__ (no new dep); reset _time in CubeDemo.build_scene; strict ActionState.from_dict type/length checks (TypeError/ValueError); clamp PerspectiveCamera pitch in __post_init__ and look_at to +-MAX_PITCH. Five regression tests added (plugin export, samples rebuild, input strict x4 asserts in 1 test, 2 camera). Deferred: cone winding, material-graph Vec3 params, PNG CRC/zlib wrap, broadphase huge-box guard, playtest/global-RNG and other unverified S3-S6 static claims (filed, not implemented).
- **Consequences**: from keystone import TextureData works; sequential run_simulation on one instance deterministic; malformed action JSON fails fast with indexable TypeError; pitch +-90deg cameras stay usable; 447 tests green, ruff clean, 6/6 aikit gates; public five-op contract, schemas and hashes unchanged (simulate hash 9993994cc8aac268c007e43d0d33c95e). Cone/material/PNG/GPU items remain future.



### ADR-046: Harden PNG, skin, scene and sample boundaries with failing-first guards
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Second verified-fix iteration over swarm claims: PNG reader ignored CRC and leaked zlib.error, MeshData accepted NaN/Inf skin weights that later poison skin_point, Node accepted mismatched component values splitting query vs get_component, CubeDemo.update crashed with bare StopIteration when orb is missing.
- **Decision**: Verify per-chunk CRC32 in read_png and wrap IHDR/zlib errors as ValueError; require finite numeric skin weights in MeshData; require isinstance(value, key) for Node components; raise RuntimeError with node name when CubeDemo orb is absent. Six regression tests added (CRC, corrupt-IDAT wrap, NaN/Inf weights, component value, orb-missing).
- **Consequences**: Corrupt PNGs fail fast with actionable ValueError; NaN weights rejected at construction; hand-built component dicts cannot desync queries; sample update error is diagnosable; 450 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (no CubeDemo asset/behavior change on the happy path).



### ADR-047: Fix cone winding, merge normals and graph color params
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Cone side normals pointed inward with inverted winding and the base cap stored -Y normals with +Y winding; MeshBuilder transformed normals with M instead of transpose(inverse(M)), breaking non-uniform merges while the GPU renderer already used the correct normal matrix; material-graph color/checker/material/pbr params rejected Vec3 even though _json_value serializes Vec3.
- **Decision**: Flip cone side cross order and both triangle windings to outward/CCW-consistent; transform merge normals with transpose(inverse(M)) matching gpu.renderer.normal_matrix (singular matrices now raise via Mat4.inverse); accept Vec3 for color, checker dark/light and material/pbr color/emissive params. Five regression tests added (outward normals, winding-vs-normal alignment, inverse-transpose values, Vec3 color, Vec3 checker/material).
- **Consequences**: Cone lighting and culling are correct; non-uniform merges match GPU shading; graph round-trips preserve Vec3; 455 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (CubeDemo uses no cones, merges or graphs). Skin CPU-oracle normals remain a known follow-up.



### ADR-048: Strict construction-time validation for OBJ, textures and meshes
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: OBJ silently dropped face-slash extras, vertex w components and trailing junk; TextureData.checker with a 2-channel color failed deep inside with a byte-count message; MeshData accepted short/NaN tuples and non-integer indices, deferring failure to bounds() with a misleading unpack error.
- **Decision**: Reject face corners beyond v/vt/vn, require exact v/vn arity while honoring the OBJ homogeneous w coordinate (x/w, y/w, z/w; zero w rejected), accept vt with optional w; validate checker dark/light as 3-channel sequences with a naming TypeError; validate MeshData positions/normals/colors as 3 finite numbers, UVs as 2 finite numbers and indices as integers at construction. Six regression tests added (extra slash, w handling, junk/short vertices, channel counts, malformed tuples).
- **Consequences**: Malformed assets fail at the boundary with OBJ line numbers instead of silent corruption; 460 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (no sample asset changes). Remaining: perspective Mat4*Vec3 guard, builder/primitive UV orientation decision, docs drift, S2 CLI/replay/clock groups.



### ADR-049: Reject ignored CLI flags and harden runtime boundaries
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: --serve/--describe/--playtest/--simulate silently ignored --frames/--size/--diff-out (e.g. --describe --diff-out misreported as a baseline error); CommandLog coerced seed 3.7 to 3 and silently emptied dict frames; run_log permanently reseeded global random; read_json choked on BOM that write_json_atomic peers (load_actions) already tolerate; FixedStepClock minted 15 phantom steps on a backwards wall timestamp and froze on NaN; snapshot coerced non-string names; load_actions reported bare AttributeError without the failing index. The swarm claim that --verify-determinism --trace is accepted was refuted on reproduction (already exit 2) and dropped.
- **Decision**: Extend the standalone-command guards (serve/describe/playtest plus a new simulate window guard) to reject window flags; require integer seeds, finite positive steps and list frames in CommandLog; save/restore random state around run_log; read JSON as utf-8-sig; ignore backwards wall time without retreating the clock and reject non-finite now; require string snapshot names; wrap bad action items as TypeError with actions[i]. Eight regression tests added across CLI, replay, headless, serialization, clock and snapshot suites.
- **Consequences**: Ignored flags now fail fast at exit 2 with the naming command; replay is side-effect-free and strict at the boundary; BOM files load; clocks cannot mint debt or freeze; 467 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. Deferred: unbind-resurrect schema, snapshot missing-asset strictness, headless hold-last semantics, UI pause-capture semantics.



### ADR-050: Guard projective misuse and close doc drift
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Mat4.transform_point silently returned non-divided points for projective matrices (eye-space z instead of NDC) while inverse() already rejected them; docs drifted (README geometry line claimed a skin export, endpoint table omitted /api/inspector and pinned schema 1, ARCHITECTURE pinned scene-doc version 1, omitted gltf/ from the layer tree and pbr from the material-graph row). ADR-029 multi-primitive note is stale (fan-out already ships) but ADRs are append-only, so it stands with this record noting the correction.
- **Decision**: transform_point (and Mat4*Vec3 through it) raises ValueError for projective matrices directing to project_point, mirroring inverse()'s affine check; analysis/world and builder paths are affine-only so behavior is unchanged. Docs: fix the geometry line, add the inspector endpoint row, correct schema versions to 2, add gltf/ and pbr to ARCHITECTURE.
- **Consequences**: Projection misuse fails fast with an actionable message; two math regression tests added; README stays within the 32500-char budget (32495) with the duplicated inspector clause folded into the endpoint table; 468 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged.



### ADR-051: Fail fast on hierarchy, script, mix and grid boundary misuse
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Node.add_child accepted duplicate ids and deferred the failure to a later read; load_actions accepted command-log documents and silently dropped their seed; mix_clips clamped per voice, making mixes order-dependent and losing headroom (+1,+1,-1 mixed to 0 instead of 1); SpatialGrid._cells_for iterated an unbounded cell range (a 4001^3-cell box projects to ~87 minutes) and insert() stored the proxy before the iteration could fail, leaving partial state.
- **Decision**: Validate duplicate ids in add_child at write time (blank ids still defer to Scene assignment); reject seed/step-shaped documents in load_actions with a --replay pointer; sum voices then clamp once in mix_clips; cap proxies at 100k cells with a finite-bounds check and materialize the cell list before mutating grid state. Six regression tests added.
- **Consequences**: Hierarchy, script, mix and grid misuse fail at the boundary with actionable messages; mixes are order-independent; enormous proxies raise instead of hanging; 472 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. Deferred: unbind-resurrect schema, snapshot missing-asset strictness, hold-last semantics, UI pause-capture semantics, UV-orientation decision, skin oracle purity, sphere pole topology, digest coverage.



### ADR-052: Cover full material, texture and skin identity in asset digests
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Asset digests feed duplicates() and refresh() change detection, but _digest_material ignored metallic/roughness/emissive, texture digests ignored dimensions (a 2x8 and a 4x4 with identical bytes collided), and _digest_mesh ignored all skinning (joints/weights/names/bind matrices), so variants shared one digest. The parallel claim that refresh() only handles the first record was refuted by reading (it iterates every source) and dropped.
- **Decision**: Hash metallic/roughness/emissive into material digests, width/height plus pixel sha into texture digests, and joint/weight/skin-joint/bind-matrix groups into mesh digests with length-prefixed packing. Two existing assertions that pinned pixel-only texture digests were updated to the new contract. Four regression tests added (metallic/roughness/emissive divergence, reshaped-texture divergence, skin-weight divergence with no false duplicates).
- **Consequences**: Content-distinct assets no longer collide in duplicates()/find_by_digest() and refresh() detects their changes; 473 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. apply_ui_action resume idempotence kept as-is (idempotent success, no harm reproduced); texture names stay out of digests by content-addressing design.



### ADR-053: Keep every reported node and isolate bot randomness
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: _node_report dropped any node whose center hit the projection plane (ZeroDivisionError -> continue skipped the whole entry, corrupting node_count and diffs); run_bot permanently reseeded global random like run_log did before ADR-049; run_bot and validate_fairness accepted NaN/Inf steps and wall budgets, silently disabling timeouts and poisoning clocks. The hygiene gate rejects bare except-pass, so the deliberate null-screen keep carries a scoped marker (bare form needs a 3+ char reason word per the checker).
- **Decision**: Degrade on-plane nodes to screen null instead of dropping them; save/restore global RNG around run_bot like run_log; require finite positive step and wall budgets in run_bot and validate_fairness. Five regression tests added (on-plane inclusion with null screen, RNG restore, NaN/Inf step rejection).
- **Consequences**: Frame reports never lose nodes; bot runs are side-effect-free and strictly validated; 475 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. apply_ui_action resume idempotence and unbind-resurrect stay filed as judgment calls, not defects.


### ADR-054: Add deterministic particle bounce, friction and contact-kill
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Particles stopped dead on every contact, so games needing sparks, debris or bouncing shots would hand-roll response math with divergent trajectories and hashes.
- **Decision**: Extend ParticleSystem.step with restitution=0.0, friction=0.0, kill_on_contact=False (defaults reproduce the legacy dead stop bit-identically, including a verbatim zero-assignment branch so no negative zero leaks into traces). Validation precedes the empty-box fast path. On a hit: kill drops the particle; else per-axis reflect-or-zero in swept X-Z-Y order with REST_SPEED 0.05 settle snapping; friction scales tangential velocity only on hit steps. CubeDemo gains a floor slab AABB center (0,-0.05,0) half (10,0.05,10) with restitution=0.45 stepped in update() but excluded from snapshot(). No Emitter, Particle, report, renderer, CLI or schema changes.
- **Consequences**: The fountain visibly bounces in headless frames while the simulate hash 772cac5232a0947b8f6d1914a5cf0cde is unchanged. Perf budget: step wall at most 1.05x legacy at 1k particles by 8 AABBs. Known quirk (pre-existing, filed as follow-up): a particle sliding tangentially while in box contact relocates to the box min face via the interior-start clause of the swept pass; the fountain never triggers it because lifetimes end before any settle.


### ADR-055: Fix slide-teleport by gating the sweep interior clause
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: The swept pass ejected any point strictly interior on the sweep axis to the min face, including points resting on a face (within POINT_SKIN) whose tangential motion should slide. A resting particle with sideways velocity teleported to the box corner and stopped. Supersedes the ADR-054 quirk paragraph: the quirk is fixed, not merely filed.
- **Decision**: Gate the interior-start clause on strict interiority on every axis (no skin tolerance), computed from the already-available point coordinates. Face-contact points (offset exactly one skin outside) skip the clause and slide; genuinely deep-interior spawns eject exactly as before. Two-line change in _move_point_flat; no signature, schema, or behavior change for crossings, rests, or ejections.
- **Consequences**: Sliding preserves tangential motion deterministically; frame-70 demo hash e37b744448a1fbbb5cf5f390f41753db is bit-identical pre/post fix and the simulate hash is unchanged. Failing-first slide/graze tests plus a deep-interior preservation lock added. Tangential exit off a box edge while still in the skin band now slides off cleanly instead of teleporting.


### ADR-056: Add skin-aware batch merging for identical rigs
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: merge_batches skipped every skinned mesh, so rigged crowds paid one draw per model with no engine path to consolidate; per-game rig merging would fork draw-call accounting and frame hashes.
- **Decision**: Merge skinned groups keyed by material, joint-name tuple and node world-matrix tuple, concatenating positions, normals, UVs, colors, joints and weights verbatim with the shared inverse binds; the merged node reuses the common world matrix so deformation is bit-exact. MeshBuilder gains a mode-guarded add_skinned_mesh path; plan_batches and the merge summary gain additive skin counters; the web inspector exports them. Cross-transform merges (inverse-bind rebasing) and palette-union remaps stay future.
- **Consequences**: N identical rigs render as 1 draw with pixel-identical frames to the unmerged scene (proven by a headless Engine pixel-parity test on a test rig module). Static plans, pins and the simulate hash are unchanged (CubeDemo is unskinned). Perf budget: merge wall at most 1.3x current cost on equivalent groups; runtime draws strictly decrease.
### ADR-057: Key skin-aware batch merges on the full bind palette

- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: The skin-aware merge keyed groups by material, joint-name tuple and node world matrix only, and MeshBuilder accepted any member with matching joint names. Two rigs sharing joint names but carrying different inverse bind matrices merged into one group keeping the first binds, so the second rig deformed against the wrong rest pose. Reproduced with identical joints/materials/transforms and shifted binds collapsing to one group.
- **Decision**: Extend the plan/merge skin keys with the inverse bind matrix tuple and reject mismatched binds in MeshBuilder.add_skinned_mesh alongside the joint-name check. Remove the unused particles._AXES constant left over from the swept-pass change.
- **Consequences**: Differing bind palettes stay in separate groups and the builder fails fast at the boundary; identical rigs still merge to one draw with pixel-identical frames. 496 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (CubeDemo is unskinned).


### ADR-058: Fix six reproduced 12-module swarm defects with minimal patches

- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: 12 parallel analysis subagents (one module each) returned completed documents; main session sampled and reproduced every implemented claim, refuted one (S04 None-context with schema 1 masked by legacy fallback, confirmed with schema 2) and narrowed one (animation duration must keep event-only clips working). Fabricated-batch rule not triggered: all sampled claims reproduced.
- **Decision**: Six minimal fixes: input.bind blank-context misroute (None vs empty), input.from_dict context str-coercion, particles.step and headless.run_simulation NaN/Inf step rejection, animation.duration tracks-only when tracks exist (event-only fallback preserved), analysis._stats per-cell grid divisor, mixer.render single master factor. Seven regression tests added (input x2, particles, headless asserts, animation x2, analysis grid, audio master).
- **Consequences**: 503 tests green, verify-determinism 120 ok, simulate hash 772cac5232a0947b8f6d1914a5cf0cde unchanged, headless report schema 10 ok, 6/6 aikit gates after fix pass. Filed-but-deferred: plan-vs-merge grouping divergence, sprite oracle vs renderer sizing, hold-last pressed parity, interior-eject direction, unbind-resurrect, touch-trigger hysteresis (real but behavior-changing, need separate versioned decisions).

### ADR-059: Fix five reproduced swarm defects with failing-first pins

- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: 12 parallel analysis subagents returned completed documents; main session reproduced a sample before touching code and refuted one flagship claim (batching B1 wrong-normal: code already computes transpose(inverse), verified against Mat4 column-major layout and rotation_z repro giving correct (0,1,0)). Five sampled claims reproduced and fixed.
- **Decision**: Five minimal fail-fast fixes: input contexts inherit custom bindings (merged from self.bindings, not DEFAULT_BINDINGS), Vec3 mul rejects non-numeric operands, Track rejects duplicate keyframe times (strictly increasing), PauseMenu.move requires int (rejects float/bool), web simulate step rejects non-finite (400 not 500). Five regression tests added; README tree fixed for test_swarm_fixes.py with size-budget trims; codebase map refreshed via update_knowledge_base.
- **Consequences**: 520 tests green, verify-determinism 120 ok hash 772cac5232a0947b8f6d1914a5cf0cde unchanged (no re-pin), headless 320x180 report ok, --describe accurate, 6/6 aikit gates pass. Filed-but-deferred: mesh_builder vs batch key divergence, sprite oracle drift, unbind resurrection, trigger teleport misses, audio unknown-bus policy, broadphase large-query contract (real but behavior-changing, need separate versioned decisions).

### ADR-060: Fail-fast on History capacity type, blank input bindings, unknown audio bus
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: Stage 3 swarm triage reproduced three validation holes with scripts: History(True)/2.5 accepted, InputMap.from_dict accepted blank action/key while bind() rejects, Mixer.play accepted typo bus with silent full gain.
- **Decision**: Reject non-int History capacity with TypeError (bool explicitly rejected); reject blank action/key in InputMap.from_dict and context maps with ValueError matching bind(); reject unknown Mixer bus with ValueError (allow master). Three regression tests added.
- **Consequences**: No sim-hash change (validation-only, default paths untouched); typo bugs fail fast; audio unknown-bus deferred item from ADR-059 now closed.

### ADR-061: Add deterministic CPU view-frustum culling to the core renderer
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: The renderer drew every world-visible node with no frustum test, so draw calls were the scaling limit; per-game culling would fork draw accounting and frame hashes.
- **Decision**: Add GL-free `keystone/culling.py` (normalized 6-plane extraction from `view_projection`, 8-corner world AABB via `world_matrix`, p-vertex test, on-plane visible, skinned always visible, `cull_scene()` reference API) plus frozen `Scene.culling` (`CullingSettings.enabled`, default on). The color pass culls inline in `group_instances(scene, planes)` reusing the already-computed world matrix (same predicate as `cull_scene`, proven by an agreement test; a second full traversal measured 1.38x so the inline path was chosen); the shadow depth pass is unchanged (off-camera casters still shade the frame). Gate with `--culling/--no-culling` in every `__main__` guard list; `--no-culling` preserves legacy pixels. Bump frame report schema 10 to 11 with `scene.culling`, add `capabilities.culling`, persist optional `environment.culling` in snapshot schema 1, export `culling` in the web scene/inspector, and extend `last_stats` with `culled_nodes/culling_enabled` plus a HUD `CULL N OFFSCREEN` line.
- **Consequences**: Off-screen meshes skip color-pass draws with identical on-screen pixels (10 behind-camera cubes: 6→5 draws, 830→710 tris, `culled_nodes` 10; `--no-culling` renders the legacy frame); `--simulate --frames 120` hash unchanged because culling never enters `snapshot()`. Frame/report hashes change and were re-pinned explicitly. Perf budget (measured, trimmed-mean over 40 headless frames at 320x180): CubeDemo wall `<=1.15x` no-cull baseline (observed 1.11x). Light-frustum shadow culling, LOD and occlusion remain future.

### ADR-062: Harden the 12-module engine audit with reproduced, fail-fast fixes

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: A second 12-module swarm (renderer, scene, loop, input, animation, particles, audio, collision, serialization, batching, HUD, web) returned 423 evidence rows. The lead reproduced the high-severity candidates independently; no batch was invalidated. The recurring root causes were permissive dataclass fields, frame-sampled one-shot edges, duplicated/nondeterministic serialization, and counters that disagreed with the renderer.
- **Decision**: Land minimal root-cause fixes with a failing-first test each: strict finite/type validation for `ActionState`, `InputMap`, `Transform`, `Node`, lights, particles, audio, physics and `CommandLog`; context-isolated binding round-trips; separate mouse-look vs click gating and pending-edge/look delivery across zero-step frames; one-shot repeated headless actions; trace deep copies; `Scene` reciprocal parent/child construction, iterative traversal, snapshot root/next-id preservation and strict versions; unique atomic temp files plus strict JSON and `stable_hash`; material-graph duplicate/cycle validation; PNG framing bounds; animation wrap events, channel type checks and inverse-transpose normals; nearest-face particle ejection; character step-up remaining-delta/zero-rise/nearest-face fixes; inside-sphere ray semantics and keyed raycast ties; exclude-aware merge and truthful instancing counters; playtest seed/witness/audit-trail fixes; web 400s, frame inference, empty-live-scene preservation, false settings, HEAD/405 and keep-alive close; report world/triangle/alpha/settings comparisons; singular-model and shadow-state renderer guards; glTF V-origin conversion; and the documented schema/version/capability drift.
- **Consequences**: Full suite 547+ tests green; `--verify-determinism --frames 120` remains `772cac5232a0947b8f6d1914a5cf0cde`; `--simulate --frames 120 --expect-hash 772cac...` exits 0; headless PNG/report proofs and 6/6 AIKit gates pass. Valid data is unchanged; invalid data now fails at the boundary. Filed-but-deferred items (stationary deep-particle depenetration, renderer cache eviction, report-hash image-path removal, HUD alpha blending, sprite size clamp, broadphase large-query policy, trigger teleport hysteresis, stateful web Step, emitter speed semantics, renderer cache and asset digest improvements) are recorded with reproductions in the Stage 4 report and are not silently implemented.

### ADR-063: Close the deferred audit items with 18 fixes and 9 evidenced drops

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The first closure pass left 26 verified defects deferred and several pre-fix reproduction scripts still asserted the old contract. The reviewer required every item to be fixed with a failing-first test or formally dropped with evidence, and every reproduction to become a passing post-fix assertion.
- **Decision**: Fix glTF reflected/singular matrix decomposition, skinned-node transform semantics (ignore the mesh node transform), finite normalized skin weights, context-loss-safe skinned release, stationary deep-particle depenetration, emitter speed as a magnitude, mixer bus removal muting, a minimum pitch guard, broadphase large-query linear fallback, grounded-only platform carry, zero-gravity ground probes, strict sphere tangency, negative-zero hash canonicalization, opaque HUD alpha blending, tiny-canvas menu suppression, diagnostics schema cleanup, explicit web reset-step labeling, finite animation track values/zero quaternions, sorted clip tracks, integer unique glTF joints, boolean coordinate rejection, Material/TextureData type checks, finite perspective parameters, world-visible disabled culling, pressure-free glTF weight validation, and finite material-graph parameters. Formally drop, with the recorded evidence and reasons: GPU cache eviction (VRAM/lifecycle policy), emitter deletion mid-flight (explicit author action; per-particle force snapshots would change the Particle contract), sprite clamp oracle (deferred visual policy), trigger teleport hysteresis (needs a swept temporal contract), report hash image path (intentional artifact identity; `same_image` is the pixel check), web resource/deployment limits, sub-120px exact headless capture (GLFW minimum; the message is now truthful), `--simulate` action-count default (documented behavior), and renderer cache/asset-digest performance work (workload/policy-dependent).
- **Consequences**: 644 tests green; 22/22 post-fix reproduction scripts pass via `reports/keystone-swarm-repro/verify_all.py`; the five named stale scripts (m2, m6, m7, m9, m11) are post-fix assertions and their `.pre_fix.py` evidence is preserved; determinism remains `772cac5232a0947b8f6d1914a5cf0cde`; headless schema 11 and `--describe` remain accurate; 6/6 AIKit gates pass. The drops are documented in `reports/keystone-swarm-deferred-closures.md`, not silently omitted.

### ADR-064: Reject malformed glTF accessors, asset cycles and unsafe direct pitch

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: A final broad M1 probe still reproduced three real validation gaps outside the original 26-row list: glTF accepted FLOAT indices, SCALAR POSITION and negative accessor counts; the asset registry accepted transitive dependency cycles; and assigning `PerspectiveCamera.pitch` directly above the clamp could make `look_at` fail.
- **Decision**: Enforce glTF accessor type/component rules for POSITION and indices, reject negative accessor counts even without a bufferView, detect transitive asset dependency cycles at registration, and clamp pitch inside `PerspectiveCamera.forward()` while preserving the stored value.
- **Consequences**: 647 tests green; 23/23 post-fix reproduction scripts pass; determinism remains `772cac5232a0947b8f6d1914a5cf0cde`; malformed imports and cycles now fail at the boundary, and direct camera pitch stays render-safe.

### ADR-065: Add deterministic prefabs for reusable scene subtrees

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Unity/Unreal-style authoring needs a reusable entity/template primitive. Keystone could save whole scenes but had no way to capture a subtree and instantiate isolated copies without rebuilding it by hand; AI clients also lacked a structural prefab description.
- **Decision**: Add `keystone.prefab.Prefab` with `from_node()`, `from_scene()`, `instantiate(scene, parent=None, instance=None)`, `node_count` and JSON-safe `describe()`. Templates are detached; components are deep-copied per instance; mesh/material payloads stay shared; IDs become `instance:original-id` or scene-allocated when no prefix is given. Export `Prefab` from the public API and add `capabilities.prefabs` to `--describe`. `Prefab.instantiate(scene)` is the canonical call to avoid a `scene -> prefab -> scene` import cycle.
- **Consequences**: 652 tests green; prefab instances are isolated and deterministic, duplicate instance IDs fail through the existing scene duplicate guard, and the five-operation game contract is unchanged. A scene-editor UI and prefab file format remain future tooling work.

### ADR-066: Add a versioned project manifest and one-command scaffolding

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Keystone could load an external game only through `--game package.module:Factory`; a human or AI had to hand-create a package, remember the five operations and pass a long spec. Unity/Unreal-style onboarding needs a project unit.
- **Decision**: Add `keystone.project` with a schema-1 `keystone.json` manifest (`name`, `game`, `description`, `assets`), strict load/save, `ProjectContext.describe()`, `create_project()`, and `load_project_game()`. Add `python -m keystone --new DIR [--name NAME] [--force]` scaffolding (`keystone.json`, a generated five-operation game module, README, `.gitignore`) and `--project DIR|keystone.json` to open it. `--project` adds the directory to the import path, uses the manifest game unless `--game` overrides it, and adds a `project` object to `--describe`.
- **Consequences**: A new project runs with one create command and one open command; generated projects are deterministic, headless-ready and contract-validated. Project manifests are local JSON and do not change the engine's five-operation contract. Prefab persistence, a scene-editor workflow and behavior/system hooks remain future work.

### ADR-067: Add a web-console scene editor with hierarchy, transforms and prefabs

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The web console could inspect a scene but not select or edit it; a Unity/Unreal-style workflow needs a hierarchy, transform editing and prefab insertion from the same AI-addressable API as the viewer.
- **Decision**: Add `keystone.web.editor` helpers and schema-1 `/api/editor`: `GET` returns hierarchy (nodes, roots, parent/child ids, local transforms, world matrices, tags/layers/components), selection and saved prefabs; `POST` supports `select`, `transform` (finite position/rotation/scale arrays), `save_prefab` (capture the selected node with `Prefab.from_node`) and `insert_prefab` (deterministic instance prefix or scene IDs). The console gains a hierarchy `<select>`, transform fields, prefab name/instance inputs and apply/save/insert buttons; the viewer reloads after edits. `--describe` advertises the editor schema and `/api/editor`.
- **Consequences**: Humans and AI clients share one editor contract; selection and prefabs are session-local, transforms mutate the live scene, and prefab insertion uses the deterministic prefab system. Editing a game-owned scene may be overwritten by the next `update()`; persistent editor state, undo/redo and prefab files remain future work. The five-operation game contract is unchanged.

### ADR-068: Persist versioned prefabs through the asset registry

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Prefabs were in-memory templates; a Unity/Unreal-style authoring loop needs prefab files that survive a process restart and resolve shared mesh/material payloads without duplicating binary data. The asset registry already owned stable ids, digests, dependencies and hot reload but knew only meshes, materials and textures.
- **Decision**: Add `PREFAB_SCHEMA_VERSION = 1`, strict `Prefab.to_dict()`/`from_dict()` documents (transform, visibility, tags, layer, components and registered mesh/material ids), and atomic `Prefab.save()`/`load()` writing `.kprefab` files. Loading custom components requires an explicit `component_types` name map; non-JSON components, unknown types and wrong asset kinds fail at the boundary. Extend `ASSET_KINDS` with `prefab`, teach `asset_kind()`/`kind_from_suffix()`/`default_loader()` and `AssetRegistry.register_file(..., component_types=...)` about the kind, derive prefab dependencies from referenced assets automatically, and digest the canonical JSON document. Refresh uses a registry-bound loader so reloads re-resolve mesh/material ids.
- **Consequences**: 673 tests green; prefabs are a first-class asset with stable hashes, dependency tracking, missing-dependency reporting and hot reload; serialized files hold ids rather than duplicate payloads; the five-operation game contract and core module boundaries are unchanged. Editor prefab libraries and undo/redo persistence remain future work.

### ADR-069: Add node authoring and bounded undo/redo to the web editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The scene editor could select, transform and insert prefabs but could not create, delete, duplicate or reparent nodes, so human and AI authoring stopped at template placement. There was no way to recover from a bad edit, and mesh/material assignment from the asset registry was unavailable.
- **Decision**: Bump `EDITOR_SCHEMA_VERSION` to 2 and centralize `EDITOR_ACTIONS` in `keystone.schema` so the CLI description and web schema cannot drift. Add pure `create_node`, `delete_node`, `duplicate_node` and `reparent_node` helpers plus a bounded `EditorHistory` that snapshots the node tree, restores it atomically when an action fails, and exposes undo/redo depths. Wire the actions through `/api/editor`, accept registry asset ids for node mesh/material fields, and add console controls for create/duplicate/delete/reparent, undo and redo. `duplicate_node` reuses the prefab cloner so component copies stay isolated.
- **Consequences**: 674 tests green; authoring actions validate before mutation, failed edits leave the scene unchanged, undo/redo preserves node IDs while replacing node objects, and the editor document reports history depth. Selection and history remain session-local; persistent editor prefabs, scene files and component authoring remain future work. The five-operation game contract is unchanged.

### ADR-070: Add a file-backed prefab library to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `.kprefab` persistence existed, but the editor kept captured prefabs in a session dictionary. Closing the console lost the authoring library, and AI clients could not discover what was on disk or why an entry failed to load.
- **Decision**: Add `keystone.prefab_library` with `PrefabLibrary` and `PrefabEntry`: one directory of `.kprefab` files, portable name validation that blocks path traversal, atomic save, registry/component-aware load, stable listing and per-entry error reporting. Wire an optional library into `GameSession`, list `source`/`error`/`node_count` in `/api/editor`, lazily load an entry on first insert, and expose the active `workspace.prefab_dir`. `--project .` defaults the library to `<project>/prefabs`; `--prefab-dir DIR` overrides it. Rebind the library to the game's live `AssetRegistry` after `build_scene()` because games may rebuild their registry.
- **Consequences**: 679 tests green; prefab authoring survives console restarts, invalid names and corrupt files are reported without breaking the editor, and only prefab writes touch the configured library directory. Project asset import, scene files and component authoring remain future work.

### ADR-071: Import project manifest assets into the game registry

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `keystone.json` already listed `assets`, but nothing loaded them. A Unity/Unreal-style project needs relative `.obj`, `.png` and `.kprefab` files to become stable registry ids before scenes and editor commands reference them, without duplicating import code in every game.
- **Decision**: Add `project_asset_id`, `import_project_assets` and `attach_project_assets`. Manifest paths must be relative and stay inside the project; ids are deterministic `project:<relative-path>` strings, kinds come from the file suffix, and prefab entries receive the game's `component_types`. `load_project_game` and the `--project` CLI path attach assets to `game.assets` when the project declares any, with an actionable `Why:`/`Fix:` error on failure. The generated game owns one `AssetRegistry`, registers built-in meshes/materials with `replace=True`, and never replaces the registry during rebuilds.
- **Consequences**: 683 tests green; projects can ship assets without hand-wiring registrations, unsafe or missing paths fail before rendering, and editor asset ids survive rebuilds. Scene files, component authoring and play-in-editor remain future work.

### ADR-072: Persist typed components in scene snapshots

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Scene snapshots preserved node identity, transforms, tags, layers, visibility, meshes and materials, but dropped typed components. Prefabs already had a component codec, and duplicating that logic would drift. A Unity/Unreal-style scene file must round-trip the same authored data the editor shows.
- **Decision**: Extract the component codec into `keystone.component_codec` and use it from both prefabs and snapshots. Bump `SCENE_SNAPSHOT_VERSION` to 2 and write a sorted `components` list per node; `scene_from_dict(..., component_types=...)` reconstructs them, rejects duplicate types, unknown names and unsupported payloads, and still accepts schema-1 snapshots without components.
- **Consequences**: 685 tests green; scene snapshots preserve dataclass, `to_dict`/`from_dict` and JSON-primitive components; loading a component-bearing scene without a type map fails explicitly. Editor scene files and component authoring remain future work.

### ADR-073: Add file-backed scene save/load to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Component-aware snapshots made scene files possible, but the editor still could not persist authored scenes. A Unity/Unreal-style workflow needs named `.kscene` files that survive restarts, restore in place and report broken entries without taking down the editor.
- **Decision**: Add `keystone.scene_library` with `SceneLibrary`/`SceneEntry`: portable name validation, atomic `.kscene` save, strict registry asset-reference validation, component-aware load and `load_into()` backed by `restore_scene()`. Bump the editor schema to 3, add `save_scene`/`load_scene`, expose saved scenes plus `workspace.scene_dir`, and add console controls. `--project .` defaults the library to `<project>/scenes`; `--scene-dir DIR` overrides it. Loading a scene clears selection and undo history while preserving the game-owned `Scene` object.
- **Consequences**: 691 tests green; authored scenes survive console restarts, missing/wrong-kind assets and corrupt entries fail explicitly, and restore keeps `self.scene` identity. Asset browser assignment, component authoring and play-in-editor remain future work.

### ADR-074: Add registry asset inventory and assignment to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `create_node` could reference registry assets by id, but existing nodes could not be inspected or reassigned. A Unity/Unreal-style inspector needs the asset browser and node mesh/material fields in the same AI-addressable editor document.
- **Decision**: Bump the editor schema to 4, include the registry's JSON-safe asset inventory (`id`, `kind`, `sha256`, `source`, `dependencies`) and each node's resolved `mesh`/`material` ids, and add `assign_asset` with `mesh`/`material` fields that assign or clear through the registry. Validate missing/kind-mismatched ids, route the mutation through `EditorHistory`, and add mesh/material selects plus an apply button to the console.
- **Consequences**: 692 tests green; humans and AI clients can discover assets and reassign node payloads with undo, while invalid ids fail with 400 before mutation. Component authoring and play-in-editor remain future work.

### ADR-075: Add typed component authoring to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The editor displayed component names but could not add, edit or remove them. Game-defined components already had a shared codec and optional `game.component_types` map for prefabs and scenes, so the editor lacked only the authoring contract and UI.
- **Decision**: Bump the editor schema to 5, expose the game's `component_types` names and each node's serialized `component_data`, and add `set_component`/`remove_component` actions. Data is decoded through `component_codec`, replacements are keyed by type, unknown or non-serializable payloads fail with 400, and mutations run through `EditorHistory`. The console adds a type select, JSON data editor and set/remove buttons.
- **Consequences**: 693 tests green; component edits undo and survive `.kscene` save/load, while games without a `component_types` map reject component authoring explicitly. Play-in-editor and richer component field forms remain future work.

### ADR-076: Add play/step/stop with authored-scene restore

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `/api/simulate` rebuilds the game scene, so running the game from the editor discarded authored changes. A Unity/Unreal-style workflow needs a play mode that advances the live scene and restores the authored state on stop.
- **Decision**: Bump the editor schema to 6 and add `play_start`, `play_step` and `play_stop`. Start snapshots the component-aware scene with `scene_to_dict`; step calls `game.update(FIXED_STEP, ActionState)` for a bounded frame count with optional action payloads; stop restores through `restore_scene`, clears history/selection and reports `play.active`/`play.frames`. Editing actions and `/api/simulate` are blocked while playing. The console adds Play/Step/Stop controls.
- **Consequences**: 694 tests green; authored scene graph state is restored after play, while game-owned counters (time, particles) are not rewound; play mode is a scene preview, not a full state rewind. Full game-state snapshots and inspector property editing remain future work.
