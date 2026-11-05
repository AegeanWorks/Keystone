# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `118`
- **Total Classes**: `174`
- **Total Top-Level Functions**: `220`
- **Total Class Methods**: `981`
- **Total Source Lines**: `19188`

---

## 📦 Modules & Exported Symbols

### [`keystone/__init__.py`](keystone/__init__.py)
> *Keystone: a game-agnostic 3D engine core.*

**Size**: `165` lines (`3565` bytes)

**Functions:**
- `def __getattr__(name)`

---

### [`keystone/__main__.py`](keystone/__main__.py)
> *Command-line entry point for the game-agnostic Keystone engine.*

**Size**: `406` lines (`22924` bytes)

**Functions:**
- `def _size(text)`
- `def _frames(text)`
- `def _hash(text)`
- `def _port(text)`
- `def _seed(text)`
- `def main(argv)`

---

### [`keystone/agents.py`](keystone/agents.py)
> *AI observation/action adapters: seen, used, audited, verified and analyzed by AI.*

**Size**: `144` lines (`6164` bytes)

**Classes:**
- `class AuditTrail` - *Append-only, hash-chained audit log for AI-driven runs.*
  - Method `.record(kind, payload)`
  - Method `.verify()`

**Functions:**
- `def parse_actions(payload)` - *Validate LLM-produced JSON into a list of ActionState.*
- `def observe(game, frames, actions, step)` - *Build one auditable AI observation: discovery + deterministic simulation.*
- `def summarize_report(report, max_nodes)` - *Compress a schema-4/5 frame report into an LLM-sized observation summary.*

---

### [`keystone/analysis.py`](keystone/analysis.py)
> *Machine-readable frame reports for AI and headless UI analysis.*

**Size**: `557` lines (`23154` bytes)

**Functions:**
- `def _rows(pixels, width, height, flip)`
- `def _stats(pixels, width, height, background, flip)`
- `def _material_report(material)`
- `def _node_report(scene, width, height)`
- `def analyze_frame(scene, pixels, width, height, image_path, ui, fx)`
- `def _compare_ui(before, after)`
- `def _shadows_of(report)`
- `def _color_of(report)`
- `def _post_of(report)`
- `def _bloom_of(report)`
- `def _sprites_of(report)`
- `def _culling_of(report)`
- `def _fx_of(report)`
- `def compare_reports(before, after)` - *Compare schema-1/2/3/4/5/6/7/8/9/10/11 frame reports for AI-driven regression checks.*
- `def diff_images(before, after, output, threshold)` - *Write a visual diff PNG and return changed-pixel statistics.*
- `def write_report(path, report)`

---

### [`keystone/animation.py`](keystone/animation.py)
> *Deterministic, game-agnostic animation: keyframe clips, sampling and control.*

**Size**: `368` lines (`15816` bytes)

