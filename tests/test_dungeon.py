"""Tests for seeded dungeon generation, field of view and pathfinding."""

import json
import unittest

from keystone.procedural.dungeon import Dungeon, DungeonGenerator, Room, Tile

WALL_MAP = (
    "#######",
    "#.....#",
    "#.....#",
    "#.....#",
    "#.....#",
    "#.....#",
    "#######",
)


class DungeonGenerationTest(unittest.TestCase):
    def setUp(self):
        self.generator = DungeonGenerator(width=33, height=21, max_rooms=8)
        self.dungeon = self.generator.generate(42)

    def test_same_seed_builds_the_same_dungeon(self):
        again = self.generator.generate(42)
        self.assertEqual(self.dungeon.tiles, again.tiles)
        self.assertEqual(self.dungeon.spawn, again.spawn)
        self.assertEqual(self.dungeon.exit, again.exit)

    def test_different_seeds_differ(self):
        other = self.generator.generate(77)
        self.assertNotEqual(self.dungeon.tiles, other.tiles)

    def test_spawn_and_exit_are_walkable(self):
        self.assertTrue(self.dungeon.is_walkable(*self.dungeon.spawn))
        self.assertTrue(self.dungeon.is_walkable(*self.dungeon.exit))

    def test_exit_is_reachable_from_spawn(self):
        path = self.dungeon.find_path(self.dungeon.spawn, self.dungeon.exit)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], self.dungeon.spawn)
        self.assertEqual(path[-1], self.dungeon.exit)

    def test_to_dict_is_json_serializable(self):
        payload = json.loads(json.dumps(self.dungeon.to_dict()))
        self.assertEqual(payload["width"], 33)
        self.assertEqual(payload["exit"], list(self.dungeon.exit))

    def test_generator_rejects_tiny_maps(self):
        with self.assertRaises(ValueError):
            DungeonGenerator(width=8, height=8)


class DungeonVisibilityTest(unittest.TestCase):
    def setUp(self):
        tiles = [[Tile.WALL for _ in range(7)] for _ in range(7)]
        for y in range(1, 6):
            for x in range(1, 6):
                tiles[y][x] = Tile.FLOOR
        for y in range(7):
            tiles[y][3] = Tile.WALL
        self.dungeon = Dungeon(
            width=7,
            height=7,
            seed=0,
            tiles=tiles,
            rooms=[Room(1, 1, 5, 5)],
            spawn=(1, 1),
            exit=(5, 5),
        )

    def test_fov_contains_the_observer_and_near_floor(self):
        visible = self.dungeon.compute_fov(1, 1, radius=6)
        self.assertIn((1, 1), visible)
        self.assertIn((2, 2), visible)

    def test_fov_is_blocked_by_a_wall(self):
        visible = self.dungeon.compute_fov(1, 1, radius=6)
        self.assertNotIn((4, 1), visible)

    def test_walls_and_out_of_bounds_are_not_walkable(self):
        self.assertFalse(self.dungeon.is_walkable(0, 0))
        self.assertFalse(self.dungeon.is_walkable(-1, 3))
        self.assertFalse(self.dungeon.find_path((1, 1), (0, 0)))


if __name__ == "__main__":
    unittest.main()
