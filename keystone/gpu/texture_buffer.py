"""GPU upload and lifecycle for immutable TextureData."""

from __future__ import annotations

from OpenGL import GL

from keystone.texture import TextureData


class GpuTexture:
    """One OpenGL 2D texture with mipmaps and repeat wrapping."""

    def __init__(self, data: TextureData) -> None:
        self.data = data
        self._texture = 0
        try:
            self._texture = GL.glGenTextures(1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            rows = [
                data.rgba[row * data.width * 4 : (row + 1) * data.width * 4]
                for row in range(data.height)
            ]
            rows.reverse()
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D,
                0,
                GL.GL_RGBA8,
                data.width,
                data.height,
                0,
                GL.GL_RGBA,
                GL.GL_UNSIGNED_BYTE,
                b"".join(rows),
            )
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        except Exception:
            self.release()
            raise

    def bind(self, unit: int = 0) -> None:
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)

    def release(self) -> None:
        if self._texture:
            GL.glDeleteTextures(1, [self._texture])
            self._texture = 0
