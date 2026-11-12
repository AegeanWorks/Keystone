"""Tests for tile maps: collision boxes, merged mesh and documents."""

import json
import unittest

from keystone.math3d import Vec3
from keystone.physics import Ray, raycast
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.tilemap import TileMap, tilemap_report


class TileMapTest(unittest.TestCase):
    def test_cells_map_to_world_centres(self):
        tiles = TileMap(4, 3, tile_size=2.0, origin=Vec3(10.0, 0.5, -4.0))
        self.assertEqual(tiles.cell_center((0, 0)), Vec3(11.0, 0.5, -3.0))
        self.assertEqual(tiles.cell_center((3, 2)), Vec3(17.0, 0.5, 1.0))
        self.assertTrue(tiles.in_bounds((3, 2)))
        self.assertFalse(tiles.in_bounds((4, 2)))

    def test_each_solid_cell_is_one_collision_box(self):
        tiles = TileMap(3, 3, tile_size=1.0, solid=frozenset({(1, 1)}), wall_height=2.0)
        boxes = tiles.colliders()
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].center, Vec3(1.5, 1.0, 1.5))
        self.assertEqual(boxes[0].half_extents, Vec3(0.5, 1.0, 0.5))

    def test_colliders_are_sorted_and_immutable(self):
        tiles = TileMap(3, 2, solid=frozenset({(2, 1), (0, 0), (1, 0)}))
        centers = [box.center for box in tiles.colliders()]
        self.assertEqual(
            centers,
            [Vec3(0.5, 0.5, 0.5), Vec3(1.5, 0.5, 0.5), Vec3(2.5, 0.5, 1.5)],
        )
        with self.assertRaises(AttributeError):
            tiles.colliders()[0].center = Vec3()  # type: ignore[misc]

    def test_with_cell_returns_a_copy(self):
        tiles = TileMap(3, 3)
        walled = tiles.with_cell((1, 1), True)
        self.assertFalse(tiles.is_solid((1, 1)))
        self.assertTrue(walled.is_solid((1, 1)))
        self.assertFalse(walled.with_cell((1, 1), False).is_solid((1, 1)))

    def test_mesh_covers_free_cells_and_walls(self):
        tiles = TileMap(2, 1, solid=frozenset({(1, 0)}))
        mesh = tiles.mesh()
        self.assertEqual(len(mesh.positions), 4 + 24)
        self.assertEqual(mesh.triangle_count(), 2 + 12)

    def test_mesh_floor_faces_up(self):
        mesh = TileMap(1, 1).mesh()
        self.assertEqual(len(mesh.normals), 4)
        for normal in mesh.normals:
            self.assertAlmostEqual(normal[1], 1.0)

    def test_mesh_bounds_cover_the_walls(self):
        tiles = TileMap(2, 2, tile_size=2.0, origin=Vec3(-3.0, 0.0, 4.0), solid=frozenset({(0, 0)}), wall_height=3.0)
        low, high = tiles.mesh().bounds()
        self.assertEqual(low[1], 0.0)
        self.assertEqual(high[1], 3.0)

    def test_colliders_feed_physics_rays(self):
        tiles = TileMap(4, 1, solid=frozenset({(2, 0)}))
        hit = raycast(Ray(Vec3(0.0, 0.5, 0.5), Vec3(1.0, 0.0, 0.0)), list(enumerate(tiles.colliders())))
        assert hit is not None
        self.assertAlmostEqual(hit.distance, 2.0)

    def test_documents_round_trip_and_are_json_safe(self):
        tiles = TileMap(
            3,
            2,
            tile_size=1.5,
            origin=Vec3(1.0, 2.0, 3.0),
            solid=frozenset({(0, 1), (2, 0)}),
            floor_color=Vec3(0.1, 0.2, 0.3),
            wall_color=Vec3(0.7, 0.6, 0.5),
            wall_height=2.5,
        )
        document = tiles.to_dict()
        self.assertEqual(document["schema"], 1)
        self.assertEqual(document["solid"], [[0, 1], [2, 0]])
        self.assertEqual(json.loads(json.dumps(document)), document)
        self.assertEqual(TileMap.from_dict(document), tiles)

    def test_documents_reject_malformed_input(self):
        valid = TileMap(2, 2).to_dict()
        with self.assertRaises(TypeError):
            TileMap.from_dict(["not", "a", "mapping"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            TileMap.from_dict(dict(valid, schema=2))
        with self.assertRaises(ValueError):
            TileMap.from_dict(dict(valid, width=0))
        with self.assertRaises(ValueError):
            TileMap.from_dict(dict(valid, solid=[[2, 0]]))
        with self.assertRaises(TypeError):
            TileMap.from_dict(dict(valid, solid=[["a", 0]]))
        with self.assertRaises(ValueError):
            TileMap.from_dict(dict(valid, extra=1))
        with self.assertRaises(ValueError):
            TileMap.from_dict(dict(valid, origin=[0.0, 0.0]))

    def test_malformed_maps_are_rejected(self):
        with self.assertRaises(ValueError):
            TileMap(0, 2)
        with self.assertRaises(ValueError):
            TileMap(2, True)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            TileMap(2, 2, tile_size=0.0)
        with self.assertRaises(ValueError):
            TileMap(2, 2, wall_height=0.0)
        with self.assertRaises(ValueError):
            TileMap(2, 2, solid=frozenset({(2, 0)}))
        with self.assertRaises(ValueError):
            TileMap(2, 2, floor_color=Vec3(1.5, 0.0, 0.0))
        with self.assertRaises(TypeError):
            TileMap(2, 2, origin=(0.0, 0.0, 0.0))  # type: ignore[arg-type]

    def test_report_is_json_safe(self):
        report = tilemap_report(TileMap(4, 3, solid=frozenset({(1, 1)})))
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["width"], 4)
        self.assertEqual(report["height"], 3)
        self.assertEqual(report["solid"], 1)
        self.assertEqual(report["free"], 11)
        self.assertEqual(report["bounds"]["min"], [0.0, 0.0, 0.0])
        self.assertEqual(report["bounds"]["max"], [4.0, 1.0, 3.0])

    def test_report_rejects_a_non_map(self):
        with self.assertRaises(TypeError):
            tilemap_report({"width": 1})  # type: ignore[arg-type]

    def test_describe_advertises_tilemaps(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["tilemap"])


if __name__ == "__main__":
    unittest.main()
