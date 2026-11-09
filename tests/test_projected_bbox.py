"""Direct tests for the projected-bbox clipping helper."""

import unittest

from keystone.analysis import _projected_bbox
from keystone.math3d import Mat4, Vec3


def _corners(low, high):
    return [
        Vec3(x, y, z)
        for x in (low[0], high[0])
        for y in (low[1], high[1])
        for z in (low[2], high[2])
    ]


class ProjectedBBoxTest(unittest.TestCase):
    """The bbox must describe on-screen extent, including near-plane crossings."""

    def setUp(self):
        # Identity view/projection: clip space equals world space, so the
        # geometry is easy to reason about without a camera.
        self.identity = Mat4.identity()
        self.width = 100
        self.height = 100

    def test_fully_visible_box_projects_directly(self):
        # z in [-1, 1] keeps it inside the clip volume; w is 1.
        corners = _corners((-0.5, -0.5, 0.0), (0.5, 0.5, 0.0))
        box = _projected_bbox(corners, self.identity, self.width, self.height)
        self.assertIsNotNone(box)
        min_x, min_y, max_x, max_y = box
        self.assertAlmostEqual(min_x, 25.0, places=2)
        self.assertAlmostEqual(max_x, 75.0, places=2)
        self.assertAlmostEqual(min_y, 25.0, places=2)
        self.assertAlmostEqual(max_y, 75.0, places=2)

    def test_fully_offscreen_box_is_clamped_to_the_frame(self):
        # x > 1 puts it right of the frame; y > 1 is above it, because clip y
        # points up while image y points down.
        corners = _corners((5.0, 5.0, 0.0), (6.0, 6.0, 0.0))
        box = _projected_bbox(corners, self.identity, self.width, self.height)
        self.assertIsNotNone(box)
        self.assertEqual(box, [100.0, 0.0, 100.0, 0.0])

        # Mirror it: x < -1 and y < -1 clamp to the opposite corner.
        corners = _corners((-6.0, -6.0, 0.0), (-5.0, -5.0, 0.0))
        box = _projected_bbox(corners, self.identity, self.width, self.height)
        self.assertEqual(box, [0.0, 100.0, 0.0, 100.0])

    def test_a_box_crossing_the_near_plane_keeps_its_extent(self):
        # Identity clip space: the near plane is z + w == 0, and w == 1 here,
        # so z == -1 is the near plane. Spanning z from -3 (behind) to 1
        # (inside) means the box crosses it.
        corners = _corners((-0.5, -0.5, -3.0), (0.5, 0.5, 1.0))
        box = _projected_bbox(corners, self.identity, self.width, self.height)
        self.assertIsNotNone(box)
        min_x, min_y, max_x, max_y = box
        self.assertGreater(max_x - min_x, 1.0)
        self.assertGreater(max_y - min_y, 1.0)
        # The crossing is at the near plane, so the box reaches the frame edge.
        self.assertGreaterEqual(max_y, 50.0)

    def test_no_corners_in_front_yields_none(self):
        corners = _corners((-0.5, -0.5, -3.0), (0.5, 0.5, -2.0))
        box = _projected_bbox(corners, self.identity, self.width, self.height)
        self.assertIsNone(box)

    def test_result_is_always_inside_the_frame(self):
        corners = _corners((-40.0, -40.0, -30.0), (40.0, 40.0, 4.0))
        box = _projected_bbox(corners, self.identity, self.width, self.height)
        self.assertIsNotNone(box)
        min_x, min_y, max_x, max_y = box
        for value in (min_x, min_y, max_x, max_y):
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, float(max(self.width, self.height)))


if __name__ == "__main__":
    unittest.main()
