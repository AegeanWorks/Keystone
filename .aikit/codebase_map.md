# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `53`
- **Total Classes**: `80`
- **Total Top-Level Functions**: `55`
- **Total Class Methods**: `458`
- **Total Source Lines**: `6606`

---

## 📦 Modules & Exported Symbols

### [`keystone/__init__.py`](keystone/__init__.py)
> *Keystone: a performance-first 3D game engine with an OpenGL 3.3 renderer.*

**Size**: `6` lines (`184` bytes)

---

### [`keystone/__main__.py`](keystone/__main__.py)
> *Command-line entry point for the Keystone demo.*

**Size**: `135` lines (`5287` bytes)

**Functions:**
- `def _size(text)`
- `def _frames(text)`
- `def _seed(text)`
- `def main(argv)`

---

### [`keystone/app.py`](keystone/app.py)
> *Engine runtime: window loop, fly controls and screenshot capture.*

**Size**: `132` lines (`4876` bytes)

**Classes:**
- `class Engine` - *Bind one scene to one OpenGL context and drive the frame loop.*
  - Method `.__init__(scene, width, height, visible, msaa, title)`
  - Method `.__enter__()`
  - Method `.__exit__(*exc_info)`
  - Method `._process_input(dt)`
  - Method `.run(update, max_frames, controls, status)` - *Render until the window closes or max_frames (0 = unlimited) is reached.*
  - Method `.screenshot(path)`
  - Method `.close()`

---

### [`keystone/atmosphere.py`](keystone/atmosphere.py)
> *Day/night atmosphere derived from a normalized world clock.*

**Size**: `63` lines (`2110` bytes)

**Classes:**
- `class Atmosphere` - *Lighting and sky colors for one moment of the day.*
  - Method `.at(day_fraction)`

**Functions:**
- `def apply_atmosphere(scene, atmosphere)`

---

### [`keystone/beams.py`](keystone/beams.py)
> *Deterministic 2D light-routing lock: mirrors, dye, color masks and receivers.*

**Size**: `128` lines (`4479` bytes)

**Classes:**
- `class BeamSegment`
- `class LightLock` - *A fixed five-cell light circuit whose mirrors seal the crypt portal.*
  - Method `.__init__(seed, origin)`
  - Method `.in_bounds(x, z)`
  - Method `.trace()`
  - Property `.solved`
  - Method `.rotate(x, z)`
  - Method `.set_orientation(x, z, orientation)`
  - Method `.nearest_mirror(world_x, world_z, radius)`
  - Method `.snapshot()`

**Functions:**
- `def mask_to_rgb(mask)`

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

### [`keystone/combat.py`](keystone/combat.py)
> *Deterministic survivors-style combat: archetypes, waves, auto-fire and bosses.*

**Size**: `240` lines (`8380` bytes)

**Classes:**
- `class EnemySpec`
- `class Enemy`
- `class Combat` - *Combat director owned by the world; no rendering, no wall clock.*
  - Method `.__post_init__()`
  - Method `.spawn_around(x, z, standable, facing)` - *Reset the arena around the player after a mode change or death.*
  - Method `.update(dt, px, pz, standable)`
  - Method `.revive(x, z, standable, facing)`
  - Method `.spawn_at(key, x, z)`
  - Method `.snapshot()`
  - Method `.status()`
  - Method `._pick_type()`
  - Method `._spawn_at_ring(x, z, standable, key, angle, radius)`
  - Method `._attack(px, pz)`
  - Method `._move_enemy(enemy, dx, dz, standable)`
  - Method `._remove_dead()`

---

### [`keystone/demo.py`](keystone/demo.py)
> *Built-in demo scene: a lit platform, an orbiting ring and a spinning crystal.*

**Size**: `111` lines (`3997` bytes)

**Classes:**
- `class Demo` - *A deterministic scene plus the animation applied by the engine loop.*
  - Method `.__init__()`
  - Method `.update(dt)`

---

### [`keystone/expedition.py`](keystone/expedition.py)
> *First-person expedition: procedural overworld, dungeon and scene assembly.*

