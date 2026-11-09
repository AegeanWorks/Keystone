"""Blinn-Phong forward renderer with fog, shadows and screenshot readback."""

from __future__ import annotations

from pathlib import Path

from OpenGL import GL

from keystone.culling import culling_enabled, extract_planes
from keystone.geometry import Material, MeshData
from keystone.gpu.bloom import (
    BLOOM_INTENSITY,
    BLOOM_KNEE,
    BLOOM_THRESHOLD,
    bloom_blur_size,
)
from keystone.gpu.bloom_fbo import BloomFbo
from keystone.gpu.instancing import group_instances
from keystone.gpu.mesh_buffer import GpuMesh
from keystone.gpu.post import POST_EXPOSURE, POST_VIGNETTE
from keystone.gpu.shader import ShaderProgram
from keystone.gpu.shadow import SHADOW_BIAS, SHADOW_MAP_SIZE, ShadowMap, light_vp_for
from keystone.gpu.skinned_buffer import SkinnedGpuMesh
from keystone.gpu.sprites import SPRITE_COLOR, sprite_alpha
from keystone.gpu.texture_buffer import GpuTexture
from keystone.math3d import Mat4, Vec3
from keystone.png import write_png
from keystone.scene import Scene
from keystone.skin import MAX_SKIN_BONES, bone_matrices
from keystone.texture import TextureData

#: Must match ``MAX_POINT_LIGHTS`` in FRAGMENT_SHADER; extra lights are dropped.
MAX_POINT_LIGHTS = 8

VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
layout(location = 3) in vec3 a_color;
uniform mat4 u_model;
uniform mat4 u_view_proj;
uniform mat3 u_normal_matrix;
out vec3 v_world;
out vec3 v_normal;
out vec2 v_uv;
out vec3 v_color;
void main() {
    vec4 world = u_model * vec4(a_position, 1.0);
    v_world = world.xyz;
    v_normal = normalize(u_normal_matrix * a_normal);
    v_uv = a_uv;
    v_color = a_color;
    gl_Position = u_view_proj * world;
}
"""

FRAGMENT_SHADER = """#version 330 core
in vec3 v_world;
in vec3 v_normal;
in vec2 v_uv;
in vec3 v_color;
uniform vec3 u_color;
uniform sampler2D u_texture;
uniform float u_has_texture;
uniform float u_specular;
uniform float u_shininess;
uniform float u_metallic;
uniform float u_roughness;
uniform vec3 u_emissive;
uniform vec3 u_camera_pos;
uniform vec3 u_light_dir;
uniform vec3 u_light_color;
uniform vec3 u_ambient;
uniform vec3 u_fog_color;
uniform float u_fog_density;
uniform float u_checker_scale;
const int MAX_POINT_LIGHTS = 8;
uniform int u_point_count;
uniform vec3 u_point_pos[MAX_POINT_LIGHTS];
uniform vec3 u_point_color[MAX_POINT_LIGHTS];
uniform float u_point_radius[MAX_POINT_LIGHTS];
uniform mat4 u_light_vp;
uniform sampler2D u_shadow_map;
uniform float u_shadow_bias;
uniform float u_shadows_enabled;
uniform float u_srgb_enabled;
uniform float u_post_enabled;
uniform float u_post_exposure;
uniform float u_post_vignette;
uniform vec2 u_resolution;
uniform float u_bloom_enabled;
uniform float u_bloom_threshold;
uniform float u_bloom_knee;
uniform float u_bloom_intensity;
out vec4 frag_color;
vec3 srgb_to_linear(vec3 c) {
    return pow(max(c, vec3(0.0)), vec3(2.2));
}
vec3 linear_to_srgb(vec3 c) {
    return pow(max(c, vec3(0.0)), vec3(1.0 / 2.2));
}
float shadow_factor(vec3 world_pos) {
    if (u_shadows_enabled < 0.5) {
        return 1.0;
    }
    vec4 sc = u_light_vp * vec4(world_pos, 1.0);
    if (sc.w <= 0.0) {
        return 1.0;
    }
    vec3 ndc = sc.xyz / sc.w;
    if (ndc.x < -1.0 || ndc.x > 1.0 || ndc.y < -1.0 || ndc.y > 1.0 || ndc.z < -1.0 || ndc.z > 1.0) {
        return 1.0;
    }
    vec2 uv = ndc.xy * 0.5 + 0.5;
    float depth = ndc.z * 0.5 + 0.5;
    float texel = 1.0 / 1024.0;
    float lit = 0.0;
    for (int x = -1; x <= 1; ++x) {
        for (int y = -1; y <= 1; ++y) {
            float stored = texture(u_shadow_map, uv + vec2(float(x), float(y)) * texel).r;
            lit += (depth - u_shadow_bias > stored) ? 0.0 : 1.0;
        }
    }
    return lit / 9.0;
}
vec3 apply_bloom(vec3 c) {
    if (u_bloom_enabled < 0.5) {
        return c;
    }
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    float b = smoothstep(u_bloom_threshold, u_bloom_threshold + u_bloom_knee, l);
    return clamp(c + c * b * u_bloom_intensity, vec3(0.0), vec3(1.0));
}
vec3 apply_post(vec3 c) {
    if (u_post_enabled < 0.5) {
        return c;
    }
    vec2 uv = gl_FragCoord.xy / max(u_resolution, vec2(1.0, 1.0));
    vec2 d = uv - vec2(0.5);
    float v = 1.0 - u_post_vignette * dot(d, d) * 2.0;
    return clamp(c * u_post_exposure * clamp(v, 0.0, 1.0), vec3(0.0), vec3(1.0));
}
void main() {
    vec3 normal = normalize(v_normal);
    vec3 to_eye = u_camera_pos - v_world;
    float distance = length(to_eye);
    vec3 view = to_eye / max(distance, 1e-4);
    vec3 light = normalize(-u_light_dir);
    float diffuse = max(dot(normal, light), 0.0);
    vec3 halfway = normalize(light + view);
    float dielectric_spec = pow(max(dot(normal, halfway), 0.0), u_shininess) * u_specular;
    float pbr_spec = pow(max(dot(normal, halfway), 0.0), mix(8.0, 128.0, 1.0 - u_roughness));
    float spec_strength = mix(dielectric_spec, pbr_spec, u_metallic);
    spec_strength *= (1.0 - u_roughness * 0.85);
    vec3 base_color = u_color * v_color;
    if (u_has_texture > 0.5) {
        base_color *= texture(u_texture, v_uv).rgb;
    }
    vec3 ambient = u_ambient;
    vec3 light_color = u_light_color;
    vec3 emissive = u_emissive;
    vec3 fog_color = u_fog_color;
    if (u_srgb_enabled > 0.5) {
        base_color = srgb_to_linear(base_color);
        ambient = srgb_to_linear(ambient);
        light_color = srgb_to_linear(light_color);
        emissive = srgb_to_linear(emissive);
        fog_color = srgb_to_linear(fog_color);
    }
    vec3 diffuse_color = base_color * (1.0 - u_metallic * 0.8);
    float shadow = shadow_factor(v_world);
    vec3 direct = (diffuse_color * light_color * diffuse + light_color * spec_strength) * shadow;
    vec3 color = diffuse_color * ambient + direct + emissive;
    for (int index = 0; index < MAX_POINT_LIGHTS; ++index) {
        if (index >= u_point_count) {
            break;
        }
        float radius = u_point_radius[index];
        if (radius <= 0.0) {
            continue;
        }
        vec3 point_color = u_point_color[index];
        if (u_srgb_enabled > 0.5) {
            point_color = srgb_to_linear(point_color);
        }
        vec3 to_point = u_point_pos[index] - v_world;
        float point_distance = length(to_point);
        float attenuation = max(0.0, 1.0 - point_distance / radius);
        float point_diffuse = max(dot(normal, normalize(to_point)), 0.0);
        color += diffuse_color * point_color * attenuation * attenuation * point_diffuse;
    }
    if (u_checker_scale > 0.0) {
        float tile = mod(floor(v_world.x * u_checker_scale) + floor(v_world.z * u_checker_scale), 2.0);
        color *= mix(0.62, 1.0, tile);
    }
    float fog = 1.0 - exp(-u_fog_density * u_fog_density * distance * distance);
    color = mix(color, fog_color, clamp(fog, 0.0, 1.0));
    if (u_srgb_enabled > 0.5) {
        color = linear_to_srgb(color);
    }
    color = apply_bloom(color);
    color = apply_post(color);
    frag_color = vec4(color, 1.0);
}
"""

VERTEX_SHADER_INSTANCED = """#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
layout(location = 3) in vec3 a_color;
layout(location = 4) in vec4 a_inst0;
layout(location = 5) in vec4 a_inst1;
layout(location = 6) in vec4 a_inst2;
layout(location = 7) in vec4 a_inst3;
layout(location = 8) in vec3 a_nrm0;
layout(location = 9) in vec3 a_nrm1;
layout(location = 10) in vec3 a_nrm2;
uniform mat4 u_view_proj;
out vec3 v_world;
out vec3 v_normal;
out vec2 v_uv;
out vec3 v_color;
void main() {
    mat4 inst = mat4(a_inst0, a_inst1, a_inst2, a_inst3);
    mat3 nmat = mat3(a_nrm0, a_nrm1, a_nrm2);
    vec4 world = inst * vec4(a_position, 1.0);
    v_world = world.xyz;
    v_normal = normalize(nmat * a_normal);
    v_uv = a_uv;
    v_color = a_color;
    gl_Position = u_view_proj * world;
}
"""

SKINNED_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
layout(location = 3) in vec3 a_color;
layout(location = 11) in vec4 a_joints;
layout(location = 12) in vec4 a_weights;
uniform mat4 u_model;
uniform mat4 u_view_proj;
uniform mat3 u_normal_matrix;
uniform mat4 u_bones[64];
out vec3 v_world;
out vec3 v_normal;
out vec2 v_uv;
out vec3 v_color;
void main() {
    vec4 skinned = vec4(0.0);
    vec3 skinned_normal = vec3(0.0);
    float total_weight = 0.0;
    for (int i = 0; i < 4; ++i) {
        int joint = int(a_joints[i] + 0.5);
        float weight = a_weights[i];
        if (weight > 0.0) {
            skinned += weight * (u_bones[joint] * vec4(a_position, 1.0));
            skinned_normal += weight * (transpose(inverse(mat3(u_bones[joint]))) * a_normal);
            total_weight += weight;
        }
    }
    if (total_weight > 0.001) {
        skinned /= total_weight;
        skinned_normal /= total_weight;
    } else {
        skinned = vec4(a_position, 1.0);
        skinned_normal = a_normal;
    }
    vec4 world = u_model * skinned;
    v_world = world.xyz;
    v_normal = normalize(u_normal_matrix * normalize(skinned_normal));
    v_uv = a_uv;
    v_color = a_color;
    gl_Position = u_view_proj * world;
}
"""

SKINNED_DEPTH_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 11) in vec4 a_joints;
layout(location = 12) in vec4 a_weights;
uniform mat4 u_model;
uniform mat4 u_light_vp;
uniform mat4 u_bones[64];
void main() {
    vec4 skinned = vec4(0.0);
    float total_weight = 0.0;
    for (int i = 0; i < 4; ++i) {
        int joint = int(a_joints[i] + 0.5);
        float weight = a_weights[i];
        if (weight > 0.0) {
            skinned += weight * (u_bones[joint] * vec4(a_position, 1.0));
            total_weight += weight;
        }
    }
    if (total_weight > 0.001) {
        skinned /= total_weight;
    } else {
        skinned = vec4(a_position, 1.0);
    }
    gl_Position = u_light_vp * u_model * skinned;
}
"""

SPRITE_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec2 a_corner;
layout(location = 1) in vec3 a_offset;
layout(location = 2) in float a_scale;
layout(location = 3) in float a_alpha;
layout(location = 4) in vec3 a_tint;
uniform mat4 u_view_proj;
uniform vec3 u_right;
uniform vec3 u_up;
out vec2 v_uv;
out float v_alpha;
out vec3 v_tint;
void main() {
    v_uv = a_corner + vec2(0.5);
    v_alpha = a_alpha;
    v_tint = a_tint;
    vec3 world = a_offset + (u_right * a_corner.x + u_up * a_corner.y) * a_scale;
    gl_Position = u_view_proj * vec4(world, 1.0);
}
"""

