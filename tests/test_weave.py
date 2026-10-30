"""Tests for the Weft-style Hamiltonian weave generator."""

import unittest

from keystone.procedural.dungeon import Tile
from keystone.procedural.weave import WeaveLayout


class WeaveLayoutTest(unittest.TestCase):
    def setUp(self):
        self.weave = WeaveLayout.generate(8)

    def test_path_covers_every_room_exactly_once(self):
        self.assertEqual(len(self.weave.path), self.weave.cols * self.weave.rows)
        self.assertEqual(len(set(self.weave.path)), len(self.weave.path))

    def test_consecutive_rooms_are_orthogonal(self):
        for first, second in zip(self.weave.path, self.weave.path[1:]):
            self.assertEqual(abs(first[0] - second[0]) + abs(first[1] - second[1]), 1)

    def test_segments_partition_the_path(self):
        flattened = [point for segment in self.weave.segments for point in segment]
        self.assertEqual(tuple(flattened), self.weave.path)
        self.assertTrue(all(len(segment) >= 3 for segment in self.weave.segments))

    def test_same_seed_is_deterministic(self):
        self.assertEqual(self.weave.path, WeaveLayout.generate(8).path)
        self.assertEqual(self.weave.segments, WeaveLayout.generate(8).segments)
        self.assertNotEqual(self.weave.path, WeaveLayout.generate(9).path)

    def test_dungeon_is_fully_connected(self):
        dungeon = self.weave.to_dungeon()
        self.assertTrue(dungeon.is_walkable(*dungeon.spawn))
        self.assertTrue(dungeon.is_walkable(*dungeon.exit))
        self.assertIsNotNone(dungeon.find_path(dungeon.spawn, dungeon.exit))
        self.assertEqual(len(dungeon.rooms), self.weave.cols * self.weave.rows)
        self.assertEqual(dungeon.tiles[dungeon.exit[1]][dungeon.exit[0]], Tile.EXIT)

    def test_room_floors_carry_thread_colors(self):
        room = self.weave.room_for(self.weave.path[0])
        color = self.weave.floor_color(room.x, room.y)
        self.assertIsNotNone(color)
        self.assertEqual(color, self.weave.colors[0])
        self.assertIsNone(self.weave.floor_color(0, 0))

    def test_rejects_tiny_layouts(self):
        with self.assertRaises(ValueError):
            WeaveLayout.generate(1, cols=2, rows=2, threads=3)


if __name__ == "__main__":
    unittest.main()
