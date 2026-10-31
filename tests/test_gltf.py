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


def _triangle_gltf(*, translation=(0.0, 0.0, 0.0), color=(0.2, 0.4, 0.6), roughness=0.25):
    positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    buffer_data = struct.pack("<" + "f" * len(positions), *positions)
    uri = "data:application/octet-stream;base64," + base64.b64encode(buffer_data).decode("ascii")
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


if __name__ == "__main__":
    unittest.main()
