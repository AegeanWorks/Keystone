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
