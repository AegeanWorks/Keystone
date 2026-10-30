"""Tests for the deterministic expedition simulation core."""

import math
import unittest

from keystone.combat import ENEMY_TYPES, Enemy
from keystone.math3d import Vec3
from keystone.sim.world import MoveIntent, World


class WorldDeterminismTest(unittest.TestCase):
    def test_same_seed_and_actions_produce_the_same_hash(self):
        first = World(7, size=32)
        second = World(7, size=32)
        action = MoveIntent(forward=1.0, turn=0.3)
        for _ in range(20):
            first.step(1.0 / 60.0, action)
            second.step(1.0 / 60.0, action)
        self.assertEqual(first.state_hash(), second.state_hash())
        self.assertEqual(first.snapshot(), second.snapshot())

    def test_different_seed_produces_a_different_world(self):
        self.assertNotEqual(World(7, size=32).state_hash(), World(8, size=32).state_hash())
        self.assertNotEqual(World(7, size=32).terrain.heights, World(8, size=32).terrain.heights)

    def test_auto_layout_uses_crypt_for_odd_and_weave_for_even_seeds(self):
        self.assertEqual(World(7, size=32).layout, "crypt")
        weave = World(8, size=32)
        self.assertEqual(weave.layout, "weave")
        self.assertIsNotNone(weave.weave)
        self.assertIsNotNone(weave.snapshot()["weave"])
        self.assertIsNone(World(7, size=32).snapshot()["weave"])

    def test_forced_weave_layout_reaches_an_exit(self):
        world = World(7, size=32, layout="weave")
        self.assertEqual(world.layout, "weave")
        self.assertTrue(world.dungeon.is_walkable(*world.dungeon.spawn))
        self.assertIsNotNone(world.dungeon.find_path(world.dungeon.spawn, world.dungeon.exit))

    def test_invalid_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            World(7, size=32, layout="maze")

    def test_hash_changes_when_the_player_moves(self):
        world = World(7, size=32)
        before = world.state_hash()
        world.step(0.5, MoveIntent(forward=1.0))
        self.assertNotEqual(before, world.state_hash())


class WorldMovementTest(unittest.TestCase):
    def setUp(self):
        self.world = World(7, size=32)

    def test_eye_height_follows_the_terrain(self):
        eye = self.world.eye_position()
        expected = self.world.terrain.height_at(self.world.player.x, self.world.player.z) + 1.75
        self.assertAlmostEqual(eye.y, expected, places=4)
        self.assertEqual(eye.x, self.world.player.x)
        self.assertEqual(eye.z, self.world.player.z)

    def test_forward_moves_the_player(self):
        before = Vec3(self.world.player.x, 0.0, self.world.player.z)
        self.world.step(0.5, MoveIntent(forward=1.0))
        after = Vec3(self.world.player.x, 0.0, self.world.player.z)
        self.assertGreater((after - before).length(), 0.5)

    def test_pitch_is_clamped(self):
        self.world.step(0.1, MoveIntent(pitch=10.0))
        self.assertLessEqual(abs(self.world.player.pitch), math.radians(89.0) + 1e-9)

    def test_day_fraction_advances_with_time(self):
        before = self.world.day_fraction
        self.world.step(10.0)
        self.assertGreater(self.world.day_fraction, before)

    def test_negative_dt_is_rejected(self):
        with self.assertRaises(ValueError):
            self.world.step(-0.1)

    def test_death_respawns_at_the_safe_point(self):
        self.world.combat.player_hp = 1.0
        self.world.combat.enemies = [
            Enemy(ENEMY_TYPES["crawler"], self.world.player.x + 0.2, self.world.player.z, 26.0, 26.0)
        ]
        self.world.step(1.0)
        self.assertEqual(self.world.combat.player_hp, self.world.combat.max_hp)
        self.assertFalse(self.world.combat.dead)
        self.assertIn("fell", " ".join(self.world.messages))


