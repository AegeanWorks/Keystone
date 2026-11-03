"""Generic collision primitives and ray queries for the engine core."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from keystone.math3d import Vec3


@dataclass(frozen=True, slots=True)
class Ray:
    origin: Vec3
    direction: Vec3
    t_max: float = math.inf

    def __post_init__(self) -> None:
        if self.direction.length_squared() < 1e-12:
            raise ValueError("ray direction must be non-zero")
        if self.t_max < 0.0:
            raise ValueError("ray t_max must be non-negative")


@dataclass(frozen=True, slots=True)
class AABB:
    center: Vec3
    half_extents: Vec3

    def __post_init__(self) -> None:
        if self.half_extents.x < 0.0 or self.half_extents.y < 0.0 or self.half_extents.z < 0.0:
            raise ValueError("AABB half extents must be non-negative")

    def low(self) -> Vec3:
        return self.center - self.half_extents

    def high(self) -> Vec3:
        return self.center + self.half_extents

    def contains(self, point: Vec3) -> bool:
        return (
            abs(point.x - self.center.x) <= self.half_extents.x
            and abs(point.y - self.center.y) <= self.half_extents.y
            and abs(point.z - self.center.z) <= self.half_extents.z
        )

    def overlaps(self, other: AABB) -> bool:
        return aabb_overlap(self, other)


@dataclass(frozen=True, slots=True)
class RayHit:
    key: str
    box: AABB
    distance: float


@dataclass(frozen=True, slots=True)
class Sphere:
    center: Vec3
    radius: float

    def __post_init__(self) -> None:
        if self.radius < 0.0:
            raise ValueError("sphere radius must be non-negative")


def ray_aabb(ray: Ray, box: AABB) -> float | None:
    """Return the nearest positive hit distance, or None."""
    direction = ray.direction
    tmin, tmax = -math.inf, math.inf
    # Slab test without allocating per axis.
    for origin, direction_component, center, half in (
        (ray.origin.x, direction.x, box.center.x, box.half_extents.x),
        (ray.origin.y, direction.y, box.center.y, box.half_extents.y),
        (ray.origin.z, direction.z, box.center.z, box.half_extents.z),
    ):
        low, high = center - half, center + half
        if abs(direction_component) < 1e-12:
            if origin < low or origin > high:
                return None
            continue
        t1 = (low - origin) / direction_component
        t2 = (high - origin) / direction_component
        if t1 > t2:
            t1, t2 = t2, t1
        tmin = max(tmin, t1)
        tmax = min(tmax, t2)
        if tmin > tmax:
            return None
    if tmax < 0.0 or tmin > ray.t_max:
        return None
    return max(tmin, 0.0)


def raycast(
    ray: Ray,
    colliders: Iterable[tuple[str, AABB]],
    predicate: Callable[[str, AABB], bool] | None = None,
) -> RayHit | None:
    """Return the nearest AABB hit, optionally filtered by key and box."""
    best: RayHit | None = None
    for key, box in colliders:
        if predicate is not None and not predicate(key, box):
            continue
        distance = ray_aabb(ray, box)
        if distance is not None and (best is None or distance < best.distance):
            best = RayHit(key, box, distance)
    return best


def ray_sphere(ray: Ray, sphere: Sphere) -> float | None:
    offset = ray.origin - sphere.center
    a = ray.direction.dot(ray.direction)
    b = 2.0 * offset.dot(ray.direction)
    c = offset.dot(offset) - sphere.radius * sphere.radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        return None
    root = math.sqrt(discriminant)
    for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
        if 0.0 <= t <= ray.t_max:
            return t
    return None


def aabb_overlap(first: AABB, second: AABB) -> bool:
    return (
        abs(first.center.x - second.center.x) <= first.half_extents.x + second.half_extents.x
        and abs(first.center.y - second.center.y) <= first.half_extents.y + second.half_extents.y
        and abs(first.center.z - second.center.z) <= first.half_extents.z + second.half_extents.z
    )


def sphere_aabb_overlap(sphere: Sphere, box: AABB) -> bool:
    closest = Vec3(
        max(box.center.x - box.half_extents.x, min(sphere.center.x, box.center.x + box.half_extents.x)),
        max(box.center.y - box.half_extents.y, min(sphere.center.y, box.center.y + box.half_extents.y)),
        max(box.center.z - box.half_extents.z, min(sphere.center.z, box.center.z + box.half_extents.z)),
    )
    return (closest - sphere.center).length_squared() <= sphere.radius * sphere.radius


def resolve_sphere_aabb(sphere: Sphere, box: AABB) -> Vec3:
    """Push a sphere out of an AABB along the shallowest axis."""
    if not sphere_aabb_overlap(sphere, box):
        return sphere.center
    low = Vec3(box.center.x - box.half_extents.x, box.center.y - box.half_extents.y, box.center.z - box.half_extents.z)
    high = Vec3(box.center.x + box.half_extents.x, box.center.y + box.half_extents.y, box.center.z + box.half_extents.z)
    center = sphere.center
    radius = sphere.radius
    candidates = (
        (abs((low.x - radius) - center.x), Vec3(low.x - radius, center.y, center.z)),
        (abs((high.x + radius) - center.x), Vec3(high.x + radius, center.y, center.z)),
        (abs((low.y - radius) - center.y), Vec3(center.x, low.y - radius, center.z)),
        (abs((high.y + radius) - center.y), Vec3(center.x, high.y + radius, center.z)),
        (abs((low.z - radius) - center.z), Vec3(center.x, center.y, low.z - radius)),
        (abs((high.z + radius) - center.z), Vec3(center.x, center.y, high.z + radius)),
    )
    return min(candidates, key=lambda item: item[0])[1]
