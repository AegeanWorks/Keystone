"""Tests for scene assembly and the expedition controller."""

import unittest

from keystone.atmosphere import Atmosphere
from keystone.expedition import Expedition
from keystone.sim.world import MoveIntent


class ExpeditionSceneTest(unittest.TestCase):
    def setUp(self):
        self.expedition = Expedition(7, size=32)

    def test_overworld_scene_has_terrain_water_trees_and_a_portal(self):
        names = [node.name for node in self.expedition.scene.traverse()]
        self.assertIn("terrain", names)
        self.assertIn("water", names)
        self.assertIn("trees-trunks", names)
        self.assertIn("trees-crowns", names)
        self.assertIn("rocks", names)
        self.assertIn("path", names)
        self.assertIn("portal-rune", names)
        crowns = next(node for node in self.expedition.scene.traverse() if node.name == "trees-crowns")
        self.assertGreater(crowns.mesh.vertex_count(), 100)

    def test_rocks_leave_the_portal_path_clear(self):
        for x, _, z in self.expedition._rocks.positions:
            self.assertGreaterEqual(self.expedition._distance_to_path(x, z), 1.4)

    def test_camera_starts_at_the_player_eye(self):
        camera = self.expedition.scene.camera
        self.assertEqual(camera.position, self.expedition.world.eye_position())
        self.assertEqual(camera.yaw, self.expedition.world.player.yaw)

    def test_step_advances_time_and_syncs_the_camera(self):
        before = self.expedition.scene.camera.position
        self.expedition.step(0.5, MoveIntent(forward=1.0))
        after = self.expedition.scene.camera.position
        self.assertNotEqual(before, after)
        self.assertEqual(after, self.expedition.world.eye_position())

    def test_entering_the_portal_switches_to_a_dungeon_scene(self):
        self.expedition.world.player.x, self.expedition.world.player.z = self.expedition.world.terrain.entrance
        events = self.expedition.step(0.016, MoveIntent(interact=True))
        names = [node.name for node in self.expedition.scene.traverse()]
        self.assertEqual(self.expedition.world.mode, "dungeon")
        self.assertIn("dungeon-floor", names)
        self.assertIn("dungeon-walls", names)
        self.assertIn("exit-rune", names)
        self.assertAlmostEqual(self.expedition.scene.camera.position.y, 1.7)
        self.assertTrue(any("crypt" in event.lower() for event in events))

    def test_atmosphere_reaches_the_scene(self):
        self.expedition.world.time = 0.0
        self.expedition.step(0.0)
        atmosphere = Atmosphere.at(self.expedition.world.day_fraction)
        self.assertEqual(self.expedition.scene.sky, atmosphere.sky)
        self.assertEqual(self.expedition.scene.background, atmosphere.horizon)

    def test_dungeon_lighting_is_darker_than_daylight(self):
        overworld = self.expedition.scene.light.intensity
        self.expedition.world.player.x, self.expedition.world.player.z = self.expedition.world.terrain.entrance
        self.expedition.step(0.016, MoveIntent(interact=True))
        self.assertLess(self.expedition.scene.light.intensity, overworld)


if __name__ == "__main__":
    unittest.main()