**Size**: `516` lines (`21579` bytes)

**Classes:**
- `class Expedition` - *Owns one seeded World and the scene that renders its current mode.*
  - Method `.__init__(seed, size, layout)`
  - Method `._build_scenery_meshes()`
  - Method `._distance_to_path(x, z)`
  - Method `._build_dungeon_meshes()`
  - Method `._rebuild()`
  - Method `._build_overworld()`
  - Method `._add_portal()`
  - Method `._add_light_lock()`
  - Method `._build_dungeon()`
  - Method `._add_network()`
  - Method `._apply_visuals()`
  - Method `._sync_enemies()`
  - Method `.status()`
  - Method `.step(dt, intent)`
  - Method `.update(dt)`
  - Method `.handle_input(dt, context)`

---

### [`keystone/geometry.py`](keystone/geometry.py)
> *Indexed triangle mesh data and surface material, independent of any GPU API.*

**Size**: `71` lines (`2774` bytes)

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

**Size**: `143` lines (`4890` bytes)

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

**Size**: `220` lines (`8286` bytes)

**Classes:**
- `class Renderer` - *Owns the shader and per-mesh GPU buffers for one OpenGL context.*
  - Method `.__init__(width, height)`
  - Method `.resize(width, height)`
  - Method `._gpu_mesh(mesh)`
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

**Size**: `80` lines (`3054` bytes)

**Classes:**
- `class ShaderProgram` - *A linked vertex/fragment program with cached uniform locations.*
  - Method `.__init__(vertex_source, fragment_source)`
  - Method `._compile(stage, source, label)`
  - Method `.use()`
  - Method `._location(name)`
  - Method `.set_mat4(name, matrix)`
  - Method `.set_mat3(name, values)`
  - Method `.set_vec3(name, vector)`
  - Method `.set_float(name, value)`
  - Method `.release()`

---

### [`keystone/harness.py`](keystone/harness.py)
> *Deterministic JSON harness for driving the expedition without a GPU.*

**Size**: `255` lines (`9755` bytes)

**Functions:**
- `def catalog()` - *Describe every action and the state an agent can observe.*
- `def _number(action, key, default)`
- `def _seconds(action)`
- `def apply_action(world, action)` - *Validate and apply one catalogued action to the world.*
- `def run_actions(seed, actions, size, layout)`
- `def selftest()` - *Prove determinism, seed sensitivity, collision and portal transitions.*
- `def _read_actions(path)`
- `def _seed_arg(text)`
- `def _size_arg(text)`
- `def _write_json(path, payload)`
- `def main(argv)`

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

### [`keystone/png.py`](keystone/png.py)
> *Minimal dependency-free PNG writer for headless frame captures.*

**Size**: `53` lines (`1739` bytes)

**Functions:**
- `def _chunk(kind, payload)`
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

### [`keystone/procedural/__init__.py`](keystone/procedural/__init__.py)
> *Seeded world generation: noise, heightfield terrain and dungeons.*

**Size**: `1` lines (`72` bytes)

---

### [`keystone/procedural/dungeon.py`](keystone/procedural/dungeon.py)
> *Seeded room-and-corridor dungeon generation with FOV and pathfinding.*

**Size**: `199` lines (`6777` bytes)

**Classes:**
- `class Tile`
- `class Room`
  - Property `.center`
  - Method `.intersects(other, padding)`
- `class Dungeon`
  - Method `.in_bounds(x, y)`
  - Method `.is_walkable(x, y)`
  - Method `.compute_fov(px, py, radius)` - *Symmetric raycasting with distance attenuation, as in Crypt-Crawler.*
  - Method `.find_path(start, goal)`
  - Method `.to_dict()`
- `class DungeonGenerator` - *Carve non-overlapping rooms and connect them with L-shaped corridors.*
  - Method `.__init__(width, height, min_room, max_room, max_rooms)`
  - Method `.generate(seed)`
  - Method `._carve_corridor(dungeon, start, end, rng)`
  - Method `._carve_h(dungeon, x0, x1, y)`
  - Method `._carve_v(dungeon, y0, y1, x)`

---

