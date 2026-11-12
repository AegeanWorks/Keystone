"""Root motion: extract a root node's delta and bake a pose in place.

Animation clips animate nodes relative to their rest pose. When the animated
node drives a character, the game needs the clip's own displacement: the
position and rotation change of a designated root between two clip times.
`extract_root_motion` returns that delta; `in_place_pose` removes it from a
sampled pose so the visual root stays at a reference transform while the rest
of the body animates.

The functions are pure and deterministic and do not know about characters,
controllers or scenes, so a game can apply the delta to whatever body it owns.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from keystone.animation import AnimationClip
from keystone.math3d import Quat, Vec3
from keystone.scene import Transform

__all__ = [
    "RootMotion",
    "RootMotionPlayer",
    "extract_root_motion",
    "in_place_pose",
    "root_motion_report",
]


def _finite(label: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class RootMotion:
    """A root delta between two clip times: world-space position and rotation."""

    position: Vec3
    rotation: Quat

    def __post_init__(self) -> None:
        if not isinstance(self.position, Vec3):
            raise TypeError("root motion position must be a Vec3")
        if not all(math.isfinite(component) for component in (self.position.x, self.position.y, self.position.z)):
            raise ValueError("root motion position must be finite")
        if not isinstance(self.rotation, Quat):
            raise TypeError("root motion rotation must be a Quat")
        if not all(math.isfinite(component) for component in (self.rotation.w, self.rotation.x, self.rotation.y, self.rotation.z)):
            raise ValueError("root motion rotation must be finite")
        if self.rotation.w ** 2 + self.rotation.x ** 2 + self.rotation.y ** 2 + self.rotation.z ** 2 < 1e-12:
            raise ValueError("root motion rotation must be non-zero")
        object.__setattr__(self, "rotation", self.rotation.normalized())

    @property
    def yaw(self) -> float:
        """Rotation around Y in radians, in the engine's right-handed frame."""
        rotation = self.rotation
        return math.atan2(
            2.0 * (rotation.w * rotation.y + rotation.x * rotation.z),
            1.0 - 2.0 * (rotation.y * rotation.y + rotation.z * rotation.z),
        )


def extract_root_motion(
    clip: AnimationClip,
    node_id: str,
    start: float = 0.0,
    end: float | None = None,
    *,
    planar: bool = False,
) -> RootMotion:
    """Return the root delta between ``start`` and ``end`` clip times.

    Times are clamped to the clip through its tracks, so a range past the
    duration repeats the last key. ``planar`` drops vertical motion, which is
    what a grounded character wants. A clip that does not animate ``node_id``
    raises, because silently returning zero would look like a motionless clip.
    """
    if not isinstance(clip, AnimationClip):
        raise TypeError("extract_root_motion needs an AnimationClip")
    if not isinstance(node_id, str):
        raise TypeError("root motion node id must be a string")
    if not node_id.strip():
        raise ValueError("root motion node id must be a non-blank string")
    if not isinstance(planar, bool):
        raise TypeError("root motion planar flag must be a boolean")
    begin = _finite("root motion start", start)
    if begin < 0.0:
        raise ValueError("root motion start must be non-negative")
    finish = clip.duration() if end is None else _finite("root motion end", end)
    if finish < begin:
        raise ValueError("root motion end must not be before start")
    first = clip.sample(begin)
    second = clip.sample(finish)
    if node_id not in first:
        raise ValueError(f"clip {clip.name!r} does not animate {node_id!r}")
    delta = second[node_id].position - first[node_id].position
    if planar:
        delta = Vec3(delta.x, 0.0, delta.z)
    rotation = (
        second[node_id].rotation.normalized()
        * first[node_id].rotation.normalized().conjugate()
    ).normalized()
    return RootMotion(delta, rotation)


def in_place_pose(
    pose: Mapping[str, Transform],
    node_id: str,
    reference: Transform | None = None,
) -> dict[str, Transform]:
    """Return a copy of ``pose`` with ``node_id`` reset to a reference transform.

    The reference defaults to the identity transform, which is the usual
    "bake root motion into the body" pose. Other nodes keep their transforms
    unchanged and the input mapping is never mutated.
    """
    if not isinstance(pose, Mapping):
        raise TypeError("in_place_pose needs a mapping of node poses")
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("in-place node id must be a non-blank string")
    if node_id not in pose:
        raise ValueError(f"pose has no node {node_id!r}")
    if reference is not None and not isinstance(reference, Transform):
        raise TypeError("in-place reference must be a Transform or None")
    result = dict(pose)
    result[node_id] = Transform() if reference is None else reference
    return result


