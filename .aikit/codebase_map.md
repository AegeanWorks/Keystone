# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `67`
- **Total Classes**: `91`
- **Total Top-Level Functions**: `70`
- **Total Class Methods**: `465`
- **Total Source Lines**: `7189`

---

## 📦 Modules & Exported Symbols

### [`keystone/__init__.py`](keystone/__init__.py)
> *Keystone: a game-agnostic 3D engine core.*

**Size**: `20` lines (`633` bytes)

**Functions:**
- `def __getattr__(name)`

---

### [`keystone/__main__.py`](keystone/__main__.py)
> *Command-line entry point for the game-agnostic Keystone engine.*

**Size**: `234` lines (`11763` bytes)

**Functions:**
- `def _size(text)`
- `def _frames(text)`
- `def _hash(text)`
- `def _port(text)`
- `def main(argv)`

---

### [`keystone/analysis.py`](keystone/analysis.py)
> *Machine-readable frame reports for AI and headless UI analysis.*

**Size**: `354` lines (`14746` bytes)

**Functions:**
- `def _rows(pixels, width, height, flip)`
- `def _stats(pixels, width, height, background, flip)`
- `def _material_report(material)`
- `def _node_report(scene, width, height)`
- `def analyze_frame(scene, pixels, width, height, image_path, ui)`
- `def _compare_ui(before, after)`
- `def compare_reports(before, after)` - *Compare schema-1/2/3/4 frame reports for AI-driven regression checks.*
- `def diff_images(before, after, output, threshold)` - *Write a visual diff PNG and return changed-pixel statistics.*
- `def write_report(path, report)`

---

### [`keystone/app.py`](keystone/app.py)
> *Game-agnostic engine runtime: window, fixed step, input, render and capture.*

**Size**: `227` lines (`8426` bytes)

**Classes:**
- `class Engine` - *Owns the runtime around one external GameModule.*
  - Method `.__init__(game, width, height, visible, msaa, title, ui)`
  - Method `.__enter__()`
  - Method `.__exit__(*exc_info)`
  - Method `._set_capture(captured)`
  - Method `._handle_system_actions(actions)`
  - Method `.toggle_pause()` - *Pause or resume gameplay; release the cursor while the menu is open.*
  - Method `.apply_ui_action(action)` - *Run a named UI action; returns False when the action is unknown.*
  - Method `._draw_ui()`
  - Method `.run(max_frames)` - *Run until the window closes or max_frames (0 = unlimited) is reached.*
  - Method `.capture(image_path, report_path)`
  - Method `.screenshot(path)`
  - Method `.close()`

---

### [`keystone/broadphase.py`](keystone/broadphase.py)
> *Deterministic spatial-grid broadphase for nearby AABB candidates.*

**Size**: `116` lines (`4333` bytes)

**Classes:**
- `class SpatialGrid` - *A uniform grid of AABB proxies with exact overlap filtering.*
  - Method `.__init__(cell_size)`
  - Method `.__len__()`
  - Method `.__contains__(key)`
  - Method `.get(key)`
  - Method `.insert(key, box)` - *Insert or replace a proxy and its current bounds.*
  - Method `.update(key, box)` - *Move a proxy; unknown keys are inserted.*
  - Method `.remove(key)` - *Remove a proxy; return whether it existed.*
  - Method `.clear()`
  - Method `.query(box)` - *Return proxies whose bounds overlap ``box`` in insertion order.*
  - Method `.query_point(point)`
  - Method `.pairs()` - *Return every exact overlapping proxy pair, once, in insertion order.*
  - Method `._cells_for(box)`
  - Method `._candidates(box)`

---

### [`keystone/camera.py`](keystone/camera.py)
> *Perspective camera with yaw/pitch orientation and fly-style movement.*

**Size**: `61` lines (`1967` bytes)

**Classes:**
- `class PerspectiveCamera` - *A right-handed camera looking down -Z when yaw and pitch are zero.*
  - Method `.forward()`
  - Method `.right()`
  - Method `.view_matrix()`
  - Method `.projection_matrix(aspect)`
  - Method `.view_projection(aspect)`
  - Method `.move(forward, right, up)`
  - Method `.rotate(yaw_delta, pitch_delta)`
  - Method `.look_at(target)`

---

### [`keystone/character.py`](keystone/character.py)
> *Game-agnostic AABB character movement with gravity and collision response.*

**Size**: `120` lines (`4109` bytes)

**Classes:**
- `class CharacterBody` - *An axis-aligned character body with velocity and ground state.*
  - Method `.__post_init__()`
  - Method `.box()`
- `class CharacterController` - *Resolve horizontal wish velocity and gravity against static AABBs.*
  - Method `.__post_init__()`
  - Method `.step(body, wish_velocity, dt, colliders)` - *Advance one step; horizontal speed is the wish velocity, vertical is body velocity.*
  - Method `._move_axis(position, half, axis, amount, colliders)`

**Functions:**
- `def _component(vector, axis)`
- `def _with_axis(vector, axis, value)`
- `def _other_axes_overlap(position, half, box, axis)`

---

### [`keystone/clock.py`](keystone/clock.py)
> *Fixed-step clock with a bounded catch-up budget.*

**Size**: `34` lines (`1174` bytes)

**Classes:**
- `class FixedStepClock` - *Accumulates wall time and releases whole deterministic simulation steps.*
  - Method `.__init__(step, max_frame)`
  - Method `.reset(now)`
  - Method `.advance(now)`

---

### [`keystone/geometry.py`](keystone/geometry.py)
> *Indexed triangle mesh data and surface material, independent of any GPU API.*

**Size**: `73` lines (`2854` bytes)

**Classes:**
- `class Material` - *Blinn-Phong surface parameters used by the renderer.*
  - Method `.__post_init__()`
- `class MeshData` - *Immutable indexed triangle mesh with optional UVs.*
  - Method `.__post_init__()`
  - Method `.vertex_count()`
  - Method `.triangle_count()`
  - Method `.bounds()`
  - Method `.interleaved()` - *Pack position, normal and UV into one vertex stream for the GPU.*