### [`keystone/procedural/network.py`](keystone/procedural/network.py)
> *Seeded cyber network: terminals, links, hack progress and a living alert.*

**Size**: `113` lines (`4041` bytes)

**Classes:**
- `class Terminal`
- `class Network`
  - Method `.__post_init__()`
  - Method `.generate(seed, dungeon, count)`
  - Property `.complete`
  - Property `.hacked_count`
  - Method `.terminal(terminal_id)`
  - Method `.near_terminal(x, z, radius)`
  - Method `.hack(terminal_id)`
  - Method `.update(dt)`
  - Method `.snapshot()`

---

### [`keystone/procedural/noise.py`](keystone/procedural/noise.py)
> *Deterministic integer-hash value noise and fractal sums (no global RNG).*

**Size**: `55` lines (`1441` bytes)

**Functions:**
- `def hash2i(ix, iy, seed)`
- `def rand01(ix, iy, seed)`
- `def _smooth(t)`
- `def value_noise(x, y, seed)`
- `def fbm(x, y, seed, octaves, lacunarity, gain)` - *Fractal Brownian motion in [0, 1], deterministic for a seed.*

---

### [`keystone/procedural/space.py`](keystone/procedural/space.py)
> *Seeded star systems, orbiting bodies and hyperlane connections.*

**Size**: `130` lines (`4101` bytes)

**Classes:**
- `class Body`
  - Method `.position(time)`
- `class StarSystem`
  - Property `.star`
  - Method `.body(body_id)`
- `class Galaxy`
  - Method `.generate(seed, count)`
  - Method `.system(system_id)`

**Functions:**
- `def body_snapshot(body, time)`

---

### [`keystone/procedural/terrain.py`](keystone/procedural/terrain.py)
> *Procedural island heightfield with per-vertex biome colors.*

**Size**: `147` lines (`5723` bytes)

**Classes:**
- `class Terrain` - *A square, island-shaped heightfield sampled once per grid point.*
  - Method `.generate(seed, size, water)`
  - Method `._find_spawn()`
  - Method `._find_entrance(spawn)`
  - Method `.height_at(x, z)` - *Bilinearly sample the heightfield at world coordinates.*
  - Method `.normal_at(x, z)`
  - Method `.is_water(x, z)`
  - Method `.is_walkable(x, z)`
  - Method `.color_at(x, z)`
  - Method `.mesh()`

---

### [`keystone/procedural/weave.py`](keystone/procedural/weave.py)
> *Weft-style Hamiltonian weave routes that become a chain of dungeon rooms.*

**Size**: `175` lines (`5946` bytes)

**Classes:**
- `class WeaveLayout`
  - Method `.generate(seed, cols, rows, threads)`
  - Method `._segment_index(step)`
  - Property `.width`
  - Property `.height`
  - Method `.room_for(cell)`
  - Method `.floor_color(x, z)`
  - Method `.to_dungeon()`
  - Method `._carve(tiles, start, end)`
  - Method `.snapshot()`

**Functions:**
- `def _neighbours(cell, cols, rows)`
- `def _remaining_connected(cols, rows, visited)`
- `def _search_path(cols, rows, rng, path, visited, nodes, total)`
- `def _hamiltonian_path(cols, rows, rng)`

---

### [`keystone/scene.py`](keystone/scene.py)
> *Scene graph: hierarchical transforms, visibility, camera and directional light.*

**Size**: `130` lines (`4162` bytes)

**Classes:**
- `class Transform` - *Translation, rotation and non-uniform scale composed as T * R * S.*
  - Method `.matrix()`
- `class Node` - *A named transform node with optional renderable payload and children.*
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
- `class Scene` - *Root node, active camera, one directional light and atmosphere settings.*
  - Method `.add(node)`
  - Method `.traverse()`

---

### [`keystone/sim/__init__.py`](keystone/sim/__init__.py)
> *Deterministic, renderer-independent simulation core.*

**Size**: `5` lines (`162` bytes)

---

### [`keystone/sim/world.py`](keystone/sim/world.py)
> *Seeded expedition state: player, terrain, dungeon, movement and replay hash.*

