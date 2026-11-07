"""Tests for scene export, the local JSON API and the browser console assets."""

import base64
import json
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import dataclass

from keystone import web
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene
from keystone.web.scene import SCENE_SCHEMA, scene_document
from keystone.web.server import GameSession, create_server


@dataclass(frozen=True)
class Health:
    value: int


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
