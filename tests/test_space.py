"""Tests for seeded star systems, orbits and hyperlanes."""

import unittest

from keystone.procedural.space import Galaxy


class GalaxyTest(unittest.TestCase):
    def setUp(self):
        self.galaxy = Galaxy.generate(7)

    def test_same_seed_is_deterministic(self):
        again = Galaxy.generate(7)
        self.assertEqual(self.galaxy.start_id, again.start_id)
        for system_id, system in self.galaxy.systems.items():
            self.assertEqual(system.connections, again.systems[system_id].connections)
            self.assertEqual([body.phase for body in system.bodies], [body.phase for body in again.systems[system_id].bodies])

    def test_every_system_has_a_star_and_planets(self):
        for system in self.galaxy.systems.values():
            self.assertEqual(system.bodies[0].kind, "star")
            self.assertGreaterEqual(len(system.bodies), 4)
            self.assertEqual(len({body.body_id for body in system.bodies}), len(system.bodies))

    def test_hyperlanes_are_symmetric_and_connected(self):
        for system_id, system in self.galaxy.systems.items():
            self.assertTrue(system.connections)
            for neighbour in system.connections:
                self.assertIn(system_id, self.galaxy.system(neighbour).connections)

    def test_orbits_move_over_time_and_stars_stay_put(self):
        system = self.galaxy.system(self.galaxy.start_id)
        star = system.star
        planet = system.bodies[1]
        self.assertEqual(star.position(0.0), (0.0, 0.0, 0.0))
        self.assertNotEqual(planet.position(0.0), planet.position(5.0))

    def test_unknown_system_and_body_are_rejected(self):
        with self.assertRaises(ValueError):
            self.galaxy.system("sys-99")
        with self.assertRaises(ValueError):
            self.galaxy.system(self.galaxy.start_id).body("body-99")

    def test_rejects_tiny_galaxies(self):
        with self.assertRaises(ValueError):
            Galaxy.generate(1, count=1)


if __name__ == "__main__":
    unittest.main()