**Size**: `286` lines (`11410` bytes)

**Classes:**
- `class MoveIntent` - *One frame of player intent, in local forward/right and radians.*
- `class Player`
- `class World` - *The authoritative expedition state; it never imports OpenGL.*
  - Method `.__init__(seed, size, layout)`
  - Property `.day_fraction`
  - Property `.near_entrance`
  - Property `.near_exit`
  - Method `.eye_position()`
  - Method `.step(dt, intent)`
  - Method `._hack_nearby_terminal()`
  - Method `._spawn_hunter()`
  - Method `.rotate_mirror()`
  - Method `.interact()`
  - Method `._record(message)`
  - Method `._move(dx, dz)`
  - Method `.is_standable(x, z)` - *Public walkability query shared by combat and future mechanics.*
  - Method `._free(x, z)`
  - Method `._respawn()`
  - Method `._dungeon_free(x, z)`
  - Method `.snapshot()`
  - Method `.state_hash()`

---

### [`keystone/space.py`](keystone/space.py)
> *Renderer-independent space flight, body surveys and hyperlane jumps.*

**Size**: `142` lines (`5219` bytes)

**Classes:**
- `class Ship`
  - Method `.forward()`
- `class SpaceWorld`
  - Method `.__init__(seed)`
  - Property `.system`
  - Property `.scanned_count`
  - Property `.complete`
  - Method `.step(dt, intent)`
  - Method `.scan()`
  - Method `.jump()`
  - Method `._record(message)`
  - Method `.snapshot()`
  - Method `.state_hash()`
  - Method `.status()`

---

### [`keystone/space_expedition.py`](keystone/space_expedition.py)
> *First-person space scene and controls over the renderer-independent SpaceWorld.*

**Size**: `164` lines (`6333` bytes)

**Classes:**
- `class SpaceExpedition` - *A free-flight ship, an orbiting system and a jump gate.*
  - Method `.__init__(seed)`
  - Method `._build_starfield(seed)`
  - Method `._build_system()`
  - Method `._add_gate()`
  - Method `._sync()`
  - Method `.step(dt, intent)`
  - Method `.update(dt)`
  - Method `.handle_input(dt, context)`
  - Method `.status()`

---

### [`keystone/space_harness.py`](keystone/space_harness.py)
> *Deterministic JSON harness for the space mode.*

**Size**: `190` lines (`7182` bytes)

**Functions:**
- `def catalog()`
- `def _number(action, key, default)`
- `def _seconds(action)`
- `def apply_action(world, action)`
- `def run_actions(seed, actions)`
- `def selftest()`
- `def _read_actions(path)`
- `def _write_json(path, payload)`
- `def main(argv)`

---

### [`tests/test_app.py`](tests/test_app.py)
> *Integration tests for the engine loop, demo scene and CLI.*

**Size**: `80` lines (`3080` bytes)

**Classes:**
- `class DemoTest`
  - Method `.test_demo_scene_contains_renderables()`
  - Method `.test_update_rotates_and_bobs_over_time()`
- `class EngineTest`
  - Method `.test_headless_engine_runs_and_saves_a_png()`
- `class ExpeditionEngineTest`
  - Method `.test_headless_expedition_renders_and_saves_a_png()`
- `class CliTest`
  - Method `.test_bad_size_is_a_usage_error()`
  - Method `.test_out_requires_headless()`
  - Method `.test_bad_seed_is_a_usage_error()`
  - Method `.test_bad_layout_is_a_usage_error()`

---

### [`tests/test_beams.py`](tests/test_beams.py)
> *Tests for the deterministic light-lock puzzle.*

**Size**: `59` lines (`2029` bytes)

**Classes:**
- `class LightLockTest`
  - Method `.test_initial_state_is_unsolved()`
  - Method `.test_solution_routes_red_through_green_dye_to_the_receiver()`
  - Method `.test_wrong_orientation_stays_sealed()`
  - Method `.test_trace_terminates_on_a_cycle()`
  - Method `.test_rotate_toggles_orientation_and_version()`
  - Method `.test_nearest_mirror_uses_world_distance()`
  - Method `.test_snapshot_is_stable()`
  - Method `.test_mask_to_rgb()`

