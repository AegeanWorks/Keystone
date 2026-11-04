"""Tests for skin-aware batch merging: identical rigs merge into one draw."""

import unittest

from keystone.batch import merge_batches, plan_batches
from keystone.geometry import Material, MeshData
from keystone.math3d import Vec3
from keystone.scene import Node, Scene, Transform
from keystone.skin import bone_matrices, skin_mesh

IDENTITY_16 = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _rig_mesh(**overrides):
    kwargs = {
        "positions": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
        "normals": ((0.0, 0.0, 1.0),) * 4,
        "indices": (0, 1, 2, 0, 2, 3),
        "joints": ((0, 1),) * 4,
        "weights": ((0.5, 0.5),) * 4,
        "skin_joints": ("j0", "j1"),
        "skin_inverse_bind": (IDENTITY_16, IDENTITY_16),
    }
    kwargs.update(overrides)
    return MeshData(**kwargs)


def _rig_scene(transform=None, material=None, mesh=None):
    scene = Scene()
    scene.add(Node("j0", id="j0"))
    scene.add(Node("j1", id="j1", transform=Transform(position=Vec3(0.0, 1.0, 0.0))))
    mesh = mesh or _rig_mesh()
    material = material or Material()
    placement = Transform(position=Vec3(2.0, 0.0, 0.0)) if transform is None else transform
    scene.add(Node("rig-a", id="rig-a", transform=placement, mesh=mesh, material=material))
    scene.add(Node("rig-b", id="rig-b", transform=placement, mesh=mesh, material=material))
    return scene


class SkinMergeTest(unittest.TestCase):
    def test_merge_combines_same_rig_groups(self):
        merged = merge_batches(_rig_scene())
        self.assertEqual(merged["schema"], 1)
        self.assertEqual(len(merged["merged"]), 1)
        group = merged["merged"][0]
        self.assertEqual(group["count"], 2)
        self.assertEqual(group["triangles"], 4)
        self.assertEqual(merged["skin_merged_calls"], 1)
        self.assertEqual(merged["skin_saved_calls"], 1)
        self.assertTrue(group["mesh"].skinned)
        self.assertEqual(group["mesh"].skin_joints, ("j0", "j1"))

    def test_merged_deformation_matches_oracle_exactly(self):
        scene = _rig_scene()
        merged = merge_batches(scene)
        mesh = merged["merged"][0]["mesh"]
        bones = bone_matrices(scene, mesh)
        posed = skin_mesh(mesh, bones)
        single = skin_mesh(_rig_mesh(), bones)
        self.assertEqual(posed.positions, single.positions + single.positions)
        self.assertEqual(posed.normals, single.normals + single.normals)
        world = scene.find(name="rig-a").world_matrix()
        for got, want in zip(posed.positions, single.positions + single.positions):
            self.assertEqual(world * Vec3(*got), world * Vec3(*want))

    def test_separates_by_material_joints_and_transform(self):
        scene = _rig_scene()
        base_material = scene.find(name="rig-a").material
        base_transform = Transform(position=Vec3(2.0, 0.0, 0.0))
        other_material = Material(color=Vec3(0.2, 0.3, 0.4))
        scene.add(Node("rig-c", id="rig-c", transform=base_transform,
                       mesh=_rig_mesh(), material=other_material))
        other_joints = _rig_mesh(skin_joints=("j0", "j2"), skin_inverse_bind=(IDENTITY_16, IDENTITY_16))
        scene.add(Node("j2", id="j2"))
        scene.add(Node("rig-d", id="rig-d", transform=base_transform,
                       mesh=other_joints, material=base_material))
        scene.add(Node("rig-e", id="rig-e", transform=Transform(position=Vec3(5.0, 0.0, 0.0)),
                       mesh=_rig_mesh(), material=base_material))
        merged = merge_batches(scene)
        self.assertEqual(merged["skin_merged_calls"], 4)
        self.assertEqual(merged["skin_saved_calls"], 1)

    def test_plan_reports_skin_counters_without_moving_main_groups(self):
        plan = plan_batches(_rig_scene())
        self.assertEqual(plan["schema"], 1)
        self.assertEqual(plan["draw_calls"], 0)
        self.assertEqual(plan["skin_calls"], 2)
        self.assertEqual(plan["skin_groups"], 1)
        self.assertEqual(plan["skin_triangles"], 4)

    def test_exclude_applies_to_skin_groups(self):
        merged = merge_batches(_rig_scene(), exclude={"rig-a"})
        self.assertEqual(merged["skin_merged_calls"], 1)
        self.assertEqual(merged["skin_saved_calls"], 1)
        self.assertEqual(merged["merged"][0]["count"], 1)

    def test_builder_rejects_mismatched_skin(self):
        from keystone.mesh_builder import MeshBuilder

        builder = MeshBuilder()
        builder.add_skinned_mesh(_rig_mesh())
        with self.assertRaises(ValueError):
            builder.add_skinned_mesh(_rig_mesh(skin_joints=("j0", "j9"),
                                              skin_inverse_bind=(IDENTITY_16, IDENTITY_16)))
        with self.assertRaises(ValueError):
            builder.add_skinned_mesh(MeshData(
                positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                normals=((0.0, 0.0, 1.0),) * 3,
                indices=(0, 1, 2),
            ))


class RigGame:
    """Minimal game module with two identical rigs for pixel-parity proofs."""

    name = "rig-pair"

    def __init__(self, merged: bool = False) -> None:
        self.scene = Scene()
        self.merged = merged

    def build_scene(self) -> Scene:
        self.scene = _rig_scene()
        if self.merged:
            from keystone.batch import merge_batches as do_merge

            group = do_merge(self.scene)["merged"][0]
            rigged = Scene()
            rigged.add(Node("j0", id="j0"))
            rigged.add(Node("j1", id="j1", transform=Transform(position=Vec3(0.0, 1.0, 0.0))))
            rigged.add(Node("merged", id="merged",
                            transform=Transform(position=Vec3(2.0, 0.0, 0.0)),
                            mesh=group["mesh"], material=group["material"]))
            self.scene = rigged
        return self.scene

    def update(self, dt: float, actions: object) -> None:
        return None

    def snapshot(self) -> dict:
        return {"time": 0.0}

    def actions(self) -> dict:
        return {}

    def status(self) -> str:
        return "ok"


class SkinPixelParityTest(unittest.TestCase):
    def test_merged_scene_renders_identical_pixels(self):
        import tempfile
        from pathlib import Path

        from keystone.app import Engine

        with tempfile.TemporaryDirectory() as directory:
            plain_png = Path(directory) / "plain.png"
            merged_png = Path(directory) / "merged.png"
            plain = Engine(RigGame(merged=False), 320, 240, visible=False)
            try:
                plain.capture(plain_png, None)
            finally:
                plain.close()
            merged = Engine(RigGame(merged=True), 320, 240, visible=False)
            try:
                merged.capture(merged_png, None)
            finally:
                merged.close()
            self.assertEqual(plain_png.read_bytes(), merged_png.read_bytes())


if __name__ == "__main__":
    unittest.main()
