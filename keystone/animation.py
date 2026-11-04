"""Deterministic, game-agnostic animation: keyframe clips, sampling and control.

No window, GL context or third-party dependency is required. Clips are plain
data (JSON-serializable) so AI clients can author, diff and audit motion;
the Controller advances time deterministically and writes Transforms to
scene nodes. Games own their clips; the engine owns sampling math.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from keystone.math3d import Quat, Vec3
from keystone.scene import Node, Scene, Transform

__all__ = ["AnimationClip", "AnimationController", "Track", "animation_report", "apply_pose", "blend_poses"]


def _check_times(times: tuple[float, ...]) -> None:
    if not times:
        raise ValueError("a track needs at least one keyframe")
    for time in times:
        if time < 0.0:
            raise ValueError("keyframe times must be non-negative")
    if any(b < a for a, b in itertools.pairwise(times)):
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

    def duration(self) -> float:
        return self.times[-1] if self.times else 0.0

    def sample(self, time: float) -> Vec3 | Quat:
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
        items = []
        for time, value in zip(self.times, self.values):
            if isinstance(value, Vec3):
                items.append({"t": time, "v": [value.x, value.y, value.z]})
            else:
                assert isinstance(value, Quat)
                items.append({"t": time, "q": [value.x, value.y, value.z, value.w]})
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
            times.append(float(key["t"]))
            if "v" in key:
                raw = key["v"]
                values.append(Vec3(float(raw[0]), float(raw[1]), float(raw[2])))
            elif "q" in key:
                raw = key["q"]
                values.append(Quat(float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])))
            else:
                raise ValueError("track key must hold 'v' or 'q'")
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
            if float(time) < 0.0:
                raise ValueError("event times must be non-negative")
            if not isinstance(label, str) or not label.strip():
                raise ValueError("event names must be non-blank strings")
            cleaned.append((float(time), label))
        object.__setattr__(self, "events", tuple(sorted(cleaned, key=lambda item: (item[0], item[1]))))
        for label, tracks in (("position", self.position_tracks), ("rotation", self.rotation_tracks), ("scale", self.scale_tracks)):
            seen: set[str] = set()
            for node_id, track in tracks:
                if node_id in seen:
                    raise ValueError(f"clip has duplicate {label} track for {node_id!r}")
                seen.add(node_id)
                if not isinstance(track, Track):
                    raise TypeError("clip tracks must be Track instances")

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
            if not isinstance(item, dict):
                raise TypeError("clip event must be a mapping")
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
        if restart:
            self.time = 0.0
            self._fresh_start = True

    def crossfade(self, name: str, duration: float) -> None:
        """Blend from the current sampled pose into another clip over duration."""
        if name not in self.clips:
            raise KeyError(f"unknown animation clip {name!r}")
        if duration < 0.0:
            raise ValueError("crossfade duration must be non-negative")
        if not self.current or self.current not in self.clips or duration == 0.0:
            self.play(name)
            return
        moment = self._moment()
        if self.blending and self._blend_duration > 0.0:
            factor = min(1.0, self._blend_elapsed / self._blend_duration)
            source = blend_poses(self._blend_from_pose, self.clips[self.current].sample(moment), factor)
        else:
            source = self.clips[self.current].sample(moment)
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
        if duration > 0.0 and self.loop:
            return self.time % duration
        return min(self.time, duration)

    def advance(self, dt: float) -> dict[str, Transform]:
        pose, _ = self.advance_with_events(dt)
        return pose

    def advance_with_events(self, dt: float) -> tuple[dict[str, Transform], list[str]]:
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
        if not self.current or self.current not in self.clips:
            return {}, []
        clip = self.clips[self.current]
        duration = clip.duration()
        previous = self._moment()
        first_step = self._fresh_start and dt * self.speed > 0.0
        self.time += dt * self.speed
        if dt * self.speed > 0.0:
            self._fresh_start = False
        moment = self._moment()
        wrapped = duration > 0.0 and self.loop and moment < previous and dt > 0.0
        if wrapped:
            fired = clip.events_in_range(previous, duration) + clip.events_in_range(-1.0, moment)
        elif first_step:
            fired = clip.events_in_range(-1.0, moment)
        else:
            fired = clip.events_in_range(previous, moment)
        pose = clip.sample(moment)
        if self.blending:
            self._blend_elapsed += dt * self.speed
            factor = 1.0 if self._blend_duration <= 0.0 else min(1.0, self._blend_elapsed / self._blend_duration)
            if self._blend_from_pose:
                pose = blend_poses(self._blend_from_pose, pose, factor)
            if factor >= 1.0:
                self.blending = False
                self._blend_from_pose = {}
        return pose, fired

def blend_poses(first: dict[str, Transform], second: dict[str, Transform], factor: float) -> dict[str, Transform]:
    """Blend two sampled poses; factor 0 returns first, 1 returns second."""
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


def apply_pose(scene: Scene, pose: dict[str, Transform]) -> list[str]:
    """Write sampled Transforms onto nodes by id or name; return updated ids."""
    index: dict[str, Node] = {}
    for node in scene.traverse():
        if node.id:
            index[node.id] = node
        index.setdefault(node.name, node)
    updated: list[str] = []
    for key, transform in pose.items():
        node = index.get(key)
        if node is None:
            continue
        node.transform = transform
        updated.append(node.id or node.name)
    return sorted(updated)


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
