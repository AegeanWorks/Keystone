"""Deterministic camera paths: timed keys sampled into camera poses.

A camera path is authored data: keys at non-negative, strictly increasing
times, each with a position, orientation and vertical field of view. Position
follows a non-uniform Catmull-Rom spline through the key times, orientation
slerps between keys and the lens interpolates linearly, so a sample depends
only on the path and a time. A looping path adds a return leg from its last
key to its first over the span between the last key time and the declared
duration, which closes the cycle without an extra key. Nothing here mutates a
camera or stores per-frame state, which keeps authored moves reproducible in
replays and captures.

``CameraPathPlayer`` owns that clock for one path: ``advance(dt)`` returns the
pose at the new time, wrapping at the duration for looping playback or
clamping for one-shot playback. ``CameraPose.to_camera()`` builds an
independent ``PerspectiveCamera`` from a sampled pose, so a game keeps camera
ownership and can compose the pose with ``CameraShaker`` or ``CameraRig``.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from keystone.camera import MAX_PITCH, PerspectiveCamera
from keystone.math3d import Quat, Vec3

__all__ = [
    "CAMERA_PATH_SCHEMA",
    "CameraKey",
    "CameraPath",
    "CameraPathPlayer",
    "CameraPose",
    "camera_key_from_dict",
    "camera_path_from_dict",
    "camera_path_player_report",
    "camera_path_report",
    "camera_path_to_dict",
    "insert_camera_key",
    "remove_camera_key",
]

CAMERA_PATH_SCHEMA = 1
_DOCUMENT_KEYS = frozenset({"schema", "loop", "duration", "keys"})
_KEY_DOCUMENT_KEYS = frozenset({"time", "position", "rotation", "fov_y"})


def _finite(label: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _finite_vec3(label: str, value: object) -> Vec3:
    if not isinstance(value, Vec3):
        raise TypeError(f"{label} must be a Vec3")
    if not all(math.isfinite(component) for component in (value.x, value.y, value.z)):
        raise ValueError(f"{label} must be finite")
    return value


def _finite_quat(label: str, value: object) -> Quat:
    if not isinstance(value, Quat):
        raise TypeError(f"{label} must be a Quat")
    if not all(
        math.isfinite(component) for component in (value.w, value.x, value.y, value.z)
    ):
        raise ValueError(f"{label} must be finite")
    if value.w**2 + value.x**2 + value.y**2 + value.z**2 < 1e-12:
        raise ValueError(f"{label} must be non-zero")
    return value


def _lens(value: object, label: str) -> float:
    fov = _finite(label, value)
    if fov <= 0.0 or fov >= 180.0:
        raise ValueError(f"{label} must be between 0 and 180 degrees")
    return fov


def _position_list(position: Vec3) -> list[float]:
    return [round(position.x, 6), round(position.y, 6), round(position.z, 6)]


def _rotation_list(rotation: Quat) -> list[float]:
    unit = rotation.normalized()
    return [round(unit.w, 6), round(unit.x, 6), round(unit.y, 6), round(unit.z, 6)]


@dataclass(frozen=True, slots=True)
class CameraKey:
    """One authored camera pose at a path time in seconds."""

    time: float
    position: Vec3
    rotation: Quat = Quat()
    fov_y: float = 60.0

    def __post_init__(self) -> None:
        moment = _finite("camera key time", self.time)
        if moment < 0.0:
            raise ValueError("camera key time must be non-negative")
        _finite_vec3("camera key position", self.position)
        _finite_quat("camera key rotation", self.rotation)
        _lens(self.fov_y, "camera key fov_y")

    @classmethod
    def look_at(
        cls,
        time: float,
        position: Vec3,
        target: Vec3,
        *,
        fov_y: float = 60.0,
    ) -> CameraKey:
        """Build a key aimed at ``target`` using the engine camera convention."""
        position = _finite_vec3("camera key position", position)
        target = _finite_vec3("camera key target", target)
        direction = target - position
        if direction.length_squared() < 1e-12:
            raise ValueError("camera key cannot look at its own position")
        direction = direction.normalized()
        yaw = math.atan2(direction.x, -direction.z)
        pitch = math.asin(max(-1.0, min(1.0, direction.y)))
        rotation = (
            Quat.from_axis_angle(Vec3.UP, -yaw)
            * Quat.from_axis_angle(Vec3(1.0, 0.0, 0.0), pitch)
        ).normalized()
        return cls(time=time, position=position, rotation=rotation, fov_y=fov_y)

    @classmethod
    def from_view(
        cls,
        time: float,
        position: Vec3,
        yaw: float,
        pitch: float,
        *,
        fov_y: float = 60.0,
    ) -> CameraKey:
        """Build a key from an engine-camera yaw/pitch view.

        This is the inverse of ``CameraPose.yaw``/``pitch``, so a key captured
        from a ``PerspectiveCamera`` samples back to the same heading. Pitch
        is clamped to the camera limit, matching ``PerspectiveCamera``.
        """
        position = _finite_vec3("camera key position", position)
        heading = _finite("camera key yaw", yaw)
        tilt = max(-MAX_PITCH, min(MAX_PITCH, _finite("camera key pitch", pitch)))
        rotation = (
            Quat.from_axis_angle(Vec3.UP, -heading)
            * Quat.from_axis_angle(Vec3(1.0, 0.0, 0.0), tilt)
        ).normalized()
        return cls(time=time, position=position, rotation=rotation, fov_y=fov_y)

    @classmethod
    def from_camera(cls, time: float, camera: PerspectiveCamera) -> CameraKey:
        """Build a key from a camera's position, heading and lens."""
        if not isinstance(camera, PerspectiveCamera):
            raise TypeError("camera key source must be a PerspectiveCamera")
        return cls.from_view(
            time,
            camera.position,
            camera.yaw,
            camera.pitch,
            fov_y=camera.fov_y,
        )


