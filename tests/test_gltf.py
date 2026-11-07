"""Unit tests for dependency-free glTF 2.0 import."""

import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path

from keystone.gltf import load_gltf
from keystone.math3d import Vec3
from keystone.png import write_png


def _data_uri(data):
    return "data:application/octet-stream;base64," + base64.b64encode(data).decode("ascii")


def _glb_bytes(document, binary_chunk):
    json_data = json.dumps(document).encode("utf-8")
    json_data += b" " * ((4 - len(json_data) % 4) % 4)
    binary_data = binary_chunk + b"\x00" * ((4 - len(binary_chunk) % 4) % 4)
    chunks = struct.pack("<II", len(json_data), 0x4E4F534A) + json_data
    chunks += struct.pack("<II", len(binary_data), 0x004E4942) + binary_data
    return struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks


def _triangle_gltf(*, translation=(0.0, 0.0, 0.0), color=(0.2, 0.4, 0.6), roughness=0.25):
    positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    buffer_data = struct.pack("<" + "f" * len(positions), *positions)
    uri = _data_uri(buffer_data)
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "tri", "mesh": 0, "translation": list(translation)}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(buffer_data), "target": 34962}],
        "buffers": [{"uri": uri, "byteLength": len(buffer_data)}],
        "materials": [{"pbrMetallicRoughness": {"baseColorFactor": [*color, 1.0], "roughnessFactor": roughness}}],
    }