---

### [`keystone/gpu/__init__.py`](keystone/gpu/__init__.py)
> *OpenGL 3.3 adapter: context, shader, mesh buffers and renderer.*

**Size**: `1` lines (`70` bytes)

---

### [`keystone/gpu/context.py`](keystone/gpu/context.py)
> *GLFW window and OpenGL 3.3 context lifecycle with deterministic teardown.*

**Size**: `151` lines (`5224` bytes)

**Classes:**
- `class GLContext` - *A hidden or visible GLFW window owning one OpenGL 3.3 core context.*
  - Method `.__init__(width, height, title, visible, msaa)`
  - Method `.__enter__()`
  - Method `.__exit__(*exc_info)`
  - Method `._version_string()`
  - Method `.version()`
  - Method `.should_close()`
  - Method `.request_close()`
  - Method `.poll_events()`
  - Method `.swap_buffers()`
  - Method `.time()`
  - Method `.key_down(name)`
  - Method `.cursor_position()`
  - Method `.mouse_down(button)`
  - Method `.set_cursor_captured(captured)`
  - Method `.set_title(title)`
  - Method `.framebuffer_size()`
  - Method `.close()`

**Functions:**
- `def require_opengl_33(version)` - *Refuse a context that cannot run the 3.3 core shader pipeline.*

---

### [`keystone/gpu/mesh_buffer.py`](keystone/gpu/mesh_buffer.py)
> *GPU mesh upload and indexed drawing for the Keystone renderer.*

**Size**: `66` lines (`2438` bytes)

**Classes:**
- `class GpuMesh` - *VAO/VBO/EBO triple owning one immutable MeshData upload.*
  - Method `.__init__(mesh)`
  - Method `.draw()`
  - Method `.release()`

---

### [`keystone/gpu/renderer.py`](keystone/gpu/renderer.py)
> *Blinn-Phong forward renderer with fog, depth testing and screenshot readback.*

**Size**: `250` lines (`9522` bytes)

**Classes:**
- `class Renderer` - *Owns the shader and per-mesh GPU buffers for one OpenGL context.*
  - Method `.__init__(width, height)`
  - Method `.resize(width, height)`
  - Method `._gpu_mesh(mesh)`
  - Method `._gpu_texture(texture)`
  - Method `._draw_sky(scene)`
  - Method `.render(scene)`
  - Method `.read_pixels()`
  - Method `.save_png(path)`
  - Method `.release()`

**Functions:**
- `def normal_matrix(model)` - *Return transpose(inverse(upper 3x3)) in column-major order.*

---

### [`keystone/gpu/shader.py`](keystone/gpu/shader.py)
> *GLSL program compilation, uniform upload and cleanup.*

**Size**: `86` lines (`3276` bytes)

**Classes:**
- `class ShaderProgram` - *A linked vertex/fragment program with cached uniform locations.*
  - Method `.__init__(vertex_source, fragment_source)`
  - Method `._compile(stage, source, label)`
  - Method `.use()`
  - Method `._location(name)`
  - Method `.set_mat4(name, matrix)`
  - Method `.set_mat3(name, values)`
  - Method `.set_vec2(name, x, y)`
  - Method `.set_vec3(name, vector)`
  - Method `.set_float(name, value)`
  - Method `.set_int(name, value)`
  - Method `.release()`

---

### [`keystone/gpu/texture_buffer.py`](keystone/gpu/texture_buffer.py)
> *GPU upload and lifecycle for immutable TextureData.*

**Size**: `53` lines (`1835` bytes)

**Classes:**
- `class GpuTexture` - *One OpenGL 2D texture with mipmaps and repeat wrapping.*
  - Method `.__init__(data)`
  - Method `.bind(unit)`
  - Method `.release()`

---

### [`keystone/gpu/ui_renderer.py`](keystone/gpu/ui_renderer.py)
> *Screen-space OpenGL renderer for the human UI canvas.*

**Size**: `94` lines (`3055` bytes)

**Classes:**
- `class UiRenderer` - *Uploads one canvas per frame and draws it over the 3D scene.*
  - Method `.__init__()`
  - Method `.draw(canvas)` - *Draw the canvas with alpha blending, then restore 3D render state.*
  - Method `.release()`

---

### [`keystone/headless.py`](keystone/headless.py)
> *Simulation without a window: JSON action scripts and deterministic traces.*

**Size**: `60` lines (`1959` bytes)

**Functions:**
- `def load_actions(path)`
- `def run_simulation(game, frames, actions, step, trace)` - *Advance a game without creating a window or OpenGL context.*

---

### [`keystone/input.py`](keystone/input.py)
> *Generic input mapping: named actions, axes and pointer look.*

**Size**: `128` lines (`4378` bytes)

**Classes:**
- `class ActionState` - *One sampled input frame; games translate names into their own rules.*
  - Method `.without_pressed()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class InputMap` - *Maps keys and pointer motion to action names and continuous axes.*
  - Method `.__init__(bindings, look_speed, mouse_sensitivity)`
  - Method `.bind(action, key)`
  - Method `.set_mouse_enabled(enabled)`
  - Method `.sample(context, dt)`

---

### [`keystone/math3d.py`](keystone/math3d.py)
> *Column-major 3D math primitives shared by the scene, camera and GPU layers.*

**Size**: `371` lines (`12816` bytes)

**Classes:**
- `class Vec3` - *Immutable 3-component vector with the usual right-handed operations.*
  - Method `.__add__(other)`
  - Method `.__sub__(other)`
  - Method `.__mul__(scalar)`
  - Method `.__truediv__(scalar)`
  - Method `.__neg__()`
  - Method `.__iter__()`
  - Method `.dot(other)`
  - Method `.cross(other)`
  - Method `.length()`
  - Method `.length_squared()`
  - Method `.normalized()`
  - Method `.lerp(other, t)`
