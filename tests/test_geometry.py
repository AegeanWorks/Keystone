"""Unit tests for indexed meshes, built-in primitives and the OBJ loader."""

import math
import tempfile
import unittest
from pathlib import Path

from keystone.geometry import Material, MeshData
from keystone.mesh_builder import MeshBuilder
from keystone.obj_loader import load_obj, parse_obj
from keystone.primitives import cone, cube, cylinder, plane, sphere

CUBE_OBJ = """\
# a unit quad
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
f 1 2 3 4
"""

NORMAL_OBJ = """\
v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 1
f 1//1 2//1 3//1
"""


class MeshDataTest(unittest.TestCase):
    def test_rejects_mismatched_attribute_counts(self):
        with self.assertRaises(ValueError):
            MeshData(positions=((0, 0, 0),), normals=(), indices=())

    def test_rejects_out_of_range_index(self):
        with self.assertRaises(ValueError):
            MeshData(
                positions=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
                normals=((0, 0, 1),) * 3,
                indices=(0, 1, 3),
            )

    def test_rejects_malformed_position_tuples_at_construction(self):
        with self.assertRaises(ValueError):
            MeshData(
                positions=((0, 0), (1, 0), (0, 1)),
                normals=((0, 0, 1),) * 3,
                indices=(0, 1, 2),
            )
        with self.assertRaises(ValueError):
            MeshData(
                positions=((0, 0, float("nan")), (1, 0, 0), (0, 1, 0)),
                normals=((0, 0, 1),) * 3,
                indices=(0, 1, 2),
            )
        with self.assertRaises(ValueError):
            MeshData(
                positions=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
                normals=((0, 0, 1),) * 3,
                uvs=((0, 0, 0), (1, 0), (0, 1)),
                indices=(0, 1, 2),
            )

    def test_bounds_and_counts(self):
        mesh = cube(2.0)
        self.assertEqual(mesh.vertex_count(), 24)
        self.assertEqual(mesh.triangle_count(), 12)
        low, high = mesh.bounds()
        self.assertEqual(low, (-1.0, -1.0, -1.0))
        self.assertEqual(high, (1.0, 1.0, 1.0))

    def test_interleaved_has_eleven_floats_per_vertex(self):
        stream = cube(1.0).interleaved()
        self.assertEqual(len(stream), 24 * 11)

    def test_vertex_colors_follow_the_uvs(self):
        mesh = MeshData(
            positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            normals=((0.0, 0.0, 1.0),) * 3,
            colors=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            indices=(0, 1, 2),
        )
        self.assertEqual(mesh.interleaved()[8:11], (1.0, 0.0, 0.0))

    def test_rejects_mismatched_vertex_colors(self):
        with self.assertRaises(ValueError):
            MeshData(
                positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                normals=((0.0, 0.0, 1.0),) * 3,
                colors=((1.0, 1.0, 1.0),),
                indices=(0, 1, 2),
            )


class PrimitiveTest(unittest.TestCase):
    def test_cube_normals_are_unit_and_outward(self):
        mesh = cube(2.0)
        for position, normal in zip(mesh.positions, mesh.normals):
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in normal)), 1.0)
            self.assertGreater(sum(p * n for p, n in zip(position, normal)), 0.0)

    def test_plane_faces_up_with_six_indices(self):
        mesh = plane(10.0)
        self.assertEqual(mesh.vertex_count(), 4)
        self.assertEqual(mesh.indices, (0, 1, 2, 0, 2, 3))
        self.assertEqual(mesh.normals[0], (0.0, 1.0, 0.0))

    def test_sphere_positions_lie_on_radius_and_normals_are_unit(self):
        mesh = sphere(2.0, segments=12, rings=6)
        for position, normal in zip(mesh.positions, mesh.normals):
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in position)), 2.0)
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in normal)), 1.0)
        self.assertEqual(mesh.triangle_count(), 12 * 6 * 2)

    def test_primitives_reject_invalid_sizes(self):
        with self.assertRaises(ValueError):
            cube(0.0)
        with self.assertRaises(ValueError):
            sphere(1.0, segments=2)
        with self.assertRaises(ValueError):
            plane(-1.0)

    def test_cone_and_cylinder_are_unit_and_bounded(self):
        for mesh in (cone(1.0, 2.0, segments=8), cylinder(1.0, 2.0, segments=8)):
            for normal in mesh.normals:
                self.assertAlmostEqual(math.sqrt(sum(c * c for c in normal)), 1.0)
            low, high = mesh.bounds()
            self.assertAlmostEqual(low[1], -1.0)
            self.assertAlmostEqual(high[1], 1.0)

    def test_cone_side_normals_point_outward(self):
        mesh = cone(1.0, 2.0, segments=8)
        self.assertGreater(mesh.normals[0][0], 0.0)
        self.assertGreater(mesh.normals[0][1], 0.0)

    def test_cone_winding_matches_stored_normals(self):
        from keystone.math3d import Vec3

        mesh = cone(1.0, 2.0, segments=4)
        for tri in range(8):
            a = Vec3(*mesh.positions[mesh.indices[tri * 3]])
            b = Vec3(*mesh.positions[mesh.indices[tri * 3 + 1]])
            c = Vec3(*mesh.positions[mesh.indices[tri * 3 + 2]])
            winding = (b - a).cross(c - a).normalized()
            stored = Vec3(*mesh.normals[mesh.indices[tri * 3]])
            self.assertGreater(winding.dot(stored), 0.0)