**Classes:**
- `class Track` - *One keyframed channel: sorted times with Vec3 or Quat values.*
  - Method `.__post_init__()`
  - Method `.duration()`
  - Method `.sample(time)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnimationClip` - *A named set of per-node tracks sharing one duration.*
  - Method `.__post_init__()`
  - Method `.duration()`
  - Method `.node_ids()`
  - Method `.sample(time)`
  - Method `.events_in_range(start, end)` - *Return event names with start < time <= end (loop callers split wraps).*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnimationController` - *Deterministic playback: advance time, loop, blend and write Transforms.*
  - Method `.add(clip)`
  - Method `.play(name, restart)`
  - Method `.crossfade(name, duration)` - *Blend from the current sampled pose into another clip over duration.*
  - Method `._moment()`
  - Method `.advance(dt)`
  - Method `.advance_with_events(dt)`

**Functions:**
- `def _check_times(times)`
- `def blend_poses(first, second, factor)` - *Blend two sampled poses; factor 0 returns first, 1 returns second.*
- `def apply_pose(scene, pose)` - *Write sampled Transforms onto nodes by id or name; return updated ids.*
- `def animation_report(controller)`

---

### [`keystone/app.py`](keystone/app.py)
> *Game-agnostic engine runtime: window, fixed step, input, render and capture.*

**Size**: `285` lines (`11038` bytes)

**Classes:**
- `class Engine` - *Owns the runtime around one external GameModule.*
  - Method `.__init__(game, width, height, visible, msaa, title, ui)`
  - Method `.__enter__()`
  - Method `.__exit__(*exc_info)`
  - Method `._set_capture(captured)`
  - Method `._handle_system_actions(actions)`
  - Method `.toggle_pause()` - *Pause or resume gameplay; release the cursor while the menu is open.*
  - Method `.apply_ui_action(action)` - *Run a named UI action; returns False when the action is unknown.*
  - Method `._game_particles()`
  - Method `._draw_ui()`
  - Method `.run(max_frames)` - *Run until the window closes or max_frames (0 = unlimited) is reached.*
  - Method `.capture(image_path, report_path)`
  - Method `.screenshot(path)`
  - Method `.close()`

---

### [`keystone/asset_io.py`](keystone/asset_io.py)
> *Disk-backed asset sources, default loaders and hot-reload reporting.*

**Size**: `125` lines (`4367` bytes)

**Classes:**
- `class AssetSource` - *One file-backed asset: where it came from, how to load it and its last stamp.*
  - Method `.__post_init__()`
- `class ReloadReport` - *Outcome of one synchronous registry refresh.*
  - Property `.ok` - *True when every checked source loaded and none disappeared.*
  - Method `.describe()` - *Return a JSON-safe report for logs and AI clients.*

**Functions:**
- `def default_loader(kind)` - *Return the built-in loader for a kind, or explain how to supply one.*
- `def kind_from_suffix(path)` - *Infer an asset kind from a .obj or .png path.*
- `def fingerprint(path)` - *Return (mtime_ns, size) for a readable path, or None when it is absent.*
- `def asset_kind(payload)` - *Return the registry kind of a payload object.*
- `def load_asset(kind, path, loader)` - *Load one source and prove the payload matches the declared kind.*

---

### [`keystone/assets.py`](keystone/assets.py)
> *Game-agnostic asset registry with stable ids, content hashes and dependencies.*

**Size**: `365` lines (`13978` bytes)

**Classes:**
- `class AssetRecord` - *One registered asset: a stable id, kind, immutable payload and content digest.*
  - Method `.__post_init__()`
  - Method `.describe()` - *Return a JSON-safe description for AI clients and diagnostics.*
- `class AssetRegistry` - *Caller-owned registry for meshes, materials and textures.*
  - Method `.__init__()`
  - Method `.__len__()`
  - Method `.__contains__(asset_id)`
  - Method `.__iter__()`
  - Method `.register(asset_id, payload, *, kind, source, dependencies, replace)` - *Register one asset, inferring its kind from the payload when omitted.*
  - Method `.register_file(asset_id, path, *, kind, loader, dependencies, replace)` - *Load a .obj or .png file, register it and bind it for hot reload.*
  - Method `.refresh()` - *Re-read every changed source and report reloaded, unchanged, failed and missing ids.*
  - Method `.get(asset_id)` - *Return one record, or None when the id is not registered.*
  - Method `.require(asset_id)` - *Return one record or raise a KeyError naming the missing asset.*
  - Method `.remove(asset_id)` - *Remove one record or raise a KeyError naming the missing asset.*
  - Method `.clear()`
  - Method `.ids(kind)` - *Return registered ids in insertion order, optionally filtered by kind.*
  - Method `.find_by_digest(sha256)` - *Return every record whose content digest matches, in insertion order.*
  - Method `.duplicates()` - *Return groups of ids that share one kind and content digest.*
  - Method `.missing_dependencies()` - *Return every (asset id, dependency id) pair whose dependency is absent.*
  - Method `.stats()` - *Return total and per-kind counts in a stable order.*
  - Method `.describe()` - *Return a JSON-safe registry document sorted by asset id.*

**Functions:**
- `def _validate_id(asset_id)`
- `def _validate_kind(kind)`
- `def _validate_dependency(asset_id, dependency)`
- `def _dependencies(asset_id, dependencies)`
- `def _digest(kind, payload)`
- `def _digest_mesh(mesh)`
- `def _digest_material(material)`

---

### [`keystone/audio.py`](keystone/audio.py)
> *Game-agnostic audio core: synth clips, bus mixer and WAV I/O.*

**Size**: `237` lines (`9560` bytes)

**Classes:**
- `class AudioClip` - *Immutable mono PCM clip in [-1, 1] with a fixed sample rate.*
  - Method `.__post_init__()`
  - Method `.duration()`
  - Method `.with_gain(gain)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Mixer` - *Named-bus mixer: voices route through per-bus gains into one deterministic mix.*
  - Method `.__post_init__()`
  - Method `.set_bus(bus, gain)`
  - Method `.play(clip, bus, gain, pitch)`
  - Method `.clear()`
  - Method `.voice_count()`
  - Method `.render()`

**Functions:**
- `def sine(frequency, duration, sample_rate, name)`
- `def square(frequency, duration, sample_rate, name)`
- `def noise(duration, seed, sample_rate, name)`
- `def mix_clips(clips)` - *Mix (clip, gain, pitch) voices deterministically; pitch resamples by index scaling.*
- `def _wav_write(clip)`
- `def write_wav(path, clip)`
- `def read_wav(path)`
- `def audio_report(clip, voices, buses)`

---

### [`keystone/batch.py`](keystone/batch.py)
> *Static batch planner: group draw nodes to cut draw calls without new deps.*

**Size**: `148` lines (`6293` bytes)

**Functions:**
- `def _skinned(mesh)` - *Whether a mesh deforms at render time and must never bake or merge.*
- `def plan_batches(scene)`
- `def merge_batches(scene, exclude)` - *Bake static groups into world-space meshes; animated ids stay separate.*

---

### [`keystone/broadphase.py`](keystone/broadphase.py)
> *Deterministic spatial-grid broadphase for nearby AABB candidates.*

**Size**: `136` lines (`5317` bytes)

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

**Size**: `64` lines (`2103` bytes)

**Classes:**
- `class PerspectiveCamera` - *A right-handed camera looking down -Z when yaw and pitch are zero.*
  - Method `.__post_init__()`
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

**Size**: `170` lines (`6308` bytes)

**Classes:**
- `class CharacterBody` - *An axis-aligned character body with velocity and ground state.*
  - Method `.__post_init__()`
  - Method `.box()`
- `class CharacterController` - *Resolve horizontal wish velocity and gravity against static AABBs.*
  - Method `.__post_init__()`
  - Method `.step(body, wish_velocity, dt, colliders, platform_velocity)` - *Advance one step; horizontal speed is the wish velocity, vertical is body velocity.*
  - Method `._try_step_up(position, half, amount_x, amount_z, colliders)`
  - Method `._move_axis(position, half, axis, amount, colliders)`

**Functions:**
- `def _component(vector, axis)`
- `def _with_axis(vector, axis, value)`
- `def _other_axes_overlap(position, half, box, axis)`

---

### [`keystone/clock.py`](keystone/clock.py)
> *Fixed-step clock with a bounded catch-up budget.*

**Size**: `42` lines (`1501` bytes)

**Classes:**
- `class FixedStepClock` - *Accumulates wall time and releases whole deterministic simulation steps.*
  - Method `.__init__(step, max_frame)`
  - Method `.reset(now)`
  - Method `.advance(now)`

---

### [`keystone/culling.py`](keystone/culling.py)
> *Deterministic CPU view-frustum culling for the core forward renderer.*

**Size**: `146` lines (`5605` bytes)

**Functions:**
- `def culling_enabled(scene)` - *Return whether frustum culling is requested for this scene.*
- `def extract_planes(view_projection)` - *Extract normalized (a, b, c, d) frustum planes, deterministic order.*
- `def world_bounds(mesh, model)` - *Return the world-space AABB of a mesh under an affine model matrix.*
- `def aabb_visible(low, high, planes)` - *Return True when an AABB touches or intersects every frustum plane.*
- `def model_visible(mesh, model, planes)` - *Return True when a mesh under an affine model matrix survives culling.*
- `def node_visible(node, planes)` - *Return True when a scene node survives frustum culling.*
- `def cull_scene(scene, width, height)` - *Return python ``id()`` values of frustum-visible nodes.*

---

### [`keystone/geometry.py`](keystone/geometry.py)
> *Indexed triangle mesh data and surface material, independent of any GPU API.*

**Size**: `175` lines (`8538` bytes)

**Classes:**
- `class Material` - *Blinn-Phong surface parameters with PBR extensions used by the renderer.*
  - Method `.__post_init__()`
- `class MeshData` - *Immutable indexed triangle mesh with optional UVs and skinning.*
  - Method `.__post_init__()`
  - Property `.skinned` - *Whether this mesh carries a bound skin palette.*
  - Method `.vertex_count()`
  - Method `.triangle_count()`
  - Method `.bounds()`
  - Method `.interleaved()` - *Pack position, normal and UV into one vertex stream for the GPU.*
  - Method `.interleaved_skinned()` - *Pack the base stream plus padded joints and weights for the GPU.*

**Functions:**
- `def _is_finite_number(value)`
- `def _check_triplets(name, values)`

---

### [`keystone/gltf/__init__.py`](keystone/gltf/__init__.py)
> *Dependency-free glTF 2.0 import for Keystone scenes.*

**Size**: `5` lines (`153` bytes)

---

### [`keystone/gltf/io.py`](keystone/gltf/io.py)
> *glTF source reading, buffers and typed accessor decoding.*

**Size**: `210` lines (`8510` bytes)

**Functions:**
- `def _decode_glb(data)`
- `def _decode_text(data)`
- `def read_source(source)` - *Return (json text, base directory, GLB binary chunk) for a source.*
- `def decode_data_uri(uri)`
- `def load_buffers(document, base_dir, binary_chunk)`
- `def read_accessor(accessor, buffer_views, buffers)`

---

### [`keystone/gltf/loader.py`](keystone/gltf/loader.py)
> *Top-level glTF import orchestration.*

**Size**: `81` lines (`3010` bytes)

**Classes:**
- `class GltfImport` - *The result of importing one glTF document.*

**Functions:**
- `def load_gltf(source, registry)` - *Load a glTF 2.0 document from a path, JSON text or bytes.*

---

### [`keystone/gltf/materials.py`](keystone/gltf/materials.py)
> *glTF material conversion.*

**Size**: `58` lines (`2455` bytes)

**Functions:**
- `def load_materials(document, textures)`

---

### [`keystone/gltf/meshes.py`](keystone/gltf/meshes.py)
> *glTF mesh and primitive decoding.*

**Size**: `224` lines (`10511` bytes)

**Functions:**
- `def _as_vec3(value)`
- `def _compute_normals(positions, indices)`
- `def load_meshes(document, buffers, buffer_views, materials)`
- `def _accessor(document, index)`
- `def _require_joints_accessor(accessor, mesh_index)`
- `def _require_weights_accessor(accessor, mesh_index)`

---

### [`keystone/gltf/scene.py`](keystone/gltf/scene.py)
> *glTF node, transform and scene construction.*

**Size**: `192` lines (`7484` bytes)

**Functions:**
- `def _matrix_to_transform(matrix)`
- `def _node_transform(raw)`
- `def _with_skin(mesh, skin)`
- `def _node_skin(document, raw, skins)`
- `def build_scene(document, meshes, materials, skins)`

---

### [`keystone/gltf/skins.py`](keystone/gltf/skins.py)
> *glTF skin parsing: joint nodes and inverse bind matrices.*

**Size**: `65` lines (`2840` bytes)

**Functions:**
- `def load_skins(document, buffers, buffer_views, node_count)` - *Parse the glTF skins array into joint indices and inverse bind matrices.*
- `def _accessor(document, index)`

---

### [`keystone/gltf/textures.py`](keystone/gltf/textures.py)
> *glTF image and texture decoding.*

**Size**: `99` lines (`3946` bytes)

**Functions:**
- `def _image_bytes(image, buffers, buffer_views, base_dir)`
- `def _mime_from_path(path)`
- `def _texture_from_bytes(data, mime_type, name)`
- `def load_textures(document, buffers, buffer_views, base_dir)`

---

### [`keystone/gpu/__init__.py`](keystone/gpu/__init__.py)
> *OpenGL 3.3 adapter: context, shader, mesh buffers and renderer.*

**Size**: `1` lines (`70` bytes)

---

### [`keystone/gpu/bloom.py`](keystone/gpu/bloom.py)
> *Deterministic emissive-aware bloom glow (luminance threshold, in-shader, no FBO).*

**Size**: `92` lines (`3146` bytes)

**Functions:**
- `def bloom_factor(luma, threshold, knee)` - *Return the deterministic smoothstep glow weight for one luminance.*
- `def bloom_color(color, threshold, knee, intensity)` - *Add the threshold glow to a display-referred 0..1 RGB triple.*
- `def bloom_blur_size(width, height, downsample)` - *Return the deterministic half-res blur size for a framebuffer.*
- `def bloom_composite(scene, blurred, intensity)` - *Add blurred light to the scene color with 0..1 clamp.*

---

### [`keystone/gpu/bloom_fbo.py`](keystone/gpu/bloom_fbo.py)
> *Deterministic RGBA8 color framebuffers for the bloom diffusion chain.*

**Size**: `89` lines (`3778` bytes)

**Classes:**
- `class BloomFbo` - *One RGBA8 color FBO owned by the renderer (one GL context).*
  - Method `.__init__(width, height)`
  - Method `.bind_for_write()`
  - Method `.unbind_after_write(width, height)`
  - Method `.bind_for_read(unit)`
  - Method `.unbind_after_read(unit)`
  - Method `.release()`

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

### [`keystone/gpu/instancing.py`](keystone/gpu/instancing.py)
> *Deterministic grouping for hardware instancing.*

**Size**: `108` lines (`4031` bytes)

**Functions:**
- `def _material_key(material)` - *Normalize the grouping key to match renderer fallback behavior.*
- `def group_instances(scene, planes)` - *Group visible nodes by identical mesh/material payloads.*
- `def plan_instanced(scene)` - *Return a JSON-safe instancing plan mirroring ``plan_batches`` counts.*

---

### [`keystone/gpu/mesh_buffer.py`](keystone/gpu/mesh_buffer.py)
> *GPU mesh upload and indexed drawing for the Keystone renderer.*

**Size**: `116` lines (`4868` bytes)

**Classes:**
- `class GpuMesh` - *VAO/VBO/EBO triple owning one immutable MeshData upload.*
  - Method `.__init__(mesh)`
  - Method `.draw()`
  - Method `.draw_instanced(model_flats, normal_flats)` - *Draw all instances with per-instance model/normal divisor attributes.*
  - Method `.release()`

---

### [`keystone/gpu/post.py`](keystone/gpu/post.py)
> *Deterministic post color-grade (exposure + vignette, in-shader, no FBO).*

**Size**: `42` lines (`1264` bytes)

**Functions:**
- `def vignette_factor(nx, ny, strength)` - *Return the deterministic vignette multiplier for normalized coords 0..1.*
- `def grade_color(color, nx, ny, exposure, strength)` - *Apply exposure then vignette to a display-referred 0..1 RGB triple.*

---

### [`keystone/gpu/renderer.py`](keystone/gpu/renderer.py)
> *Blinn-Phong forward renderer with fog, shadows and screenshot readback.*

**Size**: `1145` lines (`45671` bytes)

**Classes:**
- `class Renderer` - *Owns the shader and per-mesh GPU buffers for one OpenGL context.*
  - Method `.__init__(width, height)`
  - Method `.resize(width, height)`
  - Method `._create_bloom_fbos()`
  - Method `._release_bloom_fbos()`
  - Method `._ensure_bloom_fbos()`
  - Method `._gpu_mesh(mesh)`
  - Method `._gpu_skinned_mesh(mesh)`
  - Method `._upload_bones(program, scene, mesh)`
  - Method `._gpu_texture(texture)`
  - Method `._draw_sky(scene, srgb_on, post_on, bloom_on)`
  - Method `._shadows_requested(scene)`
  - Method `._srgb_requested(scene)`
  - Method `._post_requested(scene)`
  - Method `._bloom_requested(scene)`
  - Method `._sprites_requested(scene)`
  - Method `._culling_requested(scene)`
  - Method `._init_sprite_buffers()`
  - Method `._release_sprite_buffers()`
  - Method `._camera_basis(scene)`
  - Method `._draw_sprites(scene, particles, view_projection, post_on, bloom_on)`
  - Method `._apply_bloom(program, bloom_on)`
  - Method `._apply_post(program, post_on)`
  - Method `._apply_shared(program, scene, view_projection, light_vp, shadows_on, srgb_on)`
  - Method `._apply_material(program, material)`
  - Method `._render_shadow_pass(scene, light_vp)`
  - Method `._draw_quad()`
  - Method `._draw_geometry(scene, view_projection, light_vp, shadows_on, srgb_on, post_on, bloom_on, planes)`
  - Method `._run_bloom_chain()`
  - Method `.render(scene, particles)`
  - Method `.read_pixels()`
  - Method `.save_png(path)`
  - Method `.release()`

**Functions:**
- `def normal_matrix(model)` - *Return transpose(inverse(upper 3x3)) in column-major order.*

---

### [`keystone/gpu/shader.py`](keystone/gpu/shader.py)
> *GLSL program compilation, uniform upload and cleanup.*

**Size**: `93` lines (`3634` bytes)

**Classes:**
- `class ShaderProgram` - *A linked vertex/fragment program with cached uniform locations.*
  - Method `.__init__(vertex_source, fragment_source)`
  - Method `._compile(stage, source, label)`
  - Method `.use()`
  - Method `._location(name)`
  - Method `.set_mat4(name, matrix)`
  - Method `.set_mat4_array(name, matrices)` - *Upload a fixed mat4 array palette (e.g. skinning bones).*
  - Method `.set_mat3(name, values)`
  - Method `.set_vec2(name, x, y)`
  - Method `.set_vec3(name, vector)`
  - Method `.set_float(name, value)`
  - Method `.set_int(name, value)`
  - Method `.release()`

---

### [`keystone/gpu/shadow.py`](keystone/gpu/shadow.py)
> *Deterministic directional shadow mapping (fixed 1024 depth map, 3x3 PCF).*

**Size**: `154` lines (`5394` bytes)

**Classes:**
- `class ShadowMap` - *Fixed-size depth FBO owned by the renderer (one GL context).*
  - Method `.__init__(size)`
  - Method `.bind_for_write()`
  - Method `.unbind_after_write(width, height)`
  - Method `.bind_for_read(unit)`
  - Method `.unbind_after_read(unit)`
  - Method `.release()`

**Functions:**
- `def orthographic(left, right, bottom, top, near, far)` - *Build a deterministic orthographic projection (column-major).*
- `def light_view(direction)` - *Look from the light direction toward the origin (deterministic).*
- `def light_vp(direction)` - *Deterministic light view-projection for the fixed ortho box.*
- `def light_vp_for(light)` - *Convenience wrapper taking the scene directional light.*

---

### [`keystone/gpu/skinned_buffer.py`](keystone/gpu/skinned_buffer.py)
> *GPU upload for skinned meshes: base stream plus joints and weights.*

**Size**: `72` lines (`2934` bytes)

**Classes:**
- `class SkinnedGpuMesh` - *VAO/VBO/EBO triple owning one immutable skinned mesh upload.*
  - Method `.__init__(mesh)`
  - Method `.draw()`
  - Method `.release()`

---

### [`keystone/gpu/sprites.py`](keystone/gpu/sprites.py)
> *Deterministic GPU point-sprite math: size attenuation and soft alpha.*

**Size**: `74` lines (`2667` bytes)

**Functions:**
- `def sprite_scale(distance, size)` - *Return the deterministic pixel size for a particle.*
- `def soft_alpha(u, v)` - *Return the soft-circle coverage for quad UVs in [0, 1].*
- `def sprite_alpha(age, lifetime, u, v)` - *Return the combined fade * soft-circle alpha for one particle.*
- `def billboard_corners(center, right, up, world_size)` - *Return the four world corners for a camera-facing quad.*

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

**Size**: `69` lines (`2375` bytes)

**Functions:**
- `def load_actions(path)`
- `def run_simulation(game, frames, actions, step, trace)` - *Advance a game without creating a window or OpenGL context.*

---

### [`keystone/history.py`](keystone/history.py)
> *Bounded undo/redo history for engine and game state.*

**Size**: `86` lines (`2813` bytes)

**Classes:**
- `class History` - *A small, bounded undo/redo stack.*
  - Method `.__init__(capacity)`
  - Property `.capacity`
  - Property `.can_undo`
  - Property `.can_redo`
  - Property `.redo_available`
  - Method `.push(value)` - *Record a new snapshot and discard any redo branch.*
  - Method `.undo()` - *Move to the previous snapshot and return it, or None when at the bottom.*
  - Method `.redo()` - *Move to the next snapshot and return it, or None when at the top.*
  - Method `.peek()` - *Return the current snapshot without moving, or None when empty.*
  - Method `.values()` - *Return all retained snapshots in chronological order.*
  - Method `.clear()`
  - Method `.__len__()`

---

### [`keystone/input.py`](keystone/input.py)
> *Generic input mapping: named actions, axes and pointer look.*

**Size**: `282` lines (`11609` bytes)

**Classes:**
- `class ActionState` - *One sampled input frame; games translate names into their own rules.*
  - Method `.without_pressed()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class InputMap` - *Maps keys and pointer motion to action names and continuous axes.*
  - Method `.__init__(bindings, look_speed, mouse_sensitivity, contexts, context)`
  - Method `.bind(action, key, context)`
  - Method `.set_context(context)`
  - Method `.get_context()`
  - Method `.list_contexts()`
  - Method `.unbind(action)` - *Remove a custom binding from the active context; returns False when not bound.*
  - Method `.list_actions()` - *Return a copy of the current action-to-key map for UI and AI clients.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.save_bindings(path)`
  - Method `.load_bindings(path)`
  - Method `.set_mouse_enabled(enabled)`
  - Method `.sample(context, dt)`