- `class Mat4` - *Immutable 4x4 matrix stored column-major, ready for OpenGL upload.*
  - Method `.__post_init__()`
  - Method `.__mul__(other)`
  - Method `.__iter__()`
  - Method `.__getitem__(index)`
  - Method `.identity()`
  - Method `.translation(x, y, z)`
  - Method `.scale(x, y, z)`
  - Method `.rotation_x(radians)`
  - Method `.rotation_y(radians)`
  - Method `.rotation_z(radians)`
  - Method `.rotation_axis(axis, radians)`
  - Method `.perspective(fov_y_degrees, aspect, near, far)`
  - Method `.look_at(eye, target, up)`
  - Method `.transform_point(point)`
  - Method `.project_point(point)` - *Transform by a projection and divide by w to obtain normalized device coordinates.*
  - Method `.transform_direction(direction)`
  - Method `.inverse()` - *Invert an affine transform; raise ValueError for perspective matrices.*
  - Method `.flat()`
- `class Quat` - *Unit quaternion (w, x, y, z) for rotation without gimbal lock.*
  - Method `.__mul__(other)`
  - Method `.identity()`
  - Method `.from_axis_angle(axis, radians)`
  - Method `.conjugate()`
  - Method `.normalized()`
  - Method `.rotate(vector)`
  - Method `.to_mat4()`
  - Method `.slerp(other, t)`
  - Method `.almost_equal(other, places)`

---

### [`keystone/mesh_builder.py`](keystone/mesh_builder.py)
> *Compose boxes and quads into a single indexed MeshData.*

**Size**: `104` lines (`3965` bytes)

**Classes:**
- `class MeshBuilder` - *Accumulates flat-shaded quads and boxes, then builds one mesh.*
  - Method `.__init__()`
  - Method `.add_quad(p0, p1, p2, p3, color)`
  - Method `.add_mesh(mesh, offset, scale, color)` - *Merge another mesh under a uniform scale and translation.*
  - Method `.add_box(cx, cy, cz, sx, sy, sz, color)`
  - Method `.is_empty()`
  - Method `.build()`

---

### [`keystone/obj_loader.py`](keystone/obj_loader.py)
> *Streaming Wavefront OBJ loader producing indexed triangle meshes.*

**Size**: `126` lines (`5286` bytes)

**Functions:**
- `def load_obj(path)` - *Read an OBJ file line by line so file size is never loaded whole.*
- `def parse_obj(text)` - *Parse OBJ text already in memory, mainly for tests and embedded assets.*
- `def _resolve_index(raw, count, kind, number, line)`
- `def _corner(token, number, line, vertices, uvs, normals)`
- `def _parse_lines(lines)`
- `def _build_mesh(positions, normals, uvs, faces)`

---

### [`keystone/physics.py`](keystone/physics.py)
> *Generic collision primitives and ray queries for the engine core.*

**Size**: `158` lines (`5921` bytes)

**Classes:**
- `class Ray`
  - Method `.__post_init__()`
- `class AABB`
  - Method `.__post_init__()`
  - Method `.low()`
  - Method `.high()`
  - Method `.contains(point)`
  - Method `.overlaps(other)`
- `class RayHit`
- `class Sphere`
  - Method `.__post_init__()`

**Functions:**
- `def ray_aabb(ray, box)` - *Return the nearest positive hit distance, or None.*
- `def raycast(ray, colliders, predicate)` - *Return the nearest AABB hit, optionally filtered by key and box.*
- `def ray_sphere(ray, sphere)`
- `def aabb_overlap(first, second)`
- `def sphere_aabb_overlap(sphere, box)`
- `def resolve_sphere_aabb(sphere, box)` - *Push a sphere out of an AABB along the shallowest axis.*

---

### [`keystone/plugin.py`](keystone/plugin.py)
> *Game-agnostic module contract and loader.*

**Size**: `69` lines (`2524` bytes)

**Classes:**
- `class GameModule` - *The five operations an external game exposes to the engine.*
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`

**Functions:**
- `def describe_game(game)` - *Return a machine-readable capability/action/snapshot description.*
- `def load_game(spec)` - *Load an external game from 'package.module:Factory'.*

---

### [`keystone/png.py`](keystone/png.py)
> *Minimal dependency-free PNG writer for headless frame captures.*

**Size**: `119` lines (`4463` bytes)

**Functions:**
- `def _chunk(kind, payload)`
- `def _paeth(a, b, c)`
- `def read_png(path)` - *Read an 8-bit RGBA non-interlaced PNG and return top-down pixels.*
- `def write_png(path, width, height, rgba, flip_vertical)` - *Write RGBA bytes (OpenGL order: bottom-up) as an 8-bit PNG.*

---

### [`keystone/primitives.py`](keystone/primitives.py)
> *Procedural primitives: cube, plane, cone, cylinder and UV sphere.*

**Size**: `170` lines (`7205` bytes)

**Functions:**
- `def _append_quad(positions, normals, uvs, indices, corners, normal)`
- `def cube(size)`
- `def plane(size)`
- `def cone(radius, height, segments)`
- `def cylinder(radius, height, segments)`
- `def sphere(radius, segments, rings)`

---

### [`keystone/replay.py`](keystone/replay.py)
> *Deterministic action logs and stable state hashes.*

**Size**: `50` lines (`1514` bytes)

**Classes:**
- `class CommandLog`
  - Method `.record(actions)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.save(path)`
  - Method `.load(path)`
  - Method `.replay_actions()`

**Functions:**
- `def stable_hash(payload)`

---

### [`keystone/samples.py`](keystone/samples.py)
> *A minimal game-agnostic sample used to smoke-test the engine.*

**Size**: `117` lines (`4325` bytes)

**Classes:**
- `class CubeDemo` - *A rotating cube scene; contains no combat, puzzles or genre rules.*
  - Method `.__init__()`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`

---

### [`keystone/scene.py`](keystone/scene.py)
> *Scene graph: hierarchical transforms, identity, components, camera and light.*