SPRITE_FRAGMENT_SHADER = """#version 330 core
in vec2 v_uv;
in float v_alpha;
in vec3 v_tint;
uniform vec3 u_sprite_color;
uniform float u_bloom_enabled;
uniform float u_bloom_threshold;
uniform float u_bloom_knee;
uniform float u_bloom_intensity;
uniform float u_post_enabled;
uniform float u_post_exposure;
uniform float u_post_vignette;
uniform vec2 u_resolution;
out vec4 frag_color;
void main() {
    vec2 d = v_uv - vec2(0.5);
    float r = length(d) * 2.0;
    float soft = clamp(1.0 - r, 0.0, 1.0);
    float a = soft * v_alpha;
    if (a <= 0.001) {
        discard;
    }
    vec3 color = u_sprite_color * v_tint;
    float l = dot(color, vec3(0.2126, 0.7152, 0.0722));
    if (u_bloom_enabled > 0.5) {
        float b = smoothstep(u_bloom_threshold, u_bloom_threshold + u_bloom_knee, l);
        color = clamp(color + color * b * u_bloom_intensity, vec3(0.0), vec3(1.0));
    }
    if (u_post_enabled > 0.5) {
        vec2 uv = gl_FragCoord.xy / max(u_resolution, vec2(1.0, 1.0));
        vec2 dd = uv - vec2(0.5);
        float v = 1.0 - u_post_vignette * dot(dd, dd) * 2.0;
        color = clamp(color * u_post_exposure * clamp(v, 0.0, 1.0), vec3(0.0), vec3(1.0));
    }
    frag_color = vec4(color, a);
}
"""

SKY_VERTEX_SHADER = """#version 330 core
out vec2 v_uv;
void main() {
    vec2 corner = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    v_uv = corner;
    gl_Position = vec4(corner * 2.0 - 1.0, 0.9999, 1.0);
}
"""

SKY_FRAGMENT_SHADER = """#version 330 core
in vec2 v_uv;
uniform vec3 u_sky_top;
uniform vec3 u_sky_bottom;
uniform float u_srgb_enabled;
uniform float u_post_enabled;
uniform float u_post_exposure;
uniform float u_post_vignette;
uniform float u_bloom_enabled;
uniform float u_bloom_threshold;
uniform float u_bloom_knee;
uniform float u_bloom_intensity;
out vec4 frag_color;
void main() {
    vec3 top = u_sky_top;
    vec3 bottom = u_sky_bottom;
    if (u_srgb_enabled > 0.5) {
        top = pow(max(top, vec3(0.0)), vec3(2.2));
        bottom = pow(max(bottom, vec3(0.0)), vec3(2.2));
    }
    vec3 color = mix(bottom, top, smoothstep(0.0, 1.0, v_uv.y));
    if (u_srgb_enabled > 0.5) {
        color = pow(max(color, vec3(0.0)), vec3(1.0 / 2.2));
    }
    if (u_bloom_enabled > 0.5) {
        float bl = dot(color, vec3(0.2126, 0.7152, 0.0722));
        float bb = smoothstep(u_bloom_threshold, u_bloom_threshold + u_bloom_knee, bl);
        color = clamp(color + color * bb * u_bloom_intensity, vec3(0.0), vec3(1.0));
    }
    if (u_post_enabled > 0.5) {
        vec2 d = v_uv - vec2(0.5);
        float v = 1.0 - u_post_vignette * dot(d, d) * 2.0;
        color = clamp(color * u_post_exposure * clamp(v, 0.0, 1.0), vec3(0.0), vec3(1.0));
    }
    frag_color = vec4(color, 1.0);
}
"""

DEPTH_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 a_position;
uniform mat4 u_model;
uniform mat4 u_light_vp;
void main() {
    gl_Position = u_light_vp * u_model * vec4(a_position, 1.0);
}
"""

DEPTH_FRAGMENT_SHADER = """#version 330 core
void main() {
}
"""

BLOOM_QUAD_VERTEX = """#version 330 core
out vec2 v_uv;
void main() {
    vec2 corner = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    v_uv = corner;
    gl_Position = vec4(corner * 2.0 - 1.0, 0.0, 1.0);
}
"""

BLOOM_BRIGHT_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D u_scene;
uniform float u_bloom_threshold;
uniform float u_bloom_knee;
out vec4 frag_color;
void main() {
    vec3 c = texture(u_scene, v_uv).rgb;
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    float b = smoothstep(u_bloom_threshold, u_bloom_threshold + u_bloom_knee, l);
    frag_color = vec4(c * b, 1.0);
}
"""

BLOOM_BLUR_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D u_blur;
uniform vec2 u_texel;
uniform vec2 u_direction;
out vec4 frag_color;
void main() {
    vec2 d = u_direction * u_texel;
    vec3 c = texture(u_blur, v_uv).rgb * 0.227027;
    c += texture(u_blur, v_uv + d * 1.3846153846).rgb * 0.3162162162;
    c += texture(u_blur, v_uv - d * 1.3846153846).rgb * 0.3162162162;
    c += texture(u_blur, v_uv + d * 3.2307692308).rgb * 0.0702702703;
    c += texture(u_blur, v_uv - d * 3.2307692308).rgb * 0.0702702703;
    frag_color = vec4(c, 1.0);
}
"""

BLOOM_COMPOSITE_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_bloom_intensity;
out vec4 frag_color;
void main() {
    vec3 scene = texture(u_scene, v_uv).rgb;
    vec3 blurred = texture(u_bloom, v_uv).rgb;
    frag_color = vec4(clamp(scene + blurred * u_bloom_intensity, vec3(0.0), vec3(1.0)), 1.0);
}
"""


