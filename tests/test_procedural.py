"""Tests for deterministic noise, heightfield terrain and day/night atmosphere."""

import unittest

from keystone.atmosphere import Atmosphere, apply_atmosphere
from keystone.procedural.noise import fbm, value_noise
from keystone.procedural.terrain import Terrain
from keystone.scene import Scene


class NoiseTest(unittest.TestCase):
    def test_noise_is_deterministic_and_bounded(self):
        self.assertEqual(value_noise(1.25, -3.5, 7), value_noise(1.25, -3.5, 7))
        for x in range(10):
            sample = value_noise(x * 0.7, x * 1.3, 11)
            self.assertGreaterEqual(sample, 0.0)
            self.assertLessEqual(sample, 1.0)

    def test_fbm_changes_with_seed(self):
        self.assertNotEqual(fbm(2.3, 4.1, 1, 5), fbm(2.3, 4.1, 2, 5))

    def test_fbm_is_bounded(self):
        for octave in (1, 3, 6):
            sample = fbm(0.4, 5.2, 42, octave)
            self.assertGreaterEqual(sample, 0.0)
            self.assertLessEqual(sample, 1.0)


class TerrainTest(unittest.TestCase):
    def setUp(self):
        self.terrain = Terrain.generate(1234, size=32)

    def test_same_seed_rebuilds_the_same_grid(self):
        again = Terrain.generate(1234, size=32)
        self.assertEqual(self.terrain.heights, again.heights)
        self.assertEqual(self.terrain.spawn, again.spawn)

    def test_mesh_is_colored_and_faces_up(self):
        mesh = self.terrain.mesh()
        side = self.terrain.size + 1
        self.assertEqual(mesh.vertex_count(), side * side)
        self.assertEqual(len(mesh.colors), side * side)
        self.assertEqual(mesh.triangle_count(), self.terrain.size * self.terrain.size * 2)
        self.assertTrue(all(normal[1] > 0.0 for normal in mesh.normals))

    def test_height_at_grid_point_matches_the_grid(self):
        height = self.terrain.height_at(0.0, 0.0)
        half = self.terrain.size / 2.0
        self.assertAlmostEqual(height, self.terrain.heights[int(half)][int(half)], places=5)

    def test_spawn_and_entrance_are_walkable(self):
        self.assertTrue(self.terrain.is_walkable(*self.terrain.spawn))
        self.assertTrue(self.terrain.is_walkable(*self.terrain.entrance))

    def test_water_and_out_of_bounds_are_not_walkable(self):
        edge = self.terrain.size / 2.0 + 0.1
        self.assertFalse(self.terrain.is_walkable(edge, edge))
        self.assertFalse(self.terrain.is_walkable(10_000.0, 10_000.0))

    def test_normals_are_unit_length(self):
        normal = self.terrain.normal_at(1.0, 2.0)
        self.assertAlmostEqual(normal.length(), 1.0)

    def test_rejects_tiny_grids(self):
        with self.assertRaises(ValueError):
            Terrain.generate(1, size=4)


class AtmosphereTest(unittest.TestCase):
    def test_noon_is_bright_and_midnight_is_dark(self):
        noon = Atmosphere.at(0.5)
        midnight = Atmosphere.at(0.0)
        self.assertGreater(noon.daylight, 0.95)
        self.assertLess(midnight.daylight, 0.05)

    def test_dawn_is_warm(self):
        self.assertGreater(Atmosphere.at(0.25).warm, 0.9)

    def test_apply_updates_scene_light_and_sky(self):
        scene = Scene()
        atmosphere = Atmosphere.at(0.5)
        apply_atmosphere(scene, atmosphere)
        self.assertEqual(scene.sky, atmosphere.sky)
        self.assertEqual(scene.background, atmosphere.horizon)
        self.assertGreater(scene.light.intensity, 0.5)

    def test_atmosphere_rejects_out_of_range_time(self):
        with self.assertRaises(ValueError):
            Atmosphere.at(1.5)


if __name__ == "__main__":
    unittest.main()
