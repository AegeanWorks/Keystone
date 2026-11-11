"""Tests for grid line-of-sight checks and path smoothing."""

import itertools
import unittest

from keystone.pathfinding import NavGrid, find_path, line_of_sight, smooth_path
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _grid(width: int = 6, height: int = 6, blocked=()) -> NavGrid:
    return NavGrid(width, height, frozenset(blocked))


class LineOfSightTest(unittest.TestCase):
    def test_an_open_straight_line_is_visible(self):
        self.assertTrue(line_of_sight(_grid(), (0, 2), (5, 2)))

    def test_a_blocked_cell_breaks_the_line(self):
        self.assertFalse(line_of_sight(_grid(blocked={(3, 2)}), (0, 2), (5, 2)))

    def test_a_clear_diagonal_line_is_visible(self):
        self.assertTrue(line_of_sight(_grid(), (0, 0), (4, 4)))

    def test_a_diagonal_line_through_a_wall_corner_is_not_visible(self):
        grid = _grid(2, 2, {(1, 0)})
        self.assertFalse(line_of_sight(grid, (0, 0), (1, 1)))

    def test_the_same_cell_is_visible(self):
        self.assertTrue(line_of_sight(_grid(), (2, 2), (2, 2)))

    def test_validation(self):
        grid = _grid()
        with self.assertRaises(TypeError):
            line_of_sight(object(), (0, 0), (1, 1))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            line_of_sight(grid, (0, 0), (6, 0))
        with self.assertRaises(TypeError):
            line_of_sight(grid, (0.0, 0.0), (1, 0))  # type: ignore[arg-type]


class SmoothPathTest(unittest.TestCase):
    def test_an_open_route_collapses_to_its_endpoints(self):
        path = find_path(_grid(), (0, 0), (5, 0)).path
        smoothed = smooth_path(_grid(), path)
        self.assertEqual(smoothed, ((0, 0), (5, 0)))

    def test_a_clear_diagonal_route_collapses_across_cells(self):
        grid = _grid()
        path = find_path(grid, (0, 0), (4, 4)).path
        self.assertEqual(smooth_path(grid, path), ((0, 0), (4, 4)))

    def test_a_wall_keeps_the_corner_it_must_round(self):
        grid = _grid(6, 6, {(3, y) for y in range(4)})
        path = find_path(grid, (0, 1), (5, 1)).path
        smoothed = smooth_path(grid, path)
        self.assertLess(len(smoothed), len(path))
        self.assertGreater(len(smoothed), 2)
        self.assertTrue(all(cell not in grid.blocked for cell in smoothed))
        self.assertTrue(_segments_clear(grid, smoothed))

    def test_the_smoothed_route_keeps_the_same_endpoints(self):
        grid = _grid(6, 6, {(2, 2), (2, 3), (3, 3)})
        path = find_path(grid, (0, 0), (5, 5)).path
        smoothed = smooth_path(grid, path)
        self.assertEqual(smoothed[0], path[0])
        self.assertEqual(smoothed[-1], path[-1])

    def test_short_and_empty_paths_are_returned_unchanged(self):
        grid = _grid()
        self.assertEqual(smooth_path(grid, ()), ())
        self.assertEqual(smooth_path(grid, ((1, 1),)), ((1, 1),))
        self.assertEqual(smooth_path(grid, ((1, 1), (2, 1))), ((1, 1), (2, 1)))

    def test_an_unreachable_result_has_nothing_to_smooth(self):
        grid = _grid(4, 4, {(2, y) for y in range(4)})
        result = find_path(grid, (0, 1), (3, 1))
        self.assertFalse(result.found)
        self.assertEqual(smooth_path(grid, result.path), ())

    def test_smoothing_is_deterministic(self):
        grid = _grid(8, 8, {(4, y) for y in range(5)} | {(2, 6)})
        path = find_path(grid, (0, 3), (7, 3)).path
        self.assertEqual(smooth_path(grid, path), smooth_path(grid, path))

    def test_validation(self):
        grid = _grid()
        with self.assertRaises(TypeError):
            smooth_path(object(), ((0, 0),))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            smooth_path(grid, ((0, 0), (6, 1)))
        with self.assertRaises(TypeError):
            smooth_path(grid, ((0.0, 0.0),))  # type: ignore[arg-type]

    def test_describe_advertises_path_smoothing(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["path_smoothing"])


def _segments_clear(grid: NavGrid, path: tuple[tuple[int, int], ...]) -> bool:
    return all(line_of_sight(grid, first, second) for first, second in itertools.pairwise(path))


if __name__ == "__main__":
    unittest.main()
