"""Unit tests for the Keystone 3D math core."""

import math
import unittest

from keystone.math3d import Mat4, Quat, Vec3


class Vec3Test(unittest.TestCase):
    def test_arithmetic_and_dot(self):
        a = Vec3(1.0, 2.0, 3.0)
        b = Vec3(4.0, 5.0, 6.0)
        self.assertEqual(a + b, Vec3(5.0, 7.0, 9.0))
        self.assertEqual(b - a, Vec3(3.0, 3.0, 3.0))
        self.assertEqual(a * 2.0, Vec3(2.0, 4.0, 6.0))
        self.assertEqual(a.dot(b), 32.0)

    def test_cross_follows_right_hand_rule(self):
        self.assertEqual(Vec3(1, 0, 0).cross(Vec3(0, 1, 0)), Vec3(0, 0, 1))

    def test_normalized_is_unit_and_zero_safe(self):
        unit = Vec3(3.0, 0.0, 4.0).normalized()
        self.assertAlmostEqual(unit.length(), 1.0)
        self.assertEqual(Vec3().normalized(), Vec3())

    def test_lerp_hits_both_ends(self):
        a, b = Vec3(0, 0, 0), Vec3(10, 20, 30)
        self.assertEqual(a.lerp(b, 0.0), a)
        self.assertEqual(a.lerp(b, 1.0), b)
        self.assertEqual(a.lerp(b, 0.5), Vec3(5, 10, 15))

    def test_mul_rejects_vector_operand(self):
        with self.assertRaises(TypeError):
            Vec3(1, 2, 3) * Vec3(4, 5, 6)  # type: ignore[operator]


class Mat4Test(unittest.TestCase):
    def test_identity_leaves_points_and_matrices_unchanged(self):
        p = Vec3(1.0, -2.0, 3.0)
        self.assertEqual(Mat4.identity() * p, p)
        m = Mat4.translation(1, 2, 3)
        self.assertEqual(Mat4.identity() * m, m)

    def test_translation_and_scale_apply_in_order(self):
        m = Mat4.translation(10, 0, 0) * Mat4.scale(2, 2, 2)
        self.assertEqual(m.transform_point(Vec3(1, 1, 1)), Vec3(12, 2, 2))

    def test_rotation_z_90_degrees(self):
        m = Mat4.rotation_z(math.pi / 2)
        got = m.transform_point(Vec3(1, 0, 0))
        self.assertAlmostEqual(got.x, 0.0)
        self.assertAlmostEqual(got.y, 1.0)
        self.assertAlmostEqual(got.z, 0.0)

    def test_direction_ignores_translation(self):
        m = Mat4.translation(100, 100, 100)
        self.assertEqual(m.transform_direction(Vec3(1, 0, 0)), Vec3(1, 0, 0))

    def test_inverse_round_trips_affine_matrix(self):
        m = (
            Mat4.translation(3, -4, 5)
            * Mat4.rotation_y(0.7)
            * Mat4.scale(2, 3, 4)
        )
        point = Vec3(1.5, -2.5, 0.5)
        round_trip = m.inverse().transform_point(m.transform_point(point))
        for got, want in zip(round_trip, point):
            self.assertAlmostEqual(got, want, places=6)
        for got, want in zip(m * m.inverse(), Mat4.identity()):
            self.assertAlmostEqual(got, want, places=6)

    def test_inverse_rejects_projective_matrix(self):
        with self.assertRaises(ValueError):
            Mat4.perspective(60.0, 1.5, 0.1, 100.0).inverse()

    def test_transform_point_rejects_projective_matrix(self):
        with self.assertRaises(ValueError):
            Mat4.perspective(60.0, 1.0, 0.5, 100.0).transform_point(Vec3(0, 0, -0.5))
        with self.assertRaises(ValueError):
            Mat4.perspective(60.0, 1.0, 0.5, 100.0) * Vec3(0, 0, -0.5)

    def test_perspective_maps_near_and_far_to_ndc(self):
        m = Mat4.perspective(60.0, 1.0, 0.5, 100.0)
        near = m.project_point(Vec3(0, 0, -0.5))
        far = m.project_point(Vec3(0, 0, -100.0))
        self.assertAlmostEqual(near.z, -1.0)
        self.assertAlmostEqual(far.z, 1.0)

    def test_perspective_rejects_invalid_fov(self):
        with self.assertRaises(ValueError):
            Mat4.perspective(0.0, 1.0, 0.1, 10.0)

    def test_look_at_puts_eye_at_origin(self):
        eye, target = Vec3(0, 5, 10), Vec3(0, 0, 0)
        m = Mat4.look_at(eye, target, Vec3(0, 1, 0))
        self.assertEqual(m.transform_point(eye), Vec3(0, 0, 0))
        forward = m.transform_direction((target - eye).normalized())
        self.assertAlmostEqual(forward.x, 0.0)
        self.assertAlmostEqual(forward.y, 0.0)
        self.assertAlmostEqual(forward.z, -1.0)

    def test_look_at_rejects_degenerate_input(self):
        with self.assertRaises(ValueError):
            Mat4.look_at(Vec3(0, 0, 0), Vec3(0, 0, 0), Vec3(0, 1, 0))

    def test_flat_is_column_major_for_opengl(self):
        m = Mat4.translation(1, 2, 3)
        self.assertEqual(m.flat()[12:15], (1.0, 2.0, 3.0))


class QuatTest(unittest.TestCase):
    def test_axis_angle_rotates_a_vector(self):
        q = Quat.from_axis_angle(Vec3(0, 0, 1), math.pi / 2)
        got = q.rotate(Vec3(1, 0, 0))
        self.assertAlmostEqual(got.x, 0.0)
        self.assertAlmostEqual(got.y, 1.0)

    def test_quaternion_matrix_matches_matrix_rotation(self):
        q = Quat.from_axis_angle(Vec3(1, 1, 0).normalized(), 0.9)
        m = Mat4.rotation_axis(Vec3(1, 1, 0).normalized(), 0.9)
        point = Vec3(0.5, -1.0, 2.0)
        self.assertEqual(q.to_mat4().transform_point(point), m.transform_point(point))

    def test_multiplication_composes_in_order(self):
        a = Quat.from_axis_angle(Vec3(0, 1, 0), 0.5)
        b = Quat.from_axis_angle(Vec3(1, 0, 0), 0.25)
        point = Vec3(1, 2, 3)
        self.assertEqual((a * b).rotate(point), a.rotate(b.rotate(point)))

    def test_slerp_endpoints(self):
        a = Quat.identity()
        b = Quat.from_axis_angle(Vec3(0, 1, 0), 1.0)
        self.assertEqual(a.slerp(b, 0.0), a)
        self.assertTrue(a.slerp(b, 1.0).almost_equal(b))


if __name__ == "__main__":
    unittest.main()
