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
    slope_rise: float = 0.55
    slope_run: float = 1.0
    step_height: float = 0.45

    def __post_init__(self) -> None:
        if self.gravity < 0.0:
            raise ValueError("gravity must be non-negative")
        if self.skin < 0.0:
            raise ValueError("skin must be non-negative")
        if self.slope_rise < 0.0:
            raise ValueError("slope rise must be non-negative")
        if self.slope_run <= 0.0:
            raise ValueError("slope run must be positive")
        if self.step_height < 0.0:
            raise ValueError("step height must be non-negative")

    def step(
        self,
        body: CharacterBody,
        wish_velocity: Vec3,
        dt: float,
        colliders: Iterable[AABB],
        platform_velocity: Vec3 | None = None,
    ) -> CharacterBody:
        """Advance one step; horizontal speed is the wish velocity, vertical is body velocity."""
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        boxes = list(colliders)
        carry = platform_velocity if platform_velocity is not None else Vec3()
        position = body.position
        if abs(carry.x) >= 1e-12 or abs(carry.y) >= 1e-12 or abs(carry.z) >= 1e-12:
            position, _ = self._move_axis(position, body.half_extents, "x", carry.x * dt, boxes)
            position, _ = self._move_axis(position, body.half_extents, "z", carry.z * dt, boxes)
            position, _ = self._move_axis(position, body.half_extents, "y", carry.y * dt, boxes)
        horizontal = Vec3(wish_velocity.x, 0.0, wish_velocity.z)
        vertical = body.velocity.y - self.gravity * dt
        position, hit_x = self._move_axis(position, body.half_extents, "x", horizontal.x * dt, boxes)
        position, hit_z = self._move_axis(position, body.half_extents, "z", horizontal.z * dt, boxes)
        if hit_x or hit_z:
            stepped = self._try_step_up(position, body.half_extents, horizontal.x * dt, horizontal.z * dt, boxes)
            if stepped is not None:
                position = stepped
                hit_x = False
                hit_z = False
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

    def _try_step_up(
        self,
        position: Vec3,
        half: Vec3,
        amount_x: float,
        amount_z: float,
        colliders: list[AABB],
    ) -> Vec3 | None:
        if self.step_height < 1e-12:
            return None
        base_y = _component(position, "y")
        raised, blocked_above = self._move_axis(position, half, "y", self.step_height, colliders)
        if blocked_above:
            return None
        moved, _ = self._move_axis(raised, half, "x", amount_x, colliders)
        moved, _ = self._move_axis(moved, half, "z", amount_z, colliders)
        run = abs(moved.x - raised.x) + abs(moved.z - raised.z)
        if run < 1e-9:
            return None
        settled, _ = self._move_axis(moved, half, "y", -self.step_height, colliders)
        rise = _component(settled, "y") - base_y
        if rise < -1e-9:
            return None
        limit = self.slope_rise * (run / self.slope_run + 1.0)
        if rise > limit + 1e-9:
            return None
        return settled

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
