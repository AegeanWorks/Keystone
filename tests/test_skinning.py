"""Tests for deterministic linear-blend skinning (max 4 influences)."""

import struct
import unittest

from keystone.geometry import MeshData
from keystone.math3d import Mat4, Quat, Vec3
from keystone.scene import Node, Scene, Transform
from keystone.skin import bone_matrices, skin_mesh, skin_point

IDENTITY_16 = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _quad_mesh(**overrides):
    positions = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0))
    normals = ((0.0, 0.0, 1.0),) * 4
    kwargs = {
        "positions": positions,
        "normals": normals,
        "indices": (0, 1, 2, 0, 2, 3),
        "joints": ((0,),) * 4,
        "weights": ((1.0,),) * 4,
        "skin_joints": ("j0",),
        "skin_inverse_bind": (IDENTITY_16,),
    }
    kwargs.update(overrides)
    return MeshData(**kwargs)


class SkinValidationTest(unittest.TestCase):
    def test_unskinned_meshes_stay_legacy(self):
        mesh = MeshData(
            positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            normals=((0.0, 0.0, 1.0),) * 3,
            indices=(0, 1, 2),
        )
        self.assertFalse(mesh.skinned)
        self.assertEqual(len(mesh.interleaved()), 3 * 11)
        with self.assertRaises(ValueError):
            mesh.interleaved_skinned()

    def test_skinned_stream_packs_padded_joints_and_weights(self):
        mesh = _quad_mesh()
        self.assertTrue(mesh.skinned)
        self.assertEqual(len(mesh.interleaved_skinned()), 4 * 19)

    def test_rejects_partial_and_mismatched_skin(self):
        base = {
            "positions": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            "normals": ((0.0, 0.0, 1.0),) * 3,
            "indices": (0, 1, 2),
        }
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,),) * 3)
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,),) * 2, weights=((1.0,),) * 3,
                      skin_joints=("j0",), skin_inverse_bind=(IDENTITY_16,))
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((1,),) * 3, weights=((1.0,),) * 3,
                      skin_joints=("j0",), skin_inverse_bind=(IDENTITY_16,))
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0, 1),) * 3, weights=((0.6,),) * 3,
                      skin_joints=("j0", "j1"), skin_inverse_bind=(IDENTITY_16,) * 2)
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,),) * 3, weights=((0.5,),) * 3,
                      skin_joints=("j0",), skin_inverse_bind=(IDENTITY_16,))
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,) * 5,) * 3, weights=((0.2,) * 5,) * 3,
                      skin_joints=("j0",), skin_inverse_bind=(IDENTITY_16,))
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,),) * 3, weights=((1.0,),) * 3,
                      skin_joints=("j0", "j0"), skin_inverse_bind=(IDENTITY_16,) * 2)
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,),) * 3, weights=((float("nan"),),) * 3,
                      skin_joints=("j0",), skin_inverse_bind=(IDENTITY_16,))
        with self.assertRaises(ValueError):
            MeshData(**base, joints=((0,),) * 3, weights=((float("inf"),),) * 3,
                      skin_joints=("j0",), skin_inverse_bind=(IDENTITY_16,))


class SkinMathTest(unittest.TestCase):
    def test_rigid_identity_keeps_bind_pose(self):
        mesh = _quad_mesh()
        bones = (Mat4(IDENTITY_16),)
        for vertex in range(4):
            position, normal = skin_point(
                Vec3(*mesh.positions[vertex]), Vec3(*mesh.normals[vertex]),
                mesh.joints[vertex], mesh.weights[vertex], bones,
            )
            self.assertAlmostEqual(position.x, mesh.positions[vertex][0])
            self.assertAlmostEqual(position.y, mesh.positions[vertex][1])
            self.assertAlmostEqual(normal.z, 1.0)

    def test_rigid_translation_moves_vertices(self):
        mesh = _quad_mesh()
        bones = (Mat4.translation(2.0, 0.0, 0.0),)
        position, _ = skin_point(Vec3(*mesh.positions[1]), Vec3(0.0, 0.0, 1.0), (0,), (1.0,), bones)
        self.assertAlmostEqual(position.x, 3.0)
        self.assertAlmostEqual(position.y, 0.0)

    def test_half_blend_averages_bones(self):
        _quad_mesh(
            joints=((0, 1),) * 4,
            weights=((0.5, 0.5),) * 4,
            skin_joints=("j0", "j1"),
            skin_inverse_bind=(IDENTITY_16, IDENTITY_16),
        )
        bones = (Mat4(IDENTITY_16), Mat4.translation(2.0, 0.0, 0.0))
        position, _ = skin_point(Vec3(0.0, 0.0, 0.0), Vec3(0.0, 0.0, 1.0), (0, 1), (0.5, 0.5), bones)
        self.assertAlmostEqual(position.x, 1.0)

    def test_bone_rotation_turns_normals(self):
        rotation = Quat(0.7071068, 0.0, 0.0, 0.7071068).normalized().to_mat4()
        bones = (rotation,)
        _, normal = skin_point(Vec3(0.0, 0.0, 0.0), Vec3(1.0, 0.0, 0.0), (0,), (1.0,), bones)
        self.assertAlmostEqual(normal.x, 0.0, places=5)
        self.assertAlmostEqual(normal.y, 1.0, places=5)

    def test_skin_mesh_preserves_layout(self):
        mesh = _quad_mesh()
        deformed = skin_mesh(mesh, (Mat4.translation(1.0, 0.0, 0.0),))
        self.assertEqual(deformed.indices, mesh.indices)
        self.assertTrue(deformed.skinned)
        self.assertAlmostEqual(deformed.positions[0][0], 1.0)

    def test_bone_palette_is_deterministic(self):
        scene = Scene()
        joint = Node("j0", id="j0")
        joint.transform = Transform(position=Vec3(1.0, 2.0, 3.0))
        scene.add(joint)
        mesh = _quad_mesh()
        first = bone_matrices(scene, mesh)
        second = bone_matrices(scene, mesh)
        self.assertEqual(first[0].flat(), second[0].flat())
        self.assertAlmostEqual(first[0][12], 1.0)

    def test_missing_joint_raises_with_fix(self):
        mesh = _quad_mesh()
        with self.assertRaises(ValueError):
            bone_matrices(Scene(), mesh)