class MeshBuilderTest(unittest.TestCase):
    def test_box_has_24_vertices_and_36_indices(self):
        mesh = MeshBuilder().add_box(0, 0, 0, 2, 4, 6).build()
        self.assertEqual(mesh.vertex_count(), 24)
        self.assertEqual(mesh.triangle_count(), 12)
        self.assertEqual(len(mesh.colors), 24)
        self.assertEqual(mesh.bounds(), ((-1.0, -2.0, -3.0), (1.0, 2.0, 3.0)))

    def test_quad_normal_follows_winding(self):
        mesh = (
            MeshBuilder()
            .add_quad(
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 1.0),
                (1.0, 0.0, 0.0),
            )
            .build()
        )
        self.assertEqual(mesh.normals[0], (0.0, 1.0, 0.0))

    def test_degenerate_quad_is_rejected(self):
        with self.assertRaises(ValueError):
            MeshBuilder().add_quad(
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (2.0, 0.0, 0.0),
                (3.0, 0.0, 0.0),
            )

    def test_add_mesh_merges_counts_and_offsets(self):
        builder = MeshBuilder()
        builder.add_mesh(cube(1.0), offset=(5.0, 0.0, 0.0), scale=2.0, color=(0.5, 1.0, 0.5))
        builder.add_mesh(cube(1.0), offset=(-5.0, 0.0, 0.0))
        mesh = builder.build()
        self.assertEqual(mesh.vertex_count(), 48)
        self.assertEqual(mesh.triangle_count(), 24)
        low, high = mesh.bounds()
        self.assertEqual(low[0], -5.5)
        self.assertEqual(high[0], 6.0)
        self.assertEqual(mesh.colors[0], (0.5, 1.0, 0.5))

    def test_add_mesh_matrix_uses_inverse_transpose_normals(self):
        from keystone.math3d import Mat4

        diagonal = MeshData(
            positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            normals=((0.70710678, 0.70710678, 0.0),) * 3,
            indices=(0, 1, 2),
        )
        mesh = MeshBuilder().add_mesh_matrix(diagonal, Mat4.scale(2.0, 1.0, 1.0)).build()
        self.assertAlmostEqual(mesh.normals[0][0], 0.44721360, places=5)
        self.assertAlmostEqual(mesh.normals[0][1], 0.89442719, places=5)


class ObjLoaderTest(unittest.TestCase):
    def test_quad_is_triangulated(self):
        mesh = parse_obj(CUBE_OBJ)
        self.assertEqual(mesh.vertex_count(), 4)
        self.assertEqual(mesh.indices, (0, 1, 2, 0, 2, 3))

    def test_normals_are_computed_when_absent(self):
        mesh = parse_obj(CUBE_OBJ)
        for normal in mesh.normals:
            self.assertAlmostEqual(normal[2], 1.0)

    def test_authored_normals_are_kept(self):
        mesh = parse_obj(NORMAL_OBJ)
        self.assertEqual(mesh.normals, ((0.0, 0.0, 1.0),) * 3)

    def test_negative_indices_are_relative(self):
        mesh = parse_obj(CUBE_OBJ.replace("f 1 2 3 4", "f -4 -3 -2 -1"))
        self.assertEqual(mesh.indices, (0, 1, 2, 0, 2, 3))

    def test_missing_file_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileNotFoundError):
            load_obj(Path(directory) / "missing.obj")

    def test_bad_index_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 9\n")

    def test_extra_face_slash_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1/1/1/extra 2 3\n")

    def test_vertex_weight_is_applied(self):
        mesh = parse_obj("v 0 0 0 1\nv 2 0 0 2\nv 0 2 0 2\nf 1 2 3\n")
        self.assertEqual(mesh.positions[1], (1.0, 0.0, 0.0))
        self.assertEqual(mesh.positions[2], (0.0, 1.0, 0.0))

    def test_vertex_junk_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_obj("v 0 0 0 extra\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        with self.assertRaises(ValueError):
            parse_obj("v 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")

    def test_file_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quad.obj"
            path.write_text(CUBE_OBJ, encoding="utf-8")
            self.assertEqual(load_obj(path).indices, (0, 1, 2, 0, 2, 3))


class MaterialTest(unittest.TestCase):
    def test_defaults_are_valid(self):
        material = Material()
        self.assertGreater(material.shininess, 0.0)
        self.assertEqual(material.checker_scale, 0.0)

    def test_rejects_negative_specular(self):
        with self.assertRaises(ValueError):
            Material(specular=-0.1)

    def test_rejects_negative_checker_scale(self):
        with self.assertRaises(ValueError):
            Material(checker_scale=-1.0)


if __name__ == "__main__":
    unittest.main()
