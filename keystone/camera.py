"""Perspective camera with yaw/pitch orientation and fly-style movement."""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.math3d import Mat4, Vec3

MAX_PITCH = math.radians(89.0)


@dataclass
class PerspectiveCamera:
    """A right-handed camera looking down -Z when yaw and pitch are zero."""

    position: Vec3 = Vec3(0.0, 0.0, 0.0)
    yaw: float = 0.0
    pitch: float = 0.0
    fov_y: float = 60.0
    near: float = 0.1
    far: float = 1000.0

    def forward(self) -> Vec3:
        cos_pitch = math.cos(self.pitch)
        return Vec3(
            math.sin(self.yaw) * cos_pitch,
            math.sin(self.pitch),
            -math.cos(self.yaw) * cos_pitch,
        )

    def right(self) -> Vec3:
        return self.forward().cross(Vec3.UP).normalized()

    def view_matrix(self) -> Mat4:
        return Mat4.look_at(self.position, self.position + self.forward(), Vec3.UP)

    def projection_matrix(self, aspect: float) -> Mat4:
        return Mat4.perspective(self.fov_y, aspect, self.near, self.far)

    def view_projection(self, aspect: float) -> Mat4:
        return self.projection_matrix(aspect) * self.view_matrix()

    def move(self, forward: float, right: float, up: float) -> None:
        self.position = (
            self.position
            + self.forward() * forward
            + self.right() * right
            + Vec3.UP * up
        )

    def rotate(self, yaw_delta: float, pitch_delta: float) -> None:
        self.yaw = (self.yaw + yaw_delta) % math.tau
        self.pitch = max(-MAX_PITCH, min(MAX_PITCH, self.pitch + pitch_delta))

    def look_at(self, target: Vec3) -> None:
        direction = (target - self.position).normalized()
        if direction.length_squared() < 1e-12:
            raise ValueError("camera cannot look at its own position")
        self.yaw = math.atan2(direction.x, -direction.z)
        self.pitch = math.asin(max(-1.0, min(1.0, direction.y)))
