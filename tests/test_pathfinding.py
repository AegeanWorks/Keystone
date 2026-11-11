"""Tests for deterministic grid pathfinding."""

import math
import unittest

from keystone.pathfinding import NavGrid, PathResult, find_path, path_report
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _open_grid(width: int = 5, height: int = 5, blocked=()) -> NavGrid:
    return NavGrid(width, height, frozenset(blocked))


class NavGridTest(unittest.TestCase):
    def test_open_and_blocked_cells(self):
        grid = _open_grid(4, 3, {(1, 1)})
        self.assertEqual(grid.width, 4)
        self.assertEqual(grid.height, 3)
        self.assertTrue(grid.is_open((0, 0)))
        self.assertFalse(grid.is_open((1, 1)))
        self.assertTrue(grid.in_bounds((3, 2)))
        self.assertFalse(grid.in_bounds((4, 2)))
        self.assertFalse(grid.in_bounds((-1, 0)))

    def test_grid_is_immutable(self):
        grid = _open_grid(4, 3)
        walled = grid.with_blocked((1, 1))
        self.assertTrue(grid.is_open((1, 1)))
        self.assertFalse(walled.is_open((1, 1)))
        self.assertTrue(walled.with_open((1, 1)).is_open((1, 1)))

    def test_malformed_grids_are_rejected(self):
        with self.assertRaises(ValueError):
            NavGrid(0, 3)
        with self.assertRaises(ValueError):
            NavGrid(3, -1)
        with self.assertRaises(ValueError):
            NavGrid(True, 3)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            NavGrid(3, 3, frozenset({(3, 0)}))
        with self.assertRaises(TypeError):
            NavGrid(3, 3, [("a", "b")])  # type: ignore[arg-type]


class FindPathTest(unittest.TestCase):
    def test_straight_path_on_an_open_grid(self):
        result = find_path(_open_grid(5, 3), (0, 1), (4, 1))
        self.assertTrue(result.found)
        self.assertEqual(result.path, ((0, 1), (1, 1), (2, 1), (3, 1), (4, 1)))
        self.assertEqual(result.cost, 4.0)
        self.assertGreater(result.expanded, 0)

    def test_path_starts_and_ends_on_the_goal(self):
        result = find_path(_open_grid(), (0, 0), (4, 4))
        self.assertEqual(result.path[0], (0, 0))
        self.assertEqual(result.path[-1], (4, 4))
        self.assertEqual(len(result.path) - 1, int(result.cost))

    def test_walks_around_a_wall(self):
        grid = _open_grid(5, 5, {(2, 0), (2, 1), (2, 2), (2, 3)})
        result = find_path(grid, (1, 2), (3, 2))
        self.assertTrue(result.found)
        self.assertTrue(all(cell not in grid.blocked for cell in result.path))
        self.assertIn((2, 4), result.path)
        self.assertEqual(result.cost, 6.0)

    def test_unreachable_goal_is_not_found(self):
        grid = _open_grid(5, 5, {(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)})
        result = find_path(grid, (0, 2), (4, 2))
        self.assertFalse(result.found)
        self.assertEqual(result.path, ())
        self.assertEqual(result.cost, 0.0)

    def test_start_equal_to_goal(self):
        result = find_path(_open_grid(), (2, 2), (2, 2))
        self.assertTrue(result.found)
        self.assertEqual(result.path, ((2, 2),))
        self.assertEqual(result.expanded, 1)

    def test_diagonal_paths_are_shorter(self):
        straight = find_path(_open_grid(6, 6), (0, 0), (3, 3))
        diagonal = find_path(_open_grid(6, 6), (0, 0), (3, 3), diagonal=True)
        self.assertAlmostEqual(diagonal.cost, 3 * math.sqrt(2))
        self.assertLess(diagonal.cost, straight.cost)

    def test_diagonal_moves_do_not_cut_corners(self):
        grid = _open_grid(3, 3, {(1, 0)})
        result = find_path(grid, (0, 0), (1, 1), diagonal=True)
        self.assertTrue(result.found)
        self.assertNotIn(((0, 0), (1, 1)), list(zip(result.path, result.path[1:])))
        self.assertEqual(result.path[0], (0, 0))
        self.assertEqual(result.path[-1], (1, 1))

    def test_blocked_endpoints_are_rejected(self):
        grid = _open_grid(3, 3, {(0, 0), (2, 2)})
        with self.assertRaises(ValueError):
            find_path(grid, (0, 0), (2, 0))
        self.assertFalse(find_path(grid, (1, 1), (2, 2)).found)

    def test_out_of_bounds_endpoints_are_rejected(self):
        grid = _open_grid(3, 3)
        with self.assertRaises(ValueError):
            find_path(grid, (-1, 0), (2, 2))
        with self.assertRaises(ValueError):
            find_path(grid, (0, 0), (3, 2))
        with self.assertRaises(TypeError):
            find_path(grid, (0.0, 0.0), (2, 2))  # type: ignore[arg-type]

    def test_results_are_deterministic(self):
        grid = _open_grid(12, 9, {(4, y) for y in range(7)} | {(8, y) for y in range(2, 9)})
        first = find_path(grid, (0, 4), (11, 4))
        second = find_path(grid, (0, 4), (11, 4))
        self.assertEqual(first, second)
        self.assertIsInstance(first, PathResult)


class PathReportTest(unittest.TestCase):
    def test_report_is_json_safe_and_names_the_route(self):
        result = find_path(_open_grid(4, 4), (0, 0), (3, 3))
        report = path_report(result)
        self.assertEqual(report["schema"], 1)
        self.assertTrue(report["found"])
        self.assertEqual(report["start"], [0, 0])
        self.assertEqual(report["goal"], [3, 3])
        self.assertEqual(report["path"][0], [0, 0])
        self.assertEqual(report["path"][-1], [3, 3])
        self.assertEqual(len(report["path"]), 7)
        self.assertEqual(report["steps"], 6)
        self.assertGreater(report["expanded"], 0)
        self.assertEqual(report["cost"], 6.0)

    def test_unreachable_report_has_an_empty_path(self):
        grid = _open_grid(3, 3, {(1, 0), (1, 1), (1, 2)})
        report = path_report(find_path(grid, (0, 1), (2, 1)))
        self.assertFalse(report["found"])
        self.assertEqual(report["path"], [])
        self.assertEqual(report["steps"], 0)

    def test_rejects_a_non_result(self):
        with self.assertRaises(TypeError):
            path_report({"found": True})  # type: ignore[arg-type]

    def test_describe_advertises_pathfinding(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["pathfinding"])


if __name__ == "__main__":
    unittest.main()