def root_motion_report(motion: RootMotion) -> dict:
    """Return a JSON-safe summary of one root delta."""
    if not isinstance(motion, RootMotion):
        raise TypeError("root_motion_report needs a RootMotion")
    return {
        "schema": 1,
        "position": [
            round(motion.position.x, 6),
            round(motion.position.y, 6),
            round(motion.position.z, 6),
        ],
        "rotation": [
            round(motion.rotation.w, 6),
            round(motion.rotation.x, 6),
            round(motion.rotation.y, 6),
            round(motion.rotation.z, 6),
        ],
        "yaw": round(motion.yaw, 6),
    }

def _compose(first: RootMotion, second: RootMotion) -> RootMotion:
    """Compose two deltas: apply ``first``, then ``second``."""
    return RootMotion(
        first.position + second.position,
        (second.rotation * first.rotation).normalized(),
    )


class RootMotionPlayer:
    """Advance one clip and return its pose and consumed root delta.

    Unlike `AnimationController`, this player does not blend or manage state
    machines; it owns a single clip's clock and answers the question a
    root-motion game asks every frame: how much did the root move while the
    clip advanced? Looping wraps compose the tail of the old cycle with the
    head of the new one, so a walk cycle reports continuous motion across the
    seam. Playback is forward-only and speed is positive.
    """

    def __init__(
        self,
        clip: AnimationClip,
        node_id: str,
        *,
        speed: float = 1.0,
        loop: bool = True,
        planar: bool = True,
    ) -> None:
        if not isinstance(clip, AnimationClip):
            raise TypeError("root motion player needs an AnimationClip")
        if not isinstance(node_id, str):
            raise TypeError("root motion player node id must be a string")
        if not node_id.strip():
            raise ValueError("root motion player node id must be a non-blank string")
        if node_id not in clip.node_ids():
            raise ValueError(f"clip {clip.name!r} does not animate {node_id!r}")
        rate = _finite("root motion player speed", speed)
        if rate <= 0.0:
            raise ValueError("root motion player speed must be positive")
        if not isinstance(loop, bool):
            raise TypeError("root motion player loop must be a boolean")
        if not isinstance(planar, bool):
            raise TypeError("root motion player planar must be a boolean")
        if clip.duration() <= 0.0:
            raise ValueError("root motion player clip must have positive duration")
        self.clip = clip
        self.node_id = node_id
        self.speed = rate
        self.loop = loop
        self.planar = planar
        self.time = 0.0
        self.looped = False

    @property
    def duration(self) -> float:
        return self.clip.duration()

    @property
    def done(self) -> bool:
        return not self.loop and self.time >= self.duration - 1e-12

    def reset(self) -> None:
        """Return the clip clock to the start."""
        self.time = 0.0
        self.looped = False

    def advance(self, dt: float) -> tuple[dict[str, Transform], RootMotion]:
        """Advance the clip and return its pose at the new time plus the delta."""
        seconds = _finite("root motion player dt", dt)
        if seconds < 0.0:
            raise ValueError("root motion player dt must be non-negative")
        distance = seconds * self.speed
        if distance / max(self.duration, 1e-12) > 1000.0:
            raise ValueError("root motion player dt spans too many loops")
        self.looped = False
        if not self.loop:
            begin = min(self.time, self.duration)
            finish = min(self.time + distance, self.duration)
            self.time = finish
            motion = (
                extract_root_motion(self.clip, self.node_id, begin, finish, planar=self.planar)
                if finish > begin
                else RootMotion(Vec3(), Quat())
            )
            return self.clip.sample(finish), motion
        phase = self.time % self.duration
        end_absolute = phase + distance
        cycles = int(end_absolute // self.duration)
        end = end_absolute - cycles * self.duration
        if cycles == 0:
            motion = extract_root_motion(
                self.clip, self.node_id, phase, end, planar=self.planar
            )
        else:
            motion = extract_root_motion(
                self.clip, self.node_id, phase, self.duration, planar=self.planar
            )
            cycle = extract_root_motion(
                self.clip, self.node_id, 0.0, self.duration, planar=self.planar
            )
            for _ in range(cycles - 1):
                motion = _compose(motion, cycle)
            motion = _compose(
                motion,
                extract_root_motion(self.clip, self.node_id, 0.0, end, planar=self.planar),
            )
            self.looped = True
        self.time += distance
        return self.clip.sample(end), motion

    def report(self, motion: RootMotion) -> dict:
        """Return a JSON-safe summary of the player and one delta."""
        if not isinstance(motion, RootMotion):
            raise TypeError("root motion player report needs a RootMotion")
        return {
            "schema": 1,
            "clip": self.clip.name,
            "node": self.node_id,
            "time": round(self.time % self.duration if self.loop else self.time, 6),
            "looped": self.looped,
            "done": self.done,
            "motion": root_motion_report(motion),
        }
