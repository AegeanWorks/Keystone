"""Tests for space flight, scanning and hyperlane jumps."""

import unittest

from keystone.math3d import Vec3
from keystone.procedural.space import Galaxy
from keystone.sim.world import MoveIntent
from keystone.space import GATE, SpaceWorld


class SpaceWorldTest(unittest.TestCase):
    def setUp(self):
        self.world = SpaceWorld(7)

    def test_seeded_galaxy_and_hash(self):
        self.assertEqual(self.world.state_hash(), SpaceWorld(7).state_hash())
        self.assertNotEqual(self.world.state_hash(), SpaceWorld(8).state_hash())

    def test_forward_flight_moves_the_ship(self):
        before = self.world.ship.position
        self.world.step(1.0, MoveIntent(forward=1.0))
        self.assertGreater((self.world.ship.position - before).length(), 5.0)

    def test_nearby_body_scan_adds_credits_and_progress(self):
        body = self.world.system.bodies[1]
        bx, by, bz = body.position(self.world.time)
        self.world.ship.position = Vec3(bx, by, bz)
        self.world.step(0.0, MoveIntent(scan=True))
        self.assertTrue(body.scanned)
        self.assertGreater(self.world.credits, 0)
        self.assertEqual(self.world.scanned_count, 1)

    def test_scan_out_of_range_does_nothing(self):
        self.world.ship.position = Vec3(80.0, 0.0, 0.0)
        self.world.step(0.0, MoveIntent(scan=True))
        self.assertEqual(self.world.scanned_count, 0)
        self.assertIn("No unscanned", " ".join(self.world.messages))

    def test_survey_completion_reports_the_gate(self):
        for body in self.world.system.bodies:
            bx, by, bz = body.position(self.world.time)
            self.world.ship.position = Vec3(bx, by, bz)
            self.world.step(0.0, MoveIntent(scan=True))
        self.assertTrue(self.world.complete)
        self.assertIn("survey complete", " ".join(self.world.messages))

    def test_jump_requires_gate_and_changes_system(self):
        original = self.world.system_id
        self.world.step(0.0, MoveIntent(jump=True))
        self.assertEqual(self.world.system_id, original)
        self.world.ship.position = GATE
        self.world.step(0.0, MoveIntent(jump=True))
        self.assertNotEqual(self.world.system_id, original)
        self.assertEqual(self.world.ship.position, Vec3(0.0, 0.0, 22.0))

    def test_negative_dt_is_rejected(self):
        with self.assertRaises(ValueError):
            self.world.step(-0.1)

    def test_galaxy_is_connected(self):
        galaxy = Galaxy.generate(7)
        for system in galaxy.systems.values():
            self.assertTrue(system.connections)


if __name__ == "__main__":
    unittest.main()