---

### [`tests/test_combat.py`](tests/test_combat.py)
> *Tests for the deterministic combat director.*

**Size**: `65` lines (`2185` bytes)

**Classes:**
- `class CombatTest`
  - Method `.make(seed)`
  - Method `.test_spawn_is_seeded_and_deterministic()`
  - Method `.test_auto_fire_kills_a_nearby_enemy()`
  - Method `.test_contact_damages_the_player()`
  - Method `.test_wave_five_spawns_a_boss()`
  - Method `.test_player_death_sets_the_flag()`
  - Method `.test_snapshot_is_stable_after_the_same_steps()`

**Functions:**
- `def flat(x, z)`

---

### [`tests/test_dungeon.py`](tests/test_dungeon.py)
> *Tests for seeded dungeon generation, field of view and pathfinding.*

**Size**: `88` lines (`2912` bytes)

**Classes:**
- `class DungeonGenerationTest`
  - Method `.setUp()`
  - Method `.test_same_seed_builds_the_same_dungeon()`
  - Method `.test_different_seeds_differ()`
  - Method `.test_spawn_and_exit_are_walkable()`
  - Method `.test_exit_is_reachable_from_spawn()`
  - Method `.test_to_dict_is_json_serializable()`
  - Method `.test_generator_rejects_tiny_maps()`
- `class DungeonVisibilityTest`
  - Method `.setUp()`
  - Method `.test_fov_contains_the_observer_and_near_floor()`
  - Method `.test_fov_is_blocked_by_a_wall()`
  - Method `.test_walls_and_out_of_bounds_are_not_walkable()`

---

### [`tests/test_expedition.py`](tests/test_expedition.py)
> *Tests for scene assembly and the expedition controller.*

**Size**: `131` lines (`6749` bytes)

**Classes:**
- `class ExpeditionSceneTest`
  - Method `.setUp()`
  - Method `.test_overworld_scene_has_terrain_water_trees_and_a_portal()`
  - Method `.test_rocks_leave_the_portal_path_clear()`
  - Method `.test_light_lock_scene_has_emitter_receiver_mirrors_and_beams()`
  - Method `.test_rotating_a_mirror_rebuilds_the_light_scene()`
  - Method `.test_camera_starts_at_the_player_eye()`
  - Method `.test_enemy_nodes_match_the_combat_state()`
  - Method `.test_step_advances_time_and_syncs_the_camera()`
  - Method `._solve_light_lock()`
  - Method `.test_entering_the_portal_switches_to_a_dungeon_scene()`
  - Method `.test_hacking_a_terminal_rebuilds_the_network_scene()`
  - Method `.test_atmosphere_reaches_the_scene()`
  - Method `.test_weave_layout_enters_a_colored_dungeon()`
  - Method `._solve_light_lock_for(expedition)`
  - Method `.test_dungeon_lighting_is_darker_than_daylight()`

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

### [`tests/test_harness.py`](tests/test_harness.py)
> *Tests for the deterministic JSON AI harness.*

**Size**: `112` lines (`4814` bytes)

**Classes:**
- `class HarnessApiTest`
  - Method `.test_catalog_describes_actions_and_state()`
  - Method `.test_actions_are_deterministic()`
  - Method `.test_seed_changes_the_run()`
  - Method `.test_layout_is_selected_and_reported()`
  - Method `.test_unknown_action_is_rejected()`
  - Method `.test_invalid_seconds_is_rejected()`
  - Method `.test_selftest_passes()`
- `class HarnessCliTest`
  - Method `.test_catalog_prints_json()`
  - Method `.test_run_reads_actions_and_writes_output()`
  - Method `.test_actions_file_with_a_utf8_bom_is_accepted()`
  - Method `.test_bad_seed_is_a_usage_error()`
  - Method `.test_bad_actions_print_a_triad()`

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

### [`tests/test_network.py`](tests/test_network.py)
> *Tests for the seeded cyber network and alert state.*

