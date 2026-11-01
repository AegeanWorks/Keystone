"""Unit tests for declarative material graphs."""

import json
import unittest

from keystone.material_graph import MaterialGraph, MaterialGraphNode
from keystone.math3d import Vec3
from keystone.texture import TextureData


def _node(node_id, kind, *, params=(), inputs=()):
    return MaterialGraphNode(id=node_id, kind=kind, params=tuple(sorted(params)), inputs=tuple(inputs))


class MaterialGraphCoreTest(unittest.TestCase):
    def test_constant_color_and_float_feed_a_material(self):
        graph = MaterialGraph(
            nodes=(
                _node("color", "color", params=(("b", 0.2), ("g", 0.4), ("r", 0.6))),
                _node("shiny", "float", params=(("value", 64.0),)),
                _node("out", "material", inputs=("color",), params=(("shininess", 64.0), ("specular", 0.5),)),
            ),
            output="out",
        )
        material = graph.evaluate()
        self.assertEqual(material.color, Vec3(0.6, 0.4, 0.2))
        self.assertEqual(material.specular, 0.5)
        self.assertEqual(material.shininess, 64.0)
        self.assertIsNone(material.texture)

    def test_checker_node_builds_a_textured_material(self):
        graph = MaterialGraph(
            nodes=(
                _node("checker", "checker", params=(("cell", 4), ("light", (0.8, 0.8, 0.9)), ("size", 16),)),
                _node("out", "material", inputs=("checker",), params=(("specular", 0.1), ("shininess", 8.0))),
            ),
            output="out",
        )
        material = graph.evaluate()
        self.assertIsNotNone(material.texture)
        self.assertEqual((material.texture.width, material.texture.height), (16, 16))

    def test_mix_combines_colors(self):
        graph = MaterialGraph(
            nodes=(
                _node("a", "color", params=(("b", 0.0), ("g", 0.0), ("r", 1.0))),
                _node("b", "color", params=(("b", 1.0), ("g", 0.0), ("r", 0.0))),
                _node("mixed", "mix", inputs=("a", "b"), params=(("factor", 0.25),)),
                _node("out", "material", inputs=("mixed",)),
            ),
            output="out",
        )
        material = graph.evaluate()
        self.assertAlmostEqual(material.color.x, 0.75)
        self.assertAlmostEqual(material.color.z, 0.25)

    def test_validation_rejects_cycles_and_bad_graphs(self):
        cycle = MaterialGraph(
            nodes=(
                _node("a", "color", inputs=("b",)),
                _node("b", "color", inputs=("a",)),
                _node("out", "material", inputs=("a",)),
            ),
            output="out",
        )
        with self.assertRaises(ValueError):
            cycle.evaluate()
        with self.assertRaises(ValueError):
            MaterialGraph(nodes=(), output="").validate()
        with self.assertRaises(ValueError):
            MaterialGraph(
                nodes=(_node("a", "color"), _node("a", "float")),
                output="a",
            ).validate()
        with self.assertRaises(ValueError):
            MaterialGraph(nodes=(_node("a", "color"),), output="missing").validate()

    def test_evaluation_is_deterministic(self):
        graph = MaterialGraph(
            nodes=(
                _node("color", "color", params=(("r", 0.5),)),
                _node("out", "material", inputs=("color",)),
            ),
            output="out",
        )
        self.assertEqual(graph.evaluate(), graph.evaluate())


class MaterialGraphSerializationTest(unittest.TestCase):
    def test_round_trip_preserves_evaluation(self):
        graph = MaterialGraph(
            nodes=(
                _node("checker", "checker", params=(("cell", 8), ("size", 32))),
                _node("out", "material", inputs=("checker",), params=(("specular", 0.2), ("shininess", 16.0))),
            ),
            output="out",
        )
        restored = MaterialGraph.from_dict(graph.to_dict())
        self.assertEqual(restored.evaluate(), graph.evaluate())
        document = graph.to_dict()
        self.assertEqual(document["schema"], 1)
        json.dumps(document)

    def test_texture_node_resolves_by_name(self):
        texture = TextureData.checker(8, name="named")
        graph = MaterialGraph(
            nodes=(
                _node("tex", "texture", params=(("name", "named"),)),
                _node("out", "material", inputs=("tex",)),
            ),
            output="out",
        )
        material = graph.evaluate(textures={"named": texture})
        self.assertEqual(material.texture, texture)

    def test_material_texture_name_must_resolve(self):
        graph = MaterialGraph(
            nodes=(_node("out", "material", params=(("texture_name", "absent"),)),),
            output="out",
        )
        with self.assertRaises(ValueError):
            graph.evaluate(textures={})


if __name__ == "__main__":
    unittest.main()
