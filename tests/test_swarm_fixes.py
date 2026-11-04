"""Swarm regression pins: one failing-first test per verified Stage-3 fix."""

import unittest


class SwarmFixesTest(unittest.TestCase):
    def test_shadow_all_exports_light_vp_for(self):
        from keystone.gpu import shadow

        self.assertIn("light_vp_for", shadow.__all__)
        self.assertTrue(callable(shadow.light_vp_for))

    def test_quat_json_round_trip(self):
        from keystone.animation import Track
        from keystone.math3d import Quat

        track = Track(times=(0.0, 1.0), values=(Quat(1, 0, 0, 0), Quat(0, 0, 0, 1)))
        restored = Track.from_dict(track.to_dict())
        self.assertEqual(restored.values, track.values)

    def test_clock_rejects_non_finite(self):
        from keystone.clock import FixedStepClock

        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                FixedStepClock(step=bad)
            with self.assertRaises(ValueError):
                FixedStepClock(step=1 / 60, max_frame=bad)

    def test_command_log_to_dict_isolated(self):
        from keystone.input import ActionState
        from keystone.replay import CommandLog

        log = CommandLog(seed=1)
        log.record(ActionState(forward=1.0))
        payload = log.to_dict()
        payload["frames"].append({"forward": 9.0})
        self.assertEqual(len(log.frames), 1)

    def test_disabled_mouse_suppresses_click(self):
        from keystone.input import InputMap
        from tests.test_input import FakeContext

        context = FakeContext()
        mouse_map = InputMap()
        mouse_map.set_mouse_enabled(False)
        mouse_map.sample(context)
        context.pointer = (10.0, 10.0)
        context.mouse = True
        self.assertFalse(mouse_map.sample(context).mouse_clicked)

    def test_update_preserves_insertion_order(self):
        from keystone.broadphase import SpatialGrid
        from keystone.math3d import Vec3
        from keystone.physics import AABB

        grid = SpatialGrid(cell_size=2.0)
        box = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        grid.insert("a", box)
        grid.insert("b", box)
        grid.update("a", box)
        self.assertEqual(grid.query(box), ["a", "b"])

    def test_none_flags_report_disabled(self):
        from keystone.samples import CubeDemo
        from keystone.web.scene import scene_document

        scene = CubeDemo().build_scene()
        scene.shadow = None
        scene.color = None
        scene.post = None
        scene.bloom = None
        scene.sprite = None
        document = scene_document(scene)
        self.assertFalse(document["shadows"]["enabled"])
        self.assertFalse(document["color"]["enabled"])
        self.assertFalse(document["post"]["enabled"])
        self.assertFalse(document["bloom"]["enabled"])
        self.assertFalse(document["sprites"]["enabled"])

    def test_hit_test_right_edge_is_exclusive(self):
        from keystone.ui.overlay import HudState, HumanOverlay

        overlay = HumanOverlay()
        overlay.build(
            HudState(
                game="g",
                status="r",
                fps=60.0,
                frame=0,
                elapsed=0.0,
                width=960,
                height=540,
                paused=True,
            )
        )
        left, top, width, height, action = overlay.hits[0]
        self.assertEqual(overlay.hit_test(left + width - 0.01, top + height / 2), action)
        self.assertIsNone(overlay.hit_test(left + width, top + height / 2))


if __name__ == "__main__":
    unittest.main()