---

### [`keystone/material_graph.py`](keystone/material_graph.py)
> *Declarative, deterministic material graphs that evaluate to a Material.*

**Size**: `349` lines (`14906` bytes)

**Classes:**
- `class MaterialGraphNode` - *One node in a material graph: a kind, parameters and input node ids.*
  - Method `.__post_init__()`
  - Method `.param(name, default)` - *Return one parameter value, or default when it is absent.*
  - Method `.to_dict()`
- `class MaterialGraph` - *An immutable, serializable graph that evaluates to one Material.*
  - Method `.__post_init__()`
  - Method `.node(node_id)`
  - Method `.validate()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.evaluate(*, textures, registry)` - *Evaluate the graph and return its Material.*

**Functions:**
- `def _json_value(value)`
- `def _from_json_value(value)`
- `def _evaluate_node(node, values, textures, registry)`

---

### [`keystone/math3d.py`](keystone/math3d.py)
> *Column-major 3D math primitives shared by the scene, camera and GPU layers.*

**Size**: `375` lines (`13166` bytes)

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

**Size**: `189` lines (`8052` bytes)

**Classes:**
- `class MeshBuilder` - *Accumulates flat-shaded quads and boxes, then builds one mesh.*
  - Method `.__init__()`
  - Method `._require_mode(mode)`
  - Method `.add_quad(p0, p1, p2, p3, color)`
  - Method `.add_mesh(mesh, offset, scale, color)` - *Merge another mesh under a uniform scale and translation.*
  - Method `.add_mesh_matrix(mesh, matrix, color)` - *Merge a mesh transformed by a world matrix (positions + normals).*
  - Method `.add_skinned_mesh(mesh)` - *Concatenate a skinned mesh verbatim (positions, joints, weights).*
  - Method `.add_box(cx, cy, cz, sx, sy, sz, color)`
  - Method `.is_empty()`
  - Method `.build()`

---

### [`keystone/obj_loader.py`](keystone/obj_loader.py)
> *Streaming Wavefront OBJ loader producing indexed triangle meshes.*

**Size**: `137` lines (`5953` bytes)

**Functions:**
- `def load_obj(path)` - *Read an OBJ file line by line so file size is never loaded whole.*
- `def parse_obj(text)` - *Parse OBJ text already in memory, mainly for tests and embedded assets.*
- `def _resolve_index(raw, count, kind, number, line)`
- `def _corner(token, number, line, vertices, uvs, normals)`
- `def _parse_lines(lines)`
- `def _build_mesh(positions, normals, uvs, faces)`

---

### [`keystone/particles.py`](keystone/particles.py)
> *Deterministic, game-agnostic CPU particles: emitters, systems and reports.*

**Size**: `367` lines (`14967` bytes)