class WorldModeTest(unittest.TestCase):
    def setUp(self):
        self.world = World(7, size=32)

    def _stand_at_entrance(self):
        self.world.player.x, self.world.player.z = self.world.terrain.entrance

    def _solve_light_lock(self):
        self.world.light_lock.set_orientation(-1, 0, "\\")
        self.world.light_lock.set_orientation(-1, 2, "/")

    def _complete_network(self):
        for terminal in self.world.network.terminals:
            while not terminal.hacked:
                self.world.network.hack(terminal.terminal_id)

    def test_portal_is_sealed_until_the_light_lock_is_solved(self):
        self.world.player.x = self.world.terrain.entrance[0] + 2.5
        self.world.player.z = self.world.terrain.entrance[1] + 0.5
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertEqual(self.world.mode, "overworld")
        self.assertIn("sealed", " ".join(self.world.messages))
        self._solve_light_lock()
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertEqual(self.world.mode, "dungeon")

    def test_mirror_rotation_changes_the_lock(self):
        self.world.player.x = self.world.terrain.entrance[0] - 1.0
        self.world.player.z = self.world.terrain.entrance[1]
        version = self.world.light_lock.version
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertGreater(self.world.light_lock.version, version)
        self.assertIn("Mirror turned", " ".join(self.world.messages))

    def test_interacting_at_the_portal_enters_the_dungeon(self):
        self._solve_light_lock()
        self._stand_at_entrance()
        self.assertTrue(self.world.near_entrance)
        events = self.world.step(0.016, MoveIntent(interact=True))
        self.assertEqual(self.world.mode, "dungeon")
        self.assertTrue(any("crypt" in event.lower() for event in events))
        self.assertEqual(
            (self.world.player.x, self.world.player.z),
            (self.world.dungeon.spawn[0] + 0.5, self.world.dungeon.spawn[1] + 0.5),
        )

    def test_dungeon_walls_block_movement(self):
        self._solve_light_lock()
        self._stand_at_entrance()
        self.world.step(0.016, MoveIntent(interact=True))
        for _ in range(300):
            self.world.step(1.0 / 60.0, MoveIntent(forward=1.0))
        tile_x = math.floor(self.world.player.x)
        tile_y = math.floor(self.world.player.z)
        self.assertTrue(self.world.dungeon.is_walkable(tile_x, tile_y))

    def test_exit_returns_to_the_overworld_portal(self):
        self._solve_light_lock()
        self._stand_at_entrance()
        self.world.step(0.016, MoveIntent(interact=True))
        self.world.player.x = self.world.dungeon.exit[0] + 0.5
        self.world.player.z = self.world.dungeon.exit[1] + 0.5
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertEqual(self.world.mode, "dungeon")
        self.assertIn("sealed", " ".join(self.world.messages))
        self._complete_network()
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertEqual(self.world.mode, "overworld")
        self.assertTrue(self.world.near_entrance)

    def test_hacking_a_terminal_advances_the_network(self):
        self._solve_light_lock()
        self._stand_at_entrance()
        self.world.step(0.016, MoveIntent(interact=True))
        terminal = self.world.network.terminals[0]
        self.world.player.x = terminal.x
        self.world.player.z = terminal.z
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertGreater(terminal.progress, 0.0)
        self.assertGreater(self.world.network.alert, 0.0)

    def test_high_alert_spawns_a_netwatch_hunter(self):
        self._solve_light_lock()
        self._stand_at_entrance()
        self.world.step(0.016, MoveIntent(interact=True))
        for terminal in self.world.network.terminals[:2]:
            self.world.player.x = terminal.x
            self.world.player.z = terminal.z
            for _ in range(4):
                self.world.step(0.016, MoveIntent(interact=True))
        self.assertGreaterEqual(self.world.network.alert, 50.0)
        self.assertIn("NetWatch", " ".join(self.world.messages))

    def test_interacting_away_from_the_portal_does_nothing(self):
        self.world.player.x = self.world.terrain.spawn[0]
        self.world.player.z = self.world.terrain.spawn[1]
        self.world.step(0.016, MoveIntent(interact=True))
        self.assertEqual(self.world.mode, "overworld")


if __name__ == "__main__":
    unittest.main()
