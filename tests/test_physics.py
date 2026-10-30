"""Tests for generic ray and collision primitives."""

import unittest

from keystone.math3d import Vec3
from keystone.physics import (
    AABB,
    Ray,
    Sphere,
    aabb_overlap,
    ray_aabb,
    ray_sphere,
    resolve_sphere_aabb,
    sphere_aabb_overlap,
)


class PhysicsTest(unittest.TestCase):
    def test_ray_hits_aabb_and_sphere(self):
        ray = Ray(Vec3(0, 0, 0), Vec3(0, 0, 1))
        self.assertAlmostEqual(ray_aabb(ray, AABB(Vec3(0, 0, 5), Vec3(1, 1, 1))), 4.0)
        self.assertAlmostEqual(ray_sphere(ray, Sphere(Vec3(0, 0, 5), 1.0)), 4.0)

    def test_rays_miss(self):
        ray = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        self.assertIsNone(ray_aabb(ray, AABB(Vec3(0, 0, 5), Vec3(1, 1, 1))))
        self.assertIsNone(ray_sphere(ray, Sphere(Vec3(0, 0, 5), 1.0)))

    def test_ray_validation(self):
        with self.assertRaises(ValueError):
            Ray(Vec3(), Vec3())

    def test_overlap_and_sphere_pushout(self):
        box = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        self.assertTrue(aabb_overlap(box, AABB(Vec3(1.5, 0, 0), Vec3(1, 1, 1))))
        sphere = Sphere(Vec3(1.5, 0, 0), 0.6)
        self.assertTrue(sphere_aabb_overlap(sphere, box))
        pushed = resolve_sphere_aabb(sphere, box)
        self.assertGreaterEqual(pushed.x, 1.6 - 1e-9)

    def test_non_overlapping_sphere_is_unchanged(self):
        box = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        sphere = Sphere(Vec3(10, 0, 0), 0.5)
        self.assertEqual(resolve_sphere_aabb(sphere, box), sphere.center)


if __name__ == "__main__":
    unittest.main()