**Classes:**
- `class Particle` - *One live particle: position, velocity, age, lifetime and size.*
  - Method `.__post_init__()`
  - Method `.alive()`
- `class Emitter` - *Deterministic spawn recipe: rate, lifetime, speed, spread and forces.*
  - Method `.__post_init__()`
  - Method `.spawn(index, origin)` - *Spawn one particle deterministically from the emitter seed and index.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ParticleSystem` - *Owns emitters and live particles; deterministic under a fixed call order.*
  - Method `.__post_init__()`
  - Method `.add(emitter)`
  - Method `.burst(emitter_name, count, origin)` - *Emit count particles immediately; returns the number actually added.*
  - Method `.step(dt, colliders, restitution, friction, kill_on_contact)` - *Advance all particles by dt; returns the live count afterwards.*
  - Method `._respond_axis(vx, vy, vz, axis, restitution)` - *Reflect one velocity axis with settle snapping; other axes untouched.*
  - Method `._step_free(dt)`
  - Method `.alive_count()`
  - Method `.clear()`
  - Method `._emitter_for(particle)`

**Functions:**
- `def _move_point_flat(px, py, pz, axis, amount, flat)` - *Float-only swept point move; axis is 0/1/2 for x/y/z.*
- `def particles_report(system)`

---

### [`keystone/physics.py`](keystone/physics.py)
> *Generic collision primitives and ray queries for the engine core.*

**Size**: `160` lines (`5753` bytes)

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

### [`keystone/playtest.py`](keystone/playtest.py)
> *Seeded bot playtesting: transcripts, diffing, policies and fairness checks.*

**Size**: `592` lines (`24657` bytes)

**Classes:**
- `class BotPolicy` - *One seeded decision step over the five-operation game contract.*
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`
- `class RandomPolicy` - *Uniform baseline: sample axes in [-1, 1], occasionally press a button.*
  - Method `.__init__(press_chance)`
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`
- `class GreedyPolicy` - *Stateful bandit: repeat the last action while score improves, else resample.*
  - Method `.__init__()`
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`
- `class ScriptedPolicy` - *Replay an action list; hold the final action when the run is longer.*
  - Method `.__init__(actions)`
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`

**Functions:**
- `def _canon_value(value)`
- `def canon(snapshot)` - *Project a snapshot to its canonical search form.*
- `def canon_hash(snapshot)` - *Stable hash of the canonical snapshot projection.*
- `def read_outcome(snapshot)` - *Read the opportunistic outcome signal; ``unknown`` when absent.*
- `def read_score(snapshot)` - *Read the opportunistic numeric score signal, if present.*
- `def to_command_log(transcript)` - *Convert a transcript back to a replayable :class:`CommandLog`.*
- `def run_bot(factory, policy, frames, seed, step, max_wall_seconds, trace)` - *Play one seeded bot run headlessly and record the transcript.*
- `def diff_transcripts(before, after)` - *Compare two transcripts: hash fast-path, then first divergence.*
- `def _validate_actions_spec(spec)`
- `def _sample_action(rng, axes, buttons)`
- `def make_report(transcript, fairness)` - *Build the frozen schema-1 playtest report shared with web adapters.*
- `def validate_fairness(factory, reference_actions, frames, seeds, step, max_states, max_wall_seconds, time_limit_frames)` - *Judge whether a configuration is winnable, with reasons.*

---

### [`keystone/plugin.py`](keystone/plugin.py)
> *Game-agnostic module contract and loader.*

**Size**: `99` lines (`3679` bytes)

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

**Size**: `128` lines (`4934` bytes)

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

**Size**: `114` lines (`3803` bytes)

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
- `def run_log(factory, log, trace)` - *Replay a command log on a fresh game without a window or GL context.*
- `def verify_log(factory, log)` - *Run one log twice from a factory and compare final hashes.*

---

### [`keystone/samples.py`](keystone/samples.py)
> *A minimal game-agnostic sample used to smoke-test the engine.*

**Size**: `157` lines (`6094` bytes)

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

**Size**: `333` lines (`11468` bytes)

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
- `class ShadowSettings` - *Deterministic directional shadow-map toggle (fixed 1024 map, bias 0.005).*
- `class ColorSettings` - *Deterministic sRGB-correct linear pipeline toggle (in-shader, pow 2.2).*
- `class PostSettings` - *Deterministic post color-grade toggle (in-shader exposure + vignette).*
- `class BloomSettings` - *Deterministic bloom glow toggle (in-shader luminance threshold).*
- `class SpriteSettings` - *Deterministic GPU point-sprite toggle (one instanced quad per particle).*
- `class CullingSettings` - *Deterministic CPU view-frustum culling toggle (color pass only).*
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

### [`keystone/scene_snapshot.py`](keystone/scene_snapshot.py)
> *Versioned, asset-aware snapshots of a Keystone scene.*

**Size**: `330` lines (`13911` bytes)

**Functions:**
- `def _vec3_to_list(value)`
- `def _vec3_from_value(value, label, default)`
- `def _light_to_dict(light)`
- `def _light_from_dict(data)`
- `def _point_light_to_dict(light)`
- `def _point_light_from_dict(data)`
- `def _transform_to_dict(transform)`
- `def _transform_from_dict(data)`
- `def _payload_asset_ids(registry)`
- `def _required_node_id(raw)`
- `def _restore_asset(registry, asset_id, expected_kind, label)`
- `def scene_to_dict(scene, registry)` - *Serialize a scene to a versioned, JSON-safe dictionary.*
- `def scene_from_dict(data, registry)` - *Rebuild a scene from a versioned snapshot.*

---

### [`keystone/schema.py`](keystone/schema.py)
> *Core-facing schema versions shared with optional adapters.*

**Size**: `6` lines (`147` bytes)

---

### [`keystone/serialization.py`](keystone/serialization.py)
> *Atomic JSON persistence for engine and game state.*

**Size**: `31` lines (`966` bytes)

**Functions:**
- `def write_json_atomic(path, payload, backup)`
- `def read_json(path)`

---

### [`keystone/skin.py`](keystone/skin.py)
> *Deterministic linear-blend skinning: bone palettes and CPU reference math.*

**Size**: `111` lines (`4260` bytes)

**Functions:**
- `def bone_matrices(scene, mesh)` - *Return world-space bone palettes (joint world matrix times inverse bind).*
- `def _rotate_normal(bone, normal)`
- `def skin_point(position, normal, joints, weights, bones)` - *Deform one vertex by its influences; mirrors the vertex shader exactly.*
- `def skin_mesh(mesh, bones)` - *Return a deformed copy of the mesh in bind-pose layout (CPU oracle).*

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

**Size**: `87` lines (`3362` bytes)

**Classes:**
- `class TextureData` - *Top-down RGBA8 pixels with a stable name for reports and debugging.*
  - Method `.__post_init__()`
  - Method `.sha256()` - *Return a stable digest of the shape plus the pixel payload.*
  - Method `.from_png(path, name)` - *Load an 8-bit RGBA non-interlaced PNG through the dependency-free reader.*
  - Method `.from_png_bytes(data, name)` - *Load an 8-bit RGBA non-interlaced PNG from bytes.*
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

**Size**: `92` lines (`5112` bytes)

**Functions:**
- `def glyph(character)` - *Return the 7x5 rows for one character; lowercase maps to uppercase.*
- `def text_width(text, scale)` - *Return the pixel width of text, excluding trailing tracking.*
- `def line_height(scale)` - *Return the pixel height of one uppercase text line.*
- `def truncate_text(text, width, scale)` - *Trim text so it fits width pixels, leaving room for an ellipsis-free cut.*

---

### [`keystone/ui/menu.py`](keystone/ui/menu.py)
> *Game-agnostic pause menu state: items, selection and activation.*

**Size**: `41` lines (`1176` bytes)

**Classes:**
- `class MenuItem` - *One labelled action the human can choose.*
- `class PauseMenu` - *Wraps selection over a fixed item list; contains no rendering or input.*
  - Method `.__init__(items)`
  - Method `.move(delta)` - *Move the selection by delta, wrapping at both ends.*
  - Method `.action()` - *Return the action of the selected item.*

---

### [`keystone/ui/overlay.py`](keystone/ui/overlay.py)
> *Game-agnostic human overlay: HUD, controls help and pause menu.*

**Size**: `162` lines (`7006` bytes)

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

**Size**: `147` lines (`5646` bytes)

**Functions:**
- `def _floats(values)`
- `def _mesh_document(mesh)`
- `def _texture_document(texture)`
- `def scene_document(scene, game)` - *Serialize one scene into a deterministic, viewer-ready document.*

---

### [`keystone/web/schema.py`](keystone/web/schema.py)
> *Versioned schemas shared by the web API, AI clients and the browser viewer.*

**Size**: `28` lines (`1425` bytes)

---

### [`keystone/web/server.py`](keystone/web/server.py)
> *A localhost JSON API and static web console for the game-agnostic engine.*

**Size**: `410` lines (`18510` bytes)

**Classes:**
- `class WebProblem` - *One client-facing error with an actionable fix.*
  - Method `.__init__(status, why, fix)`
- `class GameSession` - *One in-memory game guarded by a lock for concurrent HTTP requests.*
  - Method `.__init__(game)`
  - Property `.name`
  - Method `.describe()`
  - Method `.simulate(frames, actions, step, trace)`
  - Method `.scene()`
  - Method `.inspector()`
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

### [`tests/support_maze_game.py`](tests/support_maze_game.py)
> *Deterministic grid stub used to prove the bot playtester end to end.*

**Size**: `230` lines (`7021` bytes)

**Classes:**
- `class MazeGame` - *A deterministic grid chase: reach the goal cell before the clock.*
  - Method `.__init__(config)`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`

