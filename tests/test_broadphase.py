"""Tests for the deterministic spatial-grid broadphase."""

import unittest

from keystone.broadphase import SpatialGrid
from keystone.math3d import Vec3
from keystone.physics import AABB


class SpatialGridTest(unittest.TestCase):
    def test_query_returns_true_overlaps_in_insertion_order(self):
        grid = SpatialGrid(cell_size=2.0)
        first = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        second = AABB(Vec3(1, 0, 0), Vec3(1, 1, 1))
        far = AABB(Vec3(10, 0, 0), Vec3(1, 1, 1))
        grid.insert("first", first)
        grid.insert("second", second)
        grid.insert("far", far)
        self.assertEqual(grid.query(first), ["first", "second"])
        self.assertEqual(grid.query_point(Vec3(1, 0, 0)), ["first", "second"])
        self.assertEqual(grid.pairs(), [("first", "second")])

    def test_same_cell_candidates_are_still_filtered(self):
        grid = SpatialGrid(cell_size=10.0)
        grid.insert("left", AABB(Vec3(0, 0, 0), Vec3(0.5, 0.5, 0.5)))
        grid.insert("right", AABB(Vec3(5, 0, 0), Vec3(0.5, 0.5, 0.5)))
        self.assertEqual(grid.query_point(Vec3(0, 0, 0)), ["left"])
        self.assertEqual(grid.pairs(), [])

    def test_update_moves_a_proxy_and_remove_deletes_it(self):
        grid = SpatialGrid(cell_size=1.0)
        grid.insert("mover", AABB(Vec3(-5, 0, 0), Vec3(0.4, 0.4, 0.4)))
        self.assertEqual(grid.query_point(Vec3(-5, 0, 0)), ["mover"])
        grid.update("mover", AABB(Vec3(5, 0, 0), Vec3(0.4, 0.4, 0.4)))
        self.assertEqual(grid.query_point(Vec3(-5, 0, 0)), [])
        self.assertEqual(grid.query_point(Vec3(5, 0, 0)), ["mover"])
        self.assertTrue(grid.remove("mover"))
        self.assertFalse(grid.remove("mover"))
        self.assertEqual(len(grid), 0)
        self.assertEqual(grid.query_point(Vec3(5, 0, 0)), [])

    def test_negative_coordinates_and_large_boxes_use_multiple_cells(self):
        grid = SpatialGrid(cell_size=1.0)
        large = AABB(Vec3(0, 0, 0), Vec3(3, 3, 3))
        grid.insert("large", large)
        self.assertEqual(grid.query_point(Vec3(-2.5, 2.5, 0.0)), ["large"])
        self.assertEqual(grid.query_point(Vec3(2.9, -2.9, 0.0)), ["large"])
        self.assertEqual(grid.query_point(Vec3(3.1, 0, 0)), [])

    def test_enormous_proxy_is_rejected_instead_of_hanging(self):
        grid = SpatialGrid(cell_size=1.0)
        huge = AABB(Vec3(0, 0, 0), Vec3(1e6, 1e6, 1e6))
        with self.assertRaises(ValueError):
            grid.insert("huge", huge)
        self.assertNotIn("huge", grid)
        with self.assertRaises(ValueError):
            grid.query(huge)

    def test_pairs_are_unique_and_ordered_by_insertion(self):
        grid = SpatialGrid(cell_size=2.0)
        box = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        for key in ("a", "b", "c"):
            grid.insert(key, box)
        self.assertEqual(grid.pairs(), [("a", "b"), ("a", "c"), ("b", "c")])

    def test_clear_and_validation(self):
        with self.assertRaises(ValueError):
            SpatialGrid(cell_size=0.0)
        grid = SpatialGrid(cell_size=1.0)
        grid.insert("a", AABB(Vec3(0, 0, 0), Vec3(1, 1, 1)))
        grid.clear()
        self.assertEqual(len(grid), 0)
        self.assertEqual(grid.pairs(), [])


if __name__ == "__main__":
    unittest.main()
