"""Tests for the space scene and controller."""

import unittest

from keystone.math3d import Vec3
from keystone.sim.world import MoveIntent
from keystone.space import GATE
from keystone.space_expedition import SpaceExpedition


class SpaceExpeditionTest(unittest.TestCase):
    def setUp(self):
        self.expedition = SpaceExpedition(7)

    def test_scene_has_starfield_bodies_and_a_gate(self):
        names = [node.name for node in self.expedition.scene.traverse()]
        self.assertIn("starfield", names)
        self.assertIn("jump-gate", names)
        self.assertGreaterEqual(sum(name.startswith("body-") for name in names), 5)

    def test_camera_follows_the_ship(self):
        before = self.expedition.scene.camera.position
        self.expedition.step(0.5, MoveIntent(forward=1.0))
        after = self.expedition.scene.camera.position
        self.assertNotEqual(before, after)
        self.assertEqual(after, self.expedition.world.ship.position)

    def test_scanning_a_body_updates_the_scene_and_status(self):
        body = self.expedition.world.system.bodies[1]
        bx, by, bz = body.position(self.expedition.world.time)
        self.expedition.world.ship.position = Vec3(bx, by, bz)
        self.expedition.step(0.0, MoveIntent(scan=True))
        self.assertTrue(body.scanned)
        self.assertIn("scanned 1/", self.expedition.status())

    def test_jump_rebuilds_the_system_scene(self):
        original = self.expedition.world.system_id
        self.expedition.world.ship.position = GATE
        self.expedition.step(0.0, MoveIntent(jump=True))
        self.assertNotEqual(self.expedition.world.system_id, original)
        names = [node.name for node in self.expedition.scene.traverse()]
        self.assertIn("jump-gate", names)
        self.assertEqual(self.expedition.scene.camera.position, Vec3(0.0, 0.0, 22.0))


if __name__ == "__main__":
    unittest.main()