**Size**: `267` lines (`9130` bytes)

**Classes:**
- `class Transform` - *Translation, rotation and non-uniform scale composed as T * R * S.*
  - Method `.matrix()`
- `class Node` - *A named transform node with identity, tags, components and children.*
  - Method `.__post_init__()`
  - Method `.add_tag(tag)`
  - Method `.remove_tag(tag)`
  - Method `.has_tag(tag)`
  - Method `.add_component(component)`
  - Method `.get_component(component_type)`
  - Method `.require_component(component_type)`
  - Method `.has_component(component_type)`
  - Method `.remove_component(component_type)`
  - Method `.add_child(child)`
  - Method `.remove_child(child)`
  - Method `.is_ancestor_of(other)`
  - Method `.world_matrix()`
  - Method `.world_visible()`
  - Method `.traverse()`
- `class DirectionalLight` - *A direction the light travels in, plus linear color and intensity.*
  - Method `.__post_init__()`
  - Method `.unit_direction()`
  - Method `.radiance()`
- `class PointLight` - *A local light with quadratic falloff, used for torches and lamps.*
  - Method `.__post_init__()`
- `class Scene` - *Root node, identity allocation, queries, camera, lights and atmosphere.*
  - Method `.add(node)`
  - Method `.traverse()`
  - Method `.query(*, name, tag, layer, component)` - *Return every node matching all supplied filters.*
  - Method `.find(*, name, tag, layer, component)` - *Return the first node matching all supplied filters.*
  - Method `.find_by_id(node_id)`
  - Method `._used_ids(exclude)`
  - Method `._prepare(node)`

**Functions:**
- `def _root_node()`

---

### [`keystone/schema.py`](keystone/schema.py)
> *Core-facing schema versions shared with optional adapters.*

**Size**: `6` lines (`147` bytes)

---

### [`keystone/serialization.py`](keystone/serialization.py)
> *Atomic JSON persistence for engine and game state.*

**Size**: `31` lines (`962` bytes)

**Functions:**
- `def write_json_atomic(path, payload, backup)`
- `def read_json(path)`

---

### [`keystone/testing.py`](keystone/testing.py)
> *Deterministic scenario helpers for AI and CI tests.*

**Size**: `52` lines (`1567` bytes)

**Functions:**
- `def run_script(game, actions, frames, step, trace)`
- `def verify_determinism(factory, actions, frames, step)` - *Run one scenario twice from a factory and compare final hashes.*
- `def assert_deterministic(factory, actions, frames, step)`

---

### [`keystone/texture.py`](keystone/texture.py)
> *Immutable RGBA texture data and dependency-free texture sources.*

**Size**: `63` lines (`2290` bytes)

**Classes:**
- `class TextureData` - *Top-down RGBA8 pixels with a stable name for reports and debugging.*
  - Method `.__post_init__()`
  - Method `.sha256()` - *Return a stable digest of the pixel payload.*
  - Method `.from_png(path, name)` - *Load an 8-bit RGBA non-interlaced PNG through the dependency-free reader.*
  - Method `.checker(size, dark, light, cell, name)` - *Build a deterministic RGBA checker texture without an image file.*

---

### [`keystone/triggers.py`](keystone/triggers.py)
> *Game-agnostic trigger volumes with enter/exit tracking.*

**Size**: `49` lines (`1458` bytes)

**Classes:**
- `class TriggerVolume` - *A named AABB that reports when a body enters or leaves it.*
  - Method `.__post_init__()`
  - Method `.contains(body)`
- `class TriggerEvents` - *The enter, exit and active sets for one tracker update.*
- `class TriggerTracker` - *Remember active trigger names across updates.*
  - Method `.update(body, volumes)`
  - Method `.reset()`

---

### [`keystone/ui/__init__.py`](keystone/ui/__init__.py)
> *Dependency-free human UI: bitmap font, canvas and HUD overlay.*

**Size**: `7` lines (`287` bytes)

---

### [`keystone/ui/canvas.py`](keystone/ui/canvas.py)
> *Screen-space 2D canvas built from clipped color quads and bitmap text.*

**Size**: `124` lines (`4348` bytes)

**Classes:**
- `class TextElement` - *One text draw call recorded for AI/UI reports.*
- `class ButtonElement` - *One interactive button recorded for AI/UI reports.*
- `class Canvas` - *Collects UI quads in top-left pixel coordinates and flattens them for GL.*
  - Method `.__init__(width, height)`
  - Property `.labels` - *Return the drawn text values in draw order.*
  - Method `._add(x, y, width, height, color)`
  - Method `.rect(x, y, width, height, color)` - *Append an axis-aligned filled rectangle, clipped to the canvas.*
  - Method `.text(x, y, text, color, scale)` - *Append bitmap text; lowercase is drawn as uppercase.*
  - Method `.add_button(x, y, width, height, label, action, selected, hovered)` - *Record button metadata; drawing stays with the widgets module.*
  - Method `.vertices()` - *Return interleaved x, y, r, g, b, a vertices for six triangles per quad.*
  - Method `.measured_height(scale)` - *Return the line height matching a text call at the same scale.*

---

### [`keystone/ui/font.py`](keystone/ui/font.py)
> *Embedded 5x7 bitmap font for the dependency-free human overlay.*

**Size**: `88` lines (`4940` bytes)

**Functions:**
- `def glyph(character)` - *Return the 7x5 rows for one character; lowercase maps to uppercase.*
- `def text_width(text, scale)` - *Return the pixel width of text, excluding trailing tracking.*
- `def line_height(scale)` - *Return the pixel height of one uppercase text line.*
- `def truncate_text(text, width, scale)` - *Trim text so it fits width pixels, leaving room for an ellipsis-free cut.*

---

### [`keystone/ui/menu.py`](keystone/ui/menu.py)
> *Game-agnostic pause menu state: items, selection and activation.*

**Size**: `39` lines (`1044` bytes)

