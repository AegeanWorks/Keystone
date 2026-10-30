"""Blinn-Phong forward renderer with fog, depth testing and screenshot readback."""

from __future__ import annotations

from pathlib import Path

from OpenGL import GL

from keystone.geometry import Material, MeshData
from keystone.gpu.mesh_buffer import GpuMesh
from keystone.gpu.shader import ShaderProgram
from keystone.math3d import Mat4
from keystone.png import write_png
from keystone.scene import Scene

VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
uniform mat4 u_model;
uniform mat4 u_view_proj;
uniform mat3 u_normal_matrix;
out vec3 v_world;
out vec3 v_normal;
void main() {
    vec4 world = u_model * vec4(a_position, 1.0);
    v_world = world.xyz;
    v_normal = normalize(u_normal_matrix * a_normal);
    gl_Position = u_view_proj * world;
}
"""

FRAGMENT_SHADER = """#version 330 core
in vec3 v_world;
in vec3 v_normal;
uniform vec3 u_color;
uniform float u_specular;
uniform float u_shininess;
uniform vec3 u_camera_pos;
uniform vec3 u_light_dir;
uniform vec3 u_light_color;
uniform vec3 u_ambient;
uniform vec3 u_fog_color;
uniform float u_fog_density;
uniform float u_checker_scale;
out vec4 frag_color;
void main() {
    vec3 normal = normalize(v_normal);
    vec3 to_eye = u_camera_pos - v_world;
    float distance = length(to_eye);
    vec3 view = to_eye / max(distance, 1e-4);
    vec3 light = normalize(-u_light_dir);
    float diffuse = max(dot(normal, light), 0.0);
    vec3 halfway = normalize(light + view);
    float specular = pow(max(dot(normal, halfway), 0.0), u_shininess) * u_specular;
    vec3 color = u_color * (u_ambient + u_light_color * diffuse) + u_light_color * specular;
    if (u_checker_scale > 0.0) {
        float tile = mod(floor(v_world.x * u_checker_scale) + floor(v_world.z * u_checker_scale), 2.0);
        color *= mix(0.62, 1.0, tile);
    }
    float fog = 1.0 - exp(-u_fog_density * u_fog_density * distance * distance);
    frag_color = vec4(mix(color, u_fog_color, clamp(fog, 0.0, 1.0)), 1.0);
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
        sky_program = None
        try:
            sky_program = ShaderProgram(SKY_VERTEX_SHADER, SKY_FRAGMENT_SHADER)
            self._sky_vao = GL.glGenVertexArrays(1)
        except Exception:
            if sky_program is not None:
                sky_program.release()
            self._program.release()
            raise
        self._sky_program = sky_program
        self._meshes: dict[int, tuple[MeshData, GpuMesh]] = {}
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

    def render(self, scene: Scene) -> None:
        GL.glViewport(0, 0, self.width, self.height)
        background = scene.background
        GL.glClearColor(background.x, background.y, background.z, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self._draw_sky(scene)
        camera = scene.camera
        view_projection = camera.view_projection(self.width / self.height)
        light = scene.light
        self._program.use()
        self._program.set_mat4("u_view_proj", view_projection)
        self._program.set_vec3("u_camera_pos", camera.position)
        self._program.set_vec3("u_light_dir", light.unit_direction())
        self._program.set_vec3("u_light_color", light.radiance())
        self._program.set_vec3("u_ambient", scene.ambient)
        self._program.set_vec3("u_fog_color", background)
        self._program.set_float("u_fog_density", scene.fog_density)
        for node in scene.traverse():
            if node.mesh is None or not node.world_visible():
                continue
            mesh = node.mesh
            if not isinstance(mesh, MeshData):
                raise TypeError("Node.mesh must be MeshData")
            material = node.material if isinstance(node.material, Material) else Material()
            model = node.world_matrix()
            self._program.set_mat4("u_model", model)
            self._program.set_mat3("u_normal_matrix", normal_matrix(model))
            self._program.set_vec3("u_color", material.color)
            self._program.set_float("u_specular", material.specular)
            self._program.set_float("u_shininess", material.shininess)
            self._program.set_float("u_checker_scale", material.checker_scale)
            self._gpu_mesh(mesh).draw()

    def read_pixels(self) -> bytes:
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        return bytes(GL.glReadPixels(0, 0, self.width, self.height, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE))

    def save_png(self, path: str | Path) -> None:
        write_png(path, self.width, self.height, self.read_pixels())

    def release(self) -> None:
        for _, mesh in self._meshes.values():
            mesh.release()
        self._meshes.clear()
        if self._sky_vao:
            GL.glDeleteVertexArrays(1, [self._sky_vao])
            self._sky_vao = 0
        self._sky_program.release()
        self._program.release()
