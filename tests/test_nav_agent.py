"""Tests for the reusable nav agent."""

import unittest

from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Vec3
from keystone.nav_agent import NavAgent, nav_agent_report
from keystone.pathfinding import NavGrid
from keystone.physics import AABB
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _floor(x: float = 0.0, z: float = 0.0) -> AABB:
    return AABB(Vec3(x, -0.5, z), Vec3(20.0, 0.5, 20.0))


def _agent(grid: NavGrid, *, x: float = 0.5, z: float = 0.5, speed: float = 2.0, **kwargs) -> NavAgent:
    body = CharacterBody(position=Vec3(x, 1.0, z))
    kwargs.setdefault("height", 0.9)
    return NavAgent(grid, CharacterController(), body, speed=speed, **kwargs)


class NavAgentPlanTest(unittest.TestCase):
    def test_a_goal_plans_a_route_and_reports_it(self):
        agent = _agent(NavGrid(5, 3))
        self.assertTrue(agent.set_goal((4, 1)))
        self.assertEqual(agent.goal, (4, 1))
        self.assertGreater(len(agent.follower.path), 1)
        report = nav_agent_report(agent)
        self.assertEqual(report["goal"], [4, 1])
        self.assertTrue(report["plan_found"])
        self.assertFalse(report["done"])

    def test_an_unreachable_goal_clears_the_plan(self):
        grid = NavGrid(5, 3, frozenset({(2, y) for y in range(3)}))
        agent = _agent(grid)
        self.assertFalse(agent.set_goal((4, 1)))
        self.assertIsNone(agent.goal)
        self.assertFalse(agent.last_plan_found)
        self.assertTrue(agent.done)
        self.assertEqual(nav_agent_report(agent)["waypoints"], 0)

    def test_a_blocked_or_outside_goal_raises(self):
        grid = NavGrid(4, 4, frozenset({(2, 2)}))
        agent = _agent(grid)
        with self.assertRaises(ValueError):
            agent.set_goal((2, 2))
        with self.assertRaises(ValueError):
            agent.set_goal((9, 9))
        with self.assertRaises(TypeError):
            agent.set_goal((1.0, 1.0))  # type: ignore[arg-type]

    def test_a_blocked_start_raises(self):
        grid = NavGrid(4, 4, frozenset({(0, 0)}))
        agent = _agent(grid)
        with self.assertRaises(ValueError):
            agent.set_goal((3, 3))

    def test_replan_without_a_goal_returns_false(self):
        agent = _agent(NavGrid(3, 3))
        self.assertFalse(agent.replan())
        self.assertTrue(agent.set_goal((2, 2)))
        self.assertTrue(agent.replan())

    def test_agent_validation(self):
        grid = NavGrid(3, 3)
        body = CharacterBody(position=Vec3(0.5, 1.0, 0.5))
        controller = CharacterController()
        with self.assertRaises(TypeError):
            NavAgent(object(), controller, body)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            NavAgent(grid, object(), body)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            NavAgent(grid, controller, object())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            NavAgent(grid, controller, body, cell_size=0.0)
        with self.assertRaises(ValueError):
            NavAgent(grid, controller, body, speed=0.0)
        with self.assertRaises(ValueError):
            NavAgent(grid, controller, body, arrive_radius=0.0)
        with self.assertRaises(ValueError):
            NavAgent(grid, controller, body, separation_weight=-1.0)
        with self.assertRaises(TypeError):
            NavAgent(grid, controller, body, diagonal=1)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            NavAgent(grid, controller, body, origin=(0.0, 0.0, 0.0))  # type: ignore[arg-type]


class NavAgentWalkTest(unittest.TestCase):
    def test_an_agent_walks_around_a_wall_to_its_goal(self):
        grid = NavGrid(6, 6, frozenset({(3, y) for y in range(4)}))
        agent = _agent(grid, x=0.5, z=1.5, speed=3.0)
        self.assertTrue(agent.set_goal((5, 1)))
        dt = 1.0 / 60.0
        for _ in range(600):
            report = agent.step(dt, [_floor()])
            if report["done"]:
                break
        self.assertTrue(agent.done)
        self.assertGreater(agent.position.x, 4.3)
        self.assertAlmostEqual(agent.position.z, 1.5, delta=0.15)
        self.assertTrue(report["on_ground"])

    def test_a_route_to_the_current_cell_finishes_immediately(self):
        agent = _agent(NavGrid(4, 4))
        self.assertTrue(agent.set_goal((0, 0)))
        report = agent.step(1.0 / 60.0, [_floor()])
        self.assertTrue(report["done"])
        self.assertIsNone(report["goal"])

    def test_step_validation(self):
        agent = _agent(NavGrid(3, 3))
        agent.set_goal((2, 2))
        with self.assertRaises(ValueError):
            agent.step(0.0)
        with self.assertRaises(TypeError):
            agent.step("soon")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            agent.step(1 / 60, [], [object()])  # type: ignore[list-item]

    def test_neighbours_can_push_an_agent_off_a_straight_route(self):
        grid = NavGrid(8, 5)
        agent = _agent(grid, x=0.5, z=2.5)
        blocker = _agent(grid, x=1.5, z=2.5)
        blocker.body = CharacterBody(
            position=Vec3(1.5, 1.0, 2.5), half_extents=Vec3(0.6, 0.9, 0.6)
        )
        agent.set_goal((7, 2))
        dt = 1.0 / 60.0
        for _ in range(30):
            report = agent.step(dt, [_floor()])
        x_without = report["position"][0]
        agent = _agent(grid, x=0.5, z=2.5)
        agent.set_goal((7, 2))
        for _ in range(30):
            report = agent.step(dt, [_floor()], [blocker])
        self.assertLess(report["position"][0], x_without - 1e-3)

    def test_zero_separation_weight_ignores_neighbours(self):
        grid = NavGrid(8, 5)
        agent = _agent(grid, x=0.5, z=2.5)
        blocker = _agent(grid, x=1.2, z=2.5)
        blocker.body = CharacterBody(
            position=Vec3(1.2, 1.0, 2.5), half_extents=Vec3(0.6, 0.9, 0.6)
        )
        agent.separation_weight = 0.0
        agent.set_goal((7, 2))
        report = agent.step(1.0 / 60.0, [_floor()], [blocker])
        self.assertAlmostEqual(report["position"][0], 0.5 + 2.0 / 60.0, places=5)

    def test_report_is_json_safe(self):
        agent = _agent(NavGrid(4, 4))
        agent.set_goal((3, 3))
        report = nav_agent_report(agent)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(len(report["position"]), 3)
        self.assertIn("remaining_distance", report)
        self.assertIn("waypoints", report)
        with self.assertRaises(TypeError):
            nav_agent_report({"done": True})  # type: ignore[arg-type]

    def test_describe_advertises_nav_agents(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["nav_agent"])


if __name__ == "__main__":
    unittest.main()