**Classes:**
- `class MenuItem` - *One labelled action the human can choose.*
- `class PauseMenu` - *Wraps selection over a fixed item list; contains no rendering or input.*
  - Method `.__init__(items)`
  - Method `.move(delta)` - *Move the selection by delta, wrapping at both ends.*
  - Method `.action()` - *Return the action of the selected item.*

---

### [`keystone/ui/overlay.py`](keystone/ui/overlay.py)
> *Game-agnostic human overlay: HUD, controls help and pause menu.*

**Size**: `142` lines (`5975` bytes)

**Classes:**
- `class HudState` - *Presentation-only snapshot the overlay needs for one frame.*
- `class HumanOverlay` - *Builds the pixel UI, pause menu and button hitboxes.*
  - Method `.__init__()`
  - Method `.toggle()`
  - Method `.hit_test(x, y)` - *Return the action of the button under the pointer, if any.*
  - Method `._menu(canvas, state, scale, line)`
  - Method `.build(state, game_draw)`

---

### [`keystone/ui/report.py`](keystone/ui/report.py)
> *Serialize a rendered UI canvas into machine-readable report metadata.*

**Size**: `38` lines (`1208` bytes)

**Functions:**
- `def describe_canvas(canvas, paused, visible)` - *Return stable top-left pixel metadata for labels and buttons.*

---

### [`keystone/ui/widgets.py`](keystone/ui/widgets.py)
> *Small immediate-mode UI widgets: panels and labelled buttons.*

**Size**: `43` lines (`1436` bytes)

**Functions:**
- `def panel(canvas, x, y, width, height, color)` - *Draw a background panel; non-positive sizes are ignored.*
- `def button(canvas, x, y, width, height, label, scale, selected, hovered)` - *Draw one menu button with selected and pointer-hover states.*

---

### [`keystone/web/__init__.py`](keystone/web/__init__.py)
> *Local web console and JSON API for Keystone.*

**Size**: `19` lines (`641` bytes)

**Functions:**
- `def __getattr__(name)`

---

### [`keystone/web/scene.py`](keystone/web/scene.py)
> *Export a game-agnostic scene as a JSON document for the browser viewer.*

**Size**: `127` lines (`4395` bytes)

**Functions:**
- `def _floats(values)`
- `def _mesh_document(mesh)`
- `def _texture_document(texture)`
- `def scene_document(scene, game)` - *Serialize one scene into a deterministic, viewer-ready document.*

---

### [`keystone/web/schema.py`](keystone/web/schema.py)
> *Versioned schemas shared by the web API, AI clients and the browser viewer.*

**Size**: `27` lines (`1310` bytes)

---

### [`keystone/web/server.py`](keystone/web/server.py)
> *A localhost JSON API and static web console for the game-agnostic engine.*

**Size**: `284` lines (`12025` bytes)

**Classes:**
- `class WebProblem` - *One client-facing error with an actionable fix.*
  - Method `.__init__(status, why, fix)`
- `class GameSession` - *One in-memory game guarded by a lock for concurrent HTTP requests.*
  - Method `.__init__(game)`
  - Property `.name`
  - Method `.describe()`
  - Method `.simulate(frames, actions, step, trace)`
  - Method `.scene()`
- `class KeystoneHTTPServer` - *Threaded server carrying one game session for the request handler.*
  - Method `.__init__(address, session)`
  - Method `.handle_error(request, client_address)`
- `class ConsoleHandler` - *Serve the API and the bundled static console.*
  - Method `.log_message(format, *args)`
  - Method `.do_OPTIONS()`
  - Method `.do_GET()`
  - Method `.do_POST()`
  - Method `.do_PUT()`
  - Method `.do_PATCH()`
  - Method `.do_DELETE()`
  - Property `.session`
  - Method `._index()`
  - Method `._health()`
  - Method `._read_json()`
  - Method `._send_file(name)`
  - Method `._send_problem(problem)`
  - Method `._method_not_allowed()`
  - Method `._send_json(status, payload)`
  - Method `._send(status, body, content_type)`

**Functions:**
- `def create_server(game, host, port)` - *Create a bound server; port 0 asks the OS for a free port.*
- `def serve(game, host, port)` - *Run the local console until interrupted.*

---

### [`tests/test_analysis.py`](tests/test_analysis.py)
> *Tests for the machine-readable frame report.*

**Size**: `245` lines (`10158` bytes)

**Classes:**
- `class Health`
- `class AnalysisTest`
  - Method `.test_pixel_stats_and_content_bbox()`
  - Method `.test_scene_nodes_have_projected_screen_bounds()`
  - Method `.test_material_and_texture_metadata_are_reported()`
  - Method `.test_scene_identity_metadata_is_reported()`
  - Method `.test_png_hash_and_atomic_report()`
  - Method `.test_compare_reports_detects_image_and_stats_changes()`
  - Method `.test_ui_metadata_is_hashed_and_compared()`
  - Method `.test_compare_reports_accepts_older_schemas()`
  - Method `.test_compare_reports_detects_identity_metadata_changes()`
  - Method `.test_compare_reports_distinguishes_duplicate_names_by_id()`
  - Method `.test_compare_reports_detects_material_changes()`
  - Method `.test_compare_reports_rejects_unknown_schema()`
  - Method `.test_pixel_diff_writes_an_artifact_and_stats()`
  - Method `.test_pixel_diff_rejects_dimension_mismatch()`
  - Method `.test_rejects_bad_pixel_count()`

---

### [`tests/test_app.py`](tests/test_app.py)
> *Tests for the game-agnostic engine loop and CLI.*

**Size**: `276` lines (`12485` bytes)

**Classes:**
- `class HudCube`
  - Method `.draw_ui(canvas, _state)`
