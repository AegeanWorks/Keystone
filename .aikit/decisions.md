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