**Functions:**
- `def _step(value)`
- `def maze_shortest_path(config)` - *Exact grid BFS ground truth: steps from spawn to goal, or None.*
- `def reachable(config)` - *Fixture-side exact reachability used as fairness ground truth.*
- `def open_config(width, height, time_limit)`
- `def walled_goal_config()` - *Goal fully surrounded: provably unwinnable.*
- `def hazard_spawn_config()` - *Spawn sits on a hazard: terminal loss on frame zero.*
- `def tight_clock_config()` - *Shortest path needs 8 steps; the clock allows 3.*
- `def optimal_actions(config)` - *Greedy reference solution: shortest-path actions, or empty when unreachable.*
- `def Factory(config)`
- `def FairMaze()`
- `def WalledMaze()`
- `def HazardMaze()`
- `def TightMaze()`

---

### [`tests/test_agents.py`](tests/test_agents.py)
> *Tests for AI observation/action adapters, audit trail and input bindings.*

**Size**: `66` lines (`2869` bytes)

**Classes:**
- `class AgentsTest`
  - Method `.test_parse_actions_validates_and_clamps()`
  - Method `.test_observe_is_deterministic_and_auditable()`
  - Method `.test_summarize_report_truncates_and_keeps_pbr()`
  - Method `.test_audit_trail_appends_and_verifies()`
  - Method `.test_input_bindings_round_trip()`

---

### [`tests/test_analysis.py`](tests/test_analysis.py)
> *Tests for the machine-readable frame report.*

**Size**: `266` lines (`11158` bytes)

**Classes:**
- `class Health`
- `class AnalysisTest`
  - Method `.test_pixel_stats_and_content_bbox()`
  - Method `.test_scene_nodes_have_projected_screen_bounds()`
  - Method `.test_node_on_the_projection_plane_stays_in_the_report()`
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
  - Method `.test_grid_luma_uses_per_cell_counts()`

---

### [`tests/test_animation.py`](tests/test_animation.py)
> *Tests for deterministic animation clips, controllers and pose application.*

**Size**: `216` lines (`8915` bytes)

**Classes:**
- `class TrackTest`
  - Method `.test_linear_interpolation()`
  - Method `.test_step_interpolation()`
  - Method `.test_validation()`
  - Method `.test_quat_slerp_endpoints()`
  - Method `.test_json_round_trip()`
- `class ClipControllerTest`
  - Method `._clip()`
  - Method `.test_clip_sample_and_duration()`
  - Method `.test_controller_loops_and_applies()`
  - Method `.test_zero_time_event_fires_on_first_advance_only()`
  - Method `.test_crossfade_from_empty_clip_completes()`
  - Method `.test_unknown_clip_rejected()`
  - Method `.test_events_fire_once_per_crossing()`
  - Method `.test_crossfade_blends_deterministically()`
- `class MergeTest`
  - Method `.test_merge_bakes_static_groups()`
  - Method `.test_merge_excludes_animated_nodes()`
- `class ClipDurationTest`
  - Method `.test_duration_ignores_far_event_when_tracks_exist()`
  - Method `.test_event_only_clip_keeps_event_duration()`
  - Method `.test_duplicate_keyframe_times_rejected()`

**Functions:**
- `def _vec_track(pairs)`

---

### [`tests/test_app.py`](tests/test_app.py)
> *Tests for the game-agnostic engine loop and CLI.*

**Size**: `312` lines (`14338` bytes)

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
  - Method `.test_replay_cli_replays_a_log_without_opening_a_window()`
  - Method `.test_serve_is_a_standalone_web_command()`
  - Method `.test_windowless_commands_reject_window_flags()`
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

### [`tests/test_assets.py`](tests/test_assets.py)
> *Unit tests for the asset registry: identity, digests and dependencies.*

**Size**: `344` lines (`15932` bytes)

**Classes:**
- `class AssetRegistryTest`
  - Method `.setUp()`
  - Method `.test_register_infers_kind_and_preserves_order()`
  - Method `.test_register_rejects_bad_ids_kinds_and_payloads()`
  - Method `.test_duplicate_id_requires_replace()`
  - Method `.test_digest_is_content_based_and_duplicates_are_reported()`
  - Method `.test_texture_and_material_digests_follow_their_content()`
  - Method `.test_mesh_digest_covers_skinning()`
  - Method `.test_dependencies_are_sorted_and_missing_ones_reported()`
  - Method `.test_stats_and_describe_are_json_safe()`
  - Method `.test_public_package_exports_the_registry()`
  - Method `.test_remove_and_clear_dispose_records()`
- `class AssetFileSourceTest`
  - Method `.test_register_file_uses_suffix_and_records_source()`
  - Method `.test_register_file_requires_kind_or_known_suffix()`
  - Method `.test_refresh_reports_unchanged()`
  - Method `.test_refresh_reloads_changed_texture()`
  - Method `.test_refresh_failure_keeps_last_good_payload()`
  - Method `.test_refresh_missing_then_recovers()`
  - Method `.test_refresh_reports_loader_type_error()`
  - Method `.test_dependencies_survive_refresh()`
  - Method `.test_clear_and_remove_drop_sources()`

**Functions:**
- `def _touch(path)`

---

### [`tests/test_audio.py`](tests/test_audio.py)
> *Tests for the game-agnostic audio core.*

**Size**: `120` lines (`4617` bytes)

**Classes:**
- `class AudioTest`
  - Method `.test_synth_clips_are_deterministic()`
  - Method `.test_noise_rejects_nonint_seed_to_keep_determinism()`
  - Method `.test_validation_rejects_bad_params()`
  - Method `.test_mixer_applies_buses_and_renders()`
  - Method `.test_mix_clips_requires_shared_rate()`
  - Method `.test_mix_clips_clamps_once_at_the_end()`
  - Method `.test_wav_round_trip()`
  - Method `.test_clip_json_round_trip()`
  - Method `.test_read_wav_accepts_full_scale_negative()`
  - Method `.test_master_bus_applies_once()`
  - Method `.test_play_rejects_unknown_bus()`

---

### [`tests/test_batch.py`](tests/test_batch.py)
> *Tests for the static batch planner and inspector endpoint.*

**Size**: `59` lines (`2323` bytes)

**Classes:**
- `class BatchTest`
  - Method `.test_shared_meshes_batch_into_few_groups()`
  - Method `.test_cube_demo_plan_reports_savings()`
- `class InspectorEndpointTest`
  - Method `.test_inspector_returns_batches_and_audio()`

---

### [`tests/test_bloom.py`](tests/test_bloom.py)
> *Tests for the deterministic bloom glow (in-shader luminance threshold).*

**Size**: `200` lines (`7865` bytes)

**Classes:**
- `class BloomMathTest`
  - Method `.test_constants_are_fixed()`
  - Method `.test_blur_size_uses_floor_half_with_min_one()`
  - Method `.test_composite_adds_and_clamps()`
  - Method `.test_dark_has_no_bloom_and_bright_saturates()`
  - Method `.test_bloom_adds_proportionally_and_clamps()`
- `class BloomContractsTest`
  - Method `.test_bloom_settings_default_enabled()`
  - Method `.test_describe_reports_bloom()`
  - Method `.test_report_includes_bloom_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_bloom()`
  - Method `.test_compare_accepts_legacy_without_bloom()`
  - Method `.test_snapshot_round_trips_bloom_flag()`
  - Method `.test_scene_document_and_inspector_expose_bloom()`
- `class BloomDiffusionIntegrationTest`
  - Method `._render_cube(bloom_on, width, height)`
  - Method `.test_diffusion_changes_pixels_without_new_draws()`
  - Method `.test_no_bloom_legacy_path_is_stable()`
  - Method `.test_resize_recreates_diffusion_buffers()`

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

**Size**: `77` lines (`3269` bytes)

**Classes:**
- `class SpatialGridTest`
  - Method `.test_query_returns_true_overlaps_in_insertion_order()`
  - Method `.test_same_cell_candidates_are_still_filtered()`
  - Method `.test_update_moves_a_proxy_and_remove_deletes_it()`
  - Method `.test_negative_coordinates_and_large_boxes_use_multiple_cells()`
  - Method `.test_enormous_proxy_is_rejected_instead_of_hanging()`
  - Method `.test_pairs_are_unique_and_ordered_by_insertion()`
  - Method `.test_clear_and_validation()`

---

### [`tests/test_character.py`](tests/test_character.py)
> *Tests for the AABB character controller.*

**Size**: `125` lines (`5688` bytes)

**Classes:**
- `class CharacterControllerTest`
  - Method `.test_body_exposes_its_collision_box()`
  - Method `.test_character_falls_and_rests_on_a_floor()`
  - Method `.test_character_stops_at_a_wall_without_tunneling()`
  - Method `.test_jump_leaves_the_ground()`
  - Method `.test_character_rejects_invalid_configuration_and_step()`
  - Method `.test_character_steps_onto_a_low_step()`
  - Method `.test_character_stops_at_a_tall_step()`
  - Method `.test_platform_carry_pushes_out_of_a_wall()`
  - Method `.test_platform_carry_off_a_ledge_then_falls()`
  - Method `.test_character_steps_are_deterministic()`

---

### [`tests/test_clock.py`](tests/test_clock.py)
> *Tests for the fixed-step clock.*

**Size**: `44` lines (`1425` bytes)

**Classes:**
- `class FixedStepClockTest`
  - Method `.test_releases_whole_steps_and_bounds_catch_up()`
  - Method `.test_reset_drops_accumulator()`
  - Method `.test_invalid_configuration()`
  - Method `.test_backwards_time_mints_no_debt()`
  - Method `.test_non_finite_time_is_rejected()`

---

### [`tests/test_culling.py`](tests/test_culling.py)
> *Tests for deterministic CPU view-frustum culling (color pass only).*

