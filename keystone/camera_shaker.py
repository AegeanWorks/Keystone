"""Compose deterministic camera shake with a base camera pose.

`CameraShake` samples an offset; this shaker applies it without mutating the
base camera. A game keeps its base position and look angles after input and
collision, then asks the shaker for the posed camera it renders with. Offsets
can be world-space (the default) or camera-local, where the sampled position
is expressed along the base camera's right/up/forward axes; rotation offsets
always add to yaw and pitch.
"""

from __future__ import annotations

from keystone.camera import PerspectiveCamera
from keystone.camera_shake import CameraShake, shake_report

__all__ = ["CameraShaker", "camera_shaker_report"]


class CameraShaker:
    """Apply a `CameraShake` offset on top of an immutable base camera pose."""

    def __init__(
        self,
        camera: PerspectiveCamera,
        shake: CameraShake,
        *,
        local: bool = False,
    ) -> None:
        if not isinstance(camera, PerspectiveCamera):
            raise TypeError("camera shaker needs a PerspectiveCamera")
        if not isinstance(shake, CameraShake):
            raise TypeError("camera shaker needs a CameraShake")
        if not isinstance(local, bool):
            raise TypeError("camera shaker local flag must be a boolean")
        self.camera = camera
        self.shake = shake
        self.local = local

    def add(self, amount: float) -> None:
        """Add trauma to the underlying shake."""
        self.shake.add(amount)

    def update(self, dt: float) -> None:
        """Advance the shake decay clock."""
        self.shake.update(dt)

    def pose(self) -> PerspectiveCamera:
        """Return the composed camera; the base camera is never changed."""
        offset = self.shake.sample()
        position = self.camera.position
        if self.local:
            position = (
                position
                + self.camera.right() * offset.position.x
                + self.camera.up() * offset.position.y
                + self.camera.forward() * offset.position.z
            )
        else:
            position = position + offset.position
        return PerspectiveCamera(
            position=position,
            yaw=self.camera.yaw + offset.yaw,
            pitch=self.camera.pitch + offset.pitch,
            fov_y=self.camera.fov_y,
            near=self.camera.near,
            far=self.camera.far,
        )


def camera_shaker_report(shaker: CameraShaker) -> dict:
    """Return a JSON-safe summary of a base pose and its shaken pose."""
    if not isinstance(shaker, CameraShaker):
        raise TypeError("camera_shaker_report needs a CameraShaker")
    base = shaker.camera
    pose = shaker.pose()
    return {
        "schema": 1,
        "local": shaker.local,
        "base": {
            "position": [round(base.position.x, 6), round(base.position.y, 6), round(base.position.z, 6)],
            "yaw": round(base.yaw, 6),
            "pitch": round(base.pitch, 6),
        },
        "pose": {
            "position": [round(pose.position.x, 6), round(pose.position.y, 6), round(pose.position.z, 6)],
            "yaw": round(pose.yaw, 6),
            "pitch": round(pose.pitch, 6),
        },
        "shake": shake_report(shaker.shake),
    }
