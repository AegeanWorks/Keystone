"""Unit tests for the Keystone scene graph and perspective camera."""

import math
import unittest
from dataclasses import dataclass

from keystone.camera import PerspectiveCamera
from keystone.math3d import Mat4, Quat, Vec3
from keystone.scene import DirectionalLight, Node, PointLight, Scene, Transform


@dataclass(frozen=True)
class Health:
    value: int


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

    def test_add_child_rejects_duplicate_ids_at_write_time(self):
        parent = Node("parent")
        parent.add_child(Node("a", id="dup"))
        with self.assertRaises(ValueError):
            parent.add_child(Node("b", id="dup"))
        with self.assertRaises(ValueError):
            Node("root", id="dup").add_child(Node("leaf", id="dup"))

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


class NodeIdentityTest(unittest.TestCase):
    def test_scene_assigns_unique_ids_on_attach(self):
        scene = Scene()
        first = scene.add(Node("first"))
        second = scene.add(Node("second"))
        self.assertEqual(scene.root.id, "root")
        self.assertEqual(first.id, "node-1")
        self.assertEqual(second.id, "node-2")

    def test_ids_are_scene_local_and_survive_reparenting(self):
        first = Scene()
        second = Scene()
        moved = first.add(Node("moved"))
        parent = first.add(Node("parent"))
        original = moved.id
        first.root.add_child(moved)
        parent.add_child(moved)
        self.assertEqual(moved.id, original)
        self.assertEqual(second.add(Node("other")).id, "node-1")

    def test_explicit_id_is_preserved_and_findable(self):
        scene = Scene()
        hero = scene.add(Node("hero", id="hero-1"))
        self.assertEqual(hero.id, "hero-1")
        self.assertIs(scene.find_by_id("hero-1"), hero)
        self.assertIsNone(scene.find_by_id("missing"))

    def test_duplicate_explicit_id_is_rejected_without_attaching(self):
        scene = Scene()
        scene.add(Node("first", id="duplicate"))
        with self.assertRaises(ValueError):
            scene.add(Node("second", id="duplicate"))
        self.assertEqual(scene.query(name="second"), [])

    def test_scene_add_rejects_attached_node_without_moving_it(self):
        scene = Scene()
        parent = scene.add(Node("parent"))
        child = Node("child")
        parent.add_child(child)
        with self.assertRaises(ValueError):
            scene.add(child)
        self.assertIs(child.parent, parent)
        self.assertIn(child, parent.children)

    def test_tags_are_copied_and_queryable(self):
        tags = {"enemy"}
        node = Node("raider", tags=tags)
        tags.add("later")
        node.add_tag("boss")
        self.assertEqual(node.tags, {"enemy", "boss"})
        scene = Scene()
        scene.add(node)
        self.assertEqual(scene.query(tag="boss"), [node])
        node.remove_tag("boss")
        self.assertEqual(scene.query(tag="boss"), [])

    def test_layer_and_component_queries_filter_attached_nodes(self):
        scene = Scene()
        actor = scene.add(Node("actor", layer="actors"))
        prop = scene.add(Node("prop", layer="props"))
        actor.add_component(Health(5))
        self.assertEqual(scene.query(layer="actors"), [actor])
        self.assertEqual(scene.query(component=Health), [actor])
        self.assertEqual(scene.query(tag="missing"), [])
        self.assertIs(scene.find(name="act"), None)
        self.assertIs(scene.find(name="actor"), actor)
        self.assertIs(scene.find(layer="props"), prop)

    def test_component_access_and_removal(self):
        node = Node("actor")
        node.add_component(Health(10))
        self.assertTrue(node.has_component(Health))
        self.assertEqual(node.get_component(Health).value, 10)
        node.remove_component(Health)
        self.assertFalse(node.has_component(Health))
        with self.assertRaises(KeyError):
            node.require_component(Health)

    def test_invalid_identity_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            Node("bad", layer="")
        with self.assertRaises(ValueError):
            Node("bad", tags={""})
        with self.assertRaises(TypeError):
            Node("bad", tags="enemy")
        with self.assertRaises(TypeError):
            Node("bad").add_component(None)
        with self.assertRaises(TypeError):
            Node("bad", components={Health: "bad"})