**Size**: `69` lines (`2915` bytes)

**Classes:**
- `class NetworkTest`
  - Method `.setUp()`
  - Method `.test_generates_reachable_terminals_outside_spawn_and_exit()`
  - Method `.test_same_seed_is_deterministic()`
  - Method `.test_hacking_needs_four_steps_and_raises_alert()`
  - Method `.test_alert_decays_over_time()`
  - Method `.test_complete_network()`
  - Method `.test_links_reference_known_terminals()`
  - Method `.test_unknown_terminal_is_rejected()`
  - Method `.test_near_terminal_uses_radius()`

---

### [`tests/test_png.py`](tests/test_png.py)
> *Unit tests for the stdlib PNG writer used by headless screenshots.*

**Size**: `63` lines (`2071` bytes)

**Classes:**
- `class PngTest`
  - Method `.test_round_trip_pixels_and_header()`
  - Method `.test_rejects_wrong_pixel_count()`
  - Method `.test_creates_missing_parent_directory()`

**Functions:**
- `def _chunks(data)`

---

### [`tests/test_procedural.py`](tests/test_procedural.py)
> *Tests for deterministic noise, heightfield terrain and day/night atmosphere.*

**Size**: `93` lines (`3540` bytes)

**Classes:**
- `class NoiseTest`
  - Method `.test_noise_is_deterministic_and_bounded()`
  - Method `.test_fbm_changes_with_seed()`
  - Method `.test_fbm_is_bounded()`
- `class TerrainTest`
  - Method `.setUp()`
  - Method `.test_same_seed_rebuilds_the_same_grid()`
  - Method `.test_mesh_is_colored_and_faces_up()`
  - Method `.test_height_at_grid_point_matches_the_grid()`
  - Method `.test_spawn_and_entrance_are_walkable()`
  - Method `.test_water_and_out_of_bounds_are_not_walkable()`
  - Method `.test_normals_are_unit_length()`
  - Method `.test_rejects_tiny_grids()`
- `class AtmosphereTest`
  - Method `.test_noon_is_bright_and_midnight_is_dark()`
  - Method `.test_dawn_is_warm()`
  - Method `.test_apply_updates_scene_light_and_sky()`
  - Method `.test_atmosphere_rejects_out_of_range_time()`

---

### [`tests/test_renderer.py`](tests/test_renderer.py)
> *Headless OpenGL integration tests for the Keystone renderer.*

**Size**: `107` lines (`3851` bytes)

**Classes:**
- `class RendererIntegrationTest`
  - Method `.setUp()`
  - Method `.test_render_fills_the_center_with_a_lit_surface()`
  - Method `.test_empty_scene_draws_a_vertical_sky_gradient()`
  - Method `.test_point_light_lights_a_surface_when_the_sun_is_off()`
  - Method `.test_screenshot_is_a_real_png()`
  - Method `.test_shader_compile_error_explains_why_and_fix()`
- `class VersionGateTest`
  - Method `.test_rejects_old_opengl()`
  - Method `.test_accepts_33_and_newer()`

**Functions:**
- `def build_scene()`

---

### [`tests/test_scene.py`](tests/test_scene.py)
> *Unit tests for the Keystone scene graph and perspective camera.*

**Size**: `158` lines (`5878` bytes)

**Classes:**
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

### [`tests/test_space.py`](tests/test_space.py)
> *Tests for seeded star systems, orbits and hyperlanes.*

**Size**: `50` lines (`2020` bytes)

**Classes:**
- `class GalaxyTest`
  - Method `.setUp()`
  - Method `.test_same_seed_is_deterministic()`
  - Method `.test_every_system_has_a_star_and_planets()`
  - Method `.test_hyperlanes_are_symmetric_and_connected()`
  - Method `.test_orbits_move_over_time_and_stars_stay_put()`
  - Method `.test_unknown_system_and_body_are_rejected()`
  - Method `.test_rejects_tiny_galaxies()`

---

### [`tests/test_space_expedition.py`](tests/test_space_expedition.py)
> *Tests for the space scene and controller.*

**Size**: `47` lines (`1901` bytes)

