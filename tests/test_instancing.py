"""Game-agnostic tests for hardware-instancing grouping."""

import unittest

from keystone.geometry import Material
from keystone.gpu.instancing import group_instances, plan_instanced
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.scene import Node, Scene, Transform


def make_scene(count: int = 3, same_material: bool = True) -> tuple[Scene, object, object]:
    scene = Scene()
    mesh = cube(1.0)
    material = Material(color=Vec3(0.8, 0.2, 0.2))
    for index in range(count):
        scene.add(
            Node(
                f"box-{index}",
                transform=Transform(position=Vec3(float(index) * 2.0, 0.0, 0.0)),
                mesh=mesh,
                material=material if same_material else Material(color=Vec3(index / 10.0, 0.2, 0.2)),
            )
        )
    return scene, mesh, material


class PlanInstancedTest(unittest.TestCase):
    def test_groups_identical_payloads(self):
        scene, _mesh, _material = make_scene(4, same_material=True)
        plan = plan_instanced(scene)
        self.assertEqual(plan["schema"], 1)
        self.assertEqual(plan["groups"], 1)
        self.assertEqual(plan["draw_calls"], 4)
        self.assertEqual(plan["instanced_calls"], 1)
        self.assertEqual(plan["saved_calls"], 3)
        self.assertEqual(plan["instances"], 4)
        self.assertEqual(plan["batches"][0]["count"], 4)
        self.assertEqual(len(plan["batches"][0]["matrices"]), 4)

    def test_separates_distinct_materials(self):
        scene, _mesh, _material = make_scene(3, same_material=False)
        plan = plan_instanced(scene)
        self.assertEqual(plan["groups"], 3)
        self.assertEqual(plan["instanced_calls"], 3)
        self.assertEqual(plan["saved_calls"], 0)
        self.assertEqual(plan["instances"], 0)

    def test_ignores_invisible_and_missing_mesh(self):
        scene, _mesh, _material = make_scene(2, same_material=True)
        hidden = Node("hidden", mesh=cube(1.0), material=Material())
        hidden.visible = False
        scene.add(hidden)
        scene.add(Node("empty"))
        plan = plan_instanced(scene)
        self.assertEqual(plan["draw_calls"], 2)

    def test_ordering_is_deterministic(self):
        first, _m, _mat = make_scene(5, same_material=True)
        second, _m2, _mat2 = make_scene(5, same_material=True)
        self.assertEqual(plan_instanced(first)["batches"], plan_instanced(second)["batches"])
        groups = group_instances(first)
        keys = [node.id or node.name for node in groups[0]["nodes"]]
        self.assertEqual(keys, sorted(keys))

    def test_matrices_follow_world_transforms(self):
        scene, _mesh, _material = make_scene(2, same_material=True)
        groups = group_instances(scene)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["models"]), 2)
        self.assertNotEqual(groups[0]["models"][0].flat(), groups[0]["models"][1].flat())

    def test_empty_scene(self):
        plan = plan_instanced(Scene())
        self.assertEqual(plan["groups"], 0)
        self.assertEqual(plan["draw_calls"], 0)
        self.assertEqual(plan["saved_calls"], 0)


if __name__ == "__main__":
    unittest.main()
