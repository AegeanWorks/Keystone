"""Unit tests for the Keystone scene graph and perspective camera."""

import math
import unittest

from keystone.camera import PerspectiveCamera
from keystone.math3d import Mat4, Quat, Vec3
from keystone.scene import DirectionalLight, Node, Scene, Transform


class TransformTest(unittest.TestCase):
    def test_matrix_applies_scale_then_rotation_then_translation(self):
        transform = Transform(
            position=Vec3(1, 2, 3),
            rotation=Quat.from_axis_angle(Vec3(0, 0, 1), math.pi / 2),
            scale=Vec3(2, 2, 2),
        )
        got = transform.matrix().transform_point(Vec3(1, 0, 0))
        self.assertAlmostEqual(got.x, 1.0)
        self.assertAlmostEqual(got.y, 4.0)
        self.assertAlmostEqual(got.z, 3.0)

    def test_default_transform_is_identity(self):
        self.assertEqual(Transform().matrix(), Mat4.identity())


class NodeTest(unittest.TestCase):
    def test_child_world_matrix_composes_with_parent(self):
        parent = Node("parent", Transform(position=Vec3(10, 0, 0)))
        child = Node("child", Transform(position=Vec3(0, 5, 0)))
        parent.add_child(child)
        got = child.world_matrix().transform_point(Vec3(0, 0, 0))
        self.assertEqual(got, Vec3(10, 5, 0))

    def test_add_child_reparents_instead_of_duplicating(self):
        first = Node("first")
        second = Node("second")
        child = Node("child")
        first.add_child(child)
        second.add_child(child)
        self.assertEqual(first.children, [])
        self.assertIs(child.parent, second)
        self.assertEqual(second.children, [child])

    def test_remove_child_clears_parent(self):
        parent = Node("parent")
        child = Node("child")
        parent.add_child(child)
        parent.remove_child(child)
        self.assertEqual(parent.children, [])
        self.assertIsNone(child.parent)

    def test_traverse_is_depth_first_in_insertion_order(self):
        root = Node("root")
        a = Node("a")
        b = Node("b")
        a_child = Node("a-child")
        root.add_child(a)
        root.add_child(b)
        a.add_child(a_child)
        self.assertEqual([n.name for n in root.traverse()], ["root", "a", "a-child", "b"])

    def test_add_child_rejects_self_and_cycles(self):
        root = Node("root")
        child = Node("child")
        root.add_child(child)
        with self.assertRaises(ValueError):
            root.add_child(root)
        with self.assertRaises(ValueError):
            child.add_child(root)

    def test_remove_child_rejects_a_stranger(self):
        with self.assertRaises(ValueError):
            Node("parent").remove_child(Node("stranger"))

    def test_world_visible_respects_hidden_ancestor(self):
        parent = Node("parent")
        child = Node("child")
        parent.add_child(child)
        self.assertTrue(child.world_visible())
        parent.visible = False
        self.assertFalse(child.world_visible())


class CameraTest(unittest.TestCase):
    def test_forward_yaw_zero_is_minus_z(self):
        forward = PerspectiveCamera().forward()
        self.assertAlmostEqual(forward.x, 0.0)
        self.assertAlmostEqual(forward.z, -1.0)

    def test_forward_yaw_90_points_positive_x(self):
        forward = PerspectiveCamera(yaw=math.pi / 2).forward()
        self.assertAlmostEqual(forward.x, 1.0, places=6)
        self.assertAlmostEqual(forward.z, 0.0, places=6)

    def test_view_puts_camera_origin_at_world_position(self):
        camera = PerspectiveCamera(position=Vec3(0, 0, 5))
        view = camera.view_matrix()
        self.assertEqual(view.transform_point(camera.position), Vec3(0, 0, 0))

    def test_projection_aspect_changes_horizontal_extent(self):
        camera = PerspectiveCamera()
        wide = camera.projection_matrix(2.0)
        square = camera.projection_matrix(1.0)
        self.assertLess(wide[0], square[0])
        self.assertAlmostEqual(wide[5], square[5])

    def test_move_follows_forward_direction(self):
        camera = PerspectiveCamera(position=Vec3(0, 0, 0), yaw=math.pi / 2)
        camera.move(2.0, 0.0, 0.0)
        self.assertAlmostEqual(camera.position.x, 2.0, places=6)
        self.assertAlmostEqual(camera.position.z, 0.0, places=6)

    def test_rotate_clamps_pitch(self):
        camera = PerspectiveCamera()
        camera.rotate(0.0, math.pi)
        self.assertLessEqual(abs(camera.pitch), math.radians(89.0) + 1e-9)

    def test_look_at_rejects_its_own_position(self):
        with self.assertRaises(ValueError):
            PerspectiveCamera().look_at(Vec3(0, 0, 0))

    def test_projection_rejects_invalid_aspect(self):
        with self.assertRaises(ValueError):
            PerspectiveCamera().projection_matrix(0.0)

    def test_look_at_points_forward_at_target(self):
        camera = PerspectiveCamera(position=Vec3(0, 0, 5))
        camera.look_at(Vec3(5, 0, 5))
        forward = camera.forward()
        self.assertAlmostEqual(forward.x, 1.0, places=6)
        self.assertAlmostEqual(forward.z, 0.0, places=6)


class SceneTest(unittest.TestCase):
    def test_scene_traverse_starts_at_root(self):
        scene = Scene()
        node = Node("mesh")
        scene.add(node)
        self.assertEqual([n.name for n in scene.traverse()], ["", "mesh"])

    def test_directional_light_normalizes_lookup_direction(self):
        light = DirectionalLight(direction=Vec3(0, -2, 0))
        self.assertAlmostEqual(light.unit_direction().y, -1.0)


if __name__ == "__main__":
    unittest.main()
