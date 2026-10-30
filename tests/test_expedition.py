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

    def test_light_lock_scene_has_emitter_receiver_mirrors_and_beams(self):
        names = [node.name for node in self.expedition.scene.traverse()]
        self.assertIn("light-emitter", names)
        self.assertIn("light-receiver", names)
        self.assertIn("light-dye", names)
        self.assertIn("light-beams", names)
        self.assertGreaterEqual(sum(name.startswith("light-mirror-") for name in names), 2)

    def test_rotating_a_mirror_rebuilds_the_light_scene(self):
        before = self.expedition.world.light_lock.version
        self.expedition.world.player.x = self.expedition.world.terrain.entrance[0] - 1.0
        self.expedition.world.player.z = self.expedition.world.terrain.entrance[1]
        self.expedition.step(0.016, MoveIntent(interact=True))
        self.assertGreater(self.expedition.world.light_lock.version, before)
        names = [node.name for node in self.expedition.scene.traverse()]
        self.assertIn("light-beams", names)

    def test_camera_starts_at_the_player_eye(self):
        camera = self.expedition.scene.camera
        self.assertEqual(camera.position, self.expedition.world.eye_position())
        self.assertEqual(camera.yaw, self.expedition.world.player.yaw)

    def test_enemy_nodes_match_the_combat_state(self):
        living = [enemy for enemy in self.expedition.world.combat.enemies if enemy.hp > 0]
        nodes = [node for node in self.expedition.scene.traverse() if node.name.startswith("enemy-")]
        self.assertEqual(len(nodes), len(living))
        self.expedition.step(0.2)
        living = [enemy for enemy in self.expedition.world.combat.enemies if enemy.hp > 0]
        nodes = [node for node in self.expedition.scene.traverse() if node.name.startswith("enemy-")]
        self.assertEqual(len(nodes), len(living))

    def test_step_advances_time_and_syncs_the_camera(self):
        before = self.expedition.scene.camera.position
        self.expedition.step(0.5, MoveIntent(forward=1.0))
        after = self.expedition.scene.camera.position
        self.assertNotEqual(before, after)
        self.assertEqual(after, self.expedition.world.eye_position())

    def _solve_light_lock(self):
        self.expedition.world.light_lock.set_orientation(-1, 0, "\\")
        self.expedition.world.light_lock.set_orientation(-1, 2, "/")

    def test_entering_the_portal_switches_to_a_dungeon_scene(self):
        self._solve_light_lock()
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

    def test_weave_layout_enters_a_colored_dungeon(self):
        expedition = Expedition(8, size=32, layout="weave")
        self._solve_light_lock_for(expedition)
        expedition.world.player.x, expedition.world.player.z = expedition.world.terrain.entrance
        expedition.step(0.016, MoveIntent(interact=True))
        names = [node.name for node in expedition.scene.traverse()]
        self.assertEqual(expedition.world.mode, "dungeon")
        self.assertEqual(expedition.world.layout, "weave")
        self.assertIn("dungeon-floor", names)
        room = expedition.world.weave.room_for(expedition.world.weave.path[0])
        self.assertIsNotNone(expedition.world.weave.floor_color(room.x, room.y))

    def _solve_light_lock_for(self, expedition):
        expedition.world.light_lock.set_orientation(-1, 0, "\\")
        expedition.world.light_lock.set_orientation(-1, 2, "/")

    def test_dungeon_lighting_is_darker_than_daylight(self):
        overworld = self.expedition.scene.light.intensity
        self._solve_light_lock()
        self.expedition.world.player.x, self.expedition.world.player.z = self.expedition.world.terrain.entrance
        self.expedition.step(0.016, MoveIntent(interact=True))
        self.assertLess(self.expedition.scene.light.intensity, overworld)


if __name__ == "__main__":
    unittest.main()