- `class EngineTest`
  - Method `.test_headless_engine_runs_fixed_steps_and_saves_a_png()`
  - Method `.test_ui_overlay_changes_the_captured_frame()`
  - Method `.test_pause_stops_updates_but_keeps_rendering()`
  - Method `.test_ui_actions_are_drivable_without_real_input()`
  - Method `.test_game_ui_hook_adds_pixels_to_the_capture()`
  - Method `.test_bad_size_is_a_usage_error()`
  - Method `.test_out_requires_headless()`
  - Method `.test_ui_flags_are_limited_to_rendered_runs()`
  - Method `.test_serve_is_a_standalone_web_command()`
  - Method `.test_web_flags_require_serve()`
  - Method `.test_bad_web_port_is_a_usage_error()`
  - Method `.test_headless_ui_capture_writes_a_report()`
  - Method `.test_start_paused_headless_report_describes_the_menu()`
  - Method `.test_bad_game_spec_reports_why_and_fix()`
  - Method `.test_describe_cli_prints_capabilities_without_opening_a_window()`
  - Method `.test_verify_determinism_cli_is_gpu_free()`
  - Method `.test_expect_hash_gate_matches_and_rejects()`
  - Method `.test_invalid_expected_hash_is_a_usage_error()`
  - Method `.test_simulate_cli_prints_json_without_opening_a_window()`
  - Method `.test_simulate_cli_reads_actions_and_writes_output()`
  - Method `.test_compare_baseline_cli_exits_zero_and_writes_diff()`
  - Method `.test_capture_report_and_png()`

---

### [`tests/test_boundary.py`](tests/test_boundary.py)
> *Boundary test: the engine core contains no game rules or imports.*

**Size**: `65` lines (`2391` bytes)

**Classes:**
- `class CoreBoundaryTest`
  - Method `.test_core_has_no_genre_modules()`
  - Method `.test_core_does_not_import_the_web_adapter()`
  - Method `.test_core_imports_only_core_modules()`

---

### [`tests/test_broadphase.py`](tests/test_broadphase.py)
> *Tests for the deterministic spatial-grid broadphase.*

**Size**: `68` lines (`2910` bytes)

**Classes:**
- `class SpatialGridTest`
  - Method `.test_query_returns_true_overlaps_in_insertion_order()`
  - Method `.test_same_cell_candidates_are_still_filtered()`
  - Method `.test_update_moves_a_proxy_and_remove_deletes_it()`
  - Method `.test_negative_coordinates_and_large_boxes_use_multiple_cells()`
  - Method `.test_pairs_are_unique_and_ordered_by_insertion()`
  - Method `.test_clear_and_validation()`

---

### [`tests/test_character.py`](tests/test_character.py)
> *Tests for the AABB character controller.*

**Size**: `60` lines (`2475` bytes)

**Classes:**
- `class CharacterControllerTest`
  - Method `.test_body_exposes_its_collision_box()`
  - Method `.test_character_falls_and_rests_on_a_floor()`
  - Method `.test_character_stops_at_a_wall_without_tunneling()`
  - Method `.test_jump_leaves_the_ground()`
  - Method `.test_character_rejects_invalid_configuration_and_step()`

---

### [`tests/test_clock.py`](tests/test_clock.py)
> *Tests for the fixed-step clock.*

**Size**: `31` lines (`965` bytes)

**Classes:**
- `class FixedStepClockTest`
  - Method `.test_releases_whole_steps_and_bounds_catch_up()`
  - Method `.test_reset_drops_accumulator()`
  - Method `.test_invalid_configuration()`

---

### [`tests/test_geometry.py`](tests/test_geometry.py)
> *Unit tests for indexed meshes, built-in primitives and the OBJ loader.*

**Size**: `205` lines (`7279` bytes)

**Classes:**
- `class MeshDataTest`
  - Method `.test_rejects_mismatched_attribute_counts()`
  - Method `.test_rejects_out_of_range_index()`
  - Method `.test_bounds_and_counts()`
  - Method `.test_interleaved_has_eleven_floats_per_vertex()`
  - Method `.test_vertex_colors_follow_the_uvs()`
  - Method `.test_rejects_mismatched_vertex_colors()`
- `class PrimitiveTest`
  - Method `.test_cube_normals_are_unit_and_outward()`
  - Method `.test_plane_faces_up_with_six_indices()`
  - Method `.test_sphere_positions_lie_on_radius_and_normals_are_unit()`
  - Method `.test_primitives_reject_invalid_sizes()`
  - Method `.test_cone_and_cylinder_are_unit_and_bounded()`
- `class MeshBuilderTest`
  - Method `.test_box_has_24_vertices_and_36_indices()`
  - Method `.test_quad_normal_follows_winding()`
  - Method `.test_degenerate_quad_is_rejected()`
  - Method `.test_add_mesh_merges_counts_and_offsets()`
- `class ObjLoaderTest`
  - Method `.test_quad_is_triangulated()`
  - Method `.test_normals_are_computed_when_absent()`
  - Method `.test_authored_normals_are_kept()`
  - Method `.test_negative_indices_are_relative()`
  - Method `.test_missing_file_raises_file_not_found()`
  - Method `.test_bad_index_raises_value_error()`
  - Method `.test_file_round_trip()`
- `class MaterialTest`
  - Method `.test_defaults_are_valid()`
  - Method `.test_rejects_negative_specular()`
  - Method `.test_rejects_negative_checker_scale()`

---

### [`tests/test_headless.py`](tests/test_headless.py)
> *Tests for no-OpenGL simulation and action scripts.*

**Size**: `47` lines (`1839` bytes)

**Classes:**
- `class HeadlessTest`
  - Method `.test_simulation_advances_without_a_window()`
  - Method `.test_same_script_is_deterministic()`
  - Method `.test_trace_contains_each_frame()`
  - Method `.test_load_actions_accepts_list_and_object()`
  - Method `.test_invalid_frames_and_step()`

---

### [`tests/test_input.py`](tests/test_input.py)
> *Tests for input sampling and action state.*

**Size**: `86` lines (`2836` bytes)

