"""Tests for waypoint following and grid-to-world route conversion."""

import unittest

from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Vec3
from keystone.navigation import PathFollower, grid_path_points, navigation_report
from keystone.physics import AABB
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


class GridPointsTest(unittest.TestCase):
    def test_cells_convert_to_world_cell_centres(self):
        points = grid_path_points(
            ((0, 0), (1, 0)),
            cell_size=2.0,
            origin=Vec3(-5.0, 0.0, -5.0),
            height=0.9,
        )
        self.assertEqual(points[0], Vec3(-4.0, 0.9, -4.0))
        self.assertEqual(points[1], Vec3(-2.0, 0.9, -4.0))

    def test_default_origin_and_height_put_the_route_on_the_floor_plane(self):
        points = grid_path_points(((2, 3),))
        self.assertEqual(points, (Vec3(2.5, 0.0, 3.5),))

    def test_empty_route_converts_to_no_points(self):
        self.assertEqual(grid_path_points(()), ())

    def test_malformed_conversions_are_rejected(self):
        with self.assertRaises(ValueError):
            grid_path_points(((0, 0),), cell_size=0.0)
        with self.assertRaises(ValueError):
            grid_path_points(((0.0, 0.0),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            grid_path_points(((0, 0),), origin=(0.0, 0.0, 0.0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            grid_path_points(((0, 0),), height=float("nan"))


class PathFollowerTest(unittest.TestCase):
    def test_follower_skips_the_start_cell_and_aims_at_the_next(self):
        follower = PathFollower((Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0)), speed=2.0)
        wish, done = follower.advance(Vec3(0.0, 0.0, 0.0))
        self.assertEqual(wish, Vec3(2.0, 0.0, 0.0))
        self.assertFalse(done)
        self.assertEqual(follower.index, 1)

    def test_follower_turns_toward_the_next_waypoint_inside_the_radius(self):
        follower = PathFollower(
            (Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0), Vec3(3.0, 0.0, 4.0)),
            speed=2.0,
        )
        follower.advance(Vec3(0.0, 0.0, 0.0))
        wish, done = follower.advance(Vec3(2.95, 0.0, 0.0))
        self.assertFalse(done)
        self.assertGreater(wish.z, 1.99)
        self.assertLess(abs(wish.x), 0.03)
        self.assertAlmostEqual(wish.length(), 2.0)

    def test_follower_finishes_on_the_last_waypoint(self):
        follower = PathFollower((Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0)), speed=2.0)
        follower.advance(Vec3(0.0, 0.0, 0.0))
        wish, done = follower.advance(Vec3(3.0, 0.0, 0.0))
        self.assertEqual(wish, Vec3())
        self.assertTrue(done)
        self.assertEqual(follower.target, None)

    def test_a_stuck_follower_keeps_aiming_at_the_same_waypoint(self):
        follower = PathFollower((Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0)), speed=1.5)
        first = follower.advance(Vec3(0.0, 0.0, 0.0))
        for _ in range(30):
            again = follower.advance(Vec3(0.0, 0.0, 0.0))
            self.assertEqual(again, first)
        self.assertEqual(follower.index, 1)

    def test_remaining_distance_covers_the_route_ahead(self):
        follower = PathFollower((Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0), Vec3(3.0, 0.0, 4.0)))
        self.assertAlmostEqual(follower.remaining_distance(Vec3(0.0, 0.0, 0.0)), 7.0)
        follower.advance(Vec3(0.0, 0.0, 0.0))
        self.assertAlmostEqual(follower.remaining_distance(Vec3(3.0, 0.0, 0.0)), 4.0)
        follower.advance(Vec3(3.0, 0.0, 0.0))
        follower.advance(Vec3(3.0, 0.0, 4.0))
        self.assertEqual(follower.remaining_distance(Vec3(3.0, 0.0, 4.0)), 0.0)

    def test_empty_path_is_done_immediately(self):
        follower = PathFollower()
        self.assertTrue(follower.done)
        self.assertEqual(follower.advance(Vec3()), (Vec3(), True))

    def test_malformed_followers_are_rejected(self):
        with self.assertRaises(ValueError):
            PathFollower((Vec3(),), speed=0.0)
        with self.assertRaises(ValueError):
            PathFollower((Vec3(),), speed=float("inf"))
        with self.assertRaises(ValueError):
            PathFollower((Vec3(),), arrive_radius=0.0)
        with self.assertRaises(ValueError):
            PathFollower((Vec3(),), index=2)
        with self.assertRaises(ValueError):
            PathFollower((Vec3(),), index=-1)
        with self.assertRaises(TypeError):
            PathFollower(((0.0, 0.0, 0.0),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            PathFollower((Vec3(),)).advance((0.0, 0.0, 0.0))  # type: ignore[arg-type]


class NavigationIntegrationTest(unittest.TestCase):
    def test_a_character_walks_a_grid_route_to_the_goal(self):
        controller = CharacterController()
        floor = AABB(Vec3(0.0, -0.5, 0.0), Vec3(10.0, 0.5, 10.0))
        body = CharacterBody(position=Vec3(0.5, 1.0, 0.5))
        path = grid_path_points(((0, 0), (1, 0), (2, 0)), cell_size=1.0, height=0.9)
        follower = PathFollower(path, speed=2.0)
        dt = 1.0 / 60.0
        for _ in range(240):
            wish, done = follower.advance(body.position)
            if done:
                break
            body = controller.step(body, wish, dt, [floor])
        self.assertTrue(follower.done)
        self.assertGreater(body.position.x, 2.3)
        self.assertAlmostEqual(body.position.z, 0.5, places=3)


class NavigationReportTest(unittest.TestCase):
    def test_report_is_json_safe(self):
        follower = PathFollower((Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0)), speed=2.0)
        follower.advance(Vec3(0.0, 0.0, 0.0))
        report = navigation_report(follower, Vec3(0.0, 0.0, 0.0))
        self.assertEqual(report["schema"], 1)
        self.assertFalse(report["done"])
        self.assertEqual(report["waypoint"], 1)
        self.assertEqual(report["waypoints"], 2)
        self.assertEqual(report["target"], [3.0, 0.0, 0.0])
        self.assertAlmostEqual(report["remaining_distance"], 3.0)
        self.assertEqual(report["speed"], 2.0)

    def test_finished_report_has_no_target(self):
        follower = PathFollower()
        report = navigation_report(follower, Vec3())
        self.assertTrue(report["done"])
        self.assertIsNone(report["target"])

    def test_report_rejects_a_non_follower(self):
        with self.assertRaises(TypeError):
            navigation_report({"done": True}, Vec3())  # type: ignore[arg-type]

    def test_describe_advertises_navigation(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["navigation"])


if __name__ == "__main__":
    unittest.main()
