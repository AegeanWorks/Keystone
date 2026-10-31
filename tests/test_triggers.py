"""Tests for trigger volumes and enter/exit tracking."""

import unittest

from keystone.math3d import Vec3
from keystone.physics import AABB
from keystone.triggers import TriggerTracker, TriggerVolume


class TriggerTest(unittest.TestCase):
    def test_trigger_volume_validates_its_name_and_overlap(self):
        with self.assertRaises(ValueError):
            TriggerVolume("", AABB(Vec3(), Vec3(1, 1, 1)))
        volume = TriggerVolume("door", AABB(Vec3(0, 0, 0), Vec3(1, 1, 1)))
        self.assertTrue(volume.contains(AABB(Vec3(0, 0, 0), Vec3(0.1, 0.1, 0.1))))
        self.assertFalse(volume.contains(AABB(Vec3(5, 0, 0), Vec3(0.1, 0.1, 0.1))))

    def test_tracker_reports_enter_stay_and_exit(self):
        volume = TriggerVolume("door", AABB(Vec3(0, 0, 0), Vec3(1, 1, 1)))
        tracker = TriggerTracker()
        inside = AABB(Vec3(0, 0, 0), Vec3(0.1, 0.1, 0.1))
        outside = AABB(Vec3(5, 0, 0), Vec3(0.1, 0.1, 0.1))
        entered = tracker.update(inside, [volume])
        self.assertEqual(entered.entered, ("door",))
        self.assertEqual(entered.exited, ())
        self.assertEqual(entered.active, frozenset({"door"}))
        stayed = tracker.update(inside, [volume])
        self.assertEqual(stayed.entered, ())
        self.assertEqual(stayed.exited, ())
        exited = tracker.update(outside, [volume])
        self.assertEqual(exited.entered, ())
        self.assertEqual(exited.exited, ("door",))
        self.assertEqual(exited.active, frozenset())

    def test_tracker_handles_multiple_volumes_in_sorted_order(self):
        volumes = [
            TriggerVolume("z-last", AABB(Vec3(0, 0, 0), Vec3(2, 2, 2))),
            TriggerVolume("a-first", AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))),
        ]
        tracker = TriggerTracker()
        events = tracker.update(AABB(Vec3(0, 0, 0), Vec3(0.1, 0.1, 0.1)), volumes)
        self.assertEqual(events.entered, ("a-first", "z-last"))
        tracker.reset()
        self.assertEqual(tracker.active, frozenset())


if __name__ == "__main__":
    unittest.main()