@dataclass(frozen=True, slots=True)
class CameraPose:
    """A sampled camera state; independent of any camera instance."""

    position: Vec3
    rotation: Quat
    fov_y: float = 60.0

    def __post_init__(self) -> None:
        _finite_vec3("camera pose position", self.position)
        _finite_quat("camera pose rotation", self.rotation)
        _lens(self.fov_y, "camera pose fov_y")

    def forward(self) -> Vec3:
        """The direction the pose looks along, matching ``PerspectiveCamera``."""
        return self.rotation.normalized().rotate(Vec3(0.0, 0.0, -1.0))

    @property
    def yaw(self) -> float:
        forward = self.forward()
        return math.atan2(forward.x, -forward.z)

    @property
    def pitch(self) -> float:
        forward = self.forward()
        return max(-MAX_PITCH, min(MAX_PITCH, math.asin(max(-1.0, min(1.0, forward.y)))))

    def to_camera(self, base: PerspectiveCamera | None = None) -> PerspectiveCamera:
        """Build a new camera from the pose, reusing the base lens range."""
        if base is not None and not isinstance(base, PerspectiveCamera):
            raise TypeError("camera pose base must be a PerspectiveCamera or None")
        return PerspectiveCamera(
            position=self.position,
            yaw=self.yaw,
            pitch=self.pitch,
            fov_y=self.fov_y,
            near=base.near if base is not None else 0.1,
            far=base.far if base is not None else 1000.0,
        )


