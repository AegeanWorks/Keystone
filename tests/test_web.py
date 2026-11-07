"""Tests for scene export, the local JSON API and the browser console assets."""

import base64
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from keystone import web
from keystone.math3d import Vec3
from keystone.prefab import Prefab
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene
from keystone.web.scene import SCENE_SCHEMA, scene_document
from keystone.web.server import GameSession, WebProblem, create_server


@dataclass(frozen=True)
class Health:
    value: int


class ComponentDemo(CubeDemo):
    component_types: ClassVar[dict[str, type]] = {"Health": Health}


class SceneDocumentTest(unittest.TestCase):
    def test_sample_scene_document_has_identity_geometry_and_texture(self):
        document = scene_document(CubeDemo().build_scene(), game="cube-demo")
        self.assertEqual(document["schema"], 2)
        self.assertEqual(document["game"], "cube-demo")
        self.assertEqual(document["node_count"], 6)
        self.assertEqual(document["mesh_count"], 3)
        self.assertEqual(document["texture_count"], 1)
        self.assertEqual(len(document["camera"]["view"]), 16)
        self.assertEqual(len(document["nodes"]), 6)
        floor = next(node for node in document["nodes"] if node["id"] == "floor")
        self.assertEqual(floor["material"]["texture"], "texture-1")
        texture = document["textures"]["texture-1"]
        self.assertEqual((texture["width"], texture["height"]), (64, 64))
        self.assertEqual(len(base64.b64decode(texture["rgba_base64"])), 64 * 64 * 4)
        self.assertEqual(len(texture["sha256"]), 64)

    def test_world_matrices_and_mesh_references_are_exported(self):
        document = scene_document(CubeDemo().build_scene())
        cube_node = next(node for node in document["nodes"] if node["id"] == "cube-0")
        self.assertAlmostEqual(cube_node["world"][12], -2.4)
        self.assertAlmostEqual(cube_node["world"][13], 0.75)
        self.assertAlmostEqual(cube_node["world"][14], 0.0)
        mesh = document["meshes"][cube_node["mesh"]]
        self.assertEqual(len(mesh["positions"]), len(mesh["normals"]))
        self.assertEqual(len(mesh["indices"]) % 3, 0)

    def test_shared_meshes_are_exported_once(self):
        scene = Scene()
        shared = cube(1.0)
        scene.add(Node("first", id="first", mesh=shared))
        scene.add(Node("second", id="second", mesh=shared))
        document = scene_document(scene)
        self.assertEqual(document["mesh_count"], 1)
        first = next(node for node in document["nodes"] if node["id"] == "first")
        second = next(node for node in document["nodes"] if node["id"] == "second")
        self.assertEqual(first["mesh"], second["mesh"])

    def test_node_identity_metadata_is_exported(self):
        scene = Scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        hero = scene.add(Node("hero", id="hero", tags={"player"}, layer="actors"))
        hero.add_component(Health(3))
        document = scene_document(scene, game="test")
        entry = next(node for node in document["nodes"] if node["id"] == "hero")
        self.assertEqual(entry["tags"], ["player"])
        self.assertEqual(entry["layer"], "actors")
        self.assertEqual(entry["components"], ["Health"])

    def test_scene_document_is_deterministic(self):
        first = scene_document(CubeDemo().build_scene())
        second = scene_document(CubeDemo().build_scene())
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_schema_describes_export_fields(self):
        self.assertEqual(SCENE_SCHEMA["version"], 2)
        self.assertIn("world", SCENE_SCHEMA["fields"]["node"])
        self.assertIn("tags", SCENE_SCHEMA["fields"]["node"])
        self.assertIn("rgba_base64", SCENE_SCHEMA["fields"]["texture"])

    def test_public_web_exports_are_available(self):
        self.assertEqual(web.SCENE_SCHEMA["version"], 2)
        self.assertTrue(callable(web.scene_document))
        self.assertTrue(callable(web.create_server))
        self.assertTrue(callable(web.serve))

    def test_falsy_settings_are_reported_disabled(self):
        scene = CubeDemo().build_scene()
        scene.shadow = False
        scene.color = 0
        scene.post = ""
        scene.bloom = False
        scene.sprite = 0
        scene.culling = ""
        document = scene_document(scene)
        for key in ("shadows", "color", "post", "bloom", "sprites", "culling"):
            self.assertFalse(document[key]["enabled"], key)

    def test_empty_live_scene_is_not_rebuilt(self):
        game = CubeDemo()
        session = GameSession(game)
        first = session.scene()
        self.assertGreater(first["node_count"], 0)
        game.scene.root.children.clear()
        self.assertEqual(session.scene()["node_count"], 1)


