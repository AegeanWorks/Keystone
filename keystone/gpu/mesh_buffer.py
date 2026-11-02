"""GPU mesh upload and indexed drawing for the Keystone renderer."""

from __future__ import annotations

import ctypes

import numpy
from OpenGL import GL

from keystone.geometry import MeshData

STRIDE = 11 * 4
POSITION_OFFSET = 0
NORMAL_OFFSET = 3 * 4
UV_OFFSET = 6 * 4
COLOR_OFFSET = 8 * 4


class GpuMesh:
    """VAO/VBO/EBO triple owning one immutable MeshData upload."""

    def __init__(self, mesh: MeshData) -> None:
        self.mesh = mesh
        self._vao = 0
        self._vbo = 0
        self._ebo = 0
        self._count = len(mesh.indices)
        try:
            vertices = numpy.asarray(mesh.interleaved(), dtype=numpy.float32)
            indices = numpy.asarray(mesh.indices, dtype=numpy.uint32)
            self._vao = GL.glGenVertexArrays(1)
            self._vbo = GL.glGenBuffers(1)
            self._ebo = GL.glGenBuffers(1)
            GL.glBindVertexArray(self._vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._ebo)
            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL.GL_STATIC_DRAW)
            GL.glEnableVertexAttribArray(0)
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, STRIDE, ctypes.c_void_p(POSITION_OFFSET))
            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, STRIDE, ctypes.c_void_p(NORMAL_OFFSET))
            GL.glEnableVertexAttribArray(2)
            GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, STRIDE, ctypes.c_void_p(UV_OFFSET))
            GL.glEnableVertexAttribArray(3)
            GL.glVertexAttribPointer(3, 3, GL.GL_FLOAT, GL.GL_FALSE, STRIDE, ctypes.c_void_p(COLOR_OFFSET))
            GL.glBindVertexArray(0)
        except Exception:
            self.release()
            raise

    def draw(self) -> None:
        GL.glBindVertexArray(self._vao)
        GL.glDrawElements(GL.GL_TRIANGLES, self._count, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)

    def draw_instanced(
        self,
        model_flats: list[tuple[float, ...] | list[float]],
        normal_flats: list[tuple[float, ...] | list[float]],
    ) -> None:
        """Draw all instances with per-instance model/normal divisor attributes.

        Locations 4-7 carry the column-major model matrix, locations 8-10 the
        column-major normal matrix. Temporary VBOs are deleted before return
        and divisor state is reset so plain draws are unaffected.
        """
        count = len(model_flats)
        if count == 0 or len(normal_flats) != count:
            raise ValueError("model and normal lists must be non-empty and match")
        models = numpy.asarray(model_flats, dtype=numpy.float32).reshape(count, 16)
        normals = numpy.asarray(normal_flats, dtype=numpy.float32).reshape(count, 9)
        model_vbo = int(GL.glGenBuffers(1))
        normal_vbo = int(GL.glGenBuffers(1))
        try:
            GL.glBindVertexArray(self._vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, model_vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, models.nbytes, models, GL.GL_DYNAMIC_DRAW)
            for column in range(4):
                location = 4 + column
                GL.glEnableVertexAttribArray(location)
                GL.glVertexAttribPointer(
                    location, 4, GL.GL_FLOAT, GL.GL_FALSE, 64, ctypes.c_void_p(column * 16)
                )
                GL.glVertexAttribDivisor(location, 1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, normal_vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, normals.nbytes, normals, GL.GL_DYNAMIC_DRAW)
            for column in range(3):
                location = 8 + column
                GL.glEnableVertexAttribArray(location)
                GL.glVertexAttribPointer(
                    location, 3, GL.GL_FLOAT, GL.GL_FALSE, 36, ctypes.c_void_p(column * 12)
                )
                GL.glVertexAttribDivisor(location, 1)
            GL.glDrawElementsInstanced(
                GL.GL_TRIANGLES, self._count, GL.GL_UNSIGNED_INT, None, count
            )
            for location in range(4, 11):
                GL.glVertexAttribDivisor(location, 0)
                GL.glDisableVertexAttribArray(location)
            GL.glBindVertexArray(0)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        finally:
            GL.glDeleteBuffers(1, [model_vbo])
            GL.glDeleteBuffers(1, [normal_vbo])

    def release(self) -> None:
        if self._ebo:
            GL.glDeleteBuffers(1, [self._ebo])
            self._ebo = 0
        if self._vbo:
            GL.glDeleteBuffers(1, [self._vbo])
            self._vbo = 0
        if self._vao:
            GL.glDeleteVertexArrays(1, [self._vao])
            self._vao = 0
