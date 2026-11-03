"""Tests for PBR material extensions: validation, glTF, graphs and reports."""

import unittest

from keystone.analysis import analyze_frame
from keystone.geometry import Material
from keystone.gltf.materials import load_materials
from keystone.material_graph import MaterialGraph, MaterialGraphNode
from keystone.math3d import Vec3
from keystone.scene import Node, Scene
from keystone.web.scene import scene_document


class PbrMaterialTest(unittest.TestCase):
    def test_defaults_preserve_legacy_look(self):
        material = Material()
        self.assertEqual(material.metallic, 0.0)
        self.assertEqual(material.roughness, 0.7)
        self.assertEqual(material.emissive, Vec3())

    def test_validation_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            Material(metallic=1.5)
        with self.assertRaises(ValueError):
            Material(roughness=-0.1)

    def test_gltf_preserves_pbr_factors(self):
        document = {
            "materials": [
                {
                    "pbrMetallicRoughness": {"metallicFactor": 0.9, "roughnessFactor": 0.25},
                    "emissiveFactor": [0.1, 0.2, 0.3],
                }
            ]
        }
        (material,) = load_materials(document, [])
        self.assertAlmostEqual(material.metallic, 0.9)
        self.assertAlmostEqual(material.roughness, 0.25)
        self.assertEqual(material.emissive, Vec3(0.1, 0.2, 0.3))

    def test_material_graph_pbr_node(self):
        graph = MaterialGraph(
            nodes=(
                MaterialGraphNode("base", "color", (("color", (0.2, 0.4, 0.6)),), ()),
                MaterialGraphNode(
                    "out",
                    "pbr",
                    (("metallic", 0.8), ("roughness", 0.3), ("emissive", (0.05, 0.0, 0.0)),),
                    ("base",),
                ),
            ),
            output="out",
        )
        material = graph.evaluate()
        self.assertAlmostEqual(material.metallic, 0.8)
        self.assertAlmostEqual(material.roughness, 0.3)
        self.assertEqual(material.emissive, Vec3(0.05, 0.0, 0.0))

    def test_report_and_scene_document_include_pbr(self):
        from keystone.primitives import cube

        scene = Scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        scene.add(Node("hero", id="hero", mesh=cube(1.0),
                       material=Material(metallic=0.5, roughness=0.2, emissive=Vec3(0.1, 0.0, 0.0))))
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], 8)
        entry = next(node for node in report["scene"]["nodes"] if node.get("id") == "hero")
        material = entry.get("material")
        self.assertIsNotNone(material)
        self.assertEqual(material["metallic"], 0.5)
        self.assertEqual(material["roughness"], 0.2)
        self.assertEqual(material["emissive"], [0.1, 0.0, 0.0])
        document = scene_document(scene)
        self.assertEqual(document["schema"], 2)
        entry = next(node for node in document["nodes"] if node["id"] == "hero")
        self.assertEqual(entry["material"]["metallic"], 0.5)
        self.assertEqual(entry["material"]["emissive"], [0.1, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