class CameraPath:
    """Timed camera keys sampled as smooth, deterministic poses.

    A looping path needs an explicit ``duration`` greater than its last key
    time: the spare interval is the return leg from the last key to the first,
    so the cycle closes without repeating a key pose.
    """

    def __init__(
        self,
        keys: Sequence[CameraKey],
        *,
        loop: bool = False,
        duration: float | None = None,
    ) -> None:
        if isinstance(keys, (str, bytes)) or not isinstance(keys, Sequence):
            raise TypeError("camera path keys must be a sequence of CameraKey")
        if not isinstance(loop, bool):
            raise TypeError("camera path loop must be a bool")
        items = tuple(keys)
        if not items:
            raise ValueError("camera path needs at least one key")
        for item in items:
            if not isinstance(item, CameraKey):
                raise TypeError("camera path keys must be CameraKey instances")
        if items[0].time != 0.0:
            raise ValueError("camera path keys must start at time 0")
        for previous, current in pairwise(items):
            if current.time <= previous.time:
                raise ValueError("camera path key times must strictly increase")
        if loop:
            if len(items) < 2:
                raise ValueError("a looping camera path needs at least two keys")
            if duration is None:
                raise ValueError("a looping camera path needs a duration")
            cycle = _finite("camera path duration", duration)
            if cycle <= items[-1].time:
                raise ValueError(
                    "camera path duration must exceed the last key time"
                )
        else:
            if duration is not None:
                raise ValueError(
                    "a one-shot camera path takes its duration from the last key"
                )
            cycle = items[-1].time
        self.keys = items
        self.loop = loop
        self.duration = cycle
        self._times = tuple(item.time for item in items)
        self._tangents = self._build_tangents()

    def _build_tangents(self) -> tuple[Vec3, ...]:
        keys = self.keys
        count = len(keys)
        if count == 1:
            return (Vec3(),)
        if count == 2 and not self.loop:
            step = keys[1].time - keys[0].time
            velocity = (keys[1].position - keys[0].position) / step
            return (velocity, velocity)
        tangents: list[Vec3] = []
        for index in range(count):
            if self.loop:
                previous = (index - 1) % count
                following = (index + 1) % count
                previous_time = keys[previous].time - (
                    self.duration if index == 0 else 0.0
                )
                following_time = keys[following].time + (
                    self.duration if index == count - 1 else 0.0
                )
            else:
                previous = max(0, index - 1)
                following = min(count - 1, index + 1)
                previous_time = keys[previous].time
                following_time = keys[following].time
            span = following_time - previous_time
            tangents.append((keys[following].position - keys[previous].position) / span)
        return tuple(tangents)

    def _pose(self, key: CameraKey) -> CameraPose:
        return CameraPose(key.position, key.rotation, key.fov_y)

    def sample(self, time: float) -> CameraPose:
        """Sample the pose at ``time`` seconds; wraps when looping, else clamps."""
        moment = _finite("camera path time", time)
        if moment < 0.0:
            raise ValueError("camera path time must be non-negative")
        keys = self.keys
        if len(keys) == 1:
            return self._pose(keys[0])
        if self.loop:
            moment = moment % self.duration
        elif moment >= self.duration:
            return self._pose(keys[-1])
        segment = bisect_right(self._times, moment) - 1
        start = keys[segment]
        if self.loop and segment == len(keys) - 1:
            end = keys[0]
            end_time = self.duration
            end_tangent = self._tangents[0]
        else:
            end = keys[segment + 1]
            end_time = end.time
            end_tangent = self._tangents[segment + 1]
        span = end_time - start.time
        factor = 0.0 if span <= 0.0 else (moment - start.time) / span
        position = _hermite(
            start.position,
            end.position,
            self._tangents[segment],
            end_tangent,
            span,
            factor,
        )
        rotation = start.rotation.normalized().slerp(end.rotation.normalized(), factor)
        fov_y = start.fov_y + (end.fov_y - start.fov_y) * factor
        return CameraPose(position, rotation.normalized(), fov_y)


def _hermite(
    start: Vec3,
    end: Vec3,
    start_tangent: Vec3,
    end_tangent: Vec3,
    span: float,
    factor: float,
) -> Vec3:
    squared = factor * factor
    cubed = squared * factor
    h00 = 2.0 * cubed - 3.0 * squared + 1.0
    h10 = cubed - 2.0 * squared + factor
    h01 = -2.0 * cubed + 3.0 * squared
    h11 = cubed - squared
    return (
        start * h00
        + start_tangent * (span * h10)
        + end * h01
        + end_tangent * (span * h11)
    )


class CameraPathPlayer:
    """Own one path's clock and return its pose as time advances."""

    def __init__(
        self,
        path: CameraPath,
        *,
        loop: bool | None = None,
        speed: float = 1.0,
    ) -> None:
        if not isinstance(path, CameraPath):
            raise TypeError("camera path player needs a CameraPath")
        if loop is not None and not isinstance(loop, bool):
            raise TypeError("camera path player loop must be a bool or None")
        self.path = path
        self.loop = path.loop if loop is None else loop
        self.speed = _finite("camera path speed", speed)
        if self.speed <= 0.0:
            raise ValueError("camera path speed must be positive")
        self.time = 0.0
        self.done = False

    def sample(self) -> CameraPose:
        """Return the pose at the current time."""
        return self.path.sample(self.time)

    def advance(self, dt: float) -> CameraPose:
        """Advance the clock and return the pose at the new time."""
        seconds = _finite("camera path dt", dt)
        if seconds < 0.0:
            raise ValueError("camera path dt must be non-negative")
        if self.loop:
            if self.path.duration > 0.0:
                self.time = (self.time + self.speed * seconds) % self.path.duration
            self.done = False
        else:
            self.time = min(self.path.duration, self.time + self.speed * seconds)
            self.done = self.time >= self.path.duration
        return self.path.sample(self.time)

    def seek(self, time: float) -> CameraPose:
        """Jump to a time, wrapping when looping and clamping otherwise."""
        moment = _finite("camera path time", time)
        if moment < 0.0:
            raise ValueError("camera path time must be non-negative")
        if self.loop:
            if self.path.duration > 0.0:
                moment = moment % self.path.duration
        else:
            moment = min(self.path.duration, moment)
        self.time = moment
        self.done = (not self.loop) and self.time >= self.path.duration
        return self.path.sample(self.time)

    def reset(self) -> None:
        """Rewind the clock to the start."""
        self.time = 0.0
        self.done = False