**Classes:**
- `class SpaceExpeditionTest`
  - Method `.setUp()`
  - Method `.test_scene_has_starfield_bodies_and_a_gate()`
  - Method `.test_camera_follows_the_ship()`
  - Method `.test_scanning_a_body_updates_the_scene_and_status()`
  - Method `.test_jump_rebuilds_the_system_scene()`

---

### [`tests/test_space_harness.py`](tests/test_space_harness.py)
> *Tests for the space harness.*

**Size**: `50` lines (`1933` bytes)

**Classes:**
- `class SpaceHarnessTest`
  - Method `.test_catalog_exposes_flight_scan_and_jump()`
  - Method `.test_actions_are_deterministic()`
  - Method `.test_invalid_action_is_rejected()`
  - Method `.test_selftest()`
  - Method `.test_cli_catalog_and_run()`

---

### [`tests/test_space_world.py`](tests/test_space_world.py)
> *Tests for space flight, scanning and hyperlane jumps.*

**Size**: `67` lines (`2621` bytes)

**Classes:**
- `class SpaceWorldTest`
  - Method `.setUp()`
  - Method `.test_seeded_galaxy_and_hash()`
  - Method `.test_forward_flight_moves_the_ship()`
  - Method `.test_nearby_body_scan_adds_credits_and_progress()`
  - Method `.test_scan_out_of_range_does_nothing()`
  - Method `.test_survey_completion_reports_the_gate()`
  - Method `.test_jump_requires_gate_and_changes_system()`
  - Method `.test_negative_dt_is_rejected()`
  - Method `.test_galaxy_is_connected()`

---

### [`tests/test_weave.py`](tests/test_weave.py)
> *Tests for the Weft-style Hamiltonian weave generator.*

**Size**: `52` lines (`2220` bytes)

**Classes:**
- `class WeaveLayoutTest`
  - Method `.setUp()`
  - Method `.test_path_covers_every_room_exactly_once()`
  - Method `.test_consecutive_rooms_are_orthogonal()`
  - Method `.test_segments_partition_the_path()`
  - Method `.test_same_seed_is_deterministic()`
  - Method `.test_dungeon_is_fully_connected()`
  - Method `.test_room_floors_carry_thread_colors()`
  - Method `.test_rejects_tiny_layouts()`

---

### [`tests/test_world.py`](tests/test_world.py)
> *Tests for the deterministic expedition simulation core.*

**Size**: `193` lines (`8290` bytes)

**Classes:**
- `class WorldDeterminismTest`
  - Method `.test_same_seed_and_actions_produce_the_same_hash()`
  - Method `.test_different_seed_produces_a_different_world()`
  - Method `.test_auto_layout_uses_crypt_for_odd_and_weave_for_even_seeds()`
  - Method `.test_forced_weave_layout_reaches_an_exit()`
  - Method `.test_invalid_layout_is_rejected()`
  - Method `.test_hash_changes_when_the_player_moves()`
- `class WorldMovementTest`
  - Method `.setUp()`
  - Method `.test_eye_height_follows_the_terrain()`
  - Method `.test_forward_moves_the_player()`
  - Method `.test_pitch_is_clamped()`
  - Method `.test_day_fraction_advances_with_time()`
  - Method `.test_negative_dt_is_rejected()`
  - Method `.test_death_respawns_at_the_safe_point()`
- `class WorldModeTest`
  - Method `.setUp()`
  - Method `._stand_at_entrance()`
  - Method `._solve_light_lock()`
  - Method `._complete_network()`
  - Method `.test_portal_is_sealed_until_the_light_lock_is_solved()`
  - Method `.test_mirror_rotation_changes_the_lock()`
  - Method `.test_interacting_at_the_portal_enters_the_dungeon()`
  - Method `.test_dungeon_walls_block_movement()`
  - Method `.test_exit_returns_to_the_overworld_portal()`
  - Method `.test_hacking_a_terminal_advances_the_network()`
  - Method `.test_high_alert_spawns_a_netwatch_hunter()`
  - Method `.test_interacting_away_from_the_portal_does_nothing()`

---