class WebServerTest(unittest.TestCase):
    def setUp(self):
        self.server = create_server(CubeDemo(), host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def _stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _request(self, path, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def _json(self, path, method="GET", payload=None):
        status, headers, body = self._request(path, method=method, payload=payload)
        return status, headers, json.loads(body.decode("utf-8"))

    def test_health_and_cors(self):
        status, headers, payload = self._json("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["game"], "cube-demo")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")

    def test_describe_includes_the_web_capability(self):
        status, _, payload = self._json("/api/describe")
        self.assertEqual(status, 200)
        self.assertEqual(payload["game"], "cube-demo")
        self.assertEqual(payload["capabilities"]["web"]["api_version"], 1)
        self.assertEqual(payload["capabilities"]["report_schema"]["version"], 11)

    def test_scene_endpoint_returns_the_scene_document(self):
        status, _, payload = self._json("/api/scene")
        self.assertEqual(status, 200)
        self.assertEqual(payload["schema"], 2)
        self.assertEqual(payload["node_count"], 6)
        self.assertEqual(payload["mesh_count"], 3)
        self.assertEqual(payload["texture_count"], 1)

    def test_simulate_endpoint_returns_a_deterministic_result(self):
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": 2, "actions": [{"forward": 1.0}]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["frames"], 2)
        self.assertEqual(len(payload["hash"]), 32)

    def test_editor_hierarchy_selection_and_transform(self):
        status, _, editor = self._json("/api/editor")
        self.assertEqual(status, 200)
        self.assertEqual(editor["schema"], 10)
        self.assertIsNone(editor["selection"])
        self.assertIn("select", editor["actions"])
        self.assertEqual(editor["history"], {"undo": 0, "redo": 0, "limit": 50})
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        self.assertEqual(cube["mesh"], "mesh.cube")
        self.assertEqual(cube["material"], "material.cube.0")
        self.assertIn("mesh.cube", {asset["id"] for asset in editor["assets"]})

        status, _, editor = self._json(
            "/api/editor", method="POST", payload={"action": "select", "id": cube["id"]}
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["selection"]["id"], cube["id"])

        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={
                "action": "transform",
                "id": cube["id"],
                "position": [1.0, 2.0, 3.0],
                "rotation": [0.0, 0.0, 0.0, 1.0],
                "scale": [2.0, 2.0, 2.0],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["selection"]["transform"]["position"], [1.0, 2.0, 3.0])
        status, _, scene = self._json("/api/scene")
        node = next(item for item in scene["nodes"] if item["id"] == cube["id"])
        self.assertEqual(node["world"][12:15], [1.0, 2.0, 3.0])

        status, _, _ = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "transform", "id": cube["id"], "position": [float("nan"), 0, 0]},
        )
        self.assertEqual(status, 400)
        status, _, _ = self._json(
            "/api/editor", method="POST", payload={"action": "select", "id": "missing"}
        )
        self.assertEqual(status, 404)
        status, _, _ = self._json(
            "/api/editor", method="POST", payload={"action": "explode"}
        )
        self.assertEqual(status, 400)

    def test_editor_node_authoring_and_undo_redo(self):
        _, _, editor = self._json("/api/editor")
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={
                "action": "create_node",
                "name": "lamp",
                "parent": cube["id"],
                "position": [1.0, 2.0, 3.0],
                "tags": ["prop"],
                "layer": "props",
                "mesh": "mesh.cube",
                "material": "material.cube.0",
            },
        )
        self.assertEqual(status, 200)
        lamp = editor["selection"]
        self.assertEqual(lamp["name"], "lamp")
        self.assertEqual(lamp["parent_id"], cube["id"])
        self.assertEqual(lamp["transform"]["position"], [1.0, 2.0, 3.0])
        self.assertEqual(lamp["tags"], ["prop"])
        self.assertEqual(lamp["layer"], "props")
        self.assertEqual(editor["history"]["undo"], 1)
        _, _, scene = self._json("/api/scene")
        lamp_scene = next(item for item in scene["nodes"] if item["id"] == lamp["id"])
        self.assertIsNotNone(lamp_scene["mesh"])
        self.assertIsNotNone(lamp_scene["material"])

        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "duplicate_node", "id": lamp["id"], "name": "lamp-copy"},
        )
        self.assertEqual(status, 200)
        copy = editor["selection"]
        self.assertNotEqual(copy["id"], lamp["id"])
        self.assertEqual(copy["name"], "lamp-copy")
        self.assertEqual(copy["parent_id"], cube["id"])

        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "reparent_node", "id": copy["id"], "parent": "root"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["selection"]["parent_id"], "root")
        status, _, editor = self._json(
            "/api/editor", method="POST", payload={"action": "undo"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["history"]["undo"], 2)
        self.assertEqual(editor["history"]["redo"], 1)
        self.assertEqual(editor["selection"]["parent_id"], cube["id"])
        status, _, editor = self._json(
            "/api/editor", method="POST", payload={"action": "redo"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["selection"]["parent_id"], "root")

        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "delete_node", "id": lamp["id"]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["selection"]["id"], cube["id"])
        self.assertNotIn(lamp["id"], {node["id"] for node in editor["nodes"]})
        self.assertIn(copy["id"], {node["id"] for node in editor["nodes"]})
        status, _, editor = self._json(
            "/api/editor", method="POST", payload={"action": "undo"}
        )
        self.assertEqual(status, 200)
        self.assertIn(lamp["id"], {node["id"] for node in editor["nodes"]})

        status, _, _ = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "create_node", "name": "bad", "mesh": "missing.mesh"},
        )
        self.assertEqual(status, 400)
        status, _, _ = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "reparent_node", "id": cube["id"], "parent": lamp["id"]},
        )
        self.assertEqual(status, 400)
        _, _, editor = self._json("/api/editor")
        cube_now = next(node for node in editor["nodes"] if node["id"] == cube["id"])
        self.assertEqual(cube_now["parent_id"], "root")

    def test_editor_asset_metadata(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        assets = {asset["id"]: asset for asset in editor["assets"]}
        self.assertGreater(assets["mesh.cube"]["metadata"]["vertices"], 0)
        self.assertGreater(assets["mesh.cube"]["metadata"]["triangles"], 0)
        self.assertIn("color", assets["material.cube.0"]["metadata"])
        self.assertEqual(assets["texture.floor-checker"]["metadata"]["width"], 64)
        self.assertEqual(assets["texture.floor-checker"]["metadata"]["height"], 64)

        prefab = Prefab.from_node(
            session.game.scene.find_by_id("cube-0"), name="cube-asset"
        )
        session.game.assets.register("prefab.cube", prefab)
        editor = session.editor()
        entry = next(
            asset for asset in editor["assets"] if asset["id"] == "prefab.cube"
        )
        self.assertEqual(entry["metadata"]["node_count"], 1)
        self.assertIn("mesh.cube", entry["metadata"]["asset_dependencies"])

    def test_editor_asset_inventory_and_assignment(self):
        _, _, editor = self._json("/api/editor")
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        _, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={
                "action": "assign_asset",
                "id": cube["id"],
                "material": "material.cube.1",
            },
        )
        self.assertEqual(editor["selection"]["material"], "material.cube.1")
        self.assertEqual(editor["selection"]["mesh"], "mesh.cube")
        _, _, editor = self._json(
            "/api/editor", method="POST", payload={"action": "undo"}
        )
        self.assertEqual(editor["selection"]["material"], "material.cube.0")
        _, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "assign_asset", "id": cube["id"], "mesh": None},
        )
        self.assertIsNone(editor["selection"]["mesh"])
        status, _, _ = self._json(
            "/api/editor",
            method="POST",
            payload={
                "action": "assign_asset",
                "id": cube["id"],
                "material": "mesh.cube",
            },
        )
        self.assertEqual(status, 400)
        status, _, _ = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "assign_asset", "id": cube["id"], "mesh": "missing.mesh"},
        )
        self.assertEqual(status, 400)
        status, _, _ = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "assign_asset", "id": cube["id"]},
        )
        self.assertEqual(status, 400)

    def test_editor_prefab_capture_and_insert(self):
        _, _, editor = self._json("/api/editor")
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        self._json("/api/editor", method="POST", payload={"action": "select", "id": cube["id"]})
        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "save_prefab", "name": "cube-template"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["prefabs"], [{"name": "cube-template", "node_count": 1}])

        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={"action": "insert_prefab", "name": "cube-template", "instance": "copy"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(editor["selection"]["id"], "copy:" + cube["id"])
        _, _, scene = self._json("/api/scene")
        self.assertIn("copy:" + cube["id"], {node["id"] for node in scene["nodes"]})

    def test_editor_prefab_library_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            first = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            editor = first.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            first.editor_action({"action": "select", "id": cube["id"]})
            saved = first.editor_action({"action": "save_prefab", "name": "cube-template"})
            path = prefab_dir / "cube-template.kprefab"
            self.assertTrue(path.is_file())
            self.assertEqual(
                saved["workspace"],
                {"prefab_dir": prefab_dir.as_posix(), "scene_dir": None},
            )
            self.assertEqual(saved["prefabs"][0]["source"], path.as_posix())
            self.assertIsNone(saved["prefabs"][0]["error"])

            second = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            editor = second.editor()
            self.assertEqual(editor["prefabs"][0]["name"], "cube-template")
            self.assertEqual(editor["prefabs"][0]["node_count"], 1)
            inserted = second.editor_action(
                {"action": "insert_prefab", "name": "cube-template", "instance": "copy"}
            )
            self.assertEqual(inserted["selection"]["id"], "copy:cube-0")

            (prefab_dir / "broken.kprefab").write_text("{}", encoding="utf-8")
            third = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            entries = {entry["name"]: entry for entry in third.editor()["prefabs"]}
            self.assertIsNotNone(entries["broken"]["error"])

    def test_editor_initial_scene_loads_at_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            scene_dir = Path(directory) / "scenes"
            first = GameSession(CubeDemo(), scene_dir=scene_dir)
            editor = first.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            first.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [4.0, 5.0, 6.0],
                }
            )
            first.editor_action({"action": "save_scene", "name": "level"})

            second = GameSession(
                CubeDemo(), scene_dir=scene_dir, initial_scene="level"
            )
            editor = second.editor()
            restored = next(
                node for node in editor["nodes"] if node["id"] == cube["id"]
            )
            self.assertEqual(restored["transform"]["position"], [4.0, 5.0, 6.0])
            self.assertIsNone(editor["selection"])
            self.assertEqual(editor["history"], {"undo": 0, "redo": 0, "limit": 50})

            with self.assertRaises(KeyError):
                GameSession(CubeDemo(), scene_dir=scene_dir, initial_scene="missing")
            with self.assertRaises(ValueError):
                GameSession(CubeDemo(), initial_scene="level")

    def test_editor_scene_library_persists_and_restores(self):
        with tempfile.TemporaryDirectory() as directory:
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), scene_dir=scene_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [1.0, 2.0, 3.0],
                }
            )
            saved = session.editor_action({"action": "save_scene", "name": "level"})
            path = scene_dir / "level.kscene"
            self.assertTrue(path.is_file())
            self.assertEqual(saved["workspace"]["scene_dir"], scene_dir.as_posix())
            self.assertEqual(saved["scenes"][0]["name"], "level")
            self.assertEqual(saved["scenes"][0]["node_count"], 5)

            session.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [9.0, 9.0, 9.0],
                }
            )
            loaded = session.editor_action({"action": "load_scene", "name": "level"})
            self.assertIsNone(loaded["selection"])
            self.assertEqual(loaded["history"], {"undo": 0, "redo": 0, "limit": 50})
            restored = next(node for node in loaded["nodes"] if node["id"] == cube["id"])
            self.assertEqual(restored["transform"]["position"], [1.0, 2.0, 3.0])

            (scene_dir / "broken.kscene").write_text("{}", encoding="utf-8")
            broken = GameSession(CubeDemo(), scene_dir=scene_dir)
            entries = {entry["name"]: entry for entry in broken.editor()["scenes"]}
            self.assertIsNotNone(entries["broken"]["error"])

    def test_editor_batch_authoring_is_atomic(self):
        session = GameSession(CubeDemo())
        session.editor()
        result = session.editor_action(
            {
                "action": "batch",
                "actions": [
                    {
                        "action": "create_node",
                        "id": "batch-a",
                        "name": "Batch A",
                        "position": [1.0, 0.0, 0.0],
                    },
                    {
                        "action": "set_node",
                        "id": "batch-a",
                        "tags": ["batch"],
                        "layer": "actors",
                    },
                    {
                        "action": "assign_asset",
                        "id": "batch-a",
                        "mesh": "mesh.cube",
                        "material": "material.cube.0",
                    },
                    {
                        "action": "create_node",
                        "id": "batch-b",
                        "name": "Batch B",
                        "parent": "batch-a",
                    },
                ],
            }
        )
        ids = {node["id"] for node in result["nodes"]}
        self.assertIn("batch-a", ids)
        self.assertIn("batch-b", ids)
        self.assertEqual(result["history"]["undo"], 1)
        batch_a = next(node for node in result["nodes"] if node["id"] == "batch-a")
        self.assertEqual(batch_a["tags"], ["batch"])
        self.assertEqual(batch_a["layer"], "actors")
        self.assertEqual(batch_a["mesh"], "mesh.cube")

        result = session.editor_action({"action": "undo"})
        ids = {node["id"] for node in result["nodes"]}
        self.assertNotIn("batch-a", ids)
        self.assertNotIn("batch-b", ids)
        self.assertEqual(result["history"]["undo"], 0)

        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "batch",
                    "actions": [
                        {
                            "action": "create_node",
                            "id": "rollback",
                            "name": "Rollback",
                        },
                        {
                            "action": "transform",
                            "id": "missing",
                            "position": [1.0, 0.0, 0.0],
                        },
                    ],
                }
            )
        self.assertEqual(caught.exception.status, 404)
        self.assertNotIn(
            "rollback", {node["id"] for node in session.editor()["nodes"]}
        )

        for payload in (
            {"action": "batch", "actions": []},
            {"action": "batch", "actions": "x"},
            {"action": "batch", "actions": [{"action": "batch", "actions": []}]},
            {"action": "batch", "actions": [{"action": "play_start"}]},
            {"action": "batch", "actions": [{"action": "undo"}]},
        ):
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(payload)
            self.assertEqual(caught.exception.status, 400)

    def test_editor_node_property_editing(self):
        _, _, editor = self._json("/api/editor")
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        status, _, editor = self._json(
            "/api/editor",
            method="POST",
            payload={
                "action": "set_node",
                "id": cube["id"],
                "name": "hero-cube",
                "visible": False,
                "tags": ["hero", "prop"],
                "layer": "actors",
            },
        )
        self.assertEqual(status, 200)
        selection = editor["selection"]
        self.assertEqual(selection["name"], "hero-cube")
        self.assertFalse(selection["visible"])
        self.assertEqual(selection["tags"], ["hero", "prop"])
        self.assertEqual(selection["layer"], "actors")

        _, _, editor = self._json(
            "/api/editor", method="POST", payload={"action": "undo"}
        )
        self.assertEqual(editor["selection"]["name"], "cube-0")
        self.assertTrue(editor["selection"]["visible"])
        self.assertEqual(editor["selection"]["tags"], [])
        self.assertEqual(editor["selection"]["layer"], "default")

        for payload in (
            {"action": "set_node", "id": cube["id"], "name": ""},
            {"action": "set_node", "id": cube["id"], "visible": "yes"},
            {"action": "set_node", "id": cube["id"], "tags": "hero"},
            {"action": "set_node", "id": cube["id"], "layer": ""},
            {"action": "set_node", "id": cube["id"]},
        ):
            status, _, _ = self._json("/api/editor", method="POST", payload=payload)
            self.assertEqual(status, 400)

    def test_editor_play_mode_restores_authored_scene(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        original = cube["transform"]["rotation"]
        self.assertFalse(editor["play"]["active"])

        started = session.editor_action({"action": "play_start"})
        self.assertTrue(started["play"]["active"])
        self.assertEqual(started["play"]["frames"], 0)
        stepped = session.editor_action({"action": "play_step", "frames": 2})
        self.assertEqual(stepped["play"]["frames"], 2)
        moved = next(node for node in stepped["nodes"] if node["id"] == cube["id"])
        self.assertNotEqual(moved["transform"]["rotation"], original)

        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [1.0, 2.0, 3.0],
                }
            )
        self.assertEqual(caught.exception.status, 400)
        with self.assertRaises(WebProblem) as caught:
            session.simulate(1, [], 0.0167, False)
        self.assertEqual(caught.exception.status, 400)

        stopped = session.editor_action({"action": "play_stop"})
        self.assertFalse(stopped["play"]["active"])
        restored = next(node for node in stopped["nodes"] if node["id"] == cube["id"])
        self.assertEqual(restored["transform"]["rotation"], original)
        self.assertEqual(stopped["history"], {"undo": 0, "redo": 0, "limit": 50})
        with self.assertRaises(WebProblem) as caught:
            session.editor_action({"action": "play_step", "frames": 1})
        self.assertEqual(caught.exception.status, 400)

    def test_editor_component_authoring_and_scene_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            scene_dir = Path(directory) / "scenes"
            session = GameSession(ComponentDemo(), scene_dir=scene_dir)
            editor = session.editor()
            self.assertEqual(editor["component_types"], ["Health"])
            self.assertEqual(
                editor["component_schemas"]["Health"]["fields"],
                [
                    {
                        "name": "value",
                        "type": "int",
                        "required": True,
                        "default": None,
                    }
                ],
            )
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            result = session.editor_action(
                {
                    "action": "set_component",
                    "id": cube["id"],
                    "type": "Health",
                    "data": {"value": 5},
                }
            )
            self.assertEqual(result["selection"]["components"], ["Health"])
            self.assertEqual(
                result["selection"]["component_data"],
                [{"type": "Health", "data": {"value": 5}}],
            )
            result = session.editor_action(
                {
                    "action": "set_component",
                    "id": cube["id"],
                    "type": "Health",
                    "data": {"value": 9},
                }
            )
            self.assertEqual(
                result["selection"]["component_data"][0]["data"]["value"], 9
            )
            session.editor_action(
                {"action": "remove_component", "id": cube["id"], "type": "Health"}
            )
            result = session.editor_action({"action": "undo"})
            self.assertEqual(
                result["selection"]["component_data"][0]["data"]["value"], 9
            )

            session.editor_action({"action": "save_scene", "name": "component-level"})
            session.editor_action(
                {"action": "remove_component", "id": cube["id"], "type": "Health"}
            )
            loaded = session.editor_action(
                {"action": "load_scene", "name": "component-level"}
            )
            restored = next(node for node in loaded["nodes"] if node["id"] == cube["id"])
            self.assertEqual(restored["component_data"][0]["data"]["value"], 9)

            other = next(node for node in editor["nodes"] if node["name"] == "cube-1")
            for payload in (
                {
                    "action": "set_component",
                    "id": cube["id"],
                    "type": "Missing",
                    "data": {},
                },
                {
                    "action": "set_component",
                    "id": cube["id"],
                    "type": "Health",
                    "data": [],
                },
                {
                    "action": "remove_component",
                    "id": other["id"],
                    "type": "Health",
                },
            ):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(payload)
                self.assertEqual(caught.exception.status, 400)

    def test_editor_static_controls_and_index(self):
        status, _, body = self._request("/")
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        for control in (
            "hierarchy",
            "play-start",
            "play-step",
            "play-stop",
            "play-state",
            "node-parent",
            "node-create",
            "node-duplicate",
            "node-delete",
            "node-reparent",
            "node-visible",
            "node-tags",
            "node-layer",
            "node-properties",
            "editor-undo",
            "editor-redo",
            "scene-name",
            "scene-save",
            "scene-load",
            "mesh-asset",
            "material-asset",
            "assign-asset",
            "component-type",
            "component-data",
            "component-set",
            "component-remove",
            "prefab-save",
            "prefab-insert",
            "transform-apply",
        ):
            self.assertIn(f'id="{control}"', text)
        status, _, body = self._request("/app.js")
        self.assertEqual(status, 200)
        script = body.decode("utf-8")
        self.assertIn("/api/editor", script)
        self.assertIn("create_node", script)
        self.assertIn("duplicate_node", script)
        self.assertIn("save_scene", script)
        self.assertIn("assign_asset", script)
        self.assertIn("set_component", script)
        self.assertIn("play_start", script)
        self.assertIn("set_node", script)
        status, _, payload = self._json("/api")
        self.assertEqual(status, 200)
        self.assertIn("editor", payload["endpoints"])

    def test_step_button_documents_its_reset_semantics(self):
        status, _, body = self._request("/")
        self.assertEqual(status, 200)
        self.assertIn("Reset + Step 1", body.decode("utf-8"))

    def test_options_preflight_and_static_assets(self):
        status, headers, _ = self._request("/api/simulate", method="OPTIONS")
        self.assertEqual(status, 204)
        self.assertIn("POST", headers["Access-Control-Allow-Methods"])
        status, headers, body = self._request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('id="canvas"', body.decode("utf-8"))
        status, headers, body = self._request("/viewer.js")
        self.assertEqual(status, 200)
        self.assertIn("class SceneViewer", body.decode("utf-8"))
        self.assertIn("javascript", headers["Content-Type"])

    def test_api_index_and_errors_are_json(self):
        status, _, payload = self._json("/api")
        self.assertEqual(status, 200)
        self.assertIn("simulate", payload["endpoints"])
        status, _, payload = self._json("/api/missing")
        self.assertEqual(status, 404)
        self.assertFalse(payload["ok"])
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": -1},
        )
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": 1, "trace": "yes"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        status, _, payload = self._json("/api/simulate", method="PUT")
        self.assertEqual(status, 405)
        self.assertFalse(payload["ok"])

    def test_simulate_rejects_non_finite_step(self):
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": 1, "step": float("nan")},
        )
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": 1, "step": float("inf")},
        )
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])

    def test_non_finite_action_is_400_without_poisoning_the_session(self):
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": 1, "actions": [{"forward": float("nan")}]},
        )
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertEqual(self._json("/api/scene")[0], 200)
        self.assertEqual(self._json("/api/describe")[0], 200)

    def test_oversized_step_and_json_number_are_client_errors(self):
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"frames": 1, "step": 10**400},
        )
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        raw = b'{"frames": ' + b"9" * 5000 + b"}"
        request = urllib.request.Request(self.base + "/api/simulate", data=raw, method="POST")
        request.add_header("Content-Type", "application/json")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)

    def test_simulate_infers_frames_from_actions(self):
        status, _, payload = self._json(
            "/api/simulate",
            method="POST",
            payload={"actions": [{"forward": 1.0}, {"right": 1.0}, {"up": 1.0}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["frames"], 3)

    def test_head_and_method_errors(self):
        status, headers, body = self._request("/api/health", method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        status, headers, _payload = self._json("/api/health", method="PUT")
        self.assertEqual(status, 405)
        self.assertIn("GET", headers.get("Allow", ""))
        status, _, _payload = self._json("/api/simulate", method="GET")
        self.assertEqual(status, 405)
        status, _, _payload = self._json("/api/health", method="POST")
        self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()
