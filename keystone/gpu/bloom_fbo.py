"""Deterministic RGBA8 color framebuffers for the bloom diffusion chain.

Fixed NEAREST + CLAMP_TO_EDGE sampling keeps blur taps identical across
drivers; sizes are derived from the renderer size with floor(half) and a
minimum of 1. Needs an OpenGL 3.3 context. No wall-clock, no randomness.
"""

from __future__ import annotations

from OpenGL import GL

__all__ = ["BloomFbo"]


class BloomFbo:
    """One RGBA8 color FBO owned by the renderer (one GL context)."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("bloom framebuffer needs positive dimensions")
        self.width = int(width)
        self.height = int(height)
        self._fbo = 0
        self._texture = 0
        self._depth = 0
        try:
            self._texture = int(GL.glGenTextures(1))
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8,
                self.width, self.height, 0,
                GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None,
            )
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            self._depth = int(GL.glGenRenderbuffers(1))
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self._depth)
            GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT24, self.width, self.height)
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, 0)
            self._fbo = int(GL.glGenFramebuffers(1))
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
            GL.glFramebufferTexture2D(
                GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self._texture, 0
            )
            GL.glFramebufferRenderbuffer(
                GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_RENDERBUFFER, self._depth
            )
            status = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            if status != GL.GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError(
                    f"Bloom framebuffer is incomplete (status {status}).\n"
                    "Why: the driver refused an RGBA8 color FBO for bloom diffusion.\n"
                    "Fix: update the GPU driver, or re-run with --no-bloom."
                )
        except Exception:
            self.release()
            raise

    def bind_for_write(self) -> None:
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
        GL.glViewport(0, 0, self.width, self.height)

    def unbind_after_write(self, width: int, height: int) -> None:
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glViewport(0, 0, int(width), int(height))

    def bind_for_read(self, unit: int = 2) -> None:
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture)

    def unbind_after_read(self, unit: int = 2) -> None:
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)

    def release(self) -> None:
        if self._fbo:
            GL.glDeleteFramebuffers(1, [self._fbo])
            self._fbo = 0
        if self._texture:
            GL.glDeleteTextures(1, [self._texture])
            self._texture = 0
        if self._depth:
            GL.glDeleteRenderbuffers(1, [self._depth])
            self._depth = 0
