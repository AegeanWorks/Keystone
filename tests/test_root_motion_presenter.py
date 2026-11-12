"""Tests for presenting a root-motion body on scene nodes."""

import math
import unittest

from keystone.animation import AnimationClip, Track
from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Quat, Vec3
from keystone.plugin import describe_game
from keystone.root_motion_body import RootMotionBody
from keystone.root_motion_presenter import (
    RootMotionPresenter,
    root_motion_presenter_report,
)
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene


def _walk(units: float = 2.0) -> AnimationClip:
    return AnimationClip(
        name="walk",
        position_tracks=(
            ("hips", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(0.0, 0.0, units)))),
            ("arm", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(0.0, 1.0, 0.0)))),
        ),
    )


def _turn() -> AnimationClip:
    return AnimationClip(
        name="turn",
        rotation_tracks=(
            ("hips", Track(times=(0.0, 1.0), values=(Quat(), Quat.from_axis_angle(Vec3(0.0, 1.0, 0.0), math.pi / 2)))),
        ),
    )


def _scene() -> tuple[Scene, Node, Node, Node]:
    scene = Scene()
    container = Node("player", id="player")
    scene.add(container)
    root = Node("hips", id="hips", parent=container)
    arm = Node("arm", id="arm", parent=container)
    return scene, container, root, arm


def _rig(clip=None) -> RootMotionBody:
    return RootMotionBody(
        clip or _walk(),
        "hips",
        CharacterController(gravity=0.0),
        CharacterBody(position=Vec3()),
    )


class RootMotionPresenterTest(unittest.TestCase):
    def test_the_container_follows_the_body_and_children_stay_in_place(self):
        scene, container, root, arm = _scene()
        presenter = RootMotionPresenter(_rig(), container)
        presenter.step(scene, 0.5)
        self.assertAlmostEqual(container.transform.position.z, 1.0)
        self.assertEqual(root.transform.position, Vec3())
        self.assertAlmostEqual(arm.transform.position.y, 0.5)

    def test_turning_rotates_the_container(self):
        scene, container, _root, _arm = _scene()
        presenter = RootMotionPresenter(_rig(_turn()), container)
        for _ in range(4):
            presenter.step(scene, 0.25)
        facing = container.transform.rotation.rotate(Vec3(0.0, 0.0, -1.0))
        self.assertAlmostEqual(facing.x, -1.0, places=6)

    def test_sync_does_not_advance_the_clip(self):
        scene, container, _root, _arm = _scene()
        rig = _rig()
        presenter = RootMotionPresenter(rig, container)
        presenter.step(scene, 0.5)
        presenter.sync()
        before = rig.player.time
        presenter.sync()
        self.assertEqual(rig.player.time, before)
        self.assertAlmostEqual(container.transform.position.z, 1.0)

    def test_scale_is_preserved(self):
        scene, container, _root, _arm = _scene()
        container.transform = container.transform.__class__(
            position=Vec3(5.0, 6.0, 7.0),
            rotation=Quat(),
            scale=Vec3(2.0, 2.0, 2.0),
        )
        presenter = RootMotionPresenter(_rig(), container)
        presenter.step(scene, 0.5)
        self.assertEqual(container.transform.scale, Vec3(2.0, 2.0, 2.0))
        self.assertAlmostEqual(container.transform.position.z, 1.0)

    def test_report_names_the_container_and_updated_nodes(self):
        scene, container, _root, _arm = _scene()
        presenter = RootMotionPresenter(_rig(), container)
        presenter.step(scene, 0.5)
        report = root_motion_presenter_report(presenter)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["container"], "player")
        self.assertEqual(sorted(report["updated"]), ["arm", "hips"])
        self.assertAlmostEqual(report["position"][2], 1.0)
        self.assertAlmostEqual(report["yaw"], 0.0)
        self.assertIn("motion", report)

    def test_colliders_stop_the_container(self):
        from keystone.physics import AABB

        scene, container, _root, _arm = _scene()
        presenter = RootMotionPresenter(_rig(), container)
        wall = AABB(Vec3(0.0, 0.0, 1.5), Vec3(1.0, 1.0, 0.5))
        for _ in range(20):
            presenter.step(scene, 0.25, [wall])
        self.assertLess(container.transform.position.z, 1.0)

    def test_missing_pose_nodes_are_reported_as_not_updated(self):
        scene = Scene()
        container = Node("player", id="player")
        scene.add(container)
        presenter = RootMotionPresenter(_rig(), container)
        presenter.step(scene, 0.5)
        self.assertEqual(root_motion_presenter_report(presenter)["updated"], [])

    def test_validation(self):
        scene, container, _root, _arm = _scene()
        with self.assertRaises(TypeError):
            RootMotionPresenter(object(), container)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            RootMotionPresenter(_rig(), object())  # type: ignore[arg-type]
        presenter = RootMotionPresenter(_rig(), container)
        with self.assertRaises(TypeError):
            presenter.step(object(), 0.5)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            presenter.step(scene, 0.0)
        with self.assertRaises(TypeError):
            root_motion_presenter_report(object())  # type: ignore[arg-type]

    def test_describe_advertises_the_presenter(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["root_motion_presenter"])


if __name__ == "__main__":
    unittest.main()