**Classes:**
- `class FakeContext`
  - Method `.__init__()`
  - Method `.key_down(key)`
  - Method `.cursor_position()`
  - Method `.mouse_down(button)`
- `class InputMapTest`
  - Method `.test_axes_and_pressed_edges()`
  - Method `.test_custom_binding()`
  - Method `.test_mouse_delta_feeds_look()`
  - Method `.test_disabled_mouse_ignores_pointer()`
  - Method `.test_mouse_click_is_a_single_frame_edge()`
  - Method `.test_action_state_round_trip_and_clear()`

---

### [`tests/test_math3d.py`](tests/test_math3d.py)
> *Unit tests for the Keystone 3D math core.*

**Size**: `128` lines (`4929` bytes)

**Classes:**
- `class Vec3Test`
  - Method `.test_arithmetic_and_dot()`
  - Method `.test_cross_follows_right_hand_rule()`
  - Method `.test_normalized_is_unit_and_zero_safe()`
  - Method `.test_lerp_hits_both_ends()`
- `class Mat4Test`
  - Method `.test_identity_leaves_points_and_matrices_unchanged()`
  - Method `.test_translation_and_scale_apply_in_order()`
  - Method `.test_rotation_z_90_degrees()`
  - Method `.test_direction_ignores_translation()`
  - Method `.test_inverse_round_trips_affine_matrix()`
  - Method `.test_inverse_rejects_projective_matrix()`
  - Method `.test_perspective_maps_near_and_far_to_ndc()`
  - Method `.test_perspective_rejects_invalid_fov()`
  - Method `.test_look_at_puts_eye_at_origin()`
  - Method `.test_look_at_rejects_degenerate_input()`
  - Method `.test_flat_is_column_major_for_opengl()`
- `class QuatTest`
  - Method `.test_axis_angle_rotates_a_vector()`
  - Method `.test_quaternion_matrix_matches_matrix_rotation()`
  - Method `.test_multiplication_composes_in_order()`
  - Method `.test_slerp_endpoints()`

---

### [`tests/test_physics.py`](tests/test_physics.py)
> *Tests for generic ray and collision primitives.*

**Size**: `77` lines (`2972` bytes)

**Classes:**
- `class PhysicsTest`
  - Method `.test_ray_hits_aabb_and_sphere()`
  - Method `.test_rays_miss()`
  - Method `.test_ray_validation()`
  - Method `.test_overlap_and_sphere_pushout()`
  - Method `.test_non_overlapping_sphere_is_unchanged()`
  - Method `.test_aabb_helpers_are_consistent_with_overlap()`
  - Method `.test_raycast_returns_the_nearest_hit()`
  - Method `.test_raycast_filter_can_skip_candidates()`

---

### [`tests/test_plugin.py`](tests/test_plugin.py)
> *Tests for the GameModule contract and loader.*

**Size**: `55` lines (`2090` bytes)

**Classes:**
- `class PluginTest`
  - Method `.test_sample_loads_and_implements_the_contract()`
  - Method `.test_describe_exposes_capabilities_actions_and_snapshot()`
  - Method `.test_describe_reports_a_game_ui_hook()`
  - Method `.test_invalid_specs_are_rejected()`
  - Method `.test_missing_methods_are_rejected()`
- `class IncompleteGame`
  - Method `.build_scene()`

---

### [`tests/test_png.py`](tests/test_png.py)
> *Unit tests for the stdlib PNG writer used by headless screenshots.*

**Size**: `82` lines (`2902` bytes)

**Classes:**
- `class PngTest`
  - Method `.test_round_trip_pixels_and_header()`
  - Method `.test_rejects_wrong_pixel_count()`
  - Method `.test_reader_round_trips_writer_pixels()`
  - Method `.test_reader_rejects_non_png()`
  - Method `.test_creates_missing_parent_directory()`

**Functions:**
- `def _chunks(data)`

---

### [`tests/test_renderer.py`](tests/test_renderer.py)
> *Headless OpenGL integration tests for the Keystone renderer.*

**Size**: `134` lines (`4911` bytes)

**Classes:**
- `class RendererIntegrationTest`
  - Method `.setUp()`
  - Method `.test_render_fills_the_center_with_a_lit_surface()`
  - Method `.test_empty_scene_draws_a_vertical_sky_gradient()`
  - Method `.test_point_light_lights_a_surface_when_the_sun_is_off()`
  - Method `.test_textured_plane_samples_the_texture()`
  - Method `.test_screenshot_is_a_real_png()`
  - Method `.test_shader_compile_error_explains_why_and_fix()`
- `class VersionGateTest`
  - Method `.test_rejects_old_opengl()`
  - Method `.test_accepts_33_and_newer()`

**Functions:**
- `def build_scene()`

---

### [`tests/test_replay.py`](tests/test_replay.py)
> *Tests for deterministic action logs and stable hashes.*

**Size**: `32` lines (`1120` bytes)

**Classes:**
- `class ReplayTest`
  - Method `.test_hash_ignores_mapping_order()`
  - Method `.test_command_log_round_trip()`
  - Method `.test_invalid_step_is_rejected()`

---

### [`tests/test_samples.py`](tests/test_samples.py)
> *Tests for the engine's sample game.*

**Size**: `43` lines (`1372` bytes)

**Classes:**
- `class SampleTest`
  - Method `.test_scene_contains_only_generic_renderables()`
  - Method `.test_update_rotates_cubes_and_moves_the_camera()`
  - Method `.test_actions_schema_is_generic()`

---

### [`tests/test_scene.py`](tests/test_scene.py)
> *Unit tests for the Keystone scene graph and perspective camera.*

**Size**: `243` lines (`9112` bytes)

**Classes:**
- `class Health`
- `class TransformTest`
  - Method `.test_matrix_applies_scale_then_rotation_then_translation()`
  - Method `.test_default_transform_is_identity()`
