"""Game-agnostic AABB character movement with gravity and collision response."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from keystone.math3d import Vec3
from keystone.physics import AABB

AXES = ("x", "y", "z")


def _component(vector: Vec3, axis: str) -> float:
    return getattr(vector, axis)


def _with_axis(vector: Vec3, axis: str, value: float) -> Vec3:
    return Vec3(
        value if axis == "x" else vector.x,
        value if axis == "y" else vector.y,
        value if axis == "z" else vector.z,
    )


def _other_axes_overlap(position: Vec3, half: Vec3, box: AABB, axis: str) -> bool:
    for other in AXES:
        if other == axis:
            continue
        if abs(_component(position, other) - _component(box.center, other)) > (
            _component(half, other) + _component(box.half_extents, other)
        ):
            return False
    return True


@dataclass(frozen=True, slots=True)
class CharacterBody:
    """An axis-aligned character body with velocity and ground state."""

    position: Vec3
    half_extents: Vec3 = Vec3(0.35, 0.9, 0.35)
    velocity: Vec3 = Vec3()
    on_ground: bool = False

    def __post_init__(self) -> None:
        if any(component < 0.0 for component in self.half_extents):
            raise ValueError("character half extents must be non-negative")

    def box(self) -> AABB:
        return AABB(self.position, self.half_extents)


@dataclass(frozen=True, slots=True)
class CharacterController:
    """Resolve horizontal wish velocity and gravity against static AABBs."""

    gravity: float = 24.0
    skin: float = 1e-4

    def __post_init__(self) -> None:
        if self.gravity < 0.0:
            raise ValueError("gravity must be non-negative")
        if self.skin < 0.0:
            raise ValueError("skin must be non-negative")

    def step(
        self,
        body: CharacterBody,
        wish_velocity: Vec3,
        dt: float,
        colliders: Iterable[AABB],
    ) -> CharacterBody:
        """Advance one step; horizontal speed is the wish velocity, vertical is body velocity."""
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        boxes = list(colliders)
        horizontal = Vec3(wish_velocity.x, 0.0, wish_velocity.z)
        vertical = body.velocity.y - self.gravity * dt
        position, hit_x = self._move_axis(body.position, body.half_extents, "x", horizontal.x * dt, boxes)
        position, hit_z = self._move_axis(position, body.half_extents, "z", horizontal.z * dt, boxes)
        position, hit_y = self._move_axis(position, body.half_extents, "y", vertical * dt, boxes)
        return CharacterBody(
            position=position,
            half_extents=body.half_extents,
            velocity=Vec3(
                0.0 if hit_x else horizontal.x,
                0.0 if hit_y else vertical,
                0.0 if hit_z else horizontal.z,
            ),
            on_ground=(hit_y and vertical <= 0.0) or (body.on_ground and abs(vertical) < 1e-12),
        )

    def _move_axis(
        self,
        position: Vec3,
        half: Vec3,
        axis: str,
        amount: float,
        colliders: list[AABB],
    ) -> tuple[Vec3, bool]:
        if abs(amount) < 1e-12:
            return position, False
        start = _component(position, axis)
        end = start + amount
        hit = False
        for box in colliders:
            if not _other_axes_overlap(position, half, box, axis):
                continue
            near = _component(box.low(), axis) - _component(half, axis)
            far = _component(box.high(), axis) + _component(half, axis)
            if amount > 0.0:
                if (end >= near and start <= near + self.skin) or (near < start < far):
                    end = min(end, near - self.skin)
                    hit = True
            else:
                if (end <= far and start >= far - self.skin) or (near < start < far):
                    end = max(end, far + self.skin)
                    hit = True
        return _with_axis(position, axis, end), hit
