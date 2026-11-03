"""Deterministic directional shadow mapping (fixed 1024 depth map, 3x3 PCF).

Pure-CPU light VP math is GL-free and unit-tested; the FBO wrapper needs
an OpenGL 3.3 context. No wall-clock, no randomness, no genre logic.
"""

from __future__ import annotations

from OpenGL import GL

from keystone.math3d import Mat4, Vec3
from keystone.scene import DirectionalLight

SHADOW_MAP_SIZE = 1024
SHADOW_BIAS = 0.005
SHADOW_EXTENT = 12.0
SHADOW_NEAR = 1.0
SHADOW_FAR = 40.0
SHADOW_EYE_DISTANCE = 20.0

__all__ = [
    "SHADOW_BIAS",
    "SHADOW_EXTENT",
    "SHADOW_EYE_DISTANCE",
    "SHADOW_FAR",
    "SHADOW_MAP_SIZE",
    "SHADOW_NEAR",
    "ShadowMap",
    "light_view",
    "light_vp",
    "orthographic",
]


def orthographic(
    left: float,
    right: float,
    bottom: float,
    top: float,
    near: float,
    far: float,
) -> Mat4:
    """Build a deterministic orthographic projection (column-major)."""
    if right == left or top == bottom or far == near:
        raise ValueError("orthographic frustum must have non-zero size")
    tx = -(right + left) / (right - left)
    ty = -(top + bottom) / (top - bottom)
    tz = -(far + near) / (far - near)
    return Mat4(
        (
            2.0 / (right - left), 0.0, 0.0, 0.0,
            0.0, 2.0 / (top - bottom), 0.0, 0.0,
            0.0, 0.0, -2.0 / (far - near), 0.0,
            tx, ty, tz, 1.0,
        )
    )


def light_view(direction: Vec3) -> Mat4:
    """Look from the light direction toward the origin (deterministic)."""
    unit = direction.normalized()
    if unit.length_squared() < 1e-12:
        raise ValueError("shadow light needs a non-zero direction")
    eye = unit * (-SHADOW_EYE_DISTANCE)
    up = Vec3(0.0, 1.0, 0.0)
    if abs(unit.dot(up)) > 0.999:
        up = Vec3(1.0, 0.0, 0.0)
    return Mat4.look_at(eye, Vec3(), up)


def light_vp(direction: Vec3) -> Mat4:
    """Deterministic light view-projection for the fixed ortho box."""
    projection = orthographic(
        -SHADOW_EXTENT, SHADOW_EXTENT,
        -SHADOW_EXTENT, SHADOW_EXTENT,
        SHADOW_NEAR, SHADOW_FAR,
    )
    return projection * light_view(direction)


def light_vp_for(light: DirectionalLight) -> Mat4:
    """Convenience wrapper taking the scene directional light."""
    return light_vp(light.direction)


class ShadowMap:
    """Fixed-size depth FBO owned by the renderer (one GL context)."""

    def __init__(self, size: int = SHADOW_MAP_SIZE) -> None:
        if size != SHADOW_MAP_SIZE:
            raise ValueError(f"shadow map size must be {SHADOW_MAP_SIZE}")
        self.size = size
        self._fbo = 0
        self._depth = 0
        try:
            self._depth = int(GL.glGenTextures(1))
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._depth)
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT24,
                size, size, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None,
            )
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_MODE, GL.GL_NONE)
            self._fbo = int(GL.glGenFramebuffers(1))
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
            GL.glFramebufferTexture2D(
                GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self._depth, 0
            )
            GL.glDrawBuffer(GL.GL_NONE)
            GL.glReadBuffer(GL.GL_NONE)
            status = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            if status != GL.GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError(
                    f"Shadow framebuffer is incomplete (status {status}).\n"
                    "Why: the driver refused a 1024 depth-only FBO.\n"
                    "Fix: update the GPU driver, or re-run with --no-shadows."
                )
        except Exception:
            self.release()
            raise

    def bind_for_write(self) -> None:
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
        GL.glViewport(0, 0, self.size, self.size)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)

    def unbind_after_write(self, width: int, height: int) -> None:
        GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glViewport(0, 0, width, height)

    def bind_for_read(self, unit: int = 1) -> None:
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._depth)

    def unbind_after_read(self, unit: int = 1) -> None:
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)

    def release(self) -> None:
        if self._fbo:
            GL.glDeleteFramebuffers(1, [self._fbo])
            self._fbo = 0
        if self._depth:
            GL.glDeleteTextures(1, [self._depth])
            self._depth = 0
