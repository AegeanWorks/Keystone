"""Tests for nav-grid documents and authoring grids from collision boxes."""

import json
import tempfile
import unittest
from pathlib import Path

from keystone.math3d import Vec3
from keystone.nav_authoring import grid_from_boxes, read_navgrid, write_navgrid
from keystone.pathfinding import NavGrid
from keystone.physics import AABB
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _box(x: float, z: float, half: float = 0.5) -> AABB:
    return AABB(Vec3(x, 0.5, z), Vec3(half, 0.5, half))


class NavGridDocumentTest(unittest.TestCase):
    def test_a_grid_round_trips_through_its_document(self):
        grid = NavGrid(4, 3, frozenset({(1, 1), (3, 2), (0, 0)}))
        document = grid.to_dict()
        self.assertEqual(document["schema"], 1)
        self.assertEqual(document["width"], 4)
        self.assertEqual(document["height"], 3)
        self.assertEqual(document["blocked"], [[0, 0], [1, 1], [3, 2]])
        self.assertEqual(NavGrid.from_dict(document), grid)

    def test_the_document_is_json_safe(self):
        document = NavGrid(2, 2, frozenset({(1, 0)})).to_dict()
        self.assertEqual(json.loads(json.dumps(document)), document)

    def test_from_dict_rejects_malformed_documents(self):
        valid = {"schema": 1, "width": 2, "height": 2, "blocked": [[0, 0]]}
        with self.assertRaises(TypeError):
            NavGrid.from_dict(["not", "a", "mapping"])  # type: ignore[arg-type]
        for schema in (2, True, "1"):
            with self.subTest(schema=schema):
                payload = dict(valid, schema=schema)
                with self.assertRaises(ValueError):
                    NavGrid.from_dict(payload)
        with self.assertRaises(ValueError):
            NavGrid.from_dict(dict(valid, width=0))
        with self.assertRaises(ValueError):
            NavGrid.from_dict(dict(valid, height=1.5))
        with self.assertRaises(TypeError):
            NavGrid.from_dict(dict(valid, blocked="none"))
        with self.assertRaises(TypeError):
            NavGrid.from_dict(dict(valid, blocked=[["0", 0]]))
        with self.assertRaises(TypeError):
            NavGrid.from_dict(dict(valid, blocked=[[0]]))
        with self.assertRaises(ValueError):
            NavGrid.from_dict(dict(valid, blocked=[[0, 0], [0, 0]]))
        with self.assertRaises(ValueError):
            NavGrid.from_dict(dict(valid, blocked=[[2, 0]]))

    def test_a_missing_blocked_list_means_no_walls(self):
        grid = NavGrid.from_dict({"schema": 1, "width": 2, "height": 3})
        self.assertEqual(grid.blocked, frozenset())


class GridFromBoxesTest(unittest.TestCase):
    def test_a_box_over_one_cell_blocks_that_cell(self):
        grid = grid_from_boxes(4, 4, [_box(1.5, 1.5)])
        self.assertEqual(grid.blocked, frozenset({(1, 1)}))

    def test_clearance_inflates_the_box_by_the_agent_radius(self):
        tight = grid_from_boxes(4, 4, [_box(1.5, 1.5)], clearance=0.4)
        roomy = grid_from_boxes(4, 4, [_box(1.5, 1.5)], clearance=0.6)
        self.assertEqual(tight.blocked, frozenset({(1, 1)}))
        self.assertEqual(roomy.blocked, frozenset((x, y) for x in (0, 1, 2) for y in (0, 1, 2)))

    def test_origin_and_cell_size_map_cells_to_world_centres(self):
        grid = grid_from_boxes(
            3,
            2,
            [AABB(Vec3(11.0, 0.5, -4.0), Vec3(0.1, 0.5, 0.1))],
            cell_size=2.0,
            origin=Vec3(10.0, 0.0, -5.0),
        )
        self.assertEqual(grid.blocked, frozenset({(0, 0)}))

    def test_boxes_outside_the_grid_block_nothing(self):
        grid = grid_from_boxes(3, 3, [_box(50.0, 50.0)])
        self.assertEqual(grid.blocked, frozenset())

    def test_several_boxes_union(self):
        grid = grid_from_boxes(4, 4, [_box(0.5, 0.5), _box(2.5, 2.5)])
        self.assertEqual(grid.blocked, frozenset({(0, 0), (2, 2)}))

    def test_an_empty_box_list_makes_an_open_grid(self):
        grid = grid_from_boxes(2, 2, [])
        self.assertEqual(grid.blocked, frozenset())
        self.assertEqual((grid.width, grid.height), (2, 2))

    def test_malformed_authoring_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            grid_from_boxes(0, 2, [])
        with self.assertRaises(ValueError):
            grid_from_boxes(2, True, [])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            grid_from_boxes(2, 2, [], cell_size=0.0)
        with self.assertRaises(ValueError):
            grid_from_boxes(2, 2, [], clearance=-1.0)
        with self.assertRaises(ValueError):
            grid_from_boxes(2, 2, [], clearance=float("nan"))
        with self.assertRaises(TypeError):
            grid_from_boxes(2, 2, [object()])  # type: ignore[list-item]
        with self.assertRaises(TypeError):
            grid_from_boxes(2, 2, [], origin=(0.0, 0.0, 0.0))  # type: ignore[arg-type]


class NavGridFileTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_a_grid_round_trips_through_a_file(self):
        path = self.directory / "level.navgrid"
        grid = NavGrid(5, 4, frozenset({(2, y) for y in range(3)}))
        write_navgrid(path, grid)
        self.assertEqual(read_navgrid(path), grid)

    def test_reading_a_non_document_is_rejected(self):
        path = self.directory / "bad.navgrid"
        path.write_text("[1, 2]", encoding="utf-8")
        with self.assertRaises(TypeError):
            read_navgrid(path)

    def test_writing_requires_a_grid(self):
        with self.assertRaises(TypeError):
            write_navgrid(self.directory / "x.navgrid", {"width": 1})  # type: ignore[arg-type]

    def test_describe_advertises_nav_authoring(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["nav_authoring"])


if __name__ == "__main__":
    unittest.main()
