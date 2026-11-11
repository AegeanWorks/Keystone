"""Camera-attached scene content: a rig whose root follows the camera pose.

A rig solves the viewmodel problem every first-person game has: parts that
belong to the lens, not the level. Instead of hand-computing world transforms
from the camera basis, a game attaches ordinary nodes with camera-space
offsets, and ``sync()`` copies the camera pose onto the rig root.

Camera space here matches the rest of the engine: ``+X`` right, ``+Y`` up,
``-Z`` forward. Attached nodes live on the reserved ``OVERLAY_LAYER``, which
the renderer draws after a depth clear so level geometry cannot cut through
them; snapshots, prefabs and the editor already carry the layer, so nothing
extra is needed to persist a rig.

Call ``sync()`` after moving the camera and before rendering. The engine owns
no hook into game-owned objects, so the game owns that one line, and moving a
camera without syncing is visible as a stale rig rather than silent magic.
"""

from __future__ import annotations

from collections.abc import Iterable

from keystone.camera import MAX_PITCH, PerspectiveCamera
from keystone.math3d import Quat, Vec3
from keystone.scene import OVERLAY_LAYER, Node, Scene, Transform

__all__ = ["CameraRig"]


class CameraRig:
    """A root node that follows one perspective camera, plus camera-space parts.

    The root is an ordinary scene node named ``camera-rig`` on the overlay
    layer. Every attached node is its child, so a part's local transform is a
    camera-space offset: ``Vec3(0.27, -0.21, -0.6)`` puts it to the right,
    below and in front of the eye.
    """

    def __init__(self, camera: PerspectiveCamera, name: str = "camera-rig") -> None:
        if not isinstance(camera, PerspectiveCamera):
            raise TypeError("camera rig needs a PerspectiveCamera")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("camera rig name must be a non-blank string")
        self.camera = camera
        self.root = Node(name, layer=OVERLAY_LAYER)

    def attach_to(self, scene: Scene) -> Node:
        """Add the rig root to a scene once and return it."""
        if not isinstance(scene, Scene):
            raise TypeError("camera rig attaches to a Scene")
        if self.root.parent is scene.root:
            return self.root
        if self.root.parent is not None:
            raise ValueError("camera rig root is already attached to another parent")
        scene.add(self.root)
        return self.root

    def attach(
        self,
        name: str,
        *,
        position: Vec3 | None = None,
        rotation: Quat | None = None,
        scale: Vec3 | None = None,
        mesh: object | None = None,
        material: object | None = None,
        sprite: object | None = None,
        visible: bool = True,
        tags: Iterable[str] = (),
    ) -> Node:
        """Attach one part at a camera-space offset and return it."""
        node = Node(
            name,
            transform=Transform(
                position=Vec3(0.0, 0.0, 0.0) if position is None else position,
                rotation=Quat() if rotation is None else rotation,
                scale=Vec3(1.0, 1.0, 1.0) if scale is None else scale,
            ),
            mesh=mesh,
            material=material,
            sprite=sprite,
            visible=visible,
            tags=set(tags),
            layer=OVERLAY_LAYER,
            parent=self.root,
        )
        return node

    def sync(self) -> Node:
        """Copy the camera pose onto the rig root and return it."""
        camera = self.camera
        pitch = max(-MAX_PITCH, min(MAX_PITCH, camera.pitch))
        yaw_only = Quat.from_axis_angle(Vec3.UP, -camera.yaw)
        pitch_only = Quat.from_axis_angle(Vec3(1.0, 0.0, 0.0), pitch)
        self.root.transform = Transform(
            position=camera.position,
            rotation=(yaw_only * pitch_only).normalized(),
            scale=self.root.transform.scale,
        )
        return self.root
