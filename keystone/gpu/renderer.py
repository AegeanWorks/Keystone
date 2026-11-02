"""Blinn-Phong forward renderer with fog, depth testing and screenshot readback."""

from __future__ import annotations

from pathlib import Path

from OpenGL import GL

from keystone.geometry import Material, MeshData
from keystone.gpu.instancing import group_instances
from keystone.gpu.mesh_buffer import GpuMesh
from keystone.gpu.shader import ShaderProgram
from keystone.gpu.texture_buffer import GpuTexture
from keystone.math3d import Mat4, Vec3
from keystone.png import write_png
from keystone.scene import Scene
from keystone.texture import TextureData

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
uniform vec3 u_point_pos;
uniform vec3 u_point_color;
uniform float u_point_radius;
out vec4 frag_color;
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
    vec3 diffuse_color = base_color * (1.0 - u_metallic * 0.8);
    vec3 color = diffuse_color * (u_ambient + u_light_color * diffuse) + u_light_color * spec_strength + u_emissive;
    if (u_point_radius > 0.0) {
        vec3 to_point = u_point_pos - v_world;
        float point_distance = length(to_point);
        float attenuation = max(0.0, 1.0 - point_distance / u_point_radius);
        float point_diffuse = max(dot(normal, normalize(to_point)), 0.0);
        color += diffuse_color * u_point_color * attenuation * attenuation * point_diffuse;
    }
    if (u_checker_scale > 0.0) {
        float tile = mod(floor(v_world.x * u_checker_scale) + floor(v_world.z * u_checker_scale), 2.0);
        color *= mix(0.62, 1.0, tile);
    }
    float fog = 1.0 - exp(-u_fog_density * u_fog_density * distance * distance);
    frag_color = vec4(mix(color, u_fog_color, clamp(fog, 0.0, 1.0)), 1.0);
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
out vec4 frag_color;
void main() {
    frag_color = vec4(mix(u_sky_bottom, u_sky_top, smoothstep(0.0, 1.0, v_uv.y)), 1.0);
}
"""


def normal_matrix(model: Mat4) -> tuple[float, ...]:
    """Return transpose(inverse(upper 3x3)) in column-major order."""
    inverse = model.inverse()
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
        try:
            inst_program = ShaderProgram(VERTEX_SHADER_INSTANCED, FRAGMENT_SHADER)
            sky_program = ShaderProgram(SKY_VERTEX_SHADER, SKY_FRAGMENT_SHADER)
            self._sky_vao = GL.glGenVertexArrays(1)
        except Exception:
            if sky_program is not None:
                sky_program.release()
            if inst_program is not None:
                inst_program.release()
            self._program.release()
            raise
        self._inst_program = inst_program
        self._sky_program = sky_program
        self._meshes: dict[int, tuple[MeshData, GpuMesh]] = {}
        self._textures: dict[int, tuple[TextureData, GpuTexture]] = {}
        self.last_stats: dict[str, int] = {
            "draw_calls": 0,
            "triangles": 0,
            "instanced_calls": 0,
            "instances": 0,
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

    def _gpu_mesh(self, mesh: MeshData) -> GpuMesh:
        cached = self._meshes.get(id(mesh))
        if cached is None or cached[0] is not mesh:
            cached = (mesh, GpuMesh(mesh))
            self._meshes[id(mesh)] = cached
        return cached[1]

    def _gpu_texture(self, texture: TextureData) -> GpuTexture:
        cached = self._textures.get(id(texture))
        if cached is None or cached[0] is not texture:
            cached = (texture, GpuTexture(texture))
            self._textures[id(texture)] = cached
        return cached[1]

    def _draw_sky(self, scene: Scene) -> None:
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        self._sky_program.use()
        self._sky_program.set_vec3("u_sky_top", scene.sky)
        self._sky_program.set_vec3("u_sky_bottom", scene.background)
        GL.glBindVertexArray(self._sky_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        GL.glBindVertexArray(0)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glEnable(GL.GL_DEPTH_TEST)

    def _apply_shared(self, program: ShaderProgram, scene: Scene, view_projection: Mat4) -> None:
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
        point = scene.point_light
        if point is None:
            program.set_vec3("u_point_pos", Vec3())
            program.set_vec3("u_point_color", Vec3())
            program.set_float("u_point_radius", 0.0)
        else:
            program.set_vec3("u_point_pos", point.position)
            program.set_vec3("u_point_color", point.color * point.intensity)
            program.set_float("u_point_radius", point.radius)

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
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            program.set_float("u_has_texture", 0.0)
        else:
            self._gpu_texture(texture).bind(0)
            program.set_int("u_texture", 0)
            program.set_float("u_has_texture", 1.0)

    def render(self, scene: Scene) -> dict[str, int]:
        draw_calls = 0
        triangles = 0
        instanced_calls = 0
        instances = 0
        GL.glViewport(0, 0, self.width, self.height)
        background = scene.background
        GL.glClearColor(background.x, background.y, background.z, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self._draw_sky(scene)
        camera = scene.camera
        view_projection = camera.view_projection(self.width / self.height)
        self._apply_shared(self._program, scene, view_projection)
        self._apply_shared(self._inst_program, scene, view_projection)
        for group in group_instances(scene):
            mesh = group["mesh"]
            if not isinstance(mesh, MeshData):
                raise TypeError("Node.mesh must be MeshData")
            material = group["material"] if isinstance(group["material"], Material) else Material()
            models = group["models"]
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
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        self.last_stats = {
            "draw_calls": draw_calls,
            "triangles": triangles,
            "instanced_calls": instanced_calls,
            "instances": instances,
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
        if self._sky_vao:
            GL.glDeleteVertexArrays(1, [self._sky_vao])
            self._sky_vao = 0
        self._sky_program.release()
        self._inst_program.release()
        self._program.release()
