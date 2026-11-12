"""Present a root-motion body on scene nodes.

`RootMotionBody` owns movement and returns an in-place pose; this presenter
owns presentation: a container node follows the body's position and yaw, and
the in-place pose is applied to the container's children. A game creates one
container with the animated hierarchy under it, then calls `step(scene, dt,
colliders)`; movement, collision and pose application stay in sync without
copying transforms by hand.

The container keeps its scale, so a game can size a character once. Nodes in
the pose that are absent from the scene are simply not updated and are left
out of the report.
"""

from __future__ import annotations

from collections.abc import Iterable

from keystone.animation import apply_pose
from keystone.physics import AABB
from keystone.root_motion import RootMotion, root_motion_report
from keystone.root_motion_body import RootMotionBody
from keystone.scene import Node, Scene, Transform

__all__ = ["RootMotionPresenter", "root_motion_presenter_report"]


class RootMotionPresenter:
    """Sync one scene container to a root-motion body and apply its pose."""

    def __init__(self, rig: RootMotionBody, container: Node) -> None:
        if not isinstance(rig, RootMotionBody):
            raise TypeError("root motion presenter needs a RootMotionBody")
        if not isinstance(container, Node):
            raise TypeError("root motion presenter needs a container Node")
        self.rig = rig
        self.container = container
        self.last_updated: list[str] = []
        self.sync()

    def sync(self) -> Node:
        """Place the container at the body position and yaw, keeping its scale."""
        transform = self.container.transform
        self.container.transform = Transform(
            position=self.rig.body.position,
            rotation=self.rig.rotation,
            scale=transform.scale,
        )
        return self.container

    def step(
        self,
        scene: Scene,
        dt: float,
        colliders: Iterable[AABB] = (),
    ) -> tuple[dict[str, Transform], RootMotion]:
        """Advance the rig, sync the container and apply the in-place pose."""
        if not isinstance(scene, Scene):
            raise TypeError("root motion presenter step needs a Scene")
        pose, motion = self.rig.step(dt, colliders)
        self.sync()
        self.last_updated = apply_pose(scene, pose)
        return pose, motion


def root_motion_presenter_report(presenter: RootMotionPresenter) -> dict:
    """Return a JSON-safe summary of a presenter's last step."""
    if not isinstance(presenter, RootMotionPresenter):
        raise TypeError("root_motion_presenter_report needs a RootMotionPresenter")
    rig = presenter.rig
    position = rig.body.position
    return {
        "schema": 1,
        "container": presenter.container.id or presenter.container.name,
        "position": [
            round(position.x, 6),
            round(position.y, 6),
            round(position.z, 6),
        ],
        "yaw": round(rig.yaw, 6),
        "updated": sorted(presenter.last_updated),
        "motion": root_motion_report(rig.last_motion),
    }