**Size**: `221` lines (`8752` bytes)

**Classes:**
- `class CullingMathTest`
  - Method `.test_planes_are_deterministic()`
  - Method `.test_degenerate_frustum_raises()`
  - Method `.test_aabb_touching_plane_is_visible()`
  - Method `.test_world_bounds_follow_translation()`
  - Method `.test_skinned_nodes_are_always_visible()`
- `class CullingSceneTest`
  - Method `.test_front_visible_behind_and_offside_culled()`
  - Method `.test_cull_scene_keeps_front_only()`
  - Method `.test_disabled_culling_returns_everything()`
  - Method `.test_default_enabled()`
  - Method `.test_cull_scene_rejects_bad_size()`
- `class CullingGroupingAgreementTest`
  - Method `.test_group_instances_planes_match_cull_scene()`
  - Method `.test_group_instances_without_planes_is_legacy()`
- `class CullingContractsTest`
  - Method `.test_describe_reports_culling()`
  - Method `.test_public_api_exports_culling_helpers()`
  - Method `.test_report_includes_culling_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_culling()`
  - Method `.test_compare_accepts_legacy_without_culling()`
  - Method `.test_compare_accepts_schema_10_baseline()`
  - Method `.test_snapshot_round_trips_culling_flag()`

**Functions:**
- `def _scene_with_cubes()`
- `def _skinned_quad()`

---

### [`tests/test_geometry.py`](tests/test_geometry.py)
> *Unit tests for indexed meshes, built-in primitives and the OBJ loader.*

**Size**: `276` lines (`10301` bytes)

**Classes:**
- `class MeshDataTest`
  - Method `.test_rejects_mismatched_attribute_counts()`
  - Method `.test_rejects_out_of_range_index()`
  - Method `.test_rejects_malformed_position_tuples_at_construction()`
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
  - Method `.test_cone_side_normals_point_outward()`
  - Method `.test_cone_winding_matches_stored_normals()`
- `class MeshBuilderTest`
  - Method `.test_box_has_24_vertices_and_36_indices()`
  - Method `.test_quad_normal_follows_winding()`
  - Method `.test_degenerate_quad_is_rejected()`
  - Method `.test_add_mesh_merges_counts_and_offsets()`
  - Method `.test_add_mesh_matrix_uses_inverse_transpose_normals()`
- `class ObjLoaderTest`
  - Method `.test_quad_is_triangulated()`
  - Method `.test_normals_are_computed_when_absent()`
  - Method `.test_authored_normals_are_kept()`
  - Method `.test_negative_indices_are_relative()`
  - Method `.test_missing_file_raises_file_not_found()`
  - Method `.test_bad_index_raises_value_error()`
  - Method `.test_extra_face_slash_is_rejected()`
  - Method `.test_vertex_weight_is_applied()`
  - Method `.test_vertex_junk_is_rejected()`
  - Method `.test_file_round_trip()`
  - Method `.test_bom_prefix_is_stripped()`
- `class MaterialTest`
  - Method `.test_defaults_are_valid()`
  - Method `.test_rejects_negative_specular()`
  - Method `.test_rejects_negative_checker_scale()`

---

### [`tests/test_gltf.py`](tests/test_gltf.py)
> *Unit tests for dependency-free glTF 2.0 import.*

**Size**: `239` lines (`10529` bytes)

**Classes:**
- `class GltfImportTest`
  - Method `.test_loads_a_triangle_mesh_and_material()`
  - Method `.test_translation_is_preserved()`
  - Method `.test_loads_from_a_file()`
  - Method `.test_rejects_wrong_version()`
  - Method `.test_rejects_missing_position()`
  - Method `.test_loads_an_embedded_png_texture()`
  - Method `.test_loads_an_external_buffer_file()`
  - Method `.test_registers_assets_when_registry_is_provided()`
  - Method `.test_generated_normals_use_triangle_indices()`
  - Method `.test_normalized_integer_colors_are_converted_to_unit_range()`
  - Method `.test_rejects_non_triangle_primitive_modes()`
  - Method `.test_rejects_unknown_material_indices()`
  - Method `.test_rejects_sparse_accessors_instead_of_silently_zeroing()`
  - Method `.test_rejects_cyclic_node_hierarchies()`
  - Method `.test_loads_a_glb_container()`
  - Method `.test_loads_a_glb_file()`
  - Method `.test_rejects_truncated_glb_data()`
  - Method `.test_rejects_unknown_material_texture_indices()`
  - Method `.test_rejects_negative_accessor_offsets()`
  - Method `.test_rejects_accessor_reads_outside_the_buffer_view()`

**Functions:**
- `def _data_uri(data)`
- `def _glb_bytes(document, binary_chunk)`
- `def _triangle_gltf(*, translation, color, roughness)`

---

### [`tests/test_headless.py`](tests/test_headless.py)
> *Tests for no-OpenGL simulation and action scripts.*

**Size**: `69` lines (`2852` bytes)

**Classes:**
- `class HeadlessTest`
  - Method `.test_simulation_advances_without_a_window()`
  - Method `.test_same_script_is_deterministic()`
  - Method `.test_trace_contains_each_frame()`
  - Method `.test_load_actions_accepts_list_and_object()`
  - Method `.test_load_actions_pins_bad_item_index()`
  - Method `.test_load_actions_rejects_command_logs()`
  - Method `.test_invalid_frames_and_step()`

---

### [`tests/test_history.py`](tests/test_history.py)
> *Unit tests for bounded undo/redo history.*

**Size**: `81` lines (`2599` bytes)

**Classes:**
- `class HistoryTest`
  - Method `.test_push_undo_redo_restores_values()`
  - Method `.test_new_push_clears_redo_branch()`
  - Method `.test_capacity_drops_oldest_entries()`
  - Method `.test_snapshots_are_deep_copied()`
  - Method `.test_clear_and_empty_behavior()`
  - Method `.test_peek_returns_current_without_moving()`
  - Method `.test_capacity_rejects_non_int()`

---

### [`tests/test_input.py`](tests/test_input.py)
> *Tests for input sampling and action state.*

**Size**: `151` lines (`6008` bytes)

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
  - Method `.test_contexts_isolate_menu_and_gameplay()`
  - Method `.test_unbind_survives_context_round_trip()`
  - Method `.test_action_state_round_trip_and_clear()`
  - Method `.test_action_state_rejects_string_pressed_and_bad_pointer()`
  - Method `.test_bind_rejects_blank_context()`
  - Method `.test_from_dict_rejects_non_string_context()`
  - Method `.test_custom_bindings_preserved_in_new_contexts()`
  - Method `.test_from_dict_rejects_blank_action_or_key()`

---

### [`tests/test_instancing.py`](tests/test_instancing.py)
> *Game-agnostic tests for hardware-instancing grouping.*

**Size**: `81` lines (`3207` bytes)

**Classes:**
- `class PlanInstancedTest`
  - Method `.test_groups_identical_payloads()`
  - Method `.test_separates_distinct_materials()`
  - Method `.test_ignores_invisible_and_missing_mesh()`
  - Method `.test_ordering_is_deterministic()`
  - Method `.test_matrices_follow_world_transforms()`
  - Method `.test_empty_scene()`

**Functions:**
- `def make_scene(count, same_material)`

---

### [`tests/test_material_graph.py`](tests/test_material_graph.py)
> *Unit tests for declarative material graphs.*

**Size**: `162` lines (`6090` bytes)

**Classes:**
- `class MaterialGraphCoreTest`
  - Method `.test_constant_color_and_float_feed_a_material()`
  - Method `.test_checker_node_builds_a_textured_material()`
  - Method `.test_mix_combines_colors()`
  - Method `.test_color_node_accepts_vec3_param()`
  - Method `.test_checker_and_material_accept_vec3_colors()`
  - Method `.test_validation_rejects_cycles_and_bad_graphs()`
  - Method `.test_evaluation_is_deterministic()`
- `class MaterialGraphSerializationTest`
  - Method `.test_round_trip_preserves_evaluation()`
  - Method `.test_texture_node_resolves_by_name()`
  - Method `.test_material_texture_name_must_resolve()`

**Functions:**
- `def _node(node_id, kind, *, params, inputs)`

---

### [`tests/test_math3d.py`](tests/test_math3d.py)
> *Unit tests for the Keystone 3D math core.*

**Size**: `138` lines (`5396` bytes)

**Classes:**
- `class Vec3Test`
  - Method `.test_arithmetic_and_dot()`
  - Method `.test_cross_follows_right_hand_rule()`
  - Method `.test_normalized_is_unit_and_zero_safe()`
  - Method `.test_lerp_hits_both_ends()`
  - Method `.test_mul_rejects_vector_operand()`
- `class Mat4Test`
  - Method `.test_identity_leaves_points_and_matrices_unchanged()`
  - Method `.test_translation_and_scale_apply_in_order()`
  - Method `.test_rotation_z_90_degrees()`
  - Method `.test_direction_ignores_translation()`
  - Method `.test_inverse_round_trips_affine_matrix()`
  - Method `.test_inverse_rejects_projective_matrix()`
  - Method `.test_transform_point_rejects_projective_matrix()`
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

### [`tests/test_merge_skin.py`](tests/test_merge_skin.py)
> *Tests for skin-aware batch merging: identical rigs merge into one draw.*

**Size**: `200` lines (`8326` bytes)

**Classes:**
- `class SkinMergeTest`
  - Method `.test_merge_combines_same_rig_groups()`
  - Method `.test_merged_deformation_matches_oracle_exactly()`
  - Method `.test_separates_by_material_joints_and_transform()`
  - Method `.test_plan_reports_skin_counters_without_moving_main_groups()`
  - Method `.test_exclude_applies_to_skin_groups()`
  - Method `.test_builder_rejects_mismatched_skin()`
  - Method `.test_differing_inverse_binds_stay_separate()`
  - Method `.test_builder_rejects_mismatched_inverse_binds()`