- `class NodeTest`
  - Method `.test_child_world_matrix_composes_with_parent()`
  - Method `.test_add_child_reparents_instead_of_duplicating()`
  - Method `.test_remove_child_clears_parent()`
  - Method `.test_traverse_is_depth_first_in_insertion_order()`
  - Method `.test_add_child_rejects_self_and_cycles()`
  - Method `.test_remove_child_rejects_a_stranger()`
  - Method `.test_world_visible_respects_hidden_ancestor()`
- `class NodeIdentityTest`
  - Method `.test_scene_assigns_unique_ids_on_attach()`
  - Method `.test_ids_are_scene_local_and_survive_reparenting()`
  - Method `.test_explicit_id_is_preserved_and_findable()`
  - Method `.test_duplicate_explicit_id_is_rejected_without_attaching()`
  - Method `.test_tags_are_copied_and_queryable()`
  - Method `.test_layer_and_component_queries_filter_attached_nodes()`
  - Method `.test_component_access_and_removal()`
  - Method `.test_invalid_identity_fields_are_rejected()`
- `class CameraTest`
  - Method `.test_forward_yaw_zero_is_minus_z()`
  - Method `.test_forward_yaw_90_points_positive_x()`
  - Method `.test_view_puts_camera_origin_at_world_position()`
  - Method `.test_projection_aspect_changes_horizontal_extent()`
  - Method `.test_move_follows_forward_direction()`
  - Method `.test_rotate_clamps_pitch()`
  - Method `.test_look_at_rejects_its_own_position()`
  - Method `.test_projection_rejects_invalid_aspect()`
  - Method `.test_look_at_points_forward_at_target()`
- `class SceneTest`
  - Method `.test_scene_traverse_starts_at_root()`
  - Method `.test_scene_has_a_sky_color_distinct_from_the_horizon()`
  - Method `.test_point_light_validates_its_radius_and_intensity()`
  - Method `.test_directional_light_normalizes_lookup_direction()`

---

### [`tests/test_serialization.py`](tests/test_serialization.py)
> *Tests for atomic JSON persistence.*

**Size**: `27` lines (`980` bytes)

**Classes:**
- `class SerializationTest`
  - Method `.test_round_trip_and_backup()`
  - Method `.test_missing_file_raises()`

---

### [`tests/test_testing.py`](tests/test_testing.py)
> *Tests for deterministic AI/CI scenario helpers.*

**Size**: `31` lines (`1174` bytes)

**Classes:**
- `class TestingHelpersTest`
  - Method `.test_run_script_uses_action_count_by_default()`
  - Method `.test_verify_determinism_passes_for_the_sample()`
  - Method `.test_assert_deterministic_returns_evidence()`
  - Method `.test_trace_mode_is_available()`

---

### [`tests/test_texture.py`](tests/test_texture.py)
> *Tests for immutable texture data and texture sources.*

**Size**: `51` lines (`1776` bytes)

**Classes:**
- `class TextureDataTest`
  - Method `.test_checker_is_deterministic_and_has_expected_shape()`
  - Method `.test_png_round_trip_keeps_pixels()`
  - Method `.test_bad_texture_data_is_rejected()`

---

### [`tests/test_triggers.py`](tests/test_triggers.py)
> *Tests for trigger volumes and enter/exit tracking.*

**Size**: `48` lines (`2043` bytes)

**Classes:**
- `class TriggerTest`
  - Method `.test_trigger_volume_validates_its_name_and_overlap()`
  - Method `.test_tracker_reports_enter_stay_and_exit()`
  - Method `.test_tracker_handles_multiple_volumes_in_sorted_order()`

---

### [`tests/test_ui.py`](tests/test_ui.py)
> *Tests for the dependency-free human UI primitives and overlay.*

**Size**: `144` lines (`5961` bytes)

**Classes:**
- `class FontTest`
  - Method `.test_metrics_match_the_bitmap_grid()`
  - Method `.test_lowercase_and_unknown_characters_are_supported()`
- `class CanvasTest`
  - Method `.test_rect_is_clipped_to_canvas_bounds()`
  - Method `.test_text_records_labels_and_stays_inside_the_canvas()`
  - Method `.test_invalid_geometry_is_rejected()`
- `class MenuTest`
  - Method `.test_selection_wraps_and_returns_actions()`
  - Method `.test_custom_items_and_empty_menu()`
- `class OverlayTest`
  - Method `.test_overlay_shows_game_status_and_metrics()`
  - Method `.test_pause_banner_and_hidden_overlay()`
  - Method `.test_game_ui_draws_beneath_the_engine_hud()`
  - Method `.test_pause_menu_buttons_are_hit_testable()`
  - Method `.test_canvas_metadata_is_report_ready()`
  - Method `.test_compact_layout_uses_smaller_text()`
  - Method `.test_tiny_canvas_is_clipped_without_errors()`

**Functions:**
- `def state(**overrides)`

---

### [`tests/test_web.py`](tests/test_web.py)
> *Tests for scene export, the local JSON API and the browser console assets.*

**Size**: `193` lines (`8398` bytes)

**Classes:**
- `class Health`
- `class SceneDocumentTest`
  - Method `.test_sample_scene_document_has_identity_geometry_and_texture()`
  - Method `.test_world_matrices_and_mesh_references_are_exported()`
  - Method `.test_shared_meshes_are_exported_once()`
  - Method `.test_node_identity_metadata_is_exported()`
  - Method `.test_scene_document_is_deterministic()`
  - Method `.test_schema_describes_export_fields()`
  - Method `.test_public_web_exports_are_available()`
- `class WebServerTest`
  - Method `.setUp()`
  - Method `._stop()`
  - Method `._request(path, method, payload)`
  - Method `._json(path, method, payload)`
  - Method `.test_health_and_cors()`
  - Method `.test_describe_includes_the_web_capability()`
  - Method `.test_scene_endpoint_returns_the_scene_document()`
  - Method `.test_simulate_endpoint_returns_a_deterministic_result()`
  - Method `.test_options_preflight_and_static_assets()`
  - Method `.test_api_index_and_errors_are_json()`

---
