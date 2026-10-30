"""Screen-space OpenGL renderer for the human UI canvas."""

from __future__ import annotations

import ctypes

import numpy
from OpenGL import GL

from keystone.gpu.shader import ShaderProgram
from keystone.ui.canvas import Canvas

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


class UiRenderer:
    """Uploads one canvas per frame and draws it over the 3D scene."""

    def __init__(self) -> None:
        self._program = ShaderProgram(VERTEX_SHADER, FRAGMENT_SHADER)
        self._vao = 0
        self._vbo = 0
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
            GL.glBindVertexArray(0)
        except Exception:
            self.release()
            raise

    def draw(self, canvas: Canvas) -> None:
        """Draw the canvas with alpha blending, then restore 3D render state."""
        vertices = canvas.vertices()
        if not vertices:
            return
        data = numpy.asarray(vertices, dtype=numpy.float32)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        try:
            self._program.use()
            self._program.set_vec2("u_size", float(canvas.width), float(canvas.height))
            GL.glBindVertexArray(self._vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(vertices) // 6)
            GL.glBindVertexArray(0)
        finally:
            GL.glDisable(GL.GL_BLEND)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDepthMask(GL.GL_TRUE)
            GL.glEnable(GL.GL_CULL_FACE)

    def release(self) -> None:
        if self._vbo:
            GL.glDeleteBuffers(1, [self._vbo])
            self._vbo = 0
        if self._vao:
            GL.glDeleteVertexArrays(1, [self._vao])
            self._vao = 0
        self._program.release()