- `class RigGame` - *Minimal game module with two identical rigs for pixel-parity proofs.*
  - Method `.__init__(merged)`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`
- `class SkinPixelParityTest`
  - Method `.test_merged_scene_renders_identical_pixels()`

**Functions:**
- `def _rig_mesh(**overrides)`
- `def _rig_scene(transform, material, mesh)`

---

### [`tests/test_particles.py`](tests/test_particles.py)
> *Tests for the deterministic particle core.*

**Size**: `394` lines (`15650` bytes)

**Classes:**
- `class EmitterTest`
  - Method `.test_spawn_is_deterministic()`
  - Method `.test_validation()`
  - Method `.test_step_rejects_non_finite_dt()`
  - Method `.test_json_round_trip()`
- `class SystemTest`
  - Method `._system()`
  - Method `.test_burst_step_and_cull_are_deterministic()`
  - Method `.test_gravity_and_drag_move_particles()`
  - Method `.test_max_particles_keeps_newest()`
  - Method `.test_errors()`
  - Method `.test_multi_emitter_systems_use_per_emitter_forces()`
  - Method `.test_report()`
  - Method `.test_particle_rests_on_a_floor()`
  - Method `.test_particle_stops_at_a_wall_without_tunneling()`
  - Method `.test_empty_colliders_match_legacy_path()`
  - Method `.test_collision_is_deterministic()`
  - Method `.test_collision_rejects_bad_colliders()`
- `class ResponseTest`
  - Method `._still_system()`
  - Method `.test_defaults_stop_dead_with_clean_zero()`
  - Method `.test_bounce_reflects_with_restitution()`
  - Method `.test_elastic_bounce_preserves_speed()`
  - Method `.test_rest_threshold_settles_micro_bounces()`
  - Method `.test_friction_scales_tangentials_on_hit_only()`
  - Method `.test_kill_on_contact_drops_the_particle()`
  - Method `.test_response_rejects_bad_parameters()`
  - Method `.test_response_is_deterministic()`
  - Method `.test_cube_demo_fountain_bounces_deterministically()`
  - Method `.test_deep_interior_spawn_ejects_through_near_face()`
- `class SlideTest`
  - Method `.test_sliding_along_face_preserves_tangential_motion()`
  - Method `.test_sliding_is_deterministic()`

---

### [`tests/test_pbr.py`](tests/test_pbr.py)
> *Tests for PBR material extensions: validation, glTF, graphs and reports.*

**Size**: `82` lines (`3272` bytes)

**Classes:**
- `class PbrMaterialTest`
  - Method `.test_defaults_preserve_legacy_look()`
  - Method `.test_validation_rejects_out_of_range()`
  - Method `.test_gltf_preserves_pbr_factors()`
  - Method `.test_material_graph_pbr_node()`
  - Method `.test_report_and_scene_document_include_pbr()`

---

### [`tests/test_physics.py`](tests/test_physics.py)
> *Tests for generic ray and collision primitives.*

**Size**: `88` lines (`3527` bytes)

**Classes:**
- `class PhysicsTest`
  - Method `.test_ray_hits_aabb_and_sphere()`
  - Method `.test_rays_miss()`
  - Method `.test_ray_validation()`
  - Method `.test_overlap_and_sphere_pushout()`
  - Method `.test_non_overlapping_sphere_is_unchanged()`
  - Method `.test_pushout_lands_exactly_outside_the_face()`
  - Method `.test_aabb_helpers_are_consistent_with_overlap()`
  - Method `.test_raycast_returns_the_nearest_hit()`
  - Method `.test_raycast_filter_can_skip_candidates()`

---

### [`tests/test_playtest.py`](tests/test_playtest.py)
> *Tests for the seeded bot playtester: transcripts, diffs, policies and fairness.*

**Size**: `421` lines (`17667` bytes)

**Classes:**
- `class TranscriptTest`
  - Method `.test_run_bot_records_a_command_log_compatible_transcript()`
  - Method `.test_transcript_hash_matches_simulation_for_the_same_actions()`
  - Method `.test_same_seed_same_transcript()`
  - Method `.test_transcript_replays_through_the_command_log()`
  - Method `.test_terminal_outcome_ends_the_run_early()`
  - Method `.test_invalid_runner_arguments_are_rejected()`
  - Method `.test_run_bot_restores_global_random_state()`
  - Method `.test_canon_drops_time_and_rounds_floats()`
- `class DiffTest`
  - Method `.test_identical_transcripts_match_with_no_divergence()`
  - Method `.test_divergent_transcripts_report_the_first_frame()`
  - Method `.test_schema_mismatches_are_rejected()`
- `class PolicyTest`
  - Method `.test_random_policy_is_bounded_and_seeded()`
  - Method `.test_greedy_policy_repeats_a_winning_action()`
  - Method `.test_greedy_policy_without_a_score_is_random_equivalent()`
  - Method `.test_scripted_policy_holds_its_final_action()`
  - Method `.test_scripted_policy_rejects_an_empty_script()`
- `class FairnessTest`
  - Method `.test_fair_configuration_is_accepted_with_a_witness()`
  - Method `.test_walled_goal_is_rejected()`
  - Method `.test_hazard_spawn_is_rejected_as_terminal()`
  - Method `.test_tight_clock_is_rejected_as_infeasible()`
  - Method `.test_game_without_an_outcome_signal_is_unknown()`
  - Method `.test_no_reference_without_a_win_is_unknown_not_unfair()`
  - Method `.test_nondeterministic_game_is_rejected()`
- `class ReportTest`
  - Method `.test_report_is_frozen_schema_1_and_web_compatible()`
  - Method `.test_report_covers_an_untraced_transcript()`
  - Method `.test_report_rejects_string_reasons_instead_of_splitting_chars()`
  - Method `.test_report_rejects_non_string_reason_elements()`
  - Method `.test_web_simulate_result_assembles_into_the_same_report()` - *A thin adapter wraps POST /api/simulate output; no browser driving.*
- `class PlaytestCliTest`
  - Method `.test_playtest_cli_writes_transcript_and_report()`
  - Method `.test_playtest_cli_rejects_an_unfair_configuration()`
  - Method `.test_playtest_cli_pins_the_transcript_hash()`
  - Method `.test_playtest_cli_flag_guards()`
  - Method `.test_describe_advertises_the_playtest_capability()`
  - Method `.test_fixture_lives_outside_the_engine_core()`

---

### [`tests/test_plugin.py`](tests/test_plugin.py)
> *Tests for the GameModule contract and loader.*

**Size**: `77` lines (`3173` bytes)

**Classes:**
- `class PluginTest`
  - Method `.test_sample_loads_and_implements_the_contract()`
  - Method `.test_describe_exposes_capabilities_actions_and_snapshot()`
  - Method `.test_describe_reports_a_game_ui_hook()`
  - Method `.test_invalid_specs_are_rejected()`
  - Method `.test_loader_rejects_multi_colon_and_noncallable_factory()`
  - Method `.test_missing_methods_are_rejected()`
  - Method `.test_public_api_exports_texture_data()`
- `class IncompleteGame`
  - Method `.build_scene()`

---

### [`tests/test_png.py`](tests/test_png.py)
> *Unit tests for the stdlib PNG writer used by headless screenshots.*

**Size**: `104` lines (`3898` bytes)

**Classes:**
- `class PngTest`
  - Method `.test_round_trip_pixels_and_header()`
  - Method `.test_rejects_wrong_pixel_count()`
  - Method `.test_reader_round_trips_writer_pixels()`
  - Method `.test_reader_rejects_non_png()`
  - Method `.test_creates_missing_parent_directory()`
  - Method `.test_reader_rejects_bad_crc()`
  - Method `.test_reader_wraps_corrupt_idat_as_value_error()`

**Functions:**
- `def _chunks(data)`

---

### [`tests/test_post.py`](tests/test_post.py)
> *Tests for the deterministic post color-grade (in-shader exposure + vignette).*

**Size**: `100` lines (`4247` bytes)

**Classes:**
- `class PostMathTest`
  - Method `.test_constants_are_fixed()`
  - Method `.test_vignette_center_is_one_and_corners_dim()`
  - Method `.test_grade_applies_exposure_then_vignette()`
- `class PostContractsTest`
  - Method `.test_post_settings_default_enabled()`
  - Method `.test_describe_reports_post()`
  - Method `.test_report_includes_post_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_post()`
  - Method `.test_compare_accepts_legacy_without_post()`
  - Method `.test_snapshot_round_trips_post_flag()`
  - Method `.test_scene_document_and_inspector_expose_post()`

---

### [`tests/test_renderer.py`](tests/test_renderer.py)
> *Headless OpenGL integration tests for the Keystone renderer.*

**Size**: `172` lines (`6465` bytes)

**Classes:**
- `class RendererIntegrationTest`
  - Method `.setUp()`
  - Method `.test_render_fills_the_center_with_a_lit_surface()`
  - Method `.test_empty_scene_draws_a_vertical_sky_gradient()`
  - Method `.test_point_light_lights_a_surface_when_the_sun_is_off()`
  - Method `.test_textured_plane_samples_the_texture()`
  - Method `.test_screenshot_is_a_real_png()`
  - Method `.test_shader_compile_error_explains_why_and_fix()`
  - Method `.test_repeated_meshes_render_instanced_with_fewer_calls()`
  - Method `.test_single_nodes_keep_plain_path_and_stats()`
- `class VersionGateTest`
  - Method `.test_rejects_old_opengl()`
  - Method `.test_accepts_33_and_newer()`

**Functions:**
- `def build_scene()`

---

### [`tests/test_replay.py`](tests/test_replay.py)
> *Tests for deterministic action logs and stable hashes.*

**Size**: `65` lines (`2420` bytes)

**Classes:**
- `class ReplayTest`
  - Method `.test_hash_ignores_mapping_order()`
  - Method `.test_command_log_round_trip()`
  - Method `.test_invalid_step_is_rejected()`
  - Method `.test_strict_seed_and_frames_are_rejected()`
  - Method `.test_run_log_restores_global_random_state()`
  - Method `.test_run_log_replays_deterministically()`

---

### [`tests/test_samples.py`](tests/test_samples.py)
> *Tests for the engine's sample game.*

**Size**: `63` lines (`2064` bytes)

**Classes:**
- `class SampleTest`
  - Method `.test_scene_contains_only_generic_renderables()`
  - Method `.test_update_rotates_cubes_and_moves_the_camera()`
  - Method `.test_actions_schema_is_generic()`
  - Method `.test_rebuild_resets_time()`
  - Method `.test_update_without_orb_fails_with_message()`

---

### [`tests/test_scene.py`](tests/test_scene.py)
> *Unit tests for the Keystone scene graph and perspective camera.*

**Size**: `272` lines (`10246` bytes)

**Classes:**
- `class Health`
- `class TransformTest`
  - Method `.test_matrix_applies_scale_then_rotation_then_translation()`
  - Method `.test_default_transform_is_identity()`
- `class NodeTest`
  - Method `.test_child_world_matrix_composes_with_parent()`
  - Method `.test_add_child_reparents_instead_of_duplicating()`
  - Method `.test_add_child_rejects_duplicate_ids_at_write_time()`
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
  - Method `.test_scene_add_rejects_attached_node_without_moving_it()`
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
  - Method `.test_direct_pitch_construction_stays_usable()`
  - Method `.test_look_at_straight_up_stays_usable()`
- `class SceneTest`
  - Method `.test_scene_traverse_starts_at_root()`
  - Method `.test_scene_has_a_sky_color_distinct_from_the_horizon()`
  - Method `.test_point_light_validates_its_radius_and_intensity()`
  - Method `.test_directional_light_normalizes_lookup_direction()`

---

### [`tests/test_scene_snapshot.py`](tests/test_scene_snapshot.py)
> *Unit tests for versioned scene snapshots.*

**Size**: `167` lines (`6912` bytes)

**Classes:**
- `class SceneSnapshotTest`
  - Method `._scene()`
  - Method `.test_round_trip_preserves_structure_and_transforms()`
  - Method `.test_round_trip_preserves_camera_lens_and_environment()`
  - Method `.test_older_schema_one_documents_keep_engine_defaults()`
  - Method `.test_rejects_duplicate_node_ids()`
  - Method `.test_rejects_unknown_parent_reference()`
  - Method `.test_rejects_asset_kind_mismatch()`
  - Method `.test_rejects_non_string_node_ids_and_asset_references()`
  - Method `.test_rejects_non_mapping_camera_and_transform()`
  - Method `.test_rejects_unknown_version()`
  - Method `.test_asset_registry_round_trip_attaches_mesh_and_material()`

---

### [`tests/test_serialization.py`](tests/test_serialization.py)
> *Tests for atomic JSON persistence.*

**Size**: `34` lines (`1308` bytes)

**Classes:**
- `class SerializationTest`
  - Method `.test_round_trip_and_backup()`
  - Method `.test_missing_file_raises()`
  - Method `.test_bom_prefixed_file_reads()`

---

### [`tests/test_shadows.py`](tests/test_shadows.py)
> *Tests for deterministic directional shadow mapping (fixed 1024 map, PCF).*

**Size**: `125` lines (`5272` bytes)

**Classes:**
- `class ShadowMathTest`
  - Method `.test_orthographic_is_deterministic()`
  - Method `.test_light_view_and_vp_are_deterministic()`
  - Method `.test_light_vp_matches_manual_composition()`
  - Method `.test_parallel_up_vector_uses_fallback()`
  - Method `.test_shadow_settings_default_enabled()`
  - Method `.test_only_fixed_size_allowed()`
- `class ShadowContractsTest`
  - Method `.test_describe_reports_shadows()`
  - Method `.test_report_includes_shadow_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_shadows()`
  - Method `.test_compare_accepts_legacy_without_shadows()`
  - Method `.test_snapshot_round_trips_shadow_flag()`
  - Method `.test_scene_document_and_inspector_expose_shadows()`
  - Method `.test_shadow_light_helper_accepts_directional_light()`

---

### [`tests/test_skinning.py`](tests/test_skinning.py)
> *Tests for deterministic linear-blend skinning (max 4 influences).*

**Size**: `294` lines (`12114` bytes)

**Classes:**
- `class SkinValidationTest`
  - Method `.test_unskinned_meshes_stay_legacy()`
  - Method `.test_skinned_stream_packs_padded_joints_and_weights()`
  - Method `.test_rejects_partial_and_mismatched_skin()`
- `class SkinMathTest`
  - Method `.test_rigid_identity_keeps_bind_pose()`
  - Method `.test_rigid_translation_moves_vertices()`
  - Method `.test_half_blend_averages_bones()`
  - Method `.test_bone_rotation_turns_normals()`
  - Method `.test_skin_mesh_preserves_layout()`
  - Method `.test_bone_palette_is_deterministic()`
  - Method `.test_missing_joint_raises_with_fix()`
- `class SkinBatchTest`
  - Method `.test_merge_keeps_skinned_meshes_in_rig_groups()`
- `class SkinGltfTest`
  - Method `._skinned_document(bad_joint, normalized_joints)`
  - Method `.test_loads_a_skin()`
  - Method `.test_rejects_bad_joint_index()`
  - Method `.test_rejects_normalized_joints()`
- `class SkinRenderTest`
  - Method `._skinned_scene()`
  - Method `.test_posed_render_differs_from_bind()`

**Functions:**
- `def _quad_mesh(**overrides)`

---

### [`tests/test_sprites.py`](tests/test_sprites.py)
> *Tests for deterministic GPU point-sprite particle rendering.*

**Size**: `158` lines (`6884` bytes)

**Classes:**
- `class SpriteMathTest`
  - Method `.test_constants_are_fixed()`
  - Method `.test_scale_attenuates_and_clamps()`
  - Method `.test_soft_alpha_center_and_edge()`
  - Method `.test_sprite_alpha_combines_fade_and_soft()`
  - Method `.test_billboard_corners_are_symmetric()`
- `class SpriteSceneTest`
  - Method `.test_scene_defaults_to_sprites_enabled()`
  - Method `.test_snapshot_round_trips_sprites()`
  - Method `.test_snapshot_rejects_non_mapping_sprites()`
- `class SpriteReportTest`
  - Method `.test_schema_is_11_with_sprites_and_fx()`
  - Method `.test_analyze_frame_reports_sprites_and_fx()`
  - Method `.test_no_sprites_changes_report_hash()`
  - Method `.test_compare_accepts_schema_9_baseline()`
  - Method `.test_describe_reports_sprites_capability()`
- `class SpriteSampleTest`
  - Method `.test_fountain_is_deterministic_and_outside_snapshot()`

---

### [`tests/test_srgb.py`](tests/test_srgb.py)
> *Tests for the deterministic sRGB-correct linear pipeline (in-shader, pow 2.2).*

**Size**: `78` lines (`3292` bytes)

**Classes:**
- `class SrgbContractsTest`
  - Method `.test_color_settings_default_enabled()`
  - Method `.test_describe_reports_srgb()`
  - Method `.test_report_includes_color_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_color()`
  - Method `.test_compare_accepts_legacy_without_color()`
  - Method `.test_snapshot_round_trips_color_flag()`
  - Method `.test_scene_document_and_snapshot_expose_color()`

---

### [`tests/test_swarm_fixes.py`](tests/test_swarm_fixes.py)
> *Swarm regression pins: one failing-first test per verified Stage-3 fix.*

**Size**: `103` lines (`3573` bytes)

**Classes:**
- `class SwarmFixesTest`
  - Method `.test_shadow_all_exports_light_vp_for()`
  - Method `.test_quat_json_round_trip()`
  - Method `.test_clock_rejects_non_finite()`
  - Method `.test_command_log_to_dict_isolated()`
  - Method `.test_disabled_mouse_suppresses_click()`
  - Method `.test_update_preserves_insertion_order()`
  - Method `.test_none_flags_report_disabled()`
  - Method `.test_hit_test_right_edge_is_exclusive()`

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

**Size**: `62` lines (`2250` bytes)

**Classes:**
- `class TextureDataTest`
  - Method `.test_checker_is_deterministic_and_has_expected_shape()`
  - Method `.test_png_round_trip_keeps_pixels()`
  - Method `.test_bad_texture_data_is_rejected()`
  - Method `.test_sha256_distinguishes_shapes()`
  - Method `.test_checker_rejects_bad_channel_counts()`

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

**Size**: `164` lines (`6548` bytes)

**Classes:**
- `class FontTest`
  - Method `.test_metrics_match_the_bitmap_grid()`
  - Method `.test_lowercase_and_unknown_characters_are_supported()`
  - Method `.test_truncate_returns_maximal_prefix()`
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
  - Method `.test_pause_menu_move_rejects_non_integer()`

**Functions:**
- `def state(**overrides)`

---

### [`tests/test_web.py`](tests/test_web.py)
> *Tests for scene export, the local JSON API and the browser console assets.*

**Size**: `209` lines (`8937` bytes)

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
  - Method `.test_simulate_rejects_non_finite_step()`

---