def camera_path_report(path: CameraPath) -> dict:
    """Return a JSON-safe summary of an authored path."""
    if not isinstance(path, CameraPath):
        raise TypeError("camera_path_report needs a CameraPath")
    return {
        "schema": 1,
        "duration": round(path.duration, 6),
        "loop": path.loop,
        "keys": [
            {
                "time": round(key.time, 6),
                "position": _position_list(key.position),
                "rotation": _rotation_list(key.rotation),
                "fov_y": round(key.fov_y, 6),
            }
            for key in path.keys
        ],
    }


def camera_path_player_report(player: CameraPathPlayer) -> dict:
    """Return a JSON-safe summary of a player and its current pose."""
    if not isinstance(player, CameraPathPlayer):
        raise TypeError("camera_path_player_report needs a CameraPathPlayer")
    pose = player.sample()
    return {
        "schema": 1,
        "time": round(player.time, 6),
        "speed": round(player.speed, 6),
        "loop": player.loop,
        "done": player.done,
        "pose": {
            "position": _position_list(pose.position),
            "rotation": _rotation_list(pose.rotation),
            "fov_y": round(pose.fov_y, 6),
            "yaw": round(pose.yaw, 6),
            "pitch": round(pose.pitch, 6),
        },
        "path": camera_path_report(player.path),
    }


def _number_list(label: str, value: object, length: int) -> list[float]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{label} must be a list of {length} numbers")
    if len(value) != length:
        raise ValueError(f"{label} must have {length} values")
    numbers: list[float] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{label} must hold real numbers")
        number = float(component)
        if not math.isfinite(number):
            raise ValueError(f"{label} must be finite")
        numbers.append(number)
    return numbers


def camera_key_from_dict(document: object) -> CameraKey:
    """Build one camera key from its document form, refusing drift."""
    if not isinstance(document, dict):
        raise TypeError("camera path key must be a JSON object")
    unknown = set(document) - _KEY_DOCUMENT_KEYS
    if unknown:
        raise ValueError(f"camera path key has unknown keys: {sorted(unknown)}")
    if "time" not in document:
        raise ValueError("camera path key needs a time")
    if "position" not in document:
        raise ValueError("camera path key needs a position")
    rotation = _number_list(
        "camera path key rotation",
        document.get("rotation", (0.0, 0.0, 0.0, 1.0)),
        4,
    )
    return CameraKey(
        time=_finite("camera path key time", document["time"]),
        position=Vec3(
            *_number_list("camera path key position", document["position"], 3)
        ),
        rotation=Quat(rotation[3], rotation[0], rotation[1], rotation[2]),
        fov_y=_lens(document.get("fov_y", 60.0), "camera path key fov_y"),
    )


def camera_path_to_dict(path: CameraPath) -> dict:
    """Return the schema-1 document for one camera path.

    Quaternions use the engine document order ``[x, y, z, w]``. A looping
    path writes its declared ``duration``; a one-shot path omits it because
    the last key time is the duration.
    """
    if not isinstance(path, CameraPath):
        raise TypeError("camera_path_to_dict needs a CameraPath")
    document: dict[str, object] = {
        "schema": CAMERA_PATH_SCHEMA,
        "loop": path.loop,
        "keys": [
            {
                "time": float(key.time),
                "position": [
                    float(key.position.x),
                    float(key.position.y),
                    float(key.position.z),
                ],
                "rotation": [
                    float(key.rotation.x),
                    float(key.rotation.y),
                    float(key.rotation.z),
                    float(key.rotation.w),
                ],
                "fov_y": float(key.fov_y),
            }
            for key in path.keys
        ],
    }
    if path.loop:
        document["duration"] = float(path.duration)
    return document