class CameraTest(unittest.TestCase):
    def test_up_is_orthonormal_to_forward_and_right(self):
        camera = PerspectiveCamera(yaw=0.4, pitch=0.3)
        forward = camera.forward()
        right = camera.right()
        up = camera.up()
        for vector in (forward, right, up):
            self.assertAlmostEqual(vector.length(), 1.0, places=6)
        self.assertAlmostEqual(forward.dot(right), 0.0, places=6)
        self.assertAlmostEqual(forward.dot(up), 0.0, places=6)
        self.assertAlmostEqual(right.dot(up), 0.0, places=6)
        # Right-handed with Y-up and forward down -Z: up x right == forward.
        cross = up.cross(right)
        self.assertAlmostEqual(cross.x, forward.x, places=6)
        self.assertAlmostEqual(cross.y, forward.y, places=6)
        self.assertAlmostEqual(cross.z, forward.z, places=6)

    def test_basis_is_a_right_handed_frame(self):
        camera = PerspectiveCamera(yaw=1.1, pitch=-0.2)
        forward, right, up = camera.basis()
        self.assertEqual(forward, camera.forward())
        self.assertEqual(right, camera.right())
        self.assertEqual(up, camera.up())
        self.assertAlmostEqual(right.dot(up), 0.0, places=6)

    def test_up_stays_level_when_pitch_is_zero(self):
        up = PerspectiveCamera().up()
        self.assertAlmostEqual(up.x, 0.0, places=6)
        self.assertAlmostEqual(up.y, 1.0, places=6)
        self.assertAlmostEqual(up.z, 0.0, places=6)

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

    def test_direct_pitch_construction_stays_usable(self):
        camera = PerspectiveCamera(pitch=math.pi / 2)
        camera.view_matrix()

    def test_direct_pitch_assignment_is_clamped_for_rendering(self):
        camera = PerspectiveCamera()
        camera.pitch = 3.0
        camera.view_matrix()
        self.assertLessEqual(camera.forward().y, math.sin(math.radians(89.0)) + 1e-9)

    def test_look_at_straight_up_stays_usable(self):
        camera = PerspectiveCamera(position=Vec3(0, 0, 5))
        camera.look_at(Vec3(0, 10, 5))
        camera.view_matrix()


class SceneTest(unittest.TestCase):
    def test_scene_traverse_starts_at_root(self):
        scene = Scene()
        node = Node("mesh")
        scene.add(node)
        self.assertEqual([n.name for n in scene.traverse()], ["", "mesh"])

    def test_scene_has_a_sky_color_distinct_from_the_horizon(self):
        scene = Scene()
        self.assertNotEqual(scene.sky, scene.background)

    def test_point_light_validates_its_radius_and_intensity(self):
        with self.assertRaises(ValueError):
            PointLight(radius=0.0)
        with self.assertRaises(ValueError):
            PointLight(intensity=-1.0)

    def test_directional_light_normalizes_lookup_direction(self):
        light = DirectionalLight(direction=Vec3(0, -2, 0))
        self.assertAlmostEqual(light.unit_direction().y, -1.0)

    def test_node_validates_public_construction(self):
        with self.assertRaises(TypeError):
            Node(5)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Node("n", transform=None)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Node("n", visible="false")  # type: ignore[arg-type]

    def test_node_parent_and_children_are_reciprocal(self):
        parent = Node("p")
        child = Node("c", parent=parent)
        self.assertEqual(parent.children, [child])
        self.assertIs(child.parent, parent)
        parent2 = Node("p2", children=[Node("c2")])
        self.assertIs(parent2.children[0].parent, parent2)

    def test_transform_rejects_non_finite_and_zero_rotation(self):
        with self.assertRaises(ValueError):
            Transform(position=Vec3(float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            Transform(rotation=Quat(0.0, 0.0, 0.0, 0.0))

    def test_traverse_is_iterative_and_tolerates_removal(self):
        scene = Scene()
        scene.add(Node("a", id="a"))
        scene.add(Node("b", id="b"))
        scene.add(Node("c", id="c"))
        seen = []
        for node in scene.traverse():
            seen.append(node.name)
            if node.name == "a":
                node.parent.remove_child(node)
        self.assertEqual(seen, ["", "a", "b", "c"])

        root = Node("root")
        current = root
        for index in range(2000):
            child = Node(f"n{index}")
            current.add_child(child)
            current = child
        self.assertEqual(sum(1 for _ in root.traverse()), 2001)

    def test_lights_reject_non_finite_and_negative_values(self):
        with self.assertRaises(ValueError):
            DirectionalLight(direction=Vec3(float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            DirectionalLight(intensity=-1.0)
        with self.assertRaises(ValueError):
            PointLight(radius=float("nan"))
        with self.assertRaises(ValueError):
            PointLight(intensity=float("inf"))


if __name__ == "__main__":
    unittest.main()
