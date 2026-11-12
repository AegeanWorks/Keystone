"""Screen-space OpenGL renderer for the human UI canvas."""

from __future__ import annotations

import ctypes

import numpy
from OpenGL import GL

from keystone.gpu.shader import ShaderProgram
from keystone.gpu.texture_buffer import GpuTexture
from keystone.texture import TextureData
from keystone.ui.canvas import Canvas, ImageElement

VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec2 a_position;
layout(location = 1) in vec4 a_color;
uniform vec2 u_size;
out vec4 v_color;
void main() {
    vec2 ndc = vec2(a_position.x / u_size.x * 2.0 - 1.0, 1.0 - a_position.y / u_size.y * 2.0);
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_color = a_color;
}
"""

FRAGMENT_SHADER = """#version 330 core
in vec4 v_color;
out vec4 frag_color;
void main() {
    frag_color = v_color;
}
"""

STRIDE = 6 * 4
POSITION_OFFSET = 0
COLOR_OFFSET = 2 * 4

IMAGE_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec2 a_position;
layout(location = 1) in vec2 a_uv;
layout(location = 2) in vec4 a_color;
uniform vec2 u_size;
out vec2 v_uv;
out vec4 v_color;
void main() {
    vec2 ndc = vec2(a_position.x / u_size.x * 2.0 - 1.0, 1.0 - a_position.y / u_size.y * 2.0);
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_uv = a_uv;
    v_color = a_color;
}
"""

IMAGE_FRAGMENT_SHADER = """#version 330 core
in vec2 v_uv;
in vec4 v_color;
uniform sampler2D u_texture;
out vec4 frag_color;
void main() {
    vec4 texel = texture(u_texture, v_uv);
    frag_color = vec4(texel.rgb * v_color.rgb, texel.a * v_color.a);
}
"""

IMAGE_STRIDE = 8 * 4
IMAGE_POSITION_OFFSET = 0
IMAGE_UV_OFFSET = 2 * 4
IMAGE_COLOR_OFFSET = 4 * 4


class UiRenderer:
    """Uploads one canvas per frame and draws it over the 3D scene."""

    def __init__(self) -> None:
        self._program = ShaderProgram(VERTEX_SHADER, FRAGMENT_SHADER)
        self._vao = 0
        self._vbo = 0
        self._image_program = ShaderProgram(IMAGE_VERTEX_SHADER, IMAGE_FRAGMENT_SHADER)
        self._image_vao = 0
        self._image_vbo = 0
        self._image_textures: dict[int, tuple[TextureData, GpuTexture]] = {}
        try:
            self._vao = GL.glGenVertexArrays(1)
            self._vbo = GL.glGenBuffers(1)
            GL.glBindVertexArray(self._vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, None, GL.GL_DYNAMIC_DRAW)
            GL.glEnableVertexAttribArray(0)
            GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, STRIDE, ctypes.c_void_p(POSITION_OFFSET))
            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(
                1, 4, GL.GL_FLOAT, GL.GL_FALSE, STRIDE, ctypes.c_void_p(COLOR_OFFSET)
            )
            self._image_vao = GL.glGenVertexArrays(1)
            self._image_vbo = GL.glGenBuffers(1)
            GL.glBindVertexArray(self._image_vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._image_vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, 0, None, GL.GL_DYNAMIC_DRAW)
            GL.glEnableVertexAttribArray(0)
            GL.glVertexAttribPointer(
                0, 2, GL.GL_FLOAT, GL.GL_FALSE, IMAGE_STRIDE, ctypes.c_void_p(IMAGE_POSITION_OFFSET)
            )
            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(
                1, 2, GL.GL_FLOAT, GL.GL_FALSE, IMAGE_STRIDE, ctypes.c_void_p(IMAGE_UV_OFFSET)
            )
            GL.glEnableVertexAttribArray(2)
            GL.glVertexAttribPointer(
                2, 4, GL.GL_FLOAT, GL.GL_FALSE, IMAGE_STRIDE, ctypes.c_void_p(IMAGE_COLOR_OFFSET)
            )
            GL.glBindVertexArray(0)
        except Exception:
            self.release()
            raise

    def draw(self, canvas: Canvas) -> None:
        """Draw the canvas with alpha blending, then restore 3D render state."""
        vertices = canvas.vertices()
        if not vertices and not canvas.images:
            return
        data = numpy.asarray(vertices, dtype=numpy.float32)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFuncSeparate(
            GL.GL_SRC_ALPHA,
            GL.GL_ONE_MINUS_SRC_ALPHA,
            GL.GL_ONE,
            GL.GL_ONE_MINUS_SRC_ALPHA,
        )
        try:
            if vertices:
                self._program.use()
                self._program.set_vec2("u_size", float(canvas.width), float(canvas.height))
                GL.glBindVertexArray(self._vao)
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
                GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(vertices) // 6)
                GL.glBindVertexArray(0)
            self._draw_images(canvas)
        finally:
            GL.glDisable(GL.GL_BLEND)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDepthMask(GL.GL_TRUE)
            GL.glEnable(GL.GL_CULL_FACE)

    def _gpu_texture(self, texture: TextureData) -> GpuTexture:
        cached = self._image_textures.get(id(texture))
        if cached is None or cached[0] is not texture:
            cached = (texture, GpuTexture(texture))
            cached[1].bind(0)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            self._image_textures[id(texture)] = cached
        return cached[1]

    @staticmethod
    def _image_vertices(element: ImageElement) -> list[float]:
        left = element.x
        top = element.y
        right = element.x + element.width
        bottom = element.y + element.height
        u0, v0, u1, v1 = element.u0, element.v0, element.u1, element.v1
        red, green, blue, alpha = element.color
        positions = (
            (left, top, u0, 1.0 - v0),
            (left, bottom, u0, 1.0 - v1),
            (right, bottom, u1, 1.0 - v1),
            (left, top, u0, 1.0 - v0),
            (right, bottom, u1, 1.0 - v1),
            (right, top, u1, 1.0 - v0),
        )
        vertices: list[float] = []
        for x, y, u, v in positions:
            vertices.extend((x, y, u, v, red, green, blue, alpha))
        return vertices

    def _draw_images(self, canvas: Canvas) -> None:
        if not canvas.images:
            return
        self._image_program.use()
        self._image_program.set_vec2("u_size", float(canvas.width), float(canvas.height))
        self._image_program.set_int("u_texture", 0)
        GL.glBindVertexArray(self._image_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._image_vbo)
        for element in canvas.images:
            if element.color[3] <= 0.0:
                continue
            texture = self._gpu_texture(element.texture)
            texture.bind(0)
            data = numpy.asarray(self._image_vertices(element), dtype=numpy.float32)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)
        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)

    def release(self) -> None:
        for _texture, cached in self._image_textures.values():
            cached.release()
        self._image_textures.clear()
        if self._image_vbo:
            GL.glDeleteBuffers(1, [self._image_vbo])
            self._image_vbo = 0
        if self._image_vao:
            GL.glDeleteVertexArrays(1, [self._image_vao])
            self._image_vao = 0
        self._image_program.release()
        if self._vbo:
            GL.glDeleteBuffers(1, [self._vbo])
            self._vbo = 0
        if self._vao:
            GL.glDeleteVertexArrays(1, [self._vao])
            self._vao = 0
        self._program.release()
