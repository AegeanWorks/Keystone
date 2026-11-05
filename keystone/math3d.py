"""Column-major 3D math primitives shared by the scene, camera and GPU layers."""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Vec3:
    """Immutable 3-component vector with the usual right-handed operations."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        if isinstance(scalar, Vec3) or not isinstance(scalar, (int, float)):
            raise TypeError("Vec3 can only be multiplied by a real number")
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> Vec3:
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    def __iter__(self) -> Iterator[float]:
        return iter((self.x, self.y, self.z))

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def length_squared(self) -> float:
        return self.dot(self)

    def normalized(self) -> Vec3:
        length = self.length()
        return self / length if length > 1e-12 else Vec3()

    def lerp(self, other: Vec3, t: float) -> Vec3:
        return self + (other - self) * t


Vec3.ZERO = Vec3(0.0, 0.0, 0.0)
Vec3.ONE = Vec3(1.0, 1.0, 1.0)
Vec3.UP = Vec3(0.0, 1.0, 0.0)
Vec3.RIGHT = Vec3(1.0, 0.0, 0.0)
Vec3.FORWARD = Vec3(0.0, 0.0, -1.0)


@dataclass(frozen=True, slots=True)
class Mat4:
    """Immutable 4x4 matrix stored column-major, ready for OpenGL upload."""

    m: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.m) != 16:
            raise ValueError("Mat4 needs exactly 16 column-major values")

    def __mul__(self, other: object) -> Mat4 | Vec3:
        if isinstance(other, Vec3):
            return self.transform_point(other)
        if isinstance(other, Mat4):
            return Mat4(
                tuple(
                    sum(self[k * 4 + row] * other.m[col * 4 + k] for k in range(4))
                    for col in range(4)
                    for row in range(4)
                )
            )
        return NotImplemented

    def __iter__(self) -> Iterator[float]:
        return iter(self.m)

    def __getitem__(self, index: int) -> float:
        return self.m[index]

    @classmethod
    def identity(cls) -> Mat4:
        return cls(
            (
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    @classmethod
    def translation(cls, x: float, y: float, z: float) -> Mat4:
        return cls(
            (
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                float(x), float(y), float(z), 1.0,
            )
        )

    @classmethod
    def scale(cls, x: float, y: float, z: float) -> Mat4:
        return cls(
            (
                float(x), 0.0, 0.0, 0.0,
                0.0, float(y), 0.0, 0.0,
                0.0, 0.0, float(z), 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    @classmethod
    def rotation_x(cls, radians: float) -> Mat4:
        c, s = math.cos(radians), math.sin(radians)
        return cls(
            (
                1.0, 0.0, 0.0, 0.0,
                0.0, c, s, 0.0,
                0.0, -s, c, 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    @classmethod
    def rotation_y(cls, radians: float) -> Mat4:
        c, s = math.cos(radians), math.sin(radians)
        return cls(
            (
                c, 0.0, -s, 0.0,
                0.0, 1.0, 0.0, 0.0,
                s, 0.0, c, 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    @classmethod
    def rotation_z(cls, radians: float) -> Mat4:
        c, s = math.cos(radians), math.sin(radians)
        return cls(
            (
                c, s, 0.0, 0.0,
                -s, c, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    @classmethod
    def rotation_axis(cls, axis: Vec3, radians: float) -> Mat4:
        a = axis.normalized()
        if a.length_squared() < 1e-12:
            raise ValueError("rotation axis must be non-zero")
        c, s = math.cos(radians), math.sin(radians)
        t = 1.0 - c
        x, y, z = a.x, a.y, a.z
        return cls(
            (
                t * x * x + c, t * x * y + s * z, t * x * z - s * y, 0.0,
                t * x * y - s * z, t * y * y + c, t * y * z + s * x, 0.0,
                t * x * z + s * y, t * y * z - s * x, t * z * z + c, 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    @classmethod
    def perspective(cls, fov_y_degrees: float, aspect: float, near: float, far: float) -> Mat4:
        if not 0.0 < fov_y_degrees < 180.0:
            raise ValueError("fov_y_degrees must be between 0 and 180")
        if aspect <= 0.0 or near <= 0.0 or far <= near:
            raise ValueError("require aspect > 0, near > 0 and far > near")
        f = 1.0 / math.tan(math.radians(fov_y_degrees) / 2.0)
        depth = near - far
        return cls(
            (
                f / aspect, 0.0, 0.0, 0.0,
                0.0, f, 0.0, 0.0,
                0.0, 0.0, (far + near) / depth, -1.0,
                0.0, 0.0, (2.0 * far * near) / depth, 0.0,
            )
        )

    @classmethod
    def look_at(cls, eye: Vec3, target: Vec3, up: Vec3) -> Mat4:
        forward = (target - eye).normalized()
        if forward.length_squared() < 1e-12:
            raise ValueError("look_at needs eye and target to differ")
        right = forward.cross(up).normalized()
        if right.length_squared() < 1e-12:
            raise ValueError("look_at needs an up vector not parallel to the view direction")
        true_up = right.cross(forward)
        return cls(
            (
                right.x, true_up.x, -forward.x, 0.0,
                right.y, true_up.y, -forward.y, 0.0,
                right.z, true_up.z, -forward.z, 0.0,
                -right.dot(eye), -true_up.dot(eye), forward.dot(eye), 1.0,
            )
        )

    def transform_point(self, point: Vec3) -> Vec3:
        if any(abs(self.m[i]) > 1e-9 for i in (3, 7, 11)) or abs(self.m[15] - 1.0) > 1e-9:
            raise ValueError("transform_point needs an affine matrix; use project_point for projections")
        x, y, z = point.x, point.y, point.z
        return Vec3(
            self.m[0] * x + self.m[4] * y + self.m[8] * z + self.m[12],
            self.m[1] * x + self.m[5] * y + self.m[9] * z + self.m[13],
            self.m[2] * x + self.m[6] * y + self.m[10] * z + self.m[14],
        )

    def project_point(self, point: Vec3) -> Vec3:
        """Transform by a projection and divide by w to obtain normalized device coordinates."""
        x, y, z = point.x, point.y, point.z
        w = self.m[3] * x + self.m[7] * y + self.m[11] * z + self.m[15]
        if abs(w) < 1e-12:
            raise ZeroDivisionError("point lies on the projection plane (w == 0)")
        return Vec3(
            (self.m[0] * x + self.m[4] * y + self.m[8] * z + self.m[12]) / w,
            (self.m[1] * x + self.m[5] * y + self.m[9] * z + self.m[13]) / w,
            (self.m[2] * x + self.m[6] * y + self.m[10] * z + self.m[14]) / w,
        )

    def transform_direction(self, direction: Vec3) -> Vec3:
        x, y, z = direction.x, direction.y, direction.z
        return Vec3(
            self.m[0] * x + self.m[4] * y + self.m[8] * z,
            self.m[1] * x + self.m[5] * y + self.m[9] * z,
            self.m[2] * x + self.m[6] * y + self.m[10] * z,
        )

    def inverse(self) -> Mat4:
        """Invert an affine transform; raise ValueError for perspective matrices."""
        if any(abs(self.m[i]) > 1e-9 for i in (3, 7, 11)) or abs(self.m[15] - 1.0) > 1e-9:
            raise ValueError("inverse supports affine transforms only")
        a00, a10, a20 = self.m[0], self.m[1], self.m[2]
        a01, a11, a21 = self.m[4], self.m[5], self.m[6]
        a02, a12, a22 = self.m[8], self.m[9], self.m[10]
        det = (
            a00 * (a11 * a22 - a12 * a21)
            - a01 * (a10 * a22 - a12 * a20)
            + a02 * (a10 * a21 - a11 * a20)
        )
        if abs(det) < 1e-12:
            raise ValueError("matrix is not invertible")
        b00 = (a11 * a22 - a12 * a21) / det
        b01 = (a02 * a21 - a01 * a22) / det
        b02 = (a01 * a12 - a02 * a11) / det
        b10 = (a12 * a20 - a10 * a22) / det
        b11 = (a00 * a22 - a02 * a20) / det
        b12 = (a02 * a10 - a00 * a12) / det
        b20 = (a10 * a21 - a11 * a20) / det
        b21 = (a01 * a20 - a00 * a21) / det
        b22 = (a00 * a11 - a01 * a10) / det
        tx, ty, tz = self.m[12], self.m[13], self.m[14]
        return Mat4(
            (
                b00, b10, b20, 0.0,
                b01, b11, b21, 0.0,
                b02, b12, b22, 0.0,
                -(b00 * tx + b01 * ty + b02 * tz),
                -(b10 * tx + b11 * ty + b12 * tz),
                -(b20 * tx + b21 * ty + b22 * tz),
                1.0,
            )
        )

    def flat(self) -> tuple[float, ...]:
        return self.m


@dataclass(frozen=True, slots=True)
class Quat:
    """Unit quaternion (w, x, y, z) for rotation without gimbal lock."""

    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __mul__(self, other: Quat) -> Quat:
        return Quat(
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
        )

    @classmethod
    def identity(cls) -> Quat:
        return cls()

    @classmethod
    def from_axis_angle(cls, axis: Vec3, radians: float) -> Quat:
        unit = axis.normalized()
        if unit.length_squared() < 1e-12:
            raise ValueError("quaternion axis must be non-zero")
        half = radians / 2.0
        s = math.sin(half)
        return cls(math.cos(half), unit.x * s, unit.y * s, unit.z * s)

    def conjugate(self) -> Quat:
        return Quat(self.w, -self.x, -self.y, -self.z)

    def normalized(self) -> Quat:
        length = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if length < 1e-12:
            raise ValueError("cannot normalize a zero quaternion")
        return Quat(self.w / length, self.x / length, self.y / length, self.z / length)

    def rotate(self, vector: Vec3) -> Vec3:
        q = self.normalized()
        v = Vec3(q.x, q.y, q.z)
        return vector + (v.cross(v.cross(vector) + vector * q.w)) * 2.0

    def to_mat4(self) -> Mat4:
        q = self.normalized()
        xx, yy, zz = q.x * q.x, q.y * q.y, q.z * q.z
        xy, xz, yz = q.x * q.y, q.x * q.z, q.y * q.z
        wx, wy, wz = q.w * q.x, q.w * q.y, q.w * q.z
        return Mat4(
            (
                1.0 - 2.0 * (yy + zz), 2.0 * (xy + wz), 2.0 * (xz - wy), 0.0,
                2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz + wx), 0.0,
                2.0 * (xz + wy), 2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy), 0.0,
                0.0, 0.0, 0.0, 1.0,
            )
        )

    def slerp(self, other: Quat, t: float) -> Quat:
        dot = self.w * other.w + self.x * other.x + self.y * other.y + self.z * other.z
        target = other if dot >= 0.0 else Quat(-other.w, -other.x, -other.y, -other.z)
        dot = abs(dot)
        if dot > 0.9995:
            return Quat(
                self.w + (target.w - self.w) * t,
                self.x + (target.x - self.x) * t,
                self.y + (target.y - self.y) * t,
                self.z + (target.z - self.z) * t,
            ).normalized()
        theta = math.acos(dot)
        sin_theta = math.sin(theta)
        a = math.sin((1.0 - t) * theta) / sin_theta
        b = math.sin(t * theta) / sin_theta
        return Quat(
            self.w * a + target.w * b,
            self.x * a + target.x * b,
            self.y * a + target.y * b,
            self.z * a + target.z * b,
        )

    def almost_equal(self, other: Quat, places: int = 6) -> bool:
        return all(
            round(a - b, places) == 0.0
            for a, b in zip((self.w, self.x, self.y, self.z), (other.w, other.x, other.y, other.z))
        )