def normal_matrix(model: Mat4) -> tuple[float, ...]:
    """Return transpose(inverse(upper 3x3)) in column-major order.

    Singular models cannot be normal-transformed; identity keeps the render
    loop alive instead of aborting on an animation-driven zero scale.
    """
    try:
        inverse = model.inverse()
    except ValueError:
        return (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    return (
        inverse[0], inverse[4], inverse[8],
        inverse[1], inverse[5], inverse[9],
        inverse[2], inverse[6], inverse[10],
    )


class Renderer:
    """Owns the shader and per-mesh GPU buffers for one OpenGL context."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("renderer width and height must be positive")
        self.width = width
        self.height = height
        self._program = ShaderProgram(VERTEX_SHADER, FRAGMENT_SHADER)
        inst_program: ShaderProgram | None = None
        sky_program = None
        depth_program: ShaderProgram | None = None
        skin_program: ShaderProgram | None = None
        skin_depth_program: ShaderProgram | None = None
        sprite_program: ShaderProgram | None = None
        bright_program: ShaderProgram | None = None
        blur_program: ShaderProgram | None = None
        composite_program: ShaderProgram | None = None
        try:
            inst_program = ShaderProgram(VERTEX_SHADER_INSTANCED, FRAGMENT_SHADER)
            sky_program = ShaderProgram(SKY_VERTEX_SHADER, SKY_FRAGMENT_SHADER)
            depth_program = ShaderProgram(DEPTH_VERTEX_SHADER, DEPTH_FRAGMENT_SHADER)
            skin_program = ShaderProgram(SKINNED_VERTEX_SHADER, FRAGMENT_SHADER)
            skin_depth_program = ShaderProgram(SKINNED_DEPTH_VERTEX_SHADER, DEPTH_FRAGMENT_SHADER)
            sprite_program = ShaderProgram(SPRITE_VERTEX_SHADER, SPRITE_FRAGMENT_SHADER)
            bright_program = ShaderProgram(BLOOM_QUAD_VERTEX, BLOOM_BRIGHT_FRAGMENT)
            blur_program = ShaderProgram(BLOOM_QUAD_VERTEX, BLOOM_BLUR_FRAGMENT)
            composite_program = ShaderProgram(BLOOM_QUAD_VERTEX, BLOOM_COMPOSITE_FRAGMENT)
            self._sky_vao = GL.glGenVertexArrays(1)
        except Exception:
            if sprite_program is not None:
                sprite_program.release()
            if composite_program is not None:
                composite_program.release()
            if blur_program is not None:
                blur_program.release()
            if bright_program is not None:
                bright_program.release()
            if skin_depth_program is not None:
                skin_depth_program.release()
            if skin_program is not None:
                skin_program.release()
            if depth_program is not None:
                depth_program.release()
            if sky_program is not None:
                sky_program.release()
            if inst_program is not None:
                inst_program.release()
            self._program.release()
            raise
        self._inst_program = inst_program
        self._sky_program = sky_program
        self._depth_program = depth_program
        self._skin_program = skin_program
        self._skin_depth_program = skin_depth_program
        self._sprite_program = sprite_program
        self._sprite_vao = 0
        self._sprite_quad_vbo = 0
        self._sprite_inst_vbo = 0
        self._sprite_ibo = 0
        self._init_sprite_buffers()
        self._bloom_bright = bright_program
        self._bloom_blur = blur_program
        self._bloom_composite = composite_program
        self._shadow: ShadowMap | None = None
        self._shadow_error: str | None = None
        try:
            self._shadow = ShadowMap()
        except (RuntimeError, ValueError) as exc:
            self._shadow_error = str(exc)
        self._bloom_scene: BloomFbo | None = None
        self._bloom_a: BloomFbo | None = None
        self._bloom_b: BloomFbo | None = None
        self._bloom_error: str | None = None
        try:
            self._create_bloom_fbos()
        except (RuntimeError, ValueError) as exc:
            self._bloom_error = str(exc)
            self._release_bloom_fbos()
        self._meshes: dict[int, tuple[MeshData, GpuMesh]] = {}
        self._skinned_meshes: dict[int, tuple[MeshData, SkinnedGpuMesh]] = {}
        self._identity_bones: tuple[Mat4, ...] = tuple(Mat4.identity() for _ in range(MAX_SKIN_BONES))
        self._textures: dict[int, tuple[TextureData, GpuTexture]] = {}
        self.last_stats: dict[str, int] = {
            "draw_calls": 0,
            "triangles": 0,
            "instanced_calls": 0,
            "instances": 0,
            "shadow_calls": 0,
            "shadow_map_size": SHADOW_MAP_SIZE,
            "shadows_enabled": 0,
            "srgb_enabled": 0,
            "post_enabled": 0,
            "bloom_enabled": 0,
            "sprite_calls": 0,
            "sprites": 0,
            "sprites_enabled": 0,
            "culled_nodes": 0,
            "culling_enabled": 0,
        }
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        GL.glFrontFace(GL.GL_CCW)
        GL.glEnable(GL.GL_MULTISAMPLE)

    def resize(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("renderer width and height must be positive")
        self.width = width
        self.height = height
        if self._bloom_scene is not None or self._bloom_a is not None or self._bloom_b is not None:
            try:
                self._create_bloom_fbos()
            except (RuntimeError, ValueError) as exc:
                self._bloom_error = str(exc)
                self._release_bloom_fbos()

    def _create_bloom_fbos(self) -> None:
        self._release_bloom_fbos()
        half_w, half_h = bloom_blur_size(self.width, self.height)
        self._bloom_scene = BloomFbo(self.width, self.height)
        self._bloom_a = BloomFbo(half_w, half_h)
        self._bloom_b = BloomFbo(half_w, half_h)

    def _release_bloom_fbos(self) -> None:
        for fbo in (self._bloom_scene, self._bloom_a, self._bloom_b):
            if fbo is not None:
                fbo.release()
        self._bloom_scene = None
        self._bloom_a = None
        self._bloom_b = None

    def _ensure_bloom_fbos(self) -> None:
        half_w, half_h = bloom_blur_size(self.width, self.height)
        scene = self._bloom_scene
        first = self._bloom_a
        second = self._bloom_b
        if (
            scene is None or first is None or second is None
            or scene.width != self.width or scene.height != self.height
            or first.width != half_w or first.height != half_h
            or second.width != half_w or second.height != half_h
        ):
            self._create_bloom_fbos()

    def _gpu_mesh(self, mesh: MeshData) -> GpuMesh:
        cached = self._meshes.get(id(mesh))
        if cached is None or cached[0] is not mesh:
            cached = (mesh, GpuMesh(mesh))
            self._meshes[id(mesh)] = cached
        return cached[1]

    def _gpu_skinned_mesh(self, mesh: MeshData) -> SkinnedGpuMesh:
        cached = self._skinned_meshes.get(id(mesh))
        if cached is None or cached[0] is not mesh:
            cached = (mesh, SkinnedGpuMesh(mesh))
            self._skinned_meshes[id(mesh)] = cached
        return cached[1]

    def _upload_bones(self, program: ShaderProgram, scene: Scene, mesh: MeshData) -> None:
        bones = bone_matrices(scene, mesh)
        if len(bones) < len(mesh.skin_joints):
            raise RuntimeError(
                "Skin bone palette is incomplete.\n"
                "Why: the scene is missing joint nodes for this skinned mesh.\n"
                "Fix: add every skin joint node to the scene before rendering."
            )
        palette = list(bones[:MAX_SKIN_BONES])
        while len(palette) < MAX_SKIN_BONES:
            palette.append(self._identity_bones[len(palette)])
        program.use()
        program.set_mat4_array("u_bones", palette)

    def _gpu_texture(self, texture: TextureData) -> GpuTexture:
        cached = self._textures.get(id(texture))
        if cached is None or cached[0] is not texture:
            cached = (texture, GpuTexture(texture))
            self._textures[id(texture)] = cached
        return cached[1]

    def _draw_sky(self, scene: Scene, srgb_on: bool = True, post_on: bool = True, bloom_on: bool = True) -> None:
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        self._sky_program.use()
        self._sky_program.set_vec3("u_sky_top", scene.sky)
        self._sky_program.set_vec3("u_sky_bottom", scene.background)
        self._sky_program.set_float("u_srgb_enabled", 1.0 if srgb_on else 0.0)
        self._sky_program.set_float("u_post_enabled", 1.0 if post_on else 0.0)
        self._sky_program.set_float("u_post_exposure", POST_EXPOSURE)
        self._sky_program.set_float("u_post_vignette", POST_VIGNETTE)
        self._sky_program.set_float("u_bloom_enabled", 1.0 if bloom_on else 0.0)
        self._sky_program.set_float("u_bloom_threshold", BLOOM_THRESHOLD)
        self._sky_program.set_float("u_bloom_knee", BLOOM_KNEE)
        self._sky_program.set_float("u_bloom_intensity", BLOOM_INTENSITY)
        GL.glBindVertexArray(self._sky_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        GL.glBindVertexArray(0)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glEnable(GL.GL_DEPTH_TEST)

    def _shadows_requested(self, scene: Scene) -> bool:
        shadow = getattr(scene, "shadow", None)
        return bool(getattr(shadow, "enabled", True))

    def _srgb_requested(self, scene: Scene) -> bool:
        color = getattr(scene, "color", None)
        return bool(getattr(color, "enabled", True))

    def _post_requested(self, scene: Scene) -> bool:
        post = getattr(scene, "post", None)
        return bool(getattr(post, "enabled", True))

    def _bloom_requested(self, scene: Scene) -> bool:
        bloom = getattr(scene, "bloom", None)
        return bool(getattr(bloom, "enabled", True))

    def _sprites_requested(self, scene: Scene) -> bool:
        sprite = getattr(scene, "sprite", None)
        return bool(getattr(sprite, "enabled", True))

    def _culling_requested(self, scene: Scene) -> bool:
        return culling_enabled(scene)

    def _init_sprite_buffers(self) -> None:
        self._sprite_vao = GL.glGenVertexArrays(1)
        self._sprite_quad_vbo = GL.glGenBuffers(1)
        self._sprite_inst_vbo = GL.glGenBuffers(1)
        self._sprite_ibo = GL.glGenBuffers(1)
        corners = [-0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5]
        indices = [0, 1, 2, 0, 2, 3]
        GL.glBindVertexArray(self._sprite_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._sprite_quad_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, len(corners) * 4, (GL.GLfloat * len(corners))(*corners), GL.GL_STATIC_DRAW)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._sprite_inst_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, None, GL.GL_DYNAMIC_DRAW)
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 8 * 4, GL.GLvoidp(0))
        GL.glVertexAttribDivisor(1, 1)
        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(2, 1, GL.GL_FLOAT, GL.GL_FALSE, 8 * 4, GL.GLvoidp(3 * 4))
        GL.glVertexAttribDivisor(2, 1)
        GL.glEnableVertexAttribArray(3)
        GL.glVertexAttribPointer(3, 1, GL.GL_FLOAT, GL.GL_FALSE, 8 * 4, GL.GLvoidp(4 * 4))
        GL.glVertexAttribDivisor(3, 1)
        GL.glEnableVertexAttribArray(4)
        GL.glVertexAttribPointer(4, 3, GL.GL_FLOAT, GL.GL_FALSE, 8 * 4, GL.GLvoidp(5 * 4))
        GL.glVertexAttribDivisor(4, 1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._sprite_ibo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, len(indices) * 4, (GL.GLuint * len(indices))(*indices), GL.GL_STATIC_DRAW)
        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def _release_sprite_buffers(self) -> None:
        if self._sprite_ibo:
            GL.glDeleteBuffers(1, [self._sprite_ibo])
            self._sprite_ibo = 0
        if self._sprite_inst_vbo:
            GL.glDeleteBuffers(1, [self._sprite_inst_vbo])
            self._sprite_inst_vbo = 0
        if self._sprite_quad_vbo:
            GL.glDeleteBuffers(1, [self._sprite_quad_vbo])
            self._sprite_quad_vbo = 0
        if self._sprite_vao:
            GL.glDeleteVertexArrays(1, [self._sprite_vao])
            self._sprite_vao = 0

    def _camera_basis(self, scene: Scene) -> tuple[Vec3, Vec3]:
        flat = scene.camera.view_matrix().flat()
        return (Vec3(flat[0], flat[4], flat[8]), Vec3(flat[1], flat[5], flat[9]))

    def _draw_sprites(
        self,
        scene: Scene,
        particles: object | None,
        view_projection: Mat4,
        post_on: bool,
        bloom_on: bool,
    ) -> tuple[int, int]:
        if not self._sprites_requested(scene):
            return (0, 0)
        rows: list[float] = []
        items = getattr(particles, "particles", None)
        if isinstance(items, list):
            for particle in items:
                try:
                    position = particle.position
                    age = float(particle.age)
                    lifetime = float(particle.lifetime)
                    size = float(particle.size)
                except (AttributeError, TypeError, ValueError):
                    continue
                if lifetime <= 0.0 or age >= lifetime:
                    continue
                try:
                    alpha = sprite_alpha(age, lifetime)
                except ValueError:
                    continue
                if alpha <= 0.001:
                    continue
                rows.extend([float(position.x), float(position.y), float(position.z), max(size * 0.35, 0.05), alpha, 1.0, 1.0, 1.0])
        # Placed sprites are scene content, so they draw even with no particles.
        for node in scene.traverse():
            sprite = getattr(node, "sprite", None)
            if sprite is None or not node.world_visible():
                continue
            if float(sprite.alpha) <= 0.001 or float(sprite.size) <= 0.0:
                continue
            center = node.world_matrix().transform_point(Vec3())
            rows.extend(
                [
                    float(center.x),
                    float(center.y),
                    float(center.z),
                    float(sprite.size),
                    float(sprite.alpha),
                    float(sprite.color.x),
                    float(sprite.color.y),
                    float(sprite.color.z),
                ]
            )
        count = len(rows) // 8
        if count == 0:
            return (0, 0)
        right, up = self._camera_basis(scene)
        data = (GL.GLfloat * len(rows))(*rows)
        GL.glBindVertexArray(self._sprite_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._sprite_inst_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, len(rows) * 4, data, GL.GL_DYNAMIC_DRAW)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)
        self._sprite_program.use()
        self._sprite_program.set_mat4("u_view_proj", view_projection)
        self._sprite_program.set_vec3("u_right", right)
        self._sprite_program.set_vec3("u_up", up)
        self._sprite_program.set_vec3("u_sprite_color", Vec3(*SPRITE_COLOR))
        self._sprite_program.set_float("u_bloom_enabled", 1.0 if bloom_on else 0.0)
        self._sprite_program.set_float("u_bloom_threshold", BLOOM_THRESHOLD)
        self._sprite_program.set_float("u_bloom_knee", BLOOM_KNEE)
        self._sprite_program.set_float("u_bloom_intensity", BLOOM_INTENSITY)
        self._sprite_program.set_float("u_post_enabled", 1.0 if post_on else 0.0)
        self._sprite_program.set_float("u_post_exposure", POST_EXPOSURE)
        self._sprite_program.set_float("u_post_vignette", POST_VIGNETTE)
        self._sprite_program.set_vec2("u_resolution", float(self.width), float(self.height))
        GL.glDrawElementsInstanced(GL.GL_TRIANGLES, 6, GL.GL_UNSIGNED_INT, None, count)
        GL.glBindVertexArray(0)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        return (1, count)

    def _apply_bloom(self, program: ShaderProgram, bloom_on: bool) -> None:
        program.use()
        program.set_float("u_bloom_enabled", 1.0 if bloom_on else 0.0)
        program.set_float("u_bloom_threshold", BLOOM_THRESHOLD)
        program.set_float("u_bloom_knee", BLOOM_KNEE)
        program.set_float("u_bloom_intensity", BLOOM_INTENSITY)

    def _apply_post(self, program: ShaderProgram, post_on: bool) -> None:
        program.use()
        program.set_float("u_post_enabled", 1.0 if post_on else 0.0)
        program.set_float("u_post_exposure", POST_EXPOSURE)
        program.set_float("u_post_vignette", POST_VIGNETTE)
        program.set_vec2("u_resolution", float(self.width), float(self.height))

    def _apply_shared(
        self,
        program: ShaderProgram,
        scene: Scene,
        view_projection: Mat4,
        light_vp: Mat4,
        shadows_on: bool,
        srgb_on: bool = True,
    ) -> None:
        camera = scene.camera
        light = scene.light
        background = scene.background
        program.use()
        program.set_mat4("u_view_proj", view_projection)
        program.set_vec3("u_camera_pos", camera.position)
        program.set_vec3("u_light_dir", light.unit_direction())
        program.set_vec3("u_light_color", light.radiance())
        program.set_vec3("u_ambient", scene.ambient)
        program.set_vec3("u_fog_color", background)
        program.set_float("u_fog_density", scene.fog_density)
        program.set_mat4("u_light_vp", light_vp)
        program.set_float("u_shadow_bias", SHADOW_BIAS)
        program.set_float("u_shadows_enabled", 1.0 if shadows_on else 0.0)
        program.set_float("u_srgb_enabled", 1.0 if srgb_on else 0.0)
        program.set_int("u_shadow_map", 1)
        lights = list(scene.point_lights)[:MAX_POINT_LIGHTS]
        if not lights:
            program.set_int("u_point_count", 0)
            program.set_vec3_array("u_point_pos", ())
            program.set_vec3_array("u_point_color", ())
            program.set_float_array("u_point_radius", ())
        else:
            program.set_int("u_point_count", len(lights))
            program.set_vec3_array("u_point_pos", [light.position for light in lights])
            program.set_vec3_array(
                "u_point_color",
                [light.color * light.intensity for light in lights],
            )
            program.set_float_array("u_point_radius", [light.radius for light in lights])

    def _apply_material(self, program: ShaderProgram, material: Material) -> None:
        program.set_vec3("u_color", material.color)
        program.set_float("u_specular", material.specular)
        program.set_float("u_shininess", material.shininess)
        program.set_float("u_metallic", material.metallic)
        program.set_float("u_roughness", material.roughness)
        program.set_vec3("u_emissive", material.emissive)
        program.set_float("u_checker_scale", material.checker_scale)
        texture = material.texture if isinstance(material.texture, TextureData) else None
        if texture is None:
            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            program.set_float("u_has_texture", 0.0)
        else:
            self._gpu_texture(texture).bind(0)
            program.set_int("u_texture", 0)
            program.set_float("u_has_texture", 1.0)

    def _render_shadow_pass(self, scene: Scene, light_vp: Mat4) -> int:
        shadow_calls = 0
        assert self._shadow is not None
        self._shadow.bind_for_write()
        try:
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDepthFunc(GL.GL_LESS)
            GL.glCullFace(GL.GL_FRONT)
            self._depth_program.use()
            self._depth_program.set_mat4("u_light_vp", light_vp)
            for group in group_instances(scene):
                mesh = group["mesh"]
                if not isinstance(mesh, MeshData):
                    raise TypeError("Node.mesh must be MeshData")
                skinned = bool(getattr(mesh, "skinned", False))
                for model in group["models"]:
                    if skinned:
                        self._skin_depth_program.use()
                        self._skin_depth_program.set_mat4("u_light_vp", light_vp)
                        self._skin_depth_program.set_mat4("u_model", Mat4.identity())
                        self._upload_bones(self._skin_depth_program, scene, mesh)
                        self._gpu_skinned_mesh(mesh).draw()
                    else:
                        self._depth_program.use()
                        self._depth_program.set_mat4("u_model", model)
                        self._gpu_mesh(mesh).draw()
                    shadow_calls += 1
            return shadow_calls
        finally:
            GL.glCullFace(GL.GL_BACK)
            self._shadow.unbind_after_write(self.width, self.height)

    def _draw_quad(self) -> None:
        GL.glBindVertexArray(self._sky_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        GL.glBindVertexArray(0)

    def _draw_geometry(
        self,
        scene: Scene,
        view_projection: Mat4,
        light_vp: Mat4,
        shadows_on: bool,
        srgb_on: bool,
        post_on: bool,
        bloom_on: bool,
        planes: tuple[tuple[float, float, float, float], ...] | None = None,
    ) -> tuple[int, int, int, int, int]:
        draw_calls = 0
        triangles = 0
        instanced_calls = 0
        instances = 0
        kept_nodes = 0
        self._apply_shared(self._program, scene, view_projection, light_vp, shadows_on, srgb_on)
        self._apply_shared(self._inst_program, scene, view_projection, light_vp, shadows_on, srgb_on)
        self._apply_shared(self._skin_program, scene, view_projection, light_vp, shadows_on, srgb_on)
        self._apply_bloom(self._program, bloom_on)
        self._apply_bloom(self._inst_program, bloom_on)
        self._apply_bloom(self._skin_program, bloom_on)
        self._apply_post(self._program, post_on)
        self._apply_post(self._inst_program, post_on)
        self._apply_post(self._skin_program, post_on)
        for group in group_instances(scene, planes):
            mesh = group["mesh"]
            if not isinstance(mesh, MeshData):
                raise TypeError("Node.mesh must be MeshData")
            material = group["material"] if isinstance(group["material"], Material) else Material()
            nodes = group["nodes"]
            models = group["models"]
            kept_nodes += len(nodes)
            skinned = bool(getattr(mesh, "skinned", False))
            if skinned:
                # glTF skinned meshes are already in world space through the
                # bone palette; the mesh node transform must be ignored.
                identity = Mat4.identity()
                for _model in models:
                    self._skin_program.use()
                    self._skin_program.set_mat4("u_model", identity)
                    self._skin_program.set_mat3("u_normal_matrix", normal_matrix(identity))
                    self._upload_bones(self._skin_program, scene, mesh)
                    self._apply_material(self._skin_program, material)
                    self._gpu_skinned_mesh(mesh).draw()
                    draw_calls += 1
                    triangles += mesh.triangle_count()
                continue
            if len(models) == 1:
                model = models[0]
                self._program.use()
                self._program.set_mat4("u_model", model)
                self._program.set_mat3("u_normal_matrix", normal_matrix(model))
                self._apply_material(self._program, material)
                self._gpu_mesh(mesh).draw()
                draw_calls += 1
                triangles += mesh.triangle_count()
            else:
                self._inst_program.use()
                self._apply_material(self._inst_program, material)
                model_flats = [model.flat() for model in models]
                normal_flats = [normal_matrix(model) for model in models]
                self._gpu_mesh(mesh).draw_instanced(model_flats, normal_flats)
                draw_calls += 1
                instanced_calls += 1
                instances += len(models)
                triangles += mesh.triangle_count() * len(models)
        return (draw_calls, triangles, instanced_calls, instances, kept_nodes)

    def _run_bloom_chain(self) -> None:
        assert self._bloom_scene is not None
        assert self._bloom_a is not None
        assert self._bloom_b is not None
        half_w, half_h = bloom_blur_size(self.width, self.height)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        self._bloom_a.bind_for_write()
        self._bloom_bright.use()
        self._bloom_scene.bind_for_read(2)
        self._bloom_bright.set_int("u_scene", 2)
        self._bloom_bright.set_float("u_bloom_threshold", BLOOM_THRESHOLD)
        self._bloom_bright.set_float("u_bloom_knee", BLOOM_KNEE)
        self._draw_quad()
        self._bloom_scene.unbind_after_read(2)
        self._bloom_b.bind_for_write()
        self._bloom_blur.use()
        self._bloom_a.bind_for_read(2)
        self._bloom_blur.set_int("u_blur", 2)
        self._bloom_blur.set_vec2("u_texel", 1.0 / max(1, half_w), 1.0 / max(1, half_h))
        self._bloom_blur.set_vec2("u_direction", 1.0, 0.0)
        self._draw_quad()
        self._bloom_a.unbind_after_read(2)
        self._bloom_a.bind_for_write()
        self._bloom_blur.use()
        self._bloom_b.bind_for_read(2)
        self._bloom_blur.set_int("u_blur", 2)
        self._bloom_blur.set_vec2("u_texel", 1.0 / max(1, half_w), 1.0 / max(1, half_h))
        self._bloom_blur.set_vec2("u_direction", 0.0, 1.0)
        self._draw_quad()
        self._bloom_b.unbind_after_read(2)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glViewport(0, 0, self.width, self.height)
        self._bloom_composite.use()
        self._bloom_scene.bind_for_read(2)
        self._bloom_a.bind_for_read(3)
        self._bloom_composite.set_int("u_scene", 2)
        self._bloom_composite.set_int("u_bloom", 3)
        self._bloom_composite.set_float("u_bloom_intensity", BLOOM_INTENSITY)
        self._draw_quad()
        self._bloom_scene.unbind_after_read(2)
        self._bloom_a.unbind_after_read(3)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glActiveTexture(GL.GL_TEXTURE0)

    def render(self, scene: Scene, particles: object | None = None) -> dict[str, int]:
        draw_calls = 0
        triangles = 0
        instanced_calls = 0
        instances = 0
        sprite_calls = 0
        sprites = 0
        shadow_calls = 0
        requested = self._shadows_requested(scene)
        if requested and self._shadow is None:
            raise RuntimeError(
                f"{self._shadow_error or 'Shadow framebuffer unavailable.'}\n"
                "Why: directional shadows are enabled but the depth FBO failed.\n"
                "Fix: update the GPU driver, or re-run with --no-shadows."
            )
        shadows_on = bool(requested and self._shadow is not None)
        srgb_on = self._srgb_requested(scene)
        post_on = self._post_requested(scene)
        bloom_on = self._bloom_requested(scene)
        sprites_on = self._sprites_requested(scene)
        culling_on = self._culling_requested(scene)
        if bloom_on and (
            self._bloom_scene is None or self._bloom_a is None or self._bloom_b is None
        ):
            raise RuntimeError(
                f"{self._bloom_error or 'Bloom framebuffers unavailable.'}\n"
                "Why: bloom diffusion is enabled but the color FBOs failed.\n"
                "Fix: update the GPU driver, or re-run with --no-bloom."
            )
        light_vp = light_vp_for(scene.light)
        if shadows_on:
            shadow_calls = self._render_shadow_pass(scene, light_vp)
            self._shadow.bind_for_read(1)
        camera = scene.camera
        view_projection = camera.view_projection(self.width / self.height)
        background = scene.background
        planes: tuple[tuple[float, float, float, float], ...] | None = None
        total_mesh = 0
        kept_nodes = 0
        if culling_on:
            try:
                planes = extract_planes(view_projection)
            except (ValueError, ArithmeticError):
                planes = None
            if planes is not None:
                for node in scene.traverse():
                    if isinstance(node.mesh, MeshData) and node.world_visible():
                        total_mesh += 1
        if not bloom_on:
            GL.glViewport(0, 0, self.width, self.height)
            GL.glClearColor(background.x, background.y, background.z, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            self._draw_sky(scene, srgb_on, post_on, bloom_on)
            drawn = self._draw_geometry(
                scene, view_projection, light_vp, shadows_on, srgb_on, post_on, bloom_on, planes
            )
            draw_calls, triangles, instanced_calls, instances, kept_nodes = drawn
            sprite_calls, sprites = self._draw_sprites(scene, particles, view_projection, post_on, bloom_on)
            draw_calls += sprite_calls
            triangles += sprites * 2
        else:
            self._ensure_bloom_fbos()
            assert self._bloom_scene is not None
            self._bloom_scene.bind_for_write()
            GL.glClearColor(background.x, background.y, background.z, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            self._draw_sky(scene, srgb_on, post_on, bloom_on)
            drawn = self._draw_geometry(
                scene, view_projection, light_vp, shadows_on, srgb_on, post_on, bloom_on, planes
            )
            draw_calls, triangles, instanced_calls, instances, kept_nodes = drawn
            sprite_calls, sprites = self._draw_sprites(scene, particles, view_projection, post_on, bloom_on)
            draw_calls += sprite_calls
            triangles += sprites * 2
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            self._run_bloom_chain()
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        if shadows_on:
            assert self._shadow is not None
            self._shadow.unbind_after_read(1)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        self.last_stats = {
            "draw_calls": draw_calls,
            "triangles": triangles,
            "instanced_calls": instanced_calls,
            "instances": instances,
            "shadow_calls": shadow_calls,
            "shadow_map_size": SHADOW_MAP_SIZE if shadows_on else 0,
            "shadows_enabled": 1 if shadows_on else 0,
            "srgb_enabled": 1 if srgb_on else 0,
            "post_enabled": 1 if post_on else 0,
            "bloom_enabled": 1 if bloom_on else 0,
            "sprite_calls": sprite_calls,
            "sprites": sprites,
            "sprites_enabled": 1 if sprites_on else 0,
            "culled_nodes": max(0, total_mesh - kept_nodes) if planes is not None else 0,
            "culling_enabled": 1 if culling_on else 0,
        }
        return dict(self.last_stats)

    def read_pixels(self) -> bytes:
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        return bytes(GL.glReadPixels(0, 0, self.width, self.height, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE))

    def save_png(self, path: str | Path) -> None:
        write_png(path, self.width, self.height, self.read_pixels())

    def release(self) -> None:
        for _, texture in self._textures.values():
            texture.release()
        self._textures.clear()
        for _, mesh in self._meshes.values():
            mesh.release()
        self._meshes.clear()
        for _, mesh in self._skinned_meshes.values():
            mesh.release()
        self._skinned_meshes.clear()
        if self._shadow is not None:
            self._shadow.release()
            self._shadow = None
        self._release_bloom_fbos()
        self._release_sprite_buffers()
        if self._sky_vao:
            GL.glDeleteVertexArrays(1, [self._sky_vao])
            self._sky_vao = 0
        self._sprite_program.release()
        self._sky_program.release()
        self._inst_program.release()
        self._depth_program.release()
        self._skin_program.release()
        self._skin_depth_program.release()
        self._bloom_bright.release()
        self._bloom_blur.release()
        self._bloom_composite.release()
        self._program.release()
