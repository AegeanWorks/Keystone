"""Deterministic, game-agnostic animation: keyframe clips, sampling and control.

No window, GL context or third-party dependency is required. Clips are plain
data (JSON-serializable) so AI clients can author, diff and audit motion;
the Controller advances time deterministically and writes Transforms to
scene nodes. Games own their clips; the engine owns sampling math.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass, field

from keystone.math3d import Quat, Vec3
from keystone.scene import Node, Scene, Transform

__all__ = ["AnimationClip", "AnimationController", "Track", "animation_report", "apply_pose", "blend_poses"]


def _check_times(times: tuple[float, ...]) -> None:
    if not times:
        raise ValueError("a track needs at least one keyframe")
    for time in times:
        if not math.isfinite(time) or time < 0.0:
            raise ValueError("keyframe times must be finite and non-negative")
    if any(b <= a for a, b in itertools.pairwise(times)):
        raise ValueError("keyframe times must be sorted")


@dataclass(frozen=True, slots=True)
class Track:
    """One keyframed channel: sorted times with Vec3 or Quat values."""

    times: tuple[float, ...] = ()
    values: tuple[object, ...] = ()
    interpolation: str = "linear"

    def __post_init__(self) -> None:
        if self.interpolation not in ("linear", "step"):
            raise ValueError("interpolation must be 'linear' or 'step'")
        _check_times(self.times)
        if len(self.times) != len(self.values):
            raise ValueError("times and values must have equal length")
        kinds = {type(value) for value in self.values}
        if len(kinds) != 1 or not kinds.pop() in (Vec3, Quat):
            raise TypeError("track values must be all Vec3 or all Quat")
        for value in self.values:
            if isinstance(value, Vec3):
                if not all(math.isfinite(component) for component in (value.x, value.y, value.z)):
                    raise ValueError("track Vec3 values must be finite")
            elif isinstance(value, Quat):
                if not all(math.isfinite(component) for component in (value.w, value.x, value.y, value.z)):
                    raise ValueError("track Quat values must be finite")
                if value.w ** 2 + value.x ** 2 + value.y ** 2 + value.z ** 2 < 1e-12:
                    raise ValueError("track Quat values must be non-zero")

    def duration(self) -> float:
        return self.times[-1] if self.times else 0.0

    def sample(self, time: float) -> Vec3 | Quat:
        if not math.isfinite(time):
            raise ValueError("sample time must be finite")
        time = max(0.0, time)
        if time <= self.times[0]:
            return self.values[0]  # type: ignore[return-value]
        if time >= self.times[-1]:
            return self.values[-1]  # type: ignore[return-value]
        if self.interpolation == "step":
            for index in range(len(self.times) - 1, -1, -1):
                if self.times[index] <= time:
                    return self.values[index]  # type: ignore[return-value]
            return self.values[0]  # type: ignore[return-value]
        for index in range(len(self.times) - 1):
            first, second = self.times[index], self.times[index + 1]
            if first <= time <= second:
                span = second - first
                factor = 0.0 if span <= 0.0 else (time - first) / span
                first_value, second_value = self.values[index], self.values[index + 1]
                if isinstance(first_value, Vec3) and isinstance(second_value, Vec3):
                    return first_value.lerp(second_value, factor)
                if isinstance(first_value, Quat) and isinstance(second_value, Quat):
                    return first_value.slerp(second_value, factor)
                raise TypeError("track values must be all Vec3 or all Quat")
        return self.values[-1]  # type: ignore[return-value]

    def to_dict(self) -> dict:
        # Emit floats: Vec3/Quat accept int components, but from_dict always
        # rebuilds floats, so raw ints made a clip differ textually after one
        # round trip.
        items = []
        for time, value in zip(self.times, self.values):
            if isinstance(value, Vec3):
                items.append(
                    {
                        "t": time,
                        "v": [float(value.x), float(value.y), float(value.z)],
                    }
                )
            else:
                assert isinstance(value, Quat)
                items.append(
                    {
                        "t": time,
                        "q": [
                            float(value.x),
                            float(value.y),
                            float(value.z),
                            float(value.w),
                        ],
                    }
                )
        return {"interpolation": self.interpolation, "keys": items}

    @classmethod
    def from_dict(cls, data: dict) -> Track:
        if not isinstance(data, dict):
            raise TypeError("track document must be a mapping")
        interpolation = str(data.get("interpolation", "linear"))
        raw_keys = data.get("keys", [])
        if not isinstance(raw_keys, (list, tuple)):
            raise TypeError("track keys must be a list")
        times: list[float] = []
        values: list[object] = []
        for key in raw_keys:
            if not isinstance(key, dict):
                raise TypeError("track key must be a mapping")
            if "t" not in key:
                raise ValueError("track key must hold 't'")
            try:
                time = float(key["t"])
            except (TypeError, ValueError) as exc:
                raise ValueError("track key time must be numeric") from exc
            if not math.isfinite(time):
                raise ValueError("track key time must be finite")
            if "v" in key:
                raw = key["v"]
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError("track key 'v' must have three values")
                if not all(isinstance(component, (int, float)) and not isinstance(component, bool) for component in raw):
                    raise ValueError("track key 'v' must be numeric")
                values.append(Vec3(float(raw[0]), float(raw[1]), float(raw[2])))
            elif "q" in key:
                raw = key["q"]
                if not isinstance(raw, (list, tuple)) or len(raw) != 4:
                    raise ValueError("track key 'q' must have four values")
                if not all(isinstance(component, (int, float)) and not isinstance(component, bool) for component in raw):
                    raise ValueError("track key 'q' must be numeric")
                values.append(Quat(float(raw[3]), float(raw[0]), float(raw[1]), float(raw[2])))
            else:
                raise ValueError("track key must hold 'v' or 'q'")
            times.append(time)
        return cls(times=tuple(times), values=tuple(values), interpolation=interpolation)


@dataclass(frozen=True, slots=True)
class AnimationClip:
    """A named set of per-node tracks sharing one duration."""

    name: str = "clip"
    position_tracks: tuple[tuple[str, Track], ...] = ()
    rotation_tracks: tuple[tuple[str, Track], ...] = ()
    scale_tracks: tuple[tuple[str, Track], ...] = ()
    events: tuple[tuple[float, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("clip name must be a non-blank string")
        cleaned: list[tuple[float, str]] = []
        for time, label in self.events:
            try:
                event_time = float(time)
            except (TypeError, ValueError) as exc:
                raise ValueError("event times must be numeric") from exc
            if not math.isfinite(event_time) or event_time < 0.0:
                raise ValueError("event times must be finite and non-negative")
            if not isinstance(label, str) or not label.strip():
                raise ValueError("event names must be non-blank strings")
            cleaned.append((event_time, label))
        object.__setattr__(self, "events", tuple(sorted(cleaned, key=lambda item: (item[0], item[1]))))
        for label, tracks, expected in (
            ("position", self.position_tracks, Vec3),
            ("rotation", self.rotation_tracks, Quat),
            ("scale", self.scale_tracks, Vec3),
        ):
            seen: set[str] = set()
            for node_id, track in tracks:
                if not isinstance(node_id, str) or not node_id.strip():
                    raise ValueError("clip node ids must be non-blank strings")
                if node_id in seen:
                    raise ValueError(f"clip has duplicate {label} track for {node_id!r}")
                seen.add(node_id)
                if not isinstance(track, Track):
                    raise TypeError("clip tracks must be Track instances")
                if not all(isinstance(value, expected) for value in track.values):
                    raise TypeError(f"{label} tracks must hold {expected.__name__} values")
            object.__setattr__(self, f"{label}_tracks", tuple(sorted(tracks, key=lambda item: item[0])))

    def duration(self) -> float:
        has_tracks = bool(self.position_tracks or self.rotation_tracks or self.scale_tracks)
        longest = 0.0
        for _, track in (*self.position_tracks, *self.rotation_tracks, *self.scale_tracks):
            longest = max(longest, track.duration())
        if has_tracks:
            return longest
        for time, _ in self.events:
            longest = max(longest, time)
        return longest

    def node_ids(self) -> list[str]:
        ids: list[str] = []
        for node_id, _ in (*self.position_tracks, *self.rotation_tracks, *self.scale_tracks):
            if node_id not in ids:
                ids.append(node_id)
        return sorted(ids)

    def sample(self, time: float) -> dict[str, Transform]:
        if not math.isfinite(time):
            raise ValueError("sample time must be finite")
        time = max(0.0, time)
        positions = {node_id: track.sample(time) for node_id, track in self.position_tracks}
        rotations = {node_id: track.sample(time) for node_id, track in self.rotation_tracks}
        scales = {node_id: track.sample(time) for node_id, track in self.scale_tracks}
        pose: dict[str, Transform] = {}
        for node_id in self.node_ids():
            position = positions.get(node_id)
            rotation = rotations.get(node_id)
            scale = scales.get(node_id)
            pose[node_id] = Transform(
                position=position if isinstance(position, Vec3) else Vec3(),
                rotation=rotation if isinstance(rotation, Quat) else Quat(),
                scale=scale if isinstance(scale, Vec3) else Vec3(1.0, 1.0, 1.0),
            )
        return pose

    def events_in_range(self, start: float, end: float) -> list[str]:
        """Return event names with start < time <= end (loop callers split wraps)."""
        return [label for time, label in self.events if start < time <= end]

    def to_dict(self) -> dict:
        def pack(tracks: tuple[tuple[str, Track], ...]) -> dict:
            return {node_id: track.to_dict() for node_id, track in tracks}

        return {
            "schema": 1,
            "name": self.name,
            "position": pack(self.position_tracks),
            "rotation": pack(self.rotation_tracks),
            "scale": pack(self.scale_tracks),
            "events": [{"t": time, "name": label} for time, label in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict) -> AnimationClip:
        if not isinstance(data, dict):
            raise TypeError("clip document must be a mapping")
        if data.get("schema", 1) != 1:
            raise ValueError("unsupported animation clip schema")

        def unpack(raw: object) -> tuple[tuple[str, Track], ...]:
            if not isinstance(raw, dict):
                raise TypeError("clip tracks must be a mapping")
            return tuple(sorted((str(node_id), Track.from_dict(track)) for node_id, track in raw.items()))

        raw_events = data.get("events", [])
        if not isinstance(raw_events, (list, tuple)):
            raise TypeError("clip events must be a list")
        events: list[tuple[float, str]] = []
        for item in raw_events:
            if not isinstance(item, dict) or "t" not in item or "name" not in item:
                raise ValueError("clip event must be a mapping with 't' and 'name'")
            events.append((float(item["t"]), str(item["name"])))
        return cls(
            name=str(data.get("name", "clip")),
            position_tracks=unpack(data.get("position", {})),
            rotation_tracks=unpack(data.get("rotation", {})),
            scale_tracks=unpack(data.get("scale", {})),
            events=tuple(events),
        )


@dataclass
class AnimationController:
    """Deterministic playback: advance time, loop, blend and write Transforms."""

    clips: dict[str, AnimationClip] = field(default_factory=dict)
    current: str = ""
    time: float = 0.0
    speed: float = 1.0
    loop: bool = True
    blending: bool = False
    _blend_from_pose: dict[str, Transform] = field(default_factory=dict, repr=False)
    _blend_to: str = ""
    _blend_duration: float = 0.0
    _blend_elapsed: float = 0.0
    _fresh_start: bool = field(default=True, repr=False)
    _pose_provider: Callable[[float], dict[str, Transform]] | None = field(
        default=None, repr=False
    )
    _wrap_duration: Callable[[], float] | None = field(default=None, repr=False)

    def set_pose_provider(
        self,
        pose: Callable[[float], dict[str, Transform]] | None,
        wrap_duration: Callable[[], float] | None = None,
    ) -> None:
        """Let a caller-supplied sampler own the pose and the loop length.

        Blend-space states sample a pose that no single clip describes and may
        span several clips, so the controller asks them for the pose at a time
        and for the length to wrap at instead of using the active clip.
        """
        self._pose_provider = pose
        self._wrap_duration = wrap_duration if pose is not None else None

    def _pose_at(self, moment: float, clip: AnimationClip) -> dict[str, Transform]:
        if self._pose_provider is not None:
            return self._pose_provider(moment)
        return clip.sample(moment)

    def __post_init__(self) -> None:
        if isinstance(self.speed, bool) or not isinstance(self.speed, (int, float)) or not math.isfinite(self.speed):
            raise ValueError("animation speed must be finite")
        if not isinstance(self.loop, bool):
            raise TypeError("animation loop must be a boolean")

    def add(self, clip: AnimationClip) -> None:
        if not isinstance(clip, AnimationClip):
            raise TypeError("controller clips must be AnimationClip instances")
        self.clips[clip.name] = clip
        if not self.current:
            self.current = clip.name

    def play(self, name: str, restart: bool = True) -> None:
        if name not in self.clips:
            raise KeyError(f"unknown animation clip {name!r}")
        self.current = name
        self.blending = False
        self._blend_from_pose = {}
        self._blend_to = ""
        self.set_pose_provider(None)
        if restart:
            self.time = 0.0
            self._fresh_start = True

    def crossfade(self, name: str, duration: float) -> None:
        """Blend from the current sampled pose into another clip over duration."""
        if name not in self.clips:
            raise KeyError(f"unknown animation clip {name!r}")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration):
            raise ValueError("crossfade duration must be finite")
        if duration < 0.0:
            raise ValueError("crossfade duration must be non-negative")
        if not self.current or self.current not in self.clips or duration == 0.0:
            self.play(name)
            return
        moment = self._moment()
        if self.blending and self._blend_duration > 0.0:
            factor = min(1.0, self._blend_elapsed / self._blend_duration)
            source = blend_poses(self._blend_from_pose, self._pose_at(moment, self.clips[self.current]), factor)
        else:
            source = self._pose_at(moment, self.clips[self.current])
        self._blend_from_pose = source
        self._blend_to = name
        self._blend_duration = duration
        self._blend_elapsed = 0.0
        self.blending = True
        self.current = name
        self.time = 0.0
        self._fresh_start = True

    def _moment(self) -> float:
        clip = self.clips.get(self.current)
        if clip is None:
            return 0.0
        duration = clip.duration()
        if self._wrap_duration is not None:
            duration = self._wrap_duration()
        if duration > 0.0 and self.loop:
            return self.time % duration
        return min(self.time, duration)

    def advance(self, dt: float) -> dict[str, Transform]:
        pose, _ = self.advance_with_events(dt)
        return pose

    def advance_with_events(self, dt: float) -> tuple[dict[str, Transform], list[str]]:
        if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt):
            raise ValueError("dt must be finite")
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
        if not self.current or self.current not in self.clips:
            return {}, []
        clip = self.clips[self.current]
        duration = clip.duration()
        previous = self._moment()
        distance = dt * self.speed
        first_step = self._fresh_start and distance > 0.0
        self.time += distance
        if distance > 0.0:
            self._fresh_start = False
        moment = self._moment()
        if duration > 0.0 and self.loop and distance > 0.0 and previous + distance >= duration:
            fired = clip.events_in_range(previous, duration) + clip.events_in_range(-1.0, moment)
        elif duration > 0.0 and self.loop and distance < 0.0 and previous + distance < 0.0:
            fired = clip.events_in_range(moment, duration) + clip.events_in_range(-1.0, previous)
        elif distance < 0.0:
            fired = clip.events_in_range(moment, previous)
        elif first_step:
            fired = clip.events_in_range(-1.0, moment)
        else:
            fired = clip.events_in_range(previous, moment)
        pose = self._pose_at(moment, clip)
        if self.blending:
            self._blend_elapsed += dt
            factor = 1.0 if self._blend_duration <= 0.0 else min(1.0, self._blend_elapsed / self._blend_duration)
            if self._blend_from_pose:
                pose = blend_poses(self._blend_from_pose, pose, factor)
            if factor >= 1.0:
                self.blending = False
                self._blend_from_pose = {}
        return pose, fired

def blend_poses(first: dict[str, Transform], second: dict[str, Transform], factor: float) -> dict[str, Transform]:
    """Blend two sampled poses; factor 0 returns first, 1 returns second."""
    if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor):
        raise ValueError("blend factor must be finite")
    factor = max(0.0, min(1.0, factor))
    pose: dict[str, Transform] = {}
    for node_id in sorted(set(first) | set(second)):
        first_transform = first.get(node_id, Transform())
        second_transform = second.get(node_id, Transform())
        pose[node_id] = Transform(
            position=first_transform.position.lerp(second_transform.position, factor),
            rotation=first_transform.rotation.slerp(second_transform.rotation, factor),
            scale=first_transform.scale.lerp(second_transform.scale, factor),
        )
    return pose


POSE_CHANNELS = ("position", "rotation", "scale")


def apply_pose(
    scene: Scene,
    pose: dict[str, Transform],
    mask: object = None,
) -> list[str]:
    """Write sampled Transforms onto nodes by id or name; return updated ids.

    ``mask`` restricts which channels are written. A game that simulates node
    position can therefore animate only ``{"rotation", "scale"}`` without
    clobbering its own movement. ``None`` (the default) writes the whole
    transform, so existing callers are unaffected.
    """
    if not isinstance(pose, dict):
        raise TypeError("pose must be a mapping of node ids to Transforms")
    channels = _pose_channels(mask)
    index: dict[str, Node] = {}
    for node in scene.traverse():
        if node.id:
            index[node.id] = node
        index.setdefault(node.name, node)
    updated: set[str] = set()
    for key, transform in pose.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("pose keys must be non-blank strings")
        if not isinstance(transform, Transform):
            raise TypeError("pose values must be Transform instances")
        node = index.get(key)
        if node is None:
            continue
        if channels is None:
            node.transform = transform
        else:
            current = node.transform
            node.transform = Transform(
                position=(
                    transform.position if "position" in channels
                    else current.position
                ),
                rotation=(
                    transform.rotation if "rotation" in channels
                    else current.rotation
                ),
                scale=(
                    transform.scale if "scale" in channels
                    else current.scale
                ),
            )
        updated.add(node.id or node.name)
    return sorted(updated)


def _pose_channels(mask: object) -> frozenset[str] | None:
    """Normalize a channel mask, rejecting names that are not pose channels."""
    if mask is None:
        return None
    if isinstance(mask, (str, bytes)) or not isinstance(
        mask, (set, frozenset, list, tuple)
    ):
        raise TypeError("pose mask must be a set of channel names or None")
    names = frozenset(mask)
    unknown = sorted(
        name for name in names if not isinstance(name, str)
    )
    if unknown:
        raise TypeError("pose mask channel names must be strings")
    surplus = sorted(names - set(POSE_CHANNELS))
    if surplus:
        raise ValueError(
            f"pose mask has unknown channels: {surplus}; "
            f"use {list(POSE_CHANNELS)}"
        )
    return names


def animation_report(controller: AnimationController) -> dict:
    return {
        "schema": 1,
        "clips": sorted(controller.clips),
        "current": controller.current,
        "time": round(controller.time, 4),
        "speed": controller.speed,
        "loop": controller.loop,
        "blending": controller.blending,
        "blend_to": controller._blend_to if controller.blending else None,
        "durations": {name: clip.duration() for name, clip in controller.clips.items()},
        "events": {name: len(clip.events) for name, clip in controller.clips.items()},
    }
