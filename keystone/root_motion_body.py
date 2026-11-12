"""Drive a character body from a root-motion clip.

`RootMotionPlayer` answers how much the root moved; this class spends that
motion: it converts the horizontal part into the controller's wish velocity,
accumulates the turn, moves the body against colliders, and returns the pose
with the root reset so a game can play it on a container node placed at the
body's position and yaw.

Planar mode is the default because a grounded controller owns vertical
motion; a clip's vertical root motion would fight gravity. Set ``planar=False``
only for clips whose vertical movement the game handles itself.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from keystone.animation import AnimationClip
from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Quat, Vec3
from keystone.physics import AABB
from keystone.root_motion import (
    RootMotion,
    RootMotionPlayer,
    in_place_pose,
    root_motion_report,
)
from keystone.scene import Transform

__all__ = ["RootMotionBody", "root_motion_body_report"]


class RootMotionBody:
    """A controller body advanced by one clip's root motion."""

    def __init__(
        self,
        clip: AnimationClip,
        node_id: str,
        controller: CharacterController,
        body: CharacterBody,
        *,
        speed: float = 1.0,
        loop: bool = True,
        planar: bool = True,
    ) -> None:
        if not isinstance(controller, CharacterController):
            raise TypeError("root motion body needs a CharacterController")
        if not isinstance(body, CharacterBody):
            raise TypeError("root motion body needs a CharacterBody")
        self.player = RootMotionPlayer(
            clip,
            node_id,
            speed=speed,
            loop=loop,
            planar=planar,
        )
        self.controller = controller
        self.body = body
        self.rotation = Quat()
        self.last_pose: dict[str, Transform] = {}
        self.last_motion = RootMotion(Vec3(), Quat())

    @property
    def node_id(self) -> str:
        return self.player.node_id

    @property
    def clip(self) -> AnimationClip:
        return self.player.clip

    @property
    def yaw(self) -> float:
        return RootMotion(Vec3(), self.rotation).yaw

    @property
    def done(self) -> bool:
        return self.player.done

    def reset(self) -> None:
        """Rewind the clip, the accumulated turn and the last motion."""
        self.player.reset()
        self.rotation = Quat()
        self.last_pose = {}
        self.last_motion = RootMotion(Vec3(), Quat())

    def step(
        self,
        dt: float,
        colliders: Iterable[AABB] = (),
    ) -> tuple[dict[str, Transform], RootMotion]:
        """Advance the clip, move the body and return the in-place pose and delta."""
        if isinstance(dt, bool) or not isinstance(dt, (int, float)):
            raise TypeError("root motion body dt must be a real number")
        seconds = float(dt)
        if not math.isfinite(seconds) or seconds <= 0.0:
            raise ValueError("root motion body dt must be finite and positive")
        pose, motion = self.player.advance(seconds)
        velocity = Vec3(
            motion.position.x / seconds,
            0.0,
            motion.position.z / seconds,
        )
        self.body = self.controller.step(self.body, velocity, seconds, colliders)
        self.rotation = (motion.rotation * self.rotation).normalized()
        self.last_motion = motion
        self.last_pose = in_place_pose(pose, self.node_id)
        return self.last_pose, motion


def root_motion_body_report(rig: RootMotionBody) -> dict:
    """Return a JSON-safe summary of a root-motion body."""
    if not isinstance(rig, RootMotionBody):
        raise TypeError("root_motion_body_report needs a RootMotionBody")
    position = rig.body.position
    return {
        "schema": 1,
        "clip": rig.clip.name,
        "node": rig.node_id,
        "done": rig.done,
        "position": [round(position.x, 6), round(position.y, 6), round(position.z, 6)],
        "yaw": round(rig.yaw, 6),
        "motion": root_motion_report(rig.last_motion),
    }
