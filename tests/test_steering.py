"""Tests for deterministic seek/arrive/separation steering."""

import unittest

from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.steering import Agent, arrive, seek, separation, steer, steering_report


class SeekTest(unittest.TestCase):
    def test_seek_points_at_the_target_at_max_speed(self):
        wish = seek(Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 4.0), 2.0)
        self.assertAlmostEqual(wish.length(), 2.0)
        self.assertAlmostEqual(wish.x, 1.2)
        self.assertAlmostEqual(wish.z, 1.6)

    def test_seek_at_the_target_is_zero(self):
        self.assertEqual(seek(Vec3(1.0, 2.0, 3.0), Vec3(1.0, 2.0, 3.0), 2.0), Vec3())

    def test_seek_validation(self):
        with self.assertRaises(TypeError):
            seek((0.0, 0.0, 0.0), Vec3(), 1.0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            seek(Vec3(), Vec3(), 0.0)
        with self.assertRaises(ValueError):
            seek(Vec3(), Vec3(float("nan"), 0.0, 0.0), 1.0)


class ArriveTest(unittest.TestCase):
    def test_outside_the_slow_radius_arrive_is_seek(self):
        self.assertEqual(
            arrive(Vec3(), Vec3(5.0, 0.0, 0.0), 2.0, 2.0),
            seek(Vec3(), Vec3(5.0, 0.0, 0.0), 2.0),
        )

    def test_inside_the_slow_radius_speeds_down_linearly(self):
        wish = arrive(Vec3(0.0, 0.0, 0.0), Vec3(1.0, 0.0, 0.0), 4.0, 2.0)
        self.assertAlmostEqual(wish.x, 2.0)
        self.assertAlmostEqual(wish.length(), 2.0)

    def test_at_the_target_arrive_stops(self):
        self.assertEqual(arrive(Vec3(2.0, 0.0, 0.0), Vec3(2.0, 0.0, 0.0), 4.0, 2.0), Vec3())

    def test_arrive_validation(self):
        with self.assertRaises(ValueError):
            arrive(Vec3(), Vec3(1.0, 0.0, 0.0), 2.0, 0.0)
        with self.assertRaises(ValueError):
            arrive(Vec3(), Vec3(1.0, 0.0, 0.0), 2.0, -1.0)


class SeparationTest(unittest.TestCase):
    def test_a_neighbour_inside_the_limit_pushes_directly_away(self):
        push = separation(Vec3(0.0, 0.0, 0.0), [(Vec3(0.5, 0.0, 0.0), 0.5)], 0.5)
        self.assertLess(push.x, 0.0)
        self.assertAlmostEqual(push.y, 0.0)
        self.assertAlmostEqual(push.z, 0.0)

    def test_outside_the_limit_or_coincident_adds_nothing(self):
        self.assertEqual(separation(Vec3(), [(Vec3(5.0, 0.0, 0.0), 0.5)], 0.5), Vec3())
        self.assertEqual(separation(Vec3(), [(Vec3(), 0.5)], 0.5), Vec3())

    def test_several_neighbours_sum_deterministically(self):
        others = [(Vec3(0.5, 0.0, 0.0), 0.5), (Vec3(-0.5, 0.0, 0.0), 0.5)]
        first = separation(Vec3(), others, 0.5)
        second = separation(Vec3(), others, 0.5)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first.x, 0.0)

    def test_strength_and_margin_scale_the_push(self):
        weak = separation(Vec3(), [(Vec3(0.5, 0.0, 0.0), 0.5)], 0.5, strength=0.5)
        strong = separation(Vec3(), [(Vec3(0.5, 0.0, 0.0), 0.5)], 0.5, strength=2.0)
        self.assertLess(weak.x, 0.0)
        self.assertLess(strong.x, weak.x)
        roomy = separation(Vec3(), [(Vec3(0.75, 0.0, 0.0), 0.5)], 0.5, margin=0.5)
        self.assertLess(roomy.x, 0.0)

    def test_separation_validation(self):
        with self.assertRaises(TypeError):
            separation((0.0, 0.0, 0.0), [], 0.5)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            separation(Vec3(), [], -0.1)
        with self.assertRaises(ValueError):
            separation(Vec3(), [(Vec3(), -0.5)], 0.5)
        with self.assertRaises(ValueError):
            separation(Vec3(), [], 0.5, strength=-1.0)
        with self.assertRaises(TypeError):
            separation(Vec3(), [(Vec3(),)], 0.5)  # type: ignore[list-item]


class SteerTest(unittest.TestCase):
    def test_without_neighbours_steer_returns_the_wish_clamped(self):
        agent = Agent(position=Vec3(), radius=0.4, max_speed=2.0)
        self.assertEqual(steer(agent, Vec3(1.0, 0.0, 0.0)), Vec3(1.0, 0.0, 0.0))
        limited = steer(agent, Vec3(6.0, 0.0, 0.0))
        self.assertAlmostEqual(limited.length(), 2.0)
        self.assertAlmostEqual(limited.x, 2.0)

    def test_steer_adds_avoidance_to_the_wish(self):
        agent = Agent(position=Vec3(), radius=0.5, max_speed=3.0)
        other = Agent(position=Vec3(0.2, 0.0, 0.0), radius=0.5)
        wish = Vec3(0.0, 0.0, 1.0)
        adjusted = steer(agent, wish, [other])
        self.assertLess(adjusted.x, 0.0)
        self.assertGreater(adjusted.z, 0.0)

    def test_steer_ignores_the_agent_itself_by_identity(self):
        agent = Agent(position=Vec3(), radius=0.5, max_speed=3.0)
        self.assertEqual(steer(agent, Vec3(1.0, 0.0, 0.0), [agent]), Vec3(1.0, 0.0, 0.0))

    def test_steer_validation(self):
        with self.assertRaises(TypeError):
            steer(object(), Vec3())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            steer(Agent(), (0.0, 0.0, 0.0))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            steer(Agent(), Vec3(), [object()])  # type: ignore[list-item]
        with self.assertRaises(ValueError):
            steer(Agent(), Vec3(), [], separation_weight=-1.0)

    def test_agent_validation(self):
        with self.assertRaises(TypeError):
            Agent(position=(0.0, 0.0, 0.0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            Agent(position=Vec3(), radius=0.0)
        with self.assertRaises(ValueError):
            Agent(position=Vec3(), max_speed=0.0)
        with self.assertRaises(ValueError):
            Agent(position=Vec3(), velocity=Vec3(float("inf"), 0.0, 0.0))


class SteeringReportTest(unittest.TestCase):
    def test_report_is_json_safe(self):
        agent = Agent(position=Vec3(), max_speed=2.0)
        report = steering_report(agent, Vec3(3.0, 0.0, 4.0))
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["wish"], [3.0, 0.0, 4.0])
        self.assertAlmostEqual(report["speed"], 5.0)
        self.assertTrue(report["limited"])

    def test_unlimited_report(self):
        report = steering_report(Agent(max_speed=10.0), Vec3(1.0, 0.0, 0.0))
        self.assertFalse(report["limited"])
        self.assertEqual(report["speed"], 1.0)

    def test_report_rejects_bad_input(self):
        with self.assertRaises(TypeError):
            steering_report(object(), Vec3())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            steering_report(Agent(), (0.0, 0.0, 0.0))  # type: ignore[arg-type]

    def test_describe_advertises_steering(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["steering"])


if __name__ == "__main__":
    unittest.main()