def camera_path_from_dict(document: object) -> CameraPath:
    """Build a camera path from a schema-1 document, refusing drift."""
    if not isinstance(document, dict):
        raise TypeError("camera path document must be a JSON object")
    schema = document.get("schema", CAMERA_PATH_SCHEMA)
    if isinstance(schema, bool) or schema != CAMERA_PATH_SCHEMA:
        raise ValueError(
            f"unsupported camera path schema; expected {CAMERA_PATH_SCHEMA}"
        )
    unknown = set(document) - _DOCUMENT_KEYS
    if unknown:
        raise ValueError(f"camera path has unknown keys: {sorted(unknown)}")
    loop = document.get("loop", False)
    if not isinstance(loop, bool):
        raise TypeError("camera path document loop must be a boolean")
    raw_keys = document.get("keys")
    if not isinstance(raw_keys, (list, tuple)):
        raise TypeError("camera path document keys must be a list")
    keys: list[CameraKey] = []
    for item in raw_keys:
        keys.append(camera_key_from_dict(item))
    if loop:
        if "duration" not in document:
            raise ValueError("a looping camera path document needs a duration")
        return CameraPath(keys, loop=True, duration=document["duration"])
    if "duration" in document:
        raise ValueError(
            "a one-shot camera path document must omit duration"
        )
    return CameraPath(keys)


def _gap(epsilon: object) -> float:
    gap = _finite("camera key epsilon", epsilon)
    if gap <= 0.0:
        raise ValueError("camera key epsilon must be positive")
    return gap


def insert_camera_key(
    path: CameraPath | None,
    key: CameraKey,
    *,
    epsilon: float = 1e-6,
) -> tuple[CameraPath, bool]:
    """Insert or replace one key, returning the path and whether it replaced.

    ``None`` starts a new one-shot path, which needs its first key at time 0.
    A key within ``epsilon`` of an existing key replaces that key's pose at the
    existing time, so float noise cannot reshuffle or unanchor a path. A
    looping path refuses a key at or past its declared duration, because the
    spare span is its return leg.
    """
    if path is not None and not isinstance(path, CameraPath):
        raise TypeError("camera key target must be a CameraPath or None")
    if not isinstance(key, CameraKey):
        raise TypeError("insert_camera_key needs a CameraKey")
    gap = _gap(epsilon)
    if path is None:
        if key.time != 0.0:
            raise ValueError("a new camera path needs its first key at time 0")
        return CameraPath([key]), False
    for existing in path.keys:
        if abs(existing.time - key.time) <= gap:
            replacement = CameraKey(
                existing.time, key.position, key.rotation, key.fov_y
            )
            keys = tuple(
                replacement if item is existing else item for item in path.keys
            )
            return _rebuild(path, keys), True
    if path.loop and key.time >= path.duration:
        raise ValueError(
            "a looping camera path key must fall before its duration"
        )
    keys = tuple(sorted(path.keys + (key,), key=lambda item: item.time))
    return _rebuild(path, keys), False


def remove_camera_key(
    path: CameraPath,
    time: float,
    *,
    epsilon: float = 1e-6,
) -> tuple[CameraPath, int]:
    """Remove the key at ``time``, returning the path and removed count.

    A missing time removes nothing so callers can report ``removed: 0``.
    Removing every key or the anchoring key at time 0 is refused; delete the
    path or empty it by other means rather than leaving an unanchored spline.
    """
    if not isinstance(path, CameraPath):
        raise TypeError("remove_camera_key needs a CameraPath")
    gap = _gap(epsilon)
    moment = _finite("camera path time", time)
    if moment < 0.0:
        raise ValueError("camera path time must be non-negative")
    doomed = tuple(
        item for item in path.keys if abs(item.time - moment) <= gap
    )
    if not doomed:
        return path, 0
    keys = tuple(item for item in path.keys if not any(item is hit for hit in doomed))
    if not keys:
        raise ValueError(
            "a camera path needs at least one key; delete the path instead"
        )
    if keys[0].time != 0.0:
        raise ValueError(
            "a camera path must start at time 0; remove the later keys first"
        )
    return _rebuild(path, keys), len(doomed)


def _rebuild(path: CameraPath, keys: tuple[CameraKey, ...]) -> CameraPath:
    if path.loop:
        return CameraPath(keys, loop=True, duration=path.duration)
    return CameraPath(keys)
