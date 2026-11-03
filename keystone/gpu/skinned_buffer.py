"""GPU upload for skinned meshes: base stream plus joints and weights."""

from __future__ import annotations

import ctypes

import numpy
from OpenGL import GL

from keystone.geometry import MeshData

SKINNED_STRIDE = 19 * 4
SKIN_JOINTS_OFFSET = 11 * 4
SKIN_WEIGHTS_OFFSET = 15 * 4

__all__ = ["SKINNED_STRIDE", "SkinnedGpuMesh"]


class SkinnedGpuMesh:
    """VAO/VBO/EBO triple owning one immutable skinned mesh upload."""

    def __init__(self, mesh: MeshData) -> None:
        if not mesh.skinned:
            raise ValueError("skinned GPU mesh needs skinning influences")
        self.mesh = mesh
        self._vao = 0
        self._vbo = 0
        self._ebo = 0
        self._count = len(mesh.indices)
        try:
            vertices = numpy.asarray(mesh.interleaved_skinned(), dtype=numpy.float32)
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
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, SKINNED_STRIDE, ctypes.c_void_p(0))
            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, SKINNED_STRIDE, ctypes.c_void_p(3 * 4))
            GL.glEnableVertexAttribArray(2)
            GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, SKINNED_STRIDE, ctypes.c_void_p(6 * 4))
            GL.glEnableVertexAttribArray(3)
            GL.glVertexAttribPointer(3, 3, GL.GL_FLOAT, GL.GL_FALSE, SKINNED_STRIDE, ctypes.c_void_p(8 * 4))
            GL.glEnableVertexAttribArray(11)
            GL.glVertexAttribPointer(11, 4, GL.GL_FLOAT, GL.GL_FALSE, SKINNED_STRIDE, ctypes.c_void_p(SKIN_JOINTS_OFFSET))
            GL.glEnableVertexAttribArray(12)
            GL.glVertexAttribPointer(12, 4, GL.GL_FLOAT, GL.GL_FALSE, SKINNED_STRIDE, ctypes.c_void_p(SKIN_WEIGHTS_OFFSET))
            GL.glBindVertexArray(0)
        except Exception:
            self.release()
            raise

    def draw(self) -> None:
        GL.glBindVertexArray(self._vao)
        GL.glDrawElements(GL.GL_TRIANGLES, self._count, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)

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
