"""Tests for camera-attached rigs and the reserved overlay layer."""

import math
import unittest

from keystone.camera import MAX_PITCH, PerspectiveCamera
from keystone.camera_rig import CameraRig
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import OVERLAY_LAYER, Node, Scene, Sprite
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


def _position(node: Node) -> Vec3:
    return node.world_matrix().transform_point(Vec3())


class CameraRigTest(unittest.TestCase):
    def test_parts_sit_at_camera_space_offsets(self):
        camera = PerspectiveCamera(position=Vec3(0.0, 0.0, 0.0))
        rig = CameraRig(camera)
        part = rig.attach("grip", position=Vec3(0.25, -0.2, -0.6))
        scene = Scene()
        rig.attach_to(scene)
        rig.sync()
        position = _position(part)
        self.assertAlmostEqual(position.x, 0.25)
        self.assertAlmostEqual(position.y, -0.2)
        self.assertAlmostEqual(position.z, -0.6)

    def test_sync_follows_camera_movement_and_rotation(self):
        camera = PerspectiveCamera(position=Vec3(3.0, 2.0, 1.0), yaw=0.6, pitch=0.25)
        rig = CameraRig(camera)
        part = rig.attach("barrel", position=Vec3(0.0, 0.0, -1.0))
        scene = Scene()
        rig.attach_to(scene)
        rig.sync()
        expected = camera.position + camera.forward() * 1.0
        position = _position(part)
        self.assertLess((position - expected).length(), 1e-9)

    def test_rig_root_orientation_matches_the_lens(self):
        camera = PerspectiveCamera(yaw=-1.1, pitch=0.4)
        rig = CameraRig(camera)
        rig.sync()
        facing = rig.root.transform.rotation.rotate(Vec3(0.0, 0.0, -1.0))
        self.assertLess((facing - camera.forward()).length(), 1e-9)

    def test_sync_clamps_pitch_like_the_camera_does(self):
        camera = PerspectiveCamera()
        rig = CameraRig(camera)
        camera.pitch = MAX_PITCH + 0.5
        rig.sync()
        facing = rig.root.transform.rotation.rotate(Vec3(0.0, 0.0, -1.0))
        self.assertLess((facing - camera.forward()).length(), 1e-9)
        self.assertLessEqual(math.asin(max(-1.0, min(1.0, facing.y))), MAX_PITCH + 1e-12)

    def test_rig_stays_still_until_synced(self):
        """Moving the camera is not enough; sync is the one explicit step."""
        camera = PerspectiveCamera()
        rig = CameraRig(camera)
        part = rig.attach("sight", position=Vec3(0.0, 0.0, -0.5))
        rig.attach_to(Scene())
        rig.sync()
        camera.move(2.0, 0.0, 0.0)
        self.assertAlmostEqual(_position(part).z, -0.5)
        rig.sync()
        self.assertAlmostEqual(_position(part).z, -2.5)

    def test_attached_nodes_use_the_overlay_layer(self):
        rig = CameraRig(PerspectiveCamera())
        part = rig.attach("reticle")
        self.assertEqual(rig.root.layer, OVERLAY_LAYER)
        self.assertEqual(part.layer, OVERLAY_LAYER)
        self.assertIs(part.parent, rig.root)

    def test_attach_carries_payloads_and_flags(self):
        rig = CameraRig(PerspectiveCamera())
        sprite = Sprite(size=0.2)
        part = rig.attach(
            "muzzle",
            mesh=cube(0.1),
            material=Material(),
            sprite=sprite,
            tags=("fx",),
            visible=False,
        )
        self.assertIs(part.sprite, sprite)
        self.assertEqual(part.tags, {"fx"})
        self.assertFalse(part.visible)

    def test_attach_to_is_idempotent(self):
        rig = CameraRig(PerspectiveCamera())
        scene = Scene()
        self.assertIs(rig.attach_to(scene), rig.root)
        self.assertIs(rig.attach_to(scene), rig.root)
        self.assertEqual([node.name for node in scene.root.children], ["camera-rig"])

    def test_rig_layers_survive_a_snapshot_round_trip(self):
        rig = CameraRig(PerspectiveCamera())
        rig.attach("grip", position=Vec3(0.1, -0.1, -0.4))
        scene = Scene()
        rig.attach_to(scene)
        restored = scene_from_dict(scene_to_dict(scene))
        layers = {node.name: node.layer for node in restored.traverse()}
        self.assertEqual(layers["camera-rig"], OVERLAY_LAYER)
        self.assertEqual(layers["grip"], OVERLAY_LAYER)

    def test_rejects_a_non_camera_and_a_non_scene(self):
        with self.assertRaises(TypeError):
            CameraRig(object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CameraRig(PerspectiveCamera()).attach_to(object())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraRig(PerspectiveCamera(), name=" ")

    def test_describe_advertises_the_rig_and_layer(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["camera_rig"])
        self.assertEqual(capabilities["overlay_layer"], OVERLAY_LAYER)


if __name__ == "__main__":
    unittest.main()