class GltfImportTest(unittest.TestCase):
    def test_loads_a_triangle_mesh_and_material(self):
        imported = load_gltf(_triangle_gltf())
        self.assertEqual(imported.node_count, 1)
        self.assertEqual(len(imported.meshes), 1)
        self.assertEqual(imported.meshes[0].triangle_count(), 1)
        self.assertEqual(imported.materials[0].color, Vec3(0.2, 0.4, 0.6))
        self.assertGreater(imported.materials[0].specular, 0.0)
        node = imported.scene.root.children[0]
        self.assertEqual(node.name, "tri")
        self.assertEqual(node.transform.position, Vec3(0.0, 0.0, 0.0))

    def test_translation_is_preserved(self):
        imported = load_gltf(_triangle_gltf(translation=(2.0, 3.0, 4.0)))
        node = imported.scene.root.children[0]
        self.assertEqual(node.transform.position, Vec3(2.0, 3.0, 4.0))

    def test_loads_from_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.gltf"
            path.write_text(json.dumps(_triangle_gltf()), encoding="utf-8")
            imported = load_gltf(path)
            self.assertEqual(imported.meshes[0].triangle_count(), 1)

    def test_rejects_wrong_version(self):
        document = _triangle_gltf()
        document["asset"]["version"] = "1.0"
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_missing_position(self):
        document = _triangle_gltf()
        del document["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_loads_an_embedded_png_texture(self):
        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "swatch.png"
            pixels = bytes((10, 20, 30, 255, 40, 50, 60, 255, 70, 80, 90, 255, 100, 110, 120, 255))
            write_png(png_path, 2, 2, pixels)
            png_bytes = png_path.read_bytes()
            uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
            document = _triangle_gltf()
            document["images"] = [{"uri": uri, "mimeType": "image/png"}]
            document["textures"] = [{"source": 0}]
            document["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
            imported = load_gltf(document)
            self.assertEqual(len(imported.textures), 1)
            self.assertEqual((imported.textures[0].width, imported.textures[0].height), (2, 2))
            self.assertEqual(imported.materials[0].texture, imported.textures[0])

    def test_loads_an_external_buffer_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
            buffer_data = struct.pack("<" + "f" * len(positions), *positions)
            (root / "mesh.bin").write_bytes(buffer_data)
            document = _triangle_gltf()
            document["buffers"] = [{"uri": "mesh.bin", "byteLength": len(buffer_data)}]
            path = root / "sample.gltf"
            path.write_text(json.dumps(document), encoding="utf-8")
            imported = load_gltf(path)
            self.assertEqual(imported.meshes[0].triangle_count(), 1)

    def test_registers_assets_when_registry_is_provided(self):
        from keystone.assets import AssetRegistry

        registry = AssetRegistry()
        load_gltf(_triangle_gltf(), registry=registry)
        self.assertGreater(len(registry), 0)
        self.assertIn("gltf.mesh.0", registry)

    def test_generated_normals_use_triangle_indices(self):
        positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0]
        indices = [0, 1, 2, 0, 2, 3]
        position_data = struct.pack("<" + "f" * len(positions), *positions)
        index_data = struct.pack("<" + "I" * len(indices), *indices)
        document = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5125, "count": 6, "type": "SCALAR"},
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(position_data)},
                {"buffer": 1, "byteOffset": 0, "byteLength": len(index_data)},
            ],
            "buffers": [
                {"uri": _data_uri(position_data), "byteLength": len(position_data)},
                {"uri": _data_uri(index_data), "byteLength": len(index_data)},
            ],
        }
        mesh = load_gltf(document).meshes[0]
        self.assertEqual(mesh.normals[3], (0.0, 0.0, 1.0))
        self.assertEqual(mesh.triangle_count(), 2)

    def test_normalized_integer_colors_are_converted_to_unit_range(self):
        document = _triangle_gltf()
        colors = bytes((255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255))
        document["buffers"].append({"uri": _data_uri(colors), "byteLength": len(colors)})
        document["bufferViews"].append({"buffer": 1, "byteOffset": 0, "byteLength": len(colors)})
        document["accessors"].append(
            {
                "bufferView": 1,
                "componentType": 5121,
                "count": 3,
                "type": "VEC4",
                "normalized": True,
            }
        )
        document["meshes"][0]["primitives"][0]["attributes"]["COLOR_0"] = 1
        mesh = load_gltf(document).meshes[0]
        self.assertEqual(mesh.colors[0], (1.0, 0.0, 0.0))

    def test_rejects_non_triangle_primitive_modes(self):
        document = _triangle_gltf()
        document["meshes"][0]["primitives"][0]["mode"] = 1
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_unknown_material_indices(self):
        document = _triangle_gltf()
        document["meshes"][0]["primitives"][0]["material"] = 99
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_sparse_accessors_instead_of_silently_zeroing(self):
        document = _triangle_gltf()
        document["accessors"][0]["sparse"] = {
            "count": 1,
            "indices": {"bufferView": 0, "componentType": 5125},
            "values": {"bufferView": 0},
        }
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_cyclic_node_hierarchies(self):
        document = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"children": [1]}, {"children": [0]}],
        }
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_loads_a_glb_container(self):
        document = _triangle_gltf()
        positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        buffer_data = struct.pack("<" + "f" * len(positions), *positions)
        document["buffers"] = [{"byteLength": len(buffer_data)}]
        imported = load_gltf(_glb_bytes(document, buffer_data))
        self.assertEqual(imported.meshes[0].triangle_count(), 1)

    def test_loads_a_glb_file(self):
        document = _triangle_gltf()
        positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        buffer_data = struct.pack("<" + "f" * len(positions), *positions)
        document["buffers"] = [{"byteLength": len(buffer_data)}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.glb"
            path.write_bytes(_glb_bytes(document, buffer_data))
            imported = load_gltf(path)
            self.assertEqual(imported.meshes[0].triangle_count(), 1)

    def test_rejects_truncated_glb_data(self):
        with self.assertRaises(ValueError):
            load_gltf(b"glTF\x02\x00\x00\x00\xff\xff\xff\xff")

    def test_rejects_unknown_material_texture_indices(self):
        document = _triangle_gltf()
        document["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 7}
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_negative_accessor_offsets(self):
        document = _triangle_gltf()
        document["accessors"][0]["byteOffset"] = -4
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_accessor_reads_outside_the_buffer_view(self):
        document = _triangle_gltf()
        document["bufferViews"][0]["byteLength"] = 8
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_negative_accessor_count_without_a_buffer_view(self):
        document = _triangle_gltf()
        document["accessors"][0] = {"componentType": 5126, "count": -1, "type": "VEC3"}
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_rejects_float_indices_and_scalar_positions(self):
        document = _triangle_gltf()
        document["meshes"][0]["primitives"][0]["indices"] = 1
        document["accessors"].append(
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "SCALAR"}
        )
        with self.assertRaises(ValueError):
            load_gltf(document)
        document = _triangle_gltf()
        document["accessors"][0]["type"] = "SCALAR"
        with self.assertRaises(ValueError):
            load_gltf(document)

    def test_reflected_matrix_preserves_the_reflection(self):
        document = _triangle_gltf()
        document["nodes"][0].pop("translation", None)
        document["nodes"][0]["matrix"] = [
            -1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]
        imported = load_gltf(document)
        node = imported.scene.root.children[0]
        self.assertEqual(node.transform.matrix().flat(), tuple(document["nodes"][0]["matrix"]))
        self.assertLess(node.transform.scale.x * node.transform.scale.y * node.transform.scale.z, 0.0)

    def test_singular_and_non_affine_matrices_are_rejected(self):
        for matrix in (
            [0.0] * 16,
            [-1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 2.0],
        ):
            document = _triangle_gltf()
            document["nodes"][0].pop("translation", None)
            document["nodes"][0]["matrix"] = matrix
            with self.assertRaises(ValueError):
                load_gltf(document)

    def test_uv_origin_is_converted_from_gltf_top_left(self):
        positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        uvs = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
        position_bytes = struct.pack("<" + "f" * len(positions), *positions)
        uv_bytes = struct.pack("<" + "f" * len(uvs), *uvs)
        buffer_data = position_bytes + uv_bytes
        document = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1}}]}],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC2"},
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(position_bytes)},
                {"buffer": 0, "byteOffset": len(position_bytes), "byteLength": len(uv_bytes)},
            ],
            "buffers": [{"uri": _data_uri(buffer_data), "byteLength": len(buffer_data)}],
        }
        imported = load_gltf(document)
        self.assertEqual(imported.meshes[0].uvs, ((0.0, 1.0), (1.0, 1.0), (0.0, 0.0)))


if __name__ == "__main__":
    unittest.main()