class SkinBatchTest(unittest.TestCase):
    def test_merge_skips_skinned_meshes(self):
        from keystone.batch import merge_batches, plan_batches

        scene = Scene()
        skinned = Node("skinned", id="skinned", mesh=_quad_mesh())
        plain = Node(
            "plain",
            id="plain",
            mesh=MeshData(
                positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                normals=((0.0, 0.0, 1.0),) * 3,
                indices=(0, 1, 2),
            ),
        )
        scene.add(skinned)
        scene.add(plain)
        plan = plan_batches(scene)
        self.assertEqual(plan["draw_calls"], 1)
        merged = merge_batches(scene)
        merged_ids = [node for group in merged["merged"] for node in group["nodes"]]
        self.assertNotIn("skinned", merged_ids)
        self.assertIn("plain", merged_ids)


class SkinGltfTest(unittest.TestCase):
    def _skinned_document(self, bad_joint=False, normalized_joints=False):
        positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        joints = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        weights = [1.0, 0.0, 0.0, 0.0, 0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
        indices = [0, 1, 2]
        ibm = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0] * 2
        blob = (
            struct.pack("<9f", *positions)
            + bytes(joints if not bad_joint else [9, 0, 0, 0] + joints[4:])
            + struct.pack("<12f", *weights)
            + struct.pack("<3H", *indices)
            + struct.pack("<32f", *ibm)
        )
        offset = 0

        def view(length):
            nonlocal offset
            result = {"buffer": 0, "byteOffset": offset, "byteLength": length}
            offset += length
            return result

        views = [view(36), view(12), view(48), view(6), view(128)]
        accessors = [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5121, "count": 3, "type": "VEC4",
             "normalized": normalized_joints},
            {"bufferView": 2, "componentType": 5126, "count": 3, "type": "VEC4"},
            {"bufferView": 3, "componentType": 5123, "count": 3, "type": "SCALAR"},
            {"bufferView": 4, "componentType": 5126, "count": 2, "type": "MAT4"},
        ]
        import base64

        return {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0, 1, 2]}],
            "nodes": [
                {"name": "mesh-node", "mesh": 0, "skin": 0},
                {"name": "j0"},
                {"name": "j1", "translation": [1.0, 0.0, 0.0]},
            ],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2}, "indices": 3}]}],
            "skins": [{"joints": [1, 2], "inverseBindMatrices": 4}],
            "accessors": accessors,
            "bufferViews": views,
            "buffers": [{"uri": "data:application/octet-stream;base64," + base64.b64encode(blob).decode(), "byteLength": len(blob)}],
        }

    def test_loads_a_skin(self):
        from keystone.gltf import load_gltf

        imported = load_gltf(self._skinned_document())
        primitive = imported.meshes[0]
        self.assertEqual(len(primitive.joints), 3)
        node = imported.scene.root.children[0]
        mesh = node.mesh
        self.assertTrue(mesh.skinned)
        self.assertEqual(mesh.skin_joints, ("node-1", "node-2"))
        self.assertEqual(len(mesh.skin_inverse_bind), 2)

    def test_rejects_bad_joint_index(self):
        from keystone.gltf import load_gltf

        with self.assertRaises(ValueError):
            load_gltf(self._skinned_document(bad_joint=True))

    def test_rejects_normalized_joints(self):
        from keystone.gltf import load_gltf

        with self.assertRaises(ValueError):
            load_gltf(self._skinned_document(normalized_joints=True))


class SkinRenderTest(unittest.TestCase):
    def _skinned_scene(self):
        scene = Scene()
        scene.camera.position = Vec3(0.0, 3.5, 9.0)
        scene.camera.look_at(Vec3(0.0, 1.2, 0.0))
        joint0 = Node("j0", id="j0")
        joint1 = Node("j1", id="j1")
        joint1.transform = Transform(position=Vec3(1.0, 0.0, 0.0))
        scene.add(joint0)
        scene.add(joint1)
        positions = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0))
        mesh = MeshData(
            positions=positions,
            normals=((0.0, 0.0, 1.0),) * 4,
            indices=(0, 1, 2, 0, 2, 3),
            joints=((0, 1),) * 4,
            weights=((0.5, 0.5),) * 4,
            skin_joints=("j0", "j1"),
            skin_inverse_bind=(IDENTITY_16, IDENTITY_16),
        )
        holder = Node("skinned", id="skinned", mesh=mesh, material=None)
        scene.add(holder)
        return scene

    def test_posed_render_differs_from_bind(self):
        from keystone.gpu.context import GLContext
        from keystone.gpu.renderer import Renderer

        context = GLContext(64, 48, visible=False)
        try:
            renderer = Renderer(64, 48)
            try:
                scene = self._skinned_scene()
                renderer.render(scene)
                bind_pixels = bytes(renderer.read_pixels())
                posed = self._skinned_scene()
                for node in posed.traverse():
                    if node.id == "j1":
                        node.transform = Transform(position=Vec3(3.0, 0.0, 0.0))
                stats = renderer.render(posed)
                posed_pixels = bytes(renderer.read_pixels())
                self.assertNotEqual(bind_pixels, posed_pixels)
                self.assertGreater(stats["draw_calls"], 0)
            finally:
                renderer.release()
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
