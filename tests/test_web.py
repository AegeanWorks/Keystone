"""Tests for scene export, the local JSON API and the browser console assets."""

import base64
import json
import os
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from keystone import web
from keystone.animation import AnimationClip, Track
from keystone.animation_state import (
    AnimationState,
    AnimationStateMachine,
    AnimationTransition,
)
from keystone.math3d import Vec3
from keystone.prefab import Prefab
from keystone.primitives import cube
from keystone.project import create_project, load_project
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene, Transform
from keystone.schema import EDITOR_ACTIONS, EDITOR_SCHEMA_VERSION
from keystone.web.scene import SCENE_SCHEMA, scene_document
from keystone.web.schema import EDITOR_SCHEMA
from keystone.web.server import GameSession, WebProblem, create_server


def _triangle_gltf():
    positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    data = struct.pack("<9f", *positions)
    uri = "data:application/octet-stream;base64," + base64.b64encode(data).decode()
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "tri", "mesh": 0}],
        "meshes": [
            {"primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(data),
                "target": 34962,
            }
        ],
        "buffers": [{"uri": uri, "byteLength": len(data)}],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.2, 0.4, 0.6, 1.0],
                    "roughnessFactor": 0.25,
                }
            }
        ],
    }


def _state_machine_document():
    idle = AnimationState(
        "idle",
        AnimationClip(
            name="idle",
            position_tracks=(
                (
                    "cube-0",
                    Track(
                        times=(0.0, 1.0),
                        values=(Vec3(0, 0, 0), Vec3(0, 0.5, 0)),
                    ),
                ),
            ),
        ),
    )
    run = AnimationState(
        "run",
        AnimationClip(
            name="run",
            position_tracks=(
                (
                    "cube-0",
                    Track(
                        times=(0.0, 1.0),
                        values=(Vec3(2, 0, 0), Vec3(2, 0.5, 0)),
                    ),
                ),
            ),
        ),
    )
    return AnimationStateMachine(
        [idle, run],
        [
            AnimationTransition(
                "idle", "run", "speed", "greater", 0.5, 0.0
            )
        ],
        {"speed": 0.0},
    ).to_dict()


@dataclass(frozen=True)
class Health:
    value: int


class ComponentDemo(CubeDemo):
    component_types: ClassVar[dict[str, type]] = {"Health": Health}


@dataclass
class Ticker:
    ticks: int = 0
    started: int = 0
    stopped: int = 0

    def start(self, context) -> None:
        self.started += 1

    def update(self, context) -> None:
        self.ticks += 1

    def stop(self, context) -> None:
        self.stopped += 1


class LifecycleDemo(CubeDemo):
    component_types: ClassVar[dict[str, type]] = {"Ticker": Ticker}


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

    def test_editor_schema_examples_cover_every_action(self):
        self.assertEqual(set(EDITOR_SCHEMA["examples"]), set(EDITOR_ACTIONS))
        for action, example in EDITOR_SCHEMA["examples"].items():
            self.assertEqual(example["action"], action)
        json.dumps(EDITOR_SCHEMA, allow_nan=False)

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
        self.assertEqual(editor["schema"], EDITOR_SCHEMA_VERSION)
        self.assertIsNone(editor["selection"])
        self.assertIn("select", editor["actions"])
        self.assertEqual(editor["history"], {"undo": 0, "redo": 0, "limit": 50, "undo_stack": [], "redo_stack": []})
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

    def test_editor_named_history_and_multi_step_undo(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        cube_id = cube["id"]
        session.editor_action(
            {"action": "transform", "id": cube_id, "position": [1.0, 0.0, 0.0]}
        )
        session.editor_action(
            {"action": "set_node", "id": cube_id, "name": "hero"}
        )
        created = session.editor_action(
            {"action": "create_node", "name": "marker", "position": [2.0, 0.0, 0.0]}
        )
        history = created["history"]
        self.assertEqual(history["undo"], 3)
        self.assertEqual(
            history["undo_stack"],
            [
                "create_node marker",
                f"set_node {cube_id}",
                f"transform {cube_id}",
            ],
        )
        self.assertEqual(history["redo_stack"], [])

        undone = session.editor_action({"action": "undo", "steps": 2})
        self.assertEqual(undone["history"]["undo"], 1)
        self.assertEqual(undone["history"]["undo_stack"], [f"transform {cube_id}"])
        self.assertEqual(
            undone["history"]["redo_stack"],
            [f"set_node {cube_id}", "create_node marker"],
        )
        nodes = {node["id"]: node for node in undone["nodes"]}
        self.assertEqual(nodes[cube_id]["name"], "cube-0")
        self.assertEqual(nodes[cube_id]["transform"]["position"], [1.0, 0.0, 0.0])
        self.assertNotIn("marker", {node["name"] for node in undone["nodes"]})

        redone = session.editor_action({"action": "redo"})
        self.assertEqual(redone["history"]["undo"], 2)
        self.assertEqual(redone["history"]["redo"], 1)
        self.assertEqual(redone["history"]["redo_stack"], ["create_node marker"])
        replayed_cube = next(
            node for node in redone["nodes"] if node["id"] == cube_id
        )
        self.assertEqual(replayed_cube["name"], "hero")
        redone = session.editor_action({"action": "redo", "steps": 1})
        self.assertEqual(redone["history"]["redo"], 0)
        self.assertIn("marker", {node["name"] for node in redone["nodes"]})

        rewound = session.editor_action({"action": "undo", "steps": 5})
        self.assertEqual(rewound["history"]["undo"], 0)
        self.assertEqual(rewound["history"]["redo"], 3)
        replayed = session.editor_action({"action": "redo", "steps": 5})
        self.assertEqual(replayed["history"]["undo"], 3)
        self.assertEqual(replayed["history"]["redo"], 0)

        for steps in (0, 101, True, "2"):
            with self.assertRaises(WebProblem) as caught:
                session.editor_action({"action": "undo", "steps": steps})
            self.assertEqual(caught.exception.status, 400)

        batched = session.editor_action(
            {
                "action": "batch",
                "actions": [
                    {"action": "create_node", "name": "batch-one"},
                    {"action": "create_node", "name": "batch-two"},
                ],
            }
        )
        self.assertEqual(batched["history"]["undo"], 4)
        self.assertEqual(batched["history"]["undo_stack"][0], "batch 2 actions")

    def test_editor_asset_metadata(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        assets = {asset["id"]: asset for asset in editor["assets"]}
        self.assertGreater(assets["mesh.cube"]["metadata"]["vertices"], 0)
        self.assertGreater(assets["mesh.cube"]["metadata"]["triangles"], 0)
        bounds = assets["mesh.cube"]["metadata"]["bounds"]
        self.assertEqual(len(bounds["min"]), 3)
        self.assertEqual(len(bounds["max"]), 3)
        self.assertLessEqual(bounds["min"][0], bounds["max"][0])
        self.assertIn("color", assets["material.cube.0"]["metadata"])
        self.assertEqual(assets["texture.floor-checker"]["metadata"]["width"], 64)
        self.assertEqual(assets["texture.floor-checker"]["metadata"]["height"], 64)
        self.assertTrue(
            assets["texture.floor-checker"]["metadata"]["preview"].startswith(
                "data:image/png;base64,"
            )
        )
        self.assertTrue(
            assets["material.floor"]["metadata"]["texture"]["preview"].startswith(
                "data:image/png;base64,"
            )
        )

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

    def test_editor_assign_assets_to_selection(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cubes = [
            node for node in editor["nodes"] if node["mesh"] == "mesh.cube"
        ][:2]
        ids = [node["id"] for node in cubes]
        selected = session.editor_action(
            {"action": "select_many", "ids": ids, "mode": "replace"}
        )
        self.assertEqual(selected["selection_count"], 2)
        assigned = session.editor_action(
            {
                "action": "assign_asset_selection",
                "mesh": "mesh.sphere",
                "material": "material.orb",
            }
        )
        selected_nodes = [
            node for node in assigned["nodes"] if node["id"] in ids
        ]
        self.assertEqual(
            {node["mesh"] for node in selected_nodes}, {"mesh.sphere"}
        )
        self.assertEqual(
            {node["material"] for node in selected_nodes},
            {"material.orb"},
        )
        self.assertEqual(assigned["history"]["undo"], 1)

        original = {node["id"]: node for node in editor["nodes"]}
        undone = session.editor_action({"action": "undo"})
        restored = [node for node in undone["nodes"] if node["id"] in ids]
        self.assertEqual(
            {node["mesh"] for node in restored},
            {original[node_id]["mesh"] for node_id in ids},
        )
        self.assertEqual(undone["history"]["undo"], 0)

        session.editor_action({"action": "select_many", "ids": [], "mode": "replace"})
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {"action": "assign_asset_selection", "mesh": "mesh.sphere"}
            )
        self.assertEqual(caught.exception.status, 400)

        session.editor_action(
            {"action": "select_many", "ids": ids, "mode": "replace"}
        )
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {"action": "assign_asset_selection", "mesh": "missing.mesh"}
            )
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(session.editor()["history"]["undo"], 0)

    def test_editor_layer_visibility(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        default = next(
            layer for layer in editor["layers"] if layer["name"] == "default"
        )
        self.assertGreater(default["count"], 0)
        self.assertEqual(editor["hidden_layers"], [])

        hidden = session.editor_action(
            {
                "action": "set_layer_visible",
                "name": "default",
                "visible": False,
            }
        )
        self.assertEqual(hidden["hidden_layers"], ["default"])
        self.assertEqual(len(hidden["nodes"]), len(editor["nodes"]))
        self.assertEqual(hidden["layers"], editor["layers"])

        shown = session.editor_action(
            {
                "action": "set_layer_visible",
                "name": "default",
                "visible": True,
            }
        )
        self.assertEqual(shown["hidden_layers"], [])

        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {"action": "set_layer_visible", "name": "", "visible": False}
            )
        self.assertEqual(caught.exception.status, 400)
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {"action": "set_layer_visible", "name": "default", "visible": 1}
            )
        self.assertEqual(caught.exception.status, 400)

    def test_editor_node_locking_blocks_edits(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cubes = [
            node for node in editor["nodes"] if node["mesh"] == "mesh.cube"
        ][:2]
        ids = [node["id"] for node in cubes]
        session.editor_action(
            {"action": "select_many", "ids": ids, "mode": "replace"}
        )
        locked = session.editor_action(
            {"action": "set_nodes_locked", "ids": ids, "locked": True}
        )
        self.assertEqual(locked["locked_count"], 2)
        self.assertEqual(set(locked["locked_ids"]), set(ids))
        locked_nodes = [
            node for node in locked["nodes"] if node["id"] in ids
        ]
        self.assertTrue(all(node["locked"] for node in locked_nodes))

        created = session.editor_action(
            {
                "action": "create_node",
                "name": "locked-child",
                "parent": ids[0],
            }
        )
        child_id = next(
            node["id"]
            for node in created["nodes"]
            if node["name"] == "locked-child"
        )
        child = next(
            node for node in created["nodes"] if node["id"] == child_id
        )
        self.assertTrue(child["locked"])
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "transform",
                    "id": child_id,
                    "position": [2.0, 0.0, 0.0],
                }
            )
        self.assertEqual(caught.exception.status, 400)

        for payload in (
            {
                "action": "transform_selection",
                "position": [1.0, 0.0, 0.0],
            },
            {"action": "delete_selection"},
            {
                "action": "assign_asset_selection",
                "mesh": "mesh.sphere",
            },
            {
                "action": "set_selection_transform",
                "position": [1.0, 0.0, 0.0],
            },
            {
                "action": "reparent_node",
                "id": ids[0],
                "parent": "floor",
            },
            {
                "action": "set_component",
                "id": ids[0],
                "type": "Health",
                "data": {},
            },
        ):
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(payload)
            self.assertEqual(caught.exception.status, 400)

        unlocked = session.editor_action(
            {"action": "set_nodes_locked", "ids": ids, "locked": False}
        )
        self.assertEqual(unlocked["locked_count"], 0)
        moved = session.editor_action(
            {
                "action": "transform_selection",
                "position": [1.0, 0.0, 0.0],
            }
        )
        self.assertEqual(moved["locked_count"], 0)

    def test_editor_copy_paste_selection(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cubes = [
            node for node in editor["nodes"] if node["mesh"] == "mesh.cube"
        ][:2]
        ids = [node["id"] for node in cubes]
        session.editor_action(
            {"action": "select_many", "ids": ids, "mode": "replace"}
        )
        copied = session.editor_action({"action": "copy_selection"})
        self.assertEqual(copied["clipboard"]["count"], 2)

        session.editor_action({"action": "select", "id": None})
        pasted = session.editor_action({"action": "paste_nodes"})
        self.assertEqual(pasted["selection_count"], 2)
        pasted_ids = pasted["selected_ids"]
        self.assertTrue(set(pasted_ids).isdisjoint(ids))
        originals = {node["id"]: node for node in editor["nodes"]}
        pasted_nodes = [
            node for node in pasted["nodes"] if node["id"] in pasted_ids
        ]
        self.assertEqual(
            {node["name"] for node in pasted_nodes},
            {originals[node_id]["name"] for node_id in ids},
        )
        self.assertEqual(
            {node["mesh"] for node in pasted_nodes}, {"mesh.cube"}
        )
        self.assertEqual(pasted["history"]["undo"], 1)

        undone = session.editor_action({"action": "undo"})
        self.assertTrue(
            set(pasted_ids).isdisjoint(
                {node["id"] for node in undone["nodes"]}
            )
        )

        parent = next(
            node for node in undone["nodes"] if node["name"] == "cube-0"
        )
        session.editor_action({"action": "select", "id": parent["id"]})
        child_paste = session.editor_action(
            {"action": "paste_nodes", "parent": parent["id"]}
        )
        child_id = child_paste["selected_ids"][0]
        child = next(
            node for node in child_paste["nodes"] if node["id"] == child_id
        )
        self.assertEqual(child["parent_id"], parent["id"])

        bare = GameSession(CubeDemo())
        with self.assertRaises(WebProblem) as caught:
            bare.editor_action({"action": "copy_selection"})
        self.assertEqual(caught.exception.status, 400)
        with self.assertRaises(WebProblem) as caught:
            bare.editor_action({"action": "paste_nodes"})
        self.assertEqual(caught.exception.status, 400)

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

    def test_editor_prefab_instance_revert_and_apply(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        original = cube["transform"]["position"]
        session.editor_action({"action": "select", "id": cube["id"]})
        session.editor_action({"action": "save_prefab", "name": "cube-template"})
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template", "instance": "copy"}
        )
        instance_id = inserted["selection"]["id"]
        self.assertEqual(
            inserted["selection"]["prefab_link"],
            {"name": "cube-template", "instance": "copy"},
        )
        self.assertEqual(
            inserted["prefab_instances"],
            [{"id": instance_id, "name": "cube-template", "instance": "copy"}],
        )
        session.editor_action(
            {"action": "transform", "id": instance_id, "position": [5.0, 0.0, 0.0]}
        )
        reverted = session.editor_action(
            {"action": "revert_prefab", "id": instance_id}
        )
        self.assertEqual(reverted["selection"]["id"], instance_id)
        self.assertEqual(reverted["selection"]["transform"]["position"], original)
        self.assertEqual(
            reverted["selection"]["prefab_link"],
            {"name": "cube-template", "instance": "copy"},
        )
        undone = session.editor_action({"action": "undo"})
        self.assertEqual(
            undone["selection"]["transform"]["position"], [5.0, 0.0, 0.0]
        )
        applied = session.editor_action({"action": "apply_prefab", "id": instance_id})
        self.assertEqual(applied["selection"]["prefab_link"]["name"], "cube-template")
        self.assertAlmostEqual(
            session.prefabs["cube-template"].roots[0].transform.position.x, 5.0
        )
        second = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template"}
        )
        self.assertEqual(
            second["selection"]["prefab_link"],
            {"name": "cube-template", "instance": "cube-template"},
        )
        self.assertAlmostEqual(second["selection"]["transform"]["position"][0], 5.0)
        with self.assertRaises(WebProblem) as caught:
            session.editor_action({"action": "apply_prefab", "id": cube["id"]})
        self.assertEqual(caught.exception.status, 400)

    def test_editor_multi_root_prefab_instance_group(self):
        session = GameSession(CubeDemo())
        session.prefabs["pair"] = Prefab(
            "pair",
            (
                Node(
                    "left",
                    id="left",
                    transform=Transform(position=Vec3(-1.0, 0.0, 0.0)),
                ),
                Node(
                    "right",
                    id="right",
                    transform=Transform(position=Vec3(1.0, 0.0, 0.0)),
                ),
            ),
        )
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "pair", "instance": "pair-1"}
        )
        linked = [
            node for node in inserted["nodes"] if node["prefab_link"] is not None
        ]
        self.assertEqual(
            [node["id"] for node in linked], ["pair-1:left", "pair-1:right"]
        )
        self.assertEqual(
            inserted["prefab_instances"],
            [
                {"id": "pair-1:left", "name": "pair", "instance": "pair-1"},
                {"id": "pair-1:right", "name": "pair", "instance": "pair-1"},
            ],
        )
        self.assertEqual(inserted["prefab_instance_count"], 1)
        session.editor_action(
            {
                "action": "transform",
                "id": "pair-1:left",
                "position": [-5.0, 0.0, 0.0],
            }
        )
        session.editor_action(
            {
                "action": "transform",
                "id": "pair-1:right",
                "position": [5.0, 0.0, 0.0],
            }
        )
        reverted = session.editor_action(
            {"action": "revert_prefab", "id": "pair-1:right"}
        )
        self.assertEqual(reverted["selection"]["id"], "pair-1:left")
        positions = {
            node["id"]: node["transform"]["position"]
            for node in reverted["nodes"]
        }
        self.assertEqual(positions["pair-1:left"], [-1.0, 0.0, 0.0])
        self.assertEqual(positions["pair-1:right"], [1.0, 0.0, 0.0])
        undone = session.editor_action({"action": "undo"})
        positions = {
            node["id"]: node["transform"]["position"]
            for node in undone["nodes"]
        }
        self.assertEqual(positions["pair-1:left"], [-5.0, 0.0, 0.0])
        self.assertEqual(positions["pair-1:right"], [5.0, 0.0, 0.0])
        applied = session.editor_action(
            {"action": "apply_prefab", "id": "pair-1:left"}
        )
        self.assertEqual(applied["prefabs"][0]["node_count"], 2)
        roots = session.prefabs["pair"].roots
        self.assertEqual([root.id for root in roots], ["left", "right"])
        self.assertEqual([root.transform.position.x for root in roots], [-5.0, 5.0])

    def test_editor_multi_root_group_delete_and_reparent(self):
        session = GameSession(CubeDemo())
        session.prefabs["pair"] = Prefab(
            "pair",
            (
                Node("left", id="left"),
                Node("right", id="right"),
            ),
        )
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "pair", "instance": "pair-1"}
        )
        cube = next(node for node in inserted["nodes"] if node["name"] == "cube-0")
        reparented = session.editor_action(
            {"action": "reparent_node", "id": "pair-1:left", "parent": cube["id"]}
        )
        parents = {
            node["id"]: node["parent_id"]
            for node in reparented["nodes"]
            if node["id"] in ("pair-1:left", "pair-1:right")
        }
        self.assertEqual(
            parents,
            {"pair-1:left": cube["id"], "pair-1:right": cube["id"]},
        )
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "reparent_node",
                    "id": "pair-1:left",
                    "parent": "pair-1:right",
                }
            )
        self.assertEqual(caught.exception.status, 400)
        deleted = session.editor_action(
            {"action": "delete_node", "id": "pair-1:right"}
        )
        ids = {node["id"] for node in deleted["nodes"]}
        self.assertNotIn("pair-1:left", ids)
        self.assertNotIn("pair-1:right", ids)
        self.assertEqual(deleted["prefab_instances"], [])
        undone = session.editor_action({"action": "undo"})
        ids = {node["id"] for node in undone["nodes"]}
        self.assertIn("pair-1:left", ids)
        self.assertIn("pair-1:right", ids)

    def test_editor_nested_prefab_capture_revert_and_apply(self):
        session = GameSession(CubeDemo())
        session.prefabs["inner"] = Prefab(
            "inner",
            (
                Node(
                    "inner",
                    id="inner",
                    transform=Transform(position=Vec3(0.0, 1.0, 0.0)),
                ),
            ),
        )
        session.editor_action(
            {"action": "create_node", "id": "outer", "name": "outer"}
        )
        session.editor_action(
            {
                "action": "insert_prefab",
                "name": "inner",
                "parent": "outer",
                "instance": "inner-1",
            }
        )
        session.editor_action(
            {"action": "save_prefab", "id": "outer", "name": "outer"}
        )
        session.editor_action({"action": "delete_node", "id": "outer"})
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "outer", "instance": "outer-1"}
        )
        outer_id = "outer-1:outer"
        nested_id = "outer-1.inner-1:inner"
        nested = next(node for node in inserted["nodes"] if node["id"] == nested_id)
        self.assertEqual(
            nested["prefab_link"],
            {"name": "inner", "instance": "outer-1.inner-1"},
        )
        self.assertEqual(inserted["prefab_instance_count"], 2)
        session.editor_action(
            {
                "action": "transform",
                "id": nested_id,
                "position": [3.0, 1.0, 0.0],
            }
        )
        overrides = session.editor()["prefab_overrides"]
        groups = {group["instance"]: group for group in overrides}
        self.assertNotIn("outer-1", groups)
        self.assertIn("outer-1.inner-1", groups)
        override_fields = groups["outer-1.inner-1"]["nodes"][0]["fields"]
        self.assertIn("transform.position", override_fields)
        self.assertEqual(session.editor()["prefab_override_count"], 1)
        reverted = session.editor_action(
            {"action": "revert_prefab", "id": nested_id}
        )
        nested = next(node for node in reverted["nodes"] if node["id"] == nested_id)
        self.assertEqual(nested["transform"]["position"], [0.0, 1.0, 0.0])
        self.assertEqual(
            reverted["selection"]["prefab_link"],
            {"name": "inner", "instance": "outer-1.inner-1"},
        )
        undone = session.editor_action({"action": "undo"})
        nested = next(node for node in undone["nodes"] if node["id"] == nested_id)
        self.assertEqual(nested["transform"]["position"], [3.0, 1.0, 0.0])
        applied = session.editor_action(
            {"action": "apply_prefab", "id": nested_id}
        )
        inner_entry = next(
            entry for entry in applied["prefabs"] if entry["name"] == "inner"
        )
        self.assertEqual(inner_entry["node_count"], 1)
        self.assertEqual(session.prefabs["inner"].roots[0].id, "inner")
        self.assertEqual(
            session.prefabs["inner"].roots[0].transform.position.x, 3.0
        )
        outer_link = next(
            node["prefab_link"]
            for node in applied["nodes"]
            if node["id"] == outer_id
        )
        self.assertEqual(outer_link, {"name": "outer", "instance": "outer-1"})
        reverted_outer = session.editor_action(
            {"action": "revert_prefab", "id": outer_id}
        )
        nested = next(
            node for node in reverted_outer["nodes"] if node["id"] == nested_id
        )
        self.assertEqual(
            nested["prefab_link"],
            {"name": "inner", "instance": "outer-1.inner-1"},
        )
        self.assertEqual(nested["transform"]["position"], [0.0, 1.0, 0.0])
        undone_outer = session.editor_action({"action": "undo"})
        nested = next(
            node for node in undone_outer["nodes"] if node["id"] == nested_id
        )
        self.assertEqual(nested["transform"]["position"], [3.0, 1.0, 0.0])

    def test_editor_prefab_override_revert_and_apply(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        template_position = cube["transform"]["position"]
        session.editor_action({"action": "select", "id": cube["id"]})
        session.editor_action({"action": "save_prefab", "name": "cube-template"})
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template", "instance": "copy"}
        )
        instance_id = inserted["selection"]["id"]
        session.editor_action(
            {"action": "transform", "id": instance_id, "position": [2.0, 0.0, 0.0]}
        )
        session.editor_action(
            {
                "action": "set_node",
                "id": instance_id,
                "name": "hero",
                "visible": False,
            }
        )
        editor = session.editor()
        group = next(
            item for item in editor["prefab_overrides"] if item["instance"] == "copy"
        )
        self.assertEqual(group["prefab"], "cube-template")
        self.assertEqual(group["roots"], [instance_id])
        node_override = next(
            item for item in group["nodes"] if item["id"] == instance_id
        )
        self.assertEqual(
            node_override["fields"]["transform.position"],
            {"template": template_position, "instance": [2.0, 0.0, 0.0]},
        )
        self.assertEqual(
            node_override["fields"]["name"],
            {"template": "cube-0", "instance": "hero"},
        )
        self.assertEqual(
            node_override["fields"]["visible"],
            {"template": True, "instance": False},
        )
        reverted = session.editor_action(
            {
                "action": "revert_prefab_override",
                "id": instance_id,
                "field": "transform.position",
            }
        )
        fields = next(
            item for item in reverted["prefab_overrides"][0]["nodes"]
        )["fields"]
        self.assertNotIn("transform.position", fields)
        self.assertIn("name", fields)
        undone = session.editor_action({"action": "undo"})
        fields = next(
            item for item in undone["prefab_overrides"][0]["nodes"]
        )["fields"]
        self.assertIn("transform.position", fields)
        session.editor_action(
            {
                "action": "apply_prefab_override",
                "id": instance_id,
                "field": "name",
            }
        )
        self.assertEqual(session.prefabs["cube-template"].roots[0].name, "hero")
        second = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template", "instance": "copy-2"}
        )
        self.assertEqual(second["selection"]["name"], "hero")
        session.editor_action(
            {
                "action": "apply_prefab_override",
                "id": instance_id,
                "field": "transform.position",
            }
        )
        self.assertEqual(
            list(session.prefabs["cube-template"].roots[0].transform.position),
            [2.0, 0.0, 0.0],
        )
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "revert_prefab_override",
                    "id": instance_id,
                    "field": "missing",
                }
            )
        self.assertEqual(caught.exception.status, 400)

    def test_editor_prefab_component_override_revert_and_apply(self):
        session = GameSession(ComponentDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        session.editor_action({"action": "select", "id": cube["id"]})
        session.editor_action(
            {
                "action": "set_component",
                "id": cube["id"],
                "type": "Health",
                "data": {"value": 10},
            }
        )
        session.editor_action({"action": "save_prefab", "name": "health-cube"})
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "health-cube", "instance": "copy"}
        )
        instance_id = inserted["selection"]["id"]
        session.editor_action(
            {
                "action": "set_component",
                "id": instance_id,
                "type": "Health",
                "data": {"value": 99},
            }
        )
        editor = session.editor()
        group = next(
            item for item in editor["prefab_overrides"] if item["instance"] == "copy"
        )
        fields = next(
            item for item in group["nodes"] if item["id"] == instance_id
        )["fields"]
        self.assertEqual(
            fields["components.Health"],
            {"template": {"value": 10}, "instance": {"value": 99}},
        )
        session.editor_action(
            {
                "action": "apply_prefab_override",
                "id": instance_id,
                "field": "components.Health",
            }
        )
        self.assertEqual(
            session.prefabs["health-cube"].roots[0].require_component(Health).value,
            99,
        )
        session.editor_action(
            {
                "action": "set_component",
                "id": instance_id,
                "type": "Health",
                "data": {"value": 50},
            }
        )
        reverted = session.editor_action(
            {
                "action": "revert_prefab_override",
                "id": instance_id,
                "field": "components.Health",
            }
        )
        node = next(
            item for item in reverted["nodes"] if item["id"] == instance_id
        )
        health = next(
            item for item in node["component_data"] if item["type"] == "Health"
        )
        self.assertEqual(health["data"], {"value": 99})
        undone = session.editor_action({"action": "undo"})
        node = next(
            item for item in undone["nodes"] if item["id"] == instance_id
        )
        health = next(
            item for item in node["component_data"] if item["type"] == "Health"
        )
        self.assertEqual(health["data"], {"value": 50})

    def test_editor_prefab_mesh_override_revert_and_apply(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        template_mesh = cube["mesh"]
        session.editor_action({"action": "select", "id": cube["id"]})
        session.editor_action({"action": "save_prefab", "name": "cube-template"})
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template", "instance": "copy"}
        )
        instance_id = inserted["selection"]["id"]
        session.editor_action(
            {"action": "assign_asset", "id": instance_id, "mesh": "mesh.sphere"}
        )
        editor = session.editor()
        group = next(
            item for item in editor["prefab_overrides"] if item["instance"] == "copy"
        )
        fields = next(
            item for item in group["nodes"] if item["id"] == instance_id
        )["fields"]
        self.assertEqual(
            fields["mesh"],
            {"template": template_mesh, "instance": "mesh.sphere"},
        )
        reverted = session.editor_action(
            {
                "action": "revert_prefab_override",
                "id": instance_id,
                "field": "mesh",
            }
        )
        node = next(
            item for item in reverted["nodes"] if item["id"] == instance_id
        )
        self.assertEqual(node["mesh"], template_mesh)
        session.editor_action(
            {"action": "assign_asset", "id": instance_id, "mesh": "mesh.sphere"}
        )
        session.editor_action(
            {
                "action": "apply_prefab_override",
                "id": instance_id,
                "field": "mesh",
            }
        )
        second = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template", "instance": "copy-2"}
        )
        self.assertEqual(second["selection"]["mesh"], "mesh.sphere")

    def test_editor_apply_prefab_override_persists_library(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            editor = session.editor()
            cube = next(
                node for node in editor["nodes"] if node["name"] == "cube-0"
            )
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action(
                {"action": "save_prefab", "name": "cube-template"}
            )
            inserted = session.editor_action(
                {
                    "action": "insert_prefab",
                    "name": "cube-template",
                    "instance": "copy",
                }
            )
            instance_id = inserted["selection"]["id"]
            session.editor_action(
                {
                    "action": "transform",
                    "id": instance_id,
                    "position": [2.0, 0.0, 0.0],
                }
            )
            session.editor_action(
                {
                    "action": "apply_prefab_override",
                    "id": instance_id,
                    "field": "transform.position",
                }
            )
            reloaded = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            fresh = reloaded.editor_action(
                {
                    "action": "insert_prefab",
                    "name": "cube-template",
                    "instance": "fresh",
                }
            )
            self.assertEqual(
                fresh["selection"]["transform"]["position"], [2.0, 0.0, 0.0]
            )

    def test_editor_batch_can_revert_prefab_instance(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        original = cube["transform"]["position"]
        session.editor_action({"action": "select", "id": cube["id"]})
        session.editor_action({"action": "save_prefab", "name": "cube-template"})
        inserted = session.editor_action(
            {"action": "insert_prefab", "name": "cube-template", "instance": "copy"}
        )
        instance_id = inserted["selection"]["id"]
        session.editor_action(
            {"action": "transform", "id": instance_id, "position": [5.0, 0.0, 0.0]}
        )
        batched = session.editor_action(
            {
                "action": "batch",
                "actions": [
                    {
                        "action": "transform",
                        "id": instance_id,
                        "position": [2.0, 0.0, 0.0],
                    },
                    {"action": "revert_prefab", "id": instance_id},
                ],
            }
        )
        self.assertEqual(batched["selection"]["transform"]["position"], original)
        undone = session.editor_action({"action": "undo"})
        self.assertEqual(
            undone["selection"]["transform"]["position"], [5.0, 0.0, 0.0]
        )

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
                {
                    "project_dir": None,
                    "prefab_dir": prefab_dir.as_posix(),
                    "scene_dir": None,
                    "animation_dir": None,
                    "material_dir": None,
                },
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

    def test_editor_prefab_edit_mode_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action({"action": "save_prefab", "name": "hero"})
            session.editor_action({"action": "create_node", "name": "before-enter"})
            before = session.editor()
            before_undo = before["history"]["undo"]

            opened = session.editor_action({"action": "edit_prefab", "name": "hero"})
            self.assertEqual(opened["prefab_edit"]["name"], "hero")
            self.assertEqual(opened["prefab_edit"]["root_count"], 1)
            self.assertFalse(opened["prefab_edit"]["dirty"])
            self.assertEqual(opened["history"]["undo"], 0)
            self.assertEqual(
                opened["scene_settings"]["camera"],
                before["scene_settings"]["camera"],
            )
            root = opened["selection"]
            self.assertEqual(root["prefab_link"]["name"], "hero")
            self.assertNotIn(
                "before-enter", {node["name"] for node in opened["nodes"]}
            )

            edited = session.editor_action(
                {
                    "action": "set_node",
                    "id": root["id"],
                    "name": "hero-edited",
                }
            )
            self.assertTrue(edited["prefab_edit"]["dirty"])
            self.assertEqual(edited["selection"]["name"], "hero-edited")
            session.editor_action(
                {
                    "action": "transform",
                    "id": root["id"],
                    "position": [4.0, 5.0, 6.0],
                }
            )

            for payload in (
                {"action": "save_scene", "name": "blocked"},
                {"action": "play_start"},
                {
                    "action": "rename_prefab",
                    "name": "hero",
                    "new_name": "blocked",
                },
            ):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(payload)
                self.assertEqual(caught.exception.status, 400)

            saved = session.editor_action({"action": "save_prefab_edit"})
            self.assertFalse(saved["prefab_edit"]["dirty"])
            self.assertTrue((prefab_dir / "hero.kprefab").is_file())
            self.assertEqual(session.prefabs["hero"].roots[0].name, "hero-edited")

            session.editor_action(
                {
                    "action": "transform",
                    "id": root["id"],
                    "position": [9.0, 9.0, 9.0],
                }
            )
            discarded = session.editor_action(
                {"action": "close_prefab_edit", "save": False}
            )
            self.assertIsNone(discarded["prefab_edit"])
            self.assertEqual(discarded["history"]["undo"], before_undo)
            self.assertIn(
                "before-enter", {node["name"] for node in discarded["nodes"]}
            )
            self.assertEqual(discarded["selection"]["name"], "before-enter")

            reopened = session.editor_action({"action": "edit_prefab", "name": "hero"})
            root = reopened["selection"]
            self.assertEqual(root["name"], "hero-edited")
            self.assertEqual(root["transform"]["position"], [4.0, 5.0, 6.0])
            session.editor_action(
                {"action": "set_node", "id": root["id"], "name": "hero-final"}
            )
            closed = session.editor_action(
                {"action": "close_prefab_edit", "save": True}
            )
            self.assertIsNone(closed["prefab_edit"])
            self.assertEqual(session.prefabs["hero"].roots[0].name, "hero-final")

            reloaded = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            inserted = reloaded.editor_action(
                {"action": "insert_prefab", "name": "hero", "instance": "fresh"}
            )
            self.assertEqual(inserted["selection"]["name"], "hero-final")

            for payload in (
                {"action": "save_prefab_edit"},
                {"action": "close_prefab_edit", "save": False},
            ):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(payload)
                self.assertEqual(caught.exception.status, 400)

    def test_editor_refresh_prefab_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action({"action": "save_prefab", "name": "hero"})
            session.editor_action(
                {"action": "insert_prefab", "name": "hero", "instance": "a"}
            )
            session.editor_action(
                {"action": "insert_prefab", "name": "hero", "instance": "b"}
            )

            opened = session.editor_action({"action": "edit_prefab", "name": "hero"})
            root_id = opened["prefab_edit"]["roots"][0]
            session.editor_action(
                {"action": "set_node", "id": root_id, "name": "hero-v2"}
            )
            session.editor_action({"action": "close_prefab_edit", "save": True})

            refreshed = session.editor_action(
                {"action": "refresh_prefab_instances", "name": "hero"}
            )
            self.assertEqual(refreshed["prefab_refresh"]["refreshed"], 2)
            self.assertEqual(refreshed["prefab_refresh"]["total"], 2)
            names = {node["id"]: node["name"] for node in refreshed["nodes"]}
            self.assertEqual(names["a:cube-0"], "hero-v2")
            self.assertEqual(names["b:cube-0"], "hero-v2")

            undone = session.editor_action({"action": "undo"})
            names = {node["id"]: node["name"] for node in undone["nodes"]}
            self.assertEqual(names["a:cube-0"], "cube-0")
            self.assertEqual(names["b:cube-0"], "cube-0")

            redone = session.editor_action({"action": "redo"})
            names = {node["id"]: node["name"] for node in redone["nodes"]}
            self.assertEqual(names["a:cube-0"], "hero-v2")
            self.assertEqual(names["b:cube-0"], "hero-v2")

            session.editor_action(
                {"action": "set_node", "id": "a:cube-0", "name": "custom"}
            )
            refreshed = session.editor_action(
                {
                    "action": "refresh_prefab_instances",
                    "name": "hero",
                    "keep_overrides": True,
                }
            )
            self.assertEqual(refreshed["prefab_refresh"]["refreshed"], 1)
            self.assertEqual(refreshed["prefab_refresh"]["skipped_overrides"], 1)
            names = {node["id"]: node["name"] for node in refreshed["nodes"]}
            self.assertEqual(names["a:cube-0"], "custom")
            self.assertEqual(names["b:cube-0"], "hero-v2")

            forced = session.editor_action(
                {"action": "refresh_prefab_instances", "name": "hero"}
            )
            self.assertEqual(forced["prefab_refresh"]["refreshed"], 2)
            names = {node["id"]: node["name"] for node in forced["nodes"]}
            self.assertEqual(names["a:cube-0"], "hero-v2")
            self.assertEqual(names["b:cube-0"], "hero-v2")

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "refresh_prefab_instances",
                        "name": "hero",
                        "keep_overrides": "yes",
                    }
                )
            self.assertEqual(caught.exception.status, 400)

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "refresh_prefab_instances", "name": "missing"}
                )
            self.assertEqual(caught.exception.status, 404)

            session.editor_action({"action": "edit_prefab", "name": "hero"})
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "refresh_prefab_instances", "name": "hero"}
                )
            self.assertEqual(caught.exception.status, 400)
            session.editor_action({"action": "close_prefab_edit", "save": False})

    def test_editor_multi_root_prefab_save_from_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            left = session.editor_action(
                {"action": "create_node", "name": "left"}
            )["selection"]["id"]
            right = session.editor_action(
                {"action": "create_node", "name": "right"}
            )["selection"]["id"]
            saved = session.editor_action(
                {"action": "save_prefab", "ids": [left, right], "name": "pair"}
            )
            entry = next(
                item for item in saved["prefabs"] if item["name"] == "pair"
            )
            self.assertEqual(entry["node_count"], 2)
            self.assertEqual(len(session.prefabs["pair"].roots), 2)
            self.assertTrue((prefab_dir / "pair.kprefab").is_file())

            inserted = session.editor_action(
                {"action": "insert_prefab", "name": "pair", "instance": "pair-1"}
            )
            ids = {node["id"] for node in inserted["nodes"]}
            self.assertIn(f"pair-1:{left}", ids)
            self.assertIn(f"pair-1:{right}", ids)
            self.assertEqual(inserted["prefab_instance_count"], 1)

            duplicate = session.editor_action(
                {
                    "action": "save_prefab",
                    "ids": [left, left, right],
                    "name": "pair-copy",
                }
            )
            self.assertIn(
                "pair-copy",
                {item["name"] for item in duplicate["prefabs"]},
            )
            self.assertEqual(len(session.prefabs["pair-copy"].roots), 2)

            parent = session.editor_action(
                {"action": "create_node", "name": "tree"}
            )["selection"]["id"]
            child = session.editor_action(
                {"action": "create_node", "name": "child", "parent": parent}
            )["selection"]["id"]
            nested = session.editor_action(
                {
                    "action": "save_prefab",
                    "ids": [parent, child],
                    "name": "tree-prefab",
                }
            )
            entry = next(
                item
                for item in nested["prefabs"]
                if item["name"] == "tree-prefab"
            )
            self.assertEqual(entry["node_count"], 2)
            self.assertEqual(len(session.prefabs["tree-prefab"].roots), 1)

            other = session.editor_action(
                {"action": "create_node", "name": "other"}
            )["selection"]["id"]
            other_child = session.editor_action(
                {"action": "create_node", "name": "other-child", "parent": other}
            )["selection"]["id"]
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "save_prefab",
                        "ids": [left, other_child],
                        "name": "bad",
                    }
                )
            self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "save_prefab", "ids": [], "name": "bad"}
                )
            self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "save_prefab", "ids": ["missing"], "name": "bad"}
                )
            self.assertEqual(caught.exception.status, 404)

            reloaded = GameSession(CubeDemo(), prefab_dir=prefab_dir)
            entry = next(
                item
                for item in reloaded.editor()["prefabs"]
                if item["name"] == "pair"
            )
            self.assertEqual(entry["node_count"], 2)

    def test_editor_library_rename_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir, scene_dir=scene_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action({"action": "save_prefab", "name": "cube-template"})
            result = session.editor_action(
                {
                    "action": "rename_prefab",
                    "name": "cube-template",
                    "new_name": "cube-alt",
                }
            )
            self.assertEqual([item["name"] for item in result["prefabs"]], ["cube-alt"])
            self.assertIn("cube-alt", session.prefabs)
            self.assertNotIn("cube-template", session.prefabs)
            inserted = session.editor_action(
                {"action": "insert_prefab", "name": "cube-alt", "instance": "copy"}
            )
            self.assertIsNotNone(inserted["selection"])
            result = session.editor_action(
                {"action": "delete_prefab", "name": "cube-alt"}
            )
            self.assertEqual(result["prefabs"], [])
            self.assertNotIn("cube-alt", session.prefabs)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action({"action": "delete_prefab", "name": "cube-alt"})
            self.assertEqual(caught.exception.status, 404)

            session.editor_action({"action": "save_scene", "name": "level"})
            result = session.editor_action(
                {"action": "rename_scene", "name": "level", "new_name": "level-alt"}
            )
            self.assertEqual([item["name"] for item in result["scenes"]], ["level-alt"])
            result = session.editor_action(
                {"action": "delete_scene", "name": "level-alt"}
            )
            self.assertEqual(result["scenes"], [])
            with self.assertRaises(WebProblem) as caught:
                session.editor_action({"action": "load_scene", "name": "level-alt"})
            self.assertEqual(caught.exception.status, 404)

    def test_editor_library_trash_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir, scene_dir=scene_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action({"action": "save_prefab", "name": "cube-template"})
            session.editor_action({"action": "save_scene", "name": "level"})

            result = session.editor_action(
                {"action": "delete_prefab", "name": "cube-template"}
            )
            self.assertEqual(result["prefabs"], [])
            self.assertEqual(result["trash"]["prefabs"][0]["name"], "cube-template")
            trash = result["trash"]["prefabs"][0]["trash"]
            result = session.editor_action(
                {"action": "restore_prefab", "trash": trash}
            )
            self.assertEqual(
                [item["name"] for item in result["prefabs"]], ["cube-template"]
            )
            self.assertIn("cube-template", session.prefabs)

            result = session.editor_action({"action": "delete_scene", "name": "level"})
            self.assertEqual(result["scenes"], [])
            trash = result["trash"]["scenes"][0]["trash"]
            result = session.editor_action(
                {"action": "restore_scene", "trash": trash}
            )
            self.assertEqual([item["name"] for item in result["scenes"]], ["level"])

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "restore_prefab", "trash": "missing.kprefab"}
                )
            self.assertEqual(caught.exception.status, 404)

    def test_editor_library_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            prefab_dir = Path(directory) / "prefabs"
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), prefab_dir=prefab_dir, scene_dir=scene_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action({"action": "save_prefab", "name": "cube-template"})
            result = session.editor_action(
                {
                    "action": "duplicate_prefab",
                    "name": "cube-template",
                    "new_name": "cube-copy",
                }
            )
            self.assertEqual(
                {item["name"] for item in result["prefabs"]},
                {"cube-template", "cube-copy"},
            )
            self.assertIn("cube-copy", session.prefabs)
            session.editor_action({"action": "save_scene", "name": "level"})
            result = session.editor_action(
                {
                    "action": "duplicate_scene",
                    "name": "level",
                    "new_name": "level-copy",
                }
            )
            self.assertEqual(
                {item["name"] for item in result["scenes"]},
                {"level", "level-copy"},
            )
            loaded = session.editor_action(
                {"action": "load_scene", "name": "level-copy"}
            )
            self.assertIsNone(loaded["selection"])

    def test_editor_scene_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), scene_dir=scene_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "save_scene", "name": "level"})
            session.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [1.0, 2.0, 3.0],
                }
            )
            session.editor_action(
                {"action": "create_node", "id": "extra", "name": "Extra"}
            )
            session.editor_action({"action": "delete_node", "id": "floor"})
            session.editor_action(
                {
                    "action": "set_scene",
                    "camera": {"fov_y": 50.0},
                    "environment": {"background": [0.1, 0.2, 0.3]},
                }
            )
            result = session.editor_action(
                {"action": "diff_scene", "name": "level"}
            )
            diff = result["diff"]
            self.assertTrue(diff["has_changes"])
            self.assertIn("extra", diff["added"])
            self.assertIn("floor", diff["removed"])
            changed = next(item for item in diff["changed"] if item["id"] == cube["id"])
            self.assertIn("transform", changed["fields"])
            self.assertIn("fov_y", diff["camera"])
            self.assertIn("background", diff["environment"])
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "diff_scene", "name": "missing"}
                )
            self.assertEqual(caught.exception.status, 404)

        plain = GameSession(CubeDemo())
        with self.assertRaises(WebProblem) as caught:
            plain.editor_action({"action": "diff_scene", "name": "level"})
        self.assertEqual(caught.exception.status, 400)

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
            self.assertEqual(editor["history"], {"undo": 0, "redo": 0, "limit": 50, "undo_stack": [], "redo_stack": []})

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
            self.assertEqual(loaded["history"], {"undo": 0, "redo": 0, "limit": 50, "undo_stack": [], "redo_stack": []})
            restored = next(node for node in loaded["nodes"] if node["id"] == cube["id"])
            self.assertEqual(restored["transform"]["position"], [1.0, 2.0, 3.0])

            (scene_dir / "broken.kscene").write_text("{}", encoding="utf-8")
            broken = GameSession(CubeDemo(), scene_dir=scene_dir)
            entries = {entry["name"]: entry for entry in broken.editor()["scenes"]}
            self.assertIsNotNone(entries["broken"]["error"])

    def test_editor_add_save_unload_scene_group(self):
        with tempfile.TemporaryDirectory() as directory:
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), scene_dir=scene_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            session.editor_action({"action": "select", "id": cube["id"]})
            session.editor_action({"action": "save_scene", "name": "level"})
            added = session.editor_action({"action": "add_scene", "name": "level"})
            self.assertEqual(added["scene_group_count"], 1)
            group = added["scene_groups"][0]
            group_id = group["id"]
            self.assertEqual(group["name"], "level")
            self.assertGreater(group["node_count"], 0)
            self.assertIn(group_id, {node["id"] for node in added["nodes"]})
            self.assertTrue(group["roots"])
            root_id = group["roots"][0]
            session.editor_action(
                {
                    "action": "transform",
                    "id": root_id,
                    "position": [4.0, 0.0, 0.0],
                }
            )
            session.editor_action({"action": "save_scene_group", "id": group_id})
            session.editor_action({"action": "save_scene", "name": "composite"})
            composite = session.editor_action(
                {"action": "load_scene", "name": "composite"}
            )
            self.assertEqual(composite["scene_group_count"], 1)
            self.assertEqual(composite["scene_groups"][0]["name"], "level")
            reloaded = GameSession(CubeDemo(), scene_dir=scene_dir)
            fresh = reloaded.editor_action({"action": "add_scene", "name": "level"})
            fresh_group = fresh["scene_groups"][0]
            fresh_root = next(
                node
                for node in fresh["nodes"]
                if node["id"] == fresh_group["roots"][0]
            )
            self.assertEqual(fresh_root["transform"]["position"], [4.0, 0.0, 0.0])
            unloaded = session.editor_action(
                {"action": "unload_scene", "id": group_id}
            )
            self.assertEqual(unloaded["scene_groups"], [])
            undone = session.editor_action({"action": "undo"})
            self.assertEqual(len(undone["scene_groups"]), 1)
            self.assertEqual(undone["scene_groups"][0]["id"], group_id)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action({"action": "add_scene", "name": "missing"})
            self.assertEqual(caught.exception.status, 404)
            second = session.editor_action({"action": "add_scene", "name": "level"})
            self.assertEqual(second["scene_group_count"], 2)
            ids = [node["id"] for node in second["nodes"]]
            self.assertEqual(len(ids), len(set(ids)))

    def test_editor_multi_selection_and_batch_actions(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        roots = editor["roots"]
        self.assertGreaterEqual(len(roots), 3)
        first_id, second_id, third_id = roots[:3]
        selected = session.editor_action(
            {
                "action": "select_many",
                "ids": [first_id, second_id],
                "mode": "replace",
            }
        )
        self.assertEqual(selected["selected_ids"], [first_id, second_id])
        self.assertEqual(selected["selection_count"], 2)
        self.assertEqual(selected["selection"]["id"], first_id)
        flags = {node["id"]: node["selected"] for node in selected["nodes"]}
        self.assertTrue(flags[first_id])
        self.assertTrue(flags[second_id])
        added = session.editor_action(
            {"action": "select_many", "ids": [third_id], "mode": "add"}
        )
        self.assertEqual(
            added["selected_ids"], [first_id, second_id, third_id]
        )
        toggled = session.editor_action(
            {
                "action": "select_many",
                "ids": [second_id, third_id],
                "mode": "toggle",
            }
        )
        self.assertEqual(toggled["selected_ids"], [first_id])
        session.editor_action(
            {
                "action": "select_many",
                "ids": [first_id, second_id],
                "mode": "replace",
            }
        )
        before = {
            node["id"]: node["transform"]["position"]
            for node in session.editor()["nodes"]
        }
        visibility = {
            node["id"]: node["visible"]
            for node in session.editor()["nodes"]
        }
        transformed = session.editor_action(
            {"action": "transform_selection", "position": [1.0, 0.0, 0.0]}
        )
        moved = {
            node["id"]: node["transform"]["position"]
            for node in transformed["nodes"]
        }
        self.assertEqual(moved[first_id][0], before[first_id][0] + 1.0)
        self.assertEqual(moved[second_id][0], before[second_id][0] + 1.0)
        undone = session.editor_action({"action": "undo"})
        restored = {
            node["id"]: node["transform"]["position"]
            for node in undone["nodes"]
        }
        self.assertEqual(restored[first_id], before[first_id])
        self.assertEqual(restored[second_id], before[second_id])
        toggled_visible = session.editor_action(
            {"action": "toggle_selection_visible"}
        )
        toggled_flags = {
            node["id"]: node["visible"]
            for node in toggled_visible["nodes"]
        }
        self.assertEqual(toggled_flags[first_id], not visibility[first_id])
        self.assertEqual(toggled_flags[second_id], not visibility[second_id])
        session.editor_action({"action": "undo"})
        deleted = session.editor_action({"action": "delete_selection"})
        remaining = {node["id"] for node in deleted["nodes"]}
        self.assertNotIn(first_id, remaining)
        self.assertNotIn(second_id, remaining)
        self.assertEqual(deleted["selected_ids"], [])
        undone = session.editor_action({"action": "undo"})
        restored_ids = {node["id"] for node in undone["nodes"]}
        self.assertIn(first_id, restored_ids)
        self.assertIn(second_id, restored_ids)

    def test_editor_multi_selection_skips_selected_descendants(self):
        session = GameSession(CubeDemo())
        session.editor_action(
            {"action": "create_node", "id": "multi-parent", "name": "parent"}
        )
        session.editor_action(
            {
                "action": "create_node",
                "id": "multi-child",
                "name": "child",
                "parent": "multi-parent",
                "position": [1.0, 0.0, 0.0],
            }
        )
        session.editor_action(
            {
                "action": "select_many",
                "ids": ["multi-parent", "multi-child"],
                "mode": "replace",
            }
        )
        result = session.editor_action(
            {"action": "transform_selection", "position": [2.0, 0.0, 0.0]}
        )
        parent = next(
            node for node in result["nodes"] if node["id"] == "multi-parent"
        )
        child = next(
            node for node in result["nodes"] if node["id"] == "multi-child"
        )
        self.assertEqual(parent["transform"]["position"], [2.0, 0.0, 0.0])
        self.assertEqual(child["transform"]["position"], [1.0, 0.0, 0.0])
        undone = session.editor_action({"action": "undo"})
        parent = next(
            node for node in undone["nodes"] if node["id"] == "multi-parent"
        )
        self.assertEqual(parent["transform"]["position"], [0.0, 0.0, 0.0])

    def test_editor_multi_selection_shared_properties_and_summary(self):
        session = GameSession(CubeDemo())
        session.editor_action(
            {
                "action": "create_node",
                "id": "shared-a",
                "name": "A",
                "position": [0.0, 0.0, 0.0],
            }
        )
        session.editor_action(
            {
                "action": "create_node",
                "id": "shared-b",
                "name": "B",
                "position": [1.0, 0.0, 0.0],
            }
        )
        session.editor_action(
            {
                "action": "select_many",
                "ids": ["shared-a", "shared-b"],
                "mode": "replace",
            }
        )
        editor = session.editor()
        summary = editor["selection_summary"]
        self.assertEqual(summary["count"], 2)
        self.assertFalse(summary["name"]["shared"])
        self.assertIsNone(summary["name"]["value"])
        self.assertTrue(summary["visible"]["shared"])
        self.assertTrue(summary["visible"]["value"])
        self.assertFalse(summary["transform"]["position"]["shared"])
        self.assertIn("name", summary["mixed"])
        self.assertIn("transform.position", summary["mixed"])
        updated = session.editor_action(
            {
                "action": "set_selection_properties",
                "name": "bulk",
                "visible": False,
                "tags": ["batch"],
                "layer": "props",
            }
        )
        summary = updated["selection_summary"]
        self.assertTrue(summary["name"]["shared"])
        self.assertEqual(summary["name"]["value"], "bulk")
        self.assertTrue(summary["visible"]["shared"])
        self.assertFalse(summary["visible"]["value"])
        self.assertTrue(summary["tags"]["shared"])
        self.assertEqual(summary["tags"]["value"], ["batch"])
        self.assertTrue(summary["layer"]["shared"])
        self.assertEqual(summary["layer"]["value"], "props")
        for node_id in ("shared-a", "shared-b"):
            node = next(
                item for item in updated["nodes"] if item["id"] == node_id
            )
            self.assertEqual(node["name"], "bulk")
            self.assertFalse(node["visible"])
            self.assertEqual(node["tags"], ["batch"])
            self.assertEqual(node["layer"], "props")
        undone = session.editor_action({"action": "undo"})
        summary = undone["selection_summary"]
        self.assertFalse(summary["name"]["shared"])
        self.assertTrue(summary["visible"]["shared"])
        self.assertIn("transform.position", summary["mixed"])

    def test_editor_multi_selection_absolute_transform(self):
        session = GameSession(CubeDemo())
        session.editor_action(
            {
                "action": "create_node",
                "id": "transform-a",
                "name": "A",
                "position": [0.0, 0.0, 0.0],
            }
        )
        session.editor_action(
            {
                "action": "create_node",
                "id": "transform-b",
                "name": "B",
                "position": [1.0, 0.0, 0.0],
            }
        )
        session.editor_action(
            {
                "action": "select_many",
                "ids": ["transform-a", "transform-b"],
                "mode": "replace",
            }
        )
        updated = session.editor_action(
            {
                "action": "set_selection_transform",
                "position": [2.0, 3.0, 4.0],
                "rotation": [0.0, 0.0, 0.0, 1.0],
                "scale": [2.0, 2.0, 2.0],
            }
        )
        summary = updated["selection_summary"]
        self.assertTrue(summary["transform"]["position"]["shared"])
        self.assertEqual(
            summary["transform"]["position"]["value"], [2.0, 3.0, 4.0]
        )
        self.assertTrue(summary["transform"]["rotation"]["shared"])
        self.assertTrue(summary["transform"]["scale"]["shared"])
        for node_id in ("transform-a", "transform-b"):
            node = next(
                item for item in updated["nodes"] if item["id"] == node_id
            )
            self.assertEqual(node["transform"]["position"], [2.0, 3.0, 4.0])
            self.assertEqual(node["transform"]["rotation"], [0.0, 0.0, 0.0, 1.0])
            self.assertEqual(node["transform"]["scale"], [2.0, 2.0, 2.0])
        undone = session.editor_action({"action": "undo"})
        summary = undone["selection_summary"]
        self.assertFalse(summary["transform"]["position"]["shared"])
        positions = {
            node["id"]: node["transform"]["position"]
            for node in undone["nodes"]
        }
        self.assertEqual(positions["transform-a"], [0.0, 0.0, 0.0])
        self.assertEqual(positions["transform-b"], [1.0, 0.0, 0.0])

    def test_editor_group_rotation_and_scale_around_selection_pivot(self):
        session = GameSession(CubeDemo())
        for node_id, x in (("group-left", -1.0), ("group-right", 1.0)):
            session.editor_action(
                {
                    "action": "create_node",
                    "id": node_id,
                    "name": node_id,
                    "position": [x, 0.0, 0.0],
                }
            )
        session.editor_action(
            {
                "action": "select_many",
                "ids": ["group-left", "group-right"],
                "mode": "replace",
            }
        )
        rotated = session.editor_action(
            {
                "action": "transform_selection",
                "pivot": [0.0, 0.0, 0.0],
                "group_rotation": [0.0, 0.7071067811865476, 0.0, 0.7071067811865476],
            }
        )
        left = next(
            node for node in rotated["nodes"] if node["id"] == "group-left"
        )
        right = next(
            node for node in rotated["nodes"] if node["id"] == "group-right"
        )
        self.assertAlmostEqual(left["transform"]["position"][0], 0.0)
        self.assertAlmostEqual(left["transform"]["position"][2], 1.0)
        self.assertAlmostEqual(right["transform"]["position"][0], 0.0)
        self.assertAlmostEqual(right["transform"]["position"][2], -1.0)
        self.assertAlmostEqual(
            left["transform"]["rotation"][1], 0.7071067811865476
        )
        undone = session.editor_action({"action": "undo"})
        right = next(
            node for node in undone["nodes"] if node["id"] == "group-right"
        )
        self.assertEqual(right["transform"]["position"], [1.0, 0.0, 0.0])
        scaled = session.editor_action(
            {
                "action": "transform_selection",
                "pivot": [0.0, 0.0, 0.0],
                "group_scale": 2.0,
            }
        )
        left = next(
            node for node in scaled["nodes"] if node["id"] == "group-left"
        )
        right = next(
            node for node in scaled["nodes"] if node["id"] == "group-right"
        )
        self.assertEqual(left["transform"]["position"], [-2.0, 0.0, 0.0])
        self.assertEqual(right["transform"]["position"], [2.0, 0.0, 0.0])
        self.assertEqual(left["transform"]["scale"], [2.0, 2.0, 2.0])
        undone = session.editor_action({"action": "undo"})
        right = next(
            node for node in undone["nodes"] if node["id"] == "group-right"
        )
        self.assertEqual(right["transform"]["position"], [1.0, 0.0, 0.0])
        axis_scaled = session.editor_action(
            {
                "action": "transform_selection",
                "pivot": [0.0, 0.0, 0.0],
                "group_scale": [2.0, 1.0, 1.0],
            }
        )
        left = next(
            node for node in axis_scaled["nodes"] if node["id"] == "group-left"
        )
        right = next(
            node for node in axis_scaled["nodes"] if node["id"] == "group-right"
        )
        self.assertEqual(left["transform"]["position"], [-2.0, 0.0, 0.0])
        self.assertEqual(right["transform"]["position"], [2.0, 0.0, 0.0])
        self.assertEqual(left["transform"]["scale"], [2.0, 1.0, 1.0])
        self.assertEqual(right["transform"]["scale"], [2.0, 1.0, 1.0])
        undone = session.editor_action({"action": "undo"})
        right = next(
            node for node in undone["nodes"] if node["id"] == "group-right"
        )
        self.assertEqual(right["transform"]["position"], [1.0, 0.0, 0.0])
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "transform_selection",
                    "pivot": [0.0, 0.0, 0.0],
                    "group_scale": [2.0, 0.0, 1.0],
                }
            )
        self.assertEqual(caught.exception.status, 400)
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {
                    "action": "transform_selection",
                    "pivot": [0.0, 0.0, 0.0],
                    "group_scale": 0.0,
                }
            )
        self.assertEqual(caught.exception.status, 400)

    def test_editor_scene_group_save_as_source_settings_and_transform(self):
        with tempfile.TemporaryDirectory() as directory:
            scene_dir = Path(directory) / "scenes"
            session = GameSession(CubeDemo(), scene_dir=scene_dir)
            session.editor_action(
                {
                    "action": "set_scene",
                    "camera": {"position": [1.0, 2.0, 3.0], "fov_y": 60.0},
                    "environment": {
                        "background": [0.1, 0.2, 0.3],
                        "fog_density": 0.02,
                    },
                }
            )
            session.editor_action({"action": "save_scene", "name": "level"})
            session.editor_action(
                {"action": "set_scene", "camera": {"position": [9.0, 9.0, 9.0]}}
            )
            added = session.editor_action(
                {"action": "add_scene", "name": "level"}
            )
            group = added["scene_groups"][0]
            group_id = group["id"]
            self.assertEqual(
                group["camera"]["position"], [1.0, 2.0, 3.0]
            )
            session.editor_action(
                {
                    "action": "transform",
                    "id": group_id,
                    "position": [10.0, 0.0, 0.0],
                }
            )
            saved = session.editor_action(
                {
                    "action": "save_scene_group",
                    "id": group_id,
                    "name": "level-copy",
                }
            )
            self.assertEqual(saved["scene_groups"][0]["name"], "level-copy")
            self.assertTrue((scene_dir / "level-copy.kscene").is_file())
            loaded = session.scene_library.load("level-copy")
            self.assertEqual(loaded.camera.position, Vec3(1.0, 2.0, 3.0))
            self.assertEqual(
                loaded.root.transform.position, Vec3(10.0, 0.0, 0.0)
            )
            undone = session.editor_action({"action": "undo"})
            self.assertEqual(undone["scene_groups"][0]["name"], "level")
            reloaded = GameSession(CubeDemo(), scene_dir=scene_dir)
            fresh = reloaded.editor_action(
                {"action": "add_scene", "name": "level-copy"}
            )
            fresh_group = fresh["scene_groups"][0]
            container = next(
                node
                for node in fresh["nodes"]
                if node["id"] == fresh_group["id"]
            )
            self.assertEqual(
                container["transform"]["position"], [10.0, 0.0, 0.0]
            )
            self.assertEqual(
                fresh_group["camera"]["position"], [1.0, 2.0, 3.0]
            )

    def test_editor_scene_settings_and_undo(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        settings = editor["scene_settings"]
        self.assertIn("camera", settings)
        self.assertIn("environment", settings)
        original_camera = dict(settings["camera"])
        original_environment = dict(settings["environment"])

        result = session.editor_action(
            {
                "action": "set_scene",
                "camera": {"position": [1.0, 2.0, 3.0], "fov_y": 50.0, "pitch": 0.2},
                "environment": {
                    "background": [0.1, 0.2, 0.3],
                    "fog_density": 0.02,
                    "light": {"intensity": 0.5},
                    "point_light": {"position": [0.0, 1.0, 0.0], "radius": 5.0},
                    "shadow": False,
                },
            }
        )
        camera = result["scene_settings"]["camera"]
        self.assertEqual(camera["position"], [1.0, 2.0, 3.0])
        self.assertEqual(camera["fov_y"], 50.0)
        environment = result["scene_settings"]["environment"]
        self.assertEqual(environment["background"], [0.1, 0.2, 0.3])
        self.assertAlmostEqual(environment["fog_density"], 0.02)
        self.assertFalse(environment["shadow"])
        self.assertEqual(environment["point_light"]["radius"], 5.0)

        scene = session.scene()
        self.assertEqual(scene["camera"]["position"], [1.0, 2.0, 3.0])
        self.assertEqual(scene["atmosphere"]["background"], [0.1, 0.2, 0.3])
        self.assertFalse(scene["shadows"]["enabled"])

        result = session.editor_action({"action": "undo"})
        self.assertEqual(result["scene_settings"]["camera"], original_camera)
        self.assertEqual(
            result["scene_settings"]["environment"], original_environment
        )

        result = session.editor_action(
            {"action": "set_scene", "environment": {"point_light": None}}
        )
        self.assertIsNone(result["scene_settings"]["environment"]["point_light"])

        for payload in (
            {"action": "set_scene"},
            {"action": "set_scene", "camera": {}},
            {"action": "set_scene", "camera": {"fov_y": 0}},
            {"action": "set_scene", "camera": {"near": 0}},
            {"action": "set_scene", "camera": {"far": 0.01}},
            {"action": "set_scene", "camera": {"position": [1.0, 2.0]}},
            {"action": "set_scene", "environment": {"fog_density": -1}},
            {"action": "set_scene", "environment": {"unknown": 1}},
            {"action": "set_scene", "environment": {"shadow": "yes"}},
        ):
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(payload)
            self.assertEqual(caught.exception.status, 400)

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
        self.assertEqual(stopped["history"], {"undo": 0, "redo": 0, "limit": 50, "undo_stack": [], "redo_stack": []})
        with self.assertRaises(WebProblem) as caught:
            session.editor_action({"action": "play_step", "frames": 1})
        self.assertEqual(caught.exception.status, 400)

    def test_editor_play_pause_resume_and_paused_step(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        started = session.editor_action({"action": "play_start"})
        self.assertTrue(started["play"]["active"])
        self.assertFalse(started["play"]["paused"])

        paused = session.editor_action({"action": "play_pause"})
        self.assertTrue(paused["play"]["paused"])
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {"action": "set_node", "id": cube["id"], "name": "blocked"}
            )
        self.assertEqual(caught.exception.status, 400)

        stepped = session.editor_action({"action": "play_step", "frames": 2})
        self.assertEqual(stepped["play"]["frames"], 2)
        self.assertTrue(stepped["play"]["paused"])

        resumed = session.editor_action({"action": "play_resume"})
        self.assertFalse(resumed["play"]["paused"])
        self.assertEqual(resumed["play"]["frames"], 2)

        stopped = session.editor_action({"action": "play_stop"})
        self.assertFalse(stopped["play"]["active"])
        self.assertFalse(stopped["play"]["paused"])
        self.assertEqual(stopped["play"]["frames"], 0)

        for payload in ({"action": "play_pause"}, {"action": "play_resume"}):
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(payload)
            self.assertEqual(caught.exception.status, 400)

        session.editor_action({"action": "play_start"})
        self.assertTrue(
            session.editor_action({"action": "play_pause"})["play"]["paused"]
        )
        self.assertTrue(
            session.editor_action({"action": "play_pause"})["play"]["paused"]
        )
        session.editor_action({"action": "play_resume"})
        resumed_again = session.editor_action({"action": "play_resume"})
        self.assertFalse(resumed_again["play"]["paused"])
        session.editor_action({"action": "play_stop"})

    def test_editor_play_state_exposes_snapshot_and_status(self):
        session = GameSession(CubeDemo())
        stopped = session.editor()
        self.assertIsNone(stopped["play"]["snapshot"])
        self.assertIsNone(stopped["play"]["status"])

        started = session.editor_action({"action": "play_start"})
        self.assertIsInstance(started["play"]["snapshot"], dict)
        self.assertIsInstance(started["play"]["status"], str)
        stepped = session.editor_action({"action": "play_step", "frames": 2})
        self.assertIn("time", stepped["play"]["snapshot"])

        stopped = session.editor_action({"action": "play_stop"})
        self.assertIsNone(stopped["play"]["snapshot"])
        self.assertIsNone(stopped["play"]["status"])

    def test_editor_play_state_reports_hook_errors(self):
        class BrokenHooks(CubeDemo):
            def snapshot(self):
                raise RuntimeError("snapshot failed")

            def status(self):
                raise RuntimeError("status failed")

        session = GameSession(BrokenHooks())
        started = session.editor_action({"action": "play_start"})
        self.assertIsNone(started["play"]["snapshot"])
        self.assertIsNone(started["play"]["status"])
        self.assertIn("snapshot failed", started["play"]["snapshot_error"])
        self.assertIn("status failed", started["play"]["status_error"])
        session.editor_action({"action": "play_stop"})

    def test_editor_validate_scene_reports_issues(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        valid = session.editor_action({"action": "validate_scene"})
        validation = valid["validation"]
        self.assertTrue(validation["ok"])
        self.assertEqual(validation["errors"], 0)
        self.assertGreater(validation["node_count"], 0)
        self.assertIsNone(
            session.editor_action(
                {"action": "select", "id": cube["id"]}
            )["validation"]
        )

        session.editor_action({"action": "create_node", "name": "dupe"})
        session.editor_action({"action": "create_node", "name": "dupe"})
        warnings = session.editor_action({"action": "validate_scene"})
        self.assertTrue(
            any(
                "share the name" in issue["message"]
                for issue in warnings["validation"]["issues"]
            )
        )

        registry = session.game.assets
        registry.remove("material.cube.0")
        missing = session.editor_action({"action": "validate_scene"})
        self.assertFalse(missing["validation"]["ok"])
        self.assertTrue(
            any(
                issue["field"] == "material"
                for issue in missing["validation"]["issues"]
            )
        )

        session.editor_action({"action": "save_prefab", "name": "hero"})
        session.editor_action(
            {"action": "insert_prefab", "name": "hero", "instance": "tmp"}
        )
        session.prefabs.pop("hero", None)
        dangling = session.editor_action({"action": "validate_scene"})
        self.assertTrue(
            any(
                issue["field"] == "prefab_link"
                for issue in dangling["validation"]["issues"]
            )
        )

    def test_editor_import_asset_updates_manifest_and_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="import-demo")
            assets = root / "assets"
            assets.mkdir()
            (assets / "crate.obj").write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 1\nf 1//1 2//1 3//1\n",
                encoding="utf-8",
            )
            session = GameSession(CubeDemo(), project_dir=root)
            editor = session.editor()
            self.assertEqual(
                editor["workspace"]["project_dir"], root.resolve().as_posix()
            )
            self.assertIsNone(editor["imported_asset"])

            imported_editor = session.editor_action(
                {"action": "import_asset", "path": "assets/crate.obj"}
            )
            imported = imported_editor["imported_asset"]
            self.assertEqual(imported["asset"], "project:assets/crate.obj")
            self.assertEqual(imported["kind"], "mesh")
            self.assertFalse(imported["duplicate"])
            self.assertEqual(imported["count"], 1)
            self.assertIn(
                "project:assets/crate.obj",
                {asset["id"] for asset in imported_editor["assets"]},
            )
            self.assertEqual(
                load_project(root).manifest.assets,
                ("assets/crate.obj",),
            )

            again = session.editor_action(
                {"action": "import_asset", "path": "./assets/crate.obj"}
            )["imported_asset"]
            self.assertTrue(again["duplicate"])
            self.assertEqual(again["count"], 1)
            self.assertEqual(
                load_project(root).manifest.assets,
                ("assets/crate.obj",),
            )

            (assets / "unknown.bin").write_bytes(b"x")
            for value, message in (
                ("../escape.obj", "inside the project"),
                ("assets/unknown.bin", "unsupported"),
            ):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(
                        {"action": "import_asset", "path": value}
                    )
                self.assertEqual(caught.exception.status, 400)
                self.assertIn(message, caught.exception.why)

            (assets / "scene.glb").write_bytes(b"glTF")
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "import_asset", "path": "assets/scene.glb"}
                )
            self.assertIn("glTF", caught.exception.why)

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "import_asset", "path": "assets/missing.obj"}
                )
            self.assertIn("does not exist", caught.exception.why)

            bare = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                bare.editor_action(
                    {"action": "import_asset", "path": "assets/crate.obj"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("--project", caught.exception.fix)

            server = create_server(
                CubeDemo(), host="127.0.0.1", port=0, project_dir=root
            )
            try:
                self.assertEqual(server.session.project_dir, root.resolve())
            finally:
                server.server_close()

    def test_editor_import_gltf_generates_prefab(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="gltf-web")
            assets = root / "assets"
            assets.mkdir()
            (assets / "model.gltf").write_text(
                json.dumps(_triangle_gltf()), encoding="utf-8"
            )
            prefab_dir = root / "prefabs"
            session = GameSession(
                CubeDemo(), project_dir=root, prefab_dir=prefab_dir
            )
            self.assertIsNone(session.editor()["imported_gltf"])
            imported_editor = session.editor_action(
                {"action": "import_gltf", "path": "assets/model.gltf"}
            )
            report = imported_editor["imported_gltf"]
            self.assertIsNotNone(report)
            self.assertEqual(report["prefab"], "model")
            self.assertEqual(
                report["assets"],
                ["gltf.model.material.0", "gltf.model.mesh.0"],
            )
            self.assertEqual(report["asset_count"], 2)
            self.assertFalse(report["duplicate"])
            self.assertFalse(report["replaced_prefab"])
            self.assertIn(
                "model", {entry["name"] for entry in imported_editor["prefabs"]}
            )
            self.assertEqual(
                load_project(root).manifest.assets, ("assets/model.gltf",)
            )
            self.assertIn(
                "gltf.model.mesh.0",
                {asset["id"] for asset in imported_editor["assets"]},
            )

            inserted = session.editor_action(
                {
                    "action": "insert_prefab",
                    "name": "model",
                    "instance": "gltf",
                }
            )
            self.assertTrue(
                any(
                    node["prefab_link"] is not None
                    for node in inserted["nodes"]
                )
            )

            again = session.editor_action(
                {"action": "import_gltf", "path": "./assets/model.gltf"}
            )["imported_gltf"]
            self.assertTrue(again["duplicate"])
            self.assertTrue(again["replaced_prefab"])

            (assets / "cube.obj").write_text("v 0 0 0", encoding="utf-8")
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "import_gltf", "path": "assets/cube.obj"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("not a glTF", caught.exception.why)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "import_gltf", "path": "assets/missing.glb"}
                )
            self.assertIn("does not exist", caught.exception.why)
            self.assertIsNone(
                session.editor_action({"action": "select", "id": None})[
                    "imported_gltf"
                ]
            )

            bare = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                bare.editor_action(
                    {"action": "import_gltf", "path": "assets/model.gltf"}
                )
            self.assertIn("--project", caught.exception.fix)

            no_library = GameSession(CubeDemo(), project_dir=root)
            with self.assertRaises(WebProblem) as caught:
                no_library.editor_action(
                    {"action": "import_gltf", "path": "assets/model.gltf"}
                )
            self.assertIn("--prefab-dir", caught.exception.fix)

    def test_editor_scene_dirty_and_revert(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="dirty-demo")
            session = GameSession(
                CubeDemo(),
                project_dir=root,
                scene_dir=root / "scenes",
                prefab_dir=root / "prefabs",
            )
            editor = session.editor()
            self.assertIsNone(editor["saved_scene"])
            self.assertFalse(editor["scene_dirty"])
            saved_main = session.editor_action(
                {"action": "save_scene", "name": "main"}
            )
            self.assertEqual(saved_main["saved_scene"], "main")
            self.assertFalse(saved_main["scene_dirty"])
            editor = saved_main
            cube = next(
                node for node in editor["nodes"] if node["name"] == "cube-0"
            )
            original = cube["transform"]["position"]

            played = session.editor_action({"action": "play_start"})
            self.assertFalse(played["scene_dirty"])
            stopped = session.editor_action({"action": "play_stop"})
            self.assertFalse(stopped["scene_dirty"])

            selected = session.editor_action(
                {"action": "select", "id": cube["id"]}
            )
            self.assertFalse(selected["scene_dirty"])
            moved = session.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [4.0, 5.0, 6.0],
                }
            )
            self.assertTrue(moved["scene_dirty"])
            self.assertEqual(moved["saved_scene"], "main")
            self.assertGreater(moved["history"]["undo"], 0)

            reverted = session.editor_action({"action": "revert_scene"})
            self.assertFalse(reverted["scene_dirty"])
            self.assertEqual(reverted["saved_scene"], "main")
            self.assertEqual(reverted["history"]["undo"], 0)
            self.assertEqual(reverted["revert"]["name"], "main")
            self.assertTrue(reverted["revert"]["cleared_history"])
            restored = next(
                node for node in reverted["nodes"] if node["id"] == cube["id"]
            )
            self.assertEqual(restored["transform"]["position"], original)

            saved = session.editor_action(
                {"action": "save_scene", "name": "level"}
            )
            self.assertEqual(saved["saved_scene"], "level")
            self.assertFalse(saved["scene_dirty"])
            session.editor_action(
                {
                    "action": "transform",
                    "id": cube["id"],
                    "position": [1.0, 0.0, 0.0],
                }
            )
            renamed = session.editor_action(
                {"action": "rename_scene", "name": "level", "new_name": "level-alt"}
            )
            self.assertEqual(renamed["saved_scene"], "level-alt")
            reverted = session.editor_action({"action": "revert_scene"})
            self.assertEqual(reverted["revert"]["name"], "level-alt")

            session.editor_action(
                {"action": "set_startup_scene", "name": None}
            )
            deleted = session.editor_action(
                {"action": "delete_scene", "name": "level-alt"}
            )
            self.assertIsNone(deleted["saved_scene"])
            self.assertTrue(deleted["scene_dirty"])
            with self.assertRaises(WebProblem) as caught:
                session.editor_action({"action": "revert_scene"})
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("no saved scene", caught.exception.why)

            no_saved = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                no_saved.editor_action({"action": "revert_scene"})
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("no saved scene", caught.exception.why)

            session.editor_action(
                {"action": "save_scene", "name": "restored"}
            )
            session.editor_action(
                {"action": "select", "id": cube["id"]}
            )
            session.editor_action({"action": "save_prefab", "name": "hero"})
            session.editor_action({"action": "edit_prefab", "name": "hero"})
            with self.assertRaises(WebProblem) as caught:
                session.editor_action({"action": "revert_scene"})
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("prefab", caught.exception.why)

    def test_editor_startup_scene_persists_and_clears(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="startup-demo")
            scene_dir = root / "scenes"
            session = GameSession(
                CubeDemo(), project_dir=root, scene_dir=scene_dir
            )
            editor = session.editor()
            self.assertEqual(editor["startup_scene"], "main")
            saved = session.editor_action(
                {"action": "save_scene", "name": "level"}
            )
            self.assertEqual(saved["startup_scene"], "main")

            set_editor = session.editor_action(
                {"action": "set_startup_scene", "name": "level"}
            )
            self.assertEqual(set_editor["startup_scene"], "level")
            self.assertEqual(
                load_project(root).manifest.startup_scene, "level"
            )

            cleared = session.editor_action(
                {"action": "set_startup_scene", "name": None}
            )
            self.assertIsNone(cleared["startup_scene"])
            self.assertIsNone(load_project(root).manifest.startup_scene)

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "set_startup_scene", "name": "missing"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("not saved", caught.exception.why)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "set_startup_scene", "name": "../escape"}
                )
            self.assertEqual(caught.exception.status, 400)

            bare = GameSession(CubeDemo(), scene_dir=scene_dir)
            with self.assertRaises(WebProblem) as caught:
                bare.editor_action(
                    {"action": "set_startup_scene", "name": "main"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("--project", caught.exception.fix)

            no_library = GameSession(CubeDemo(), project_dir=root)
            with self.assertRaises(WebProblem) as caught:
                no_library.editor_action(
                    {"action": "set_startup_scene", "name": "main"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("--scene-dir", caught.exception.fix)

    def test_editor_startup_scene_follows_rename_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="startup-sync")
            session = GameSession(
                CubeDemo(),
                project_dir=root,
                scene_dir=root / "scenes",
            )
            session.editor_action(
                {"action": "save_scene", "name": "level"}
            )
            session.editor_action(
                {"action": "set_startup_scene", "name": "level"}
            )
            renamed = session.editor_action(
                {
                    "action": "rename_scene",
                    "name": "level",
                    "new_name": "level-alt",
                }
            )
            self.assertEqual(renamed["startup_scene"], "level-alt")
            self.assertEqual(
                load_project(root).manifest.startup_scene, "level-alt"
            )

            deleted = session.editor_action(
                {"action": "delete_scene", "name": "level-alt"}
            )
            self.assertIsNone(deleted["startup_scene"])
            self.assertIsNone(load_project(root).manifest.startup_scene)

    def test_editor_forget_asset_and_project_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="forget-demo")
            assets = root / "assets"
            assets.mkdir()
            source = assets / "cube.obj"
            source.write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 1\nf 1//1 2//1 3//1\n",
                encoding="utf-8",
            )
            session = GameSession(
                CubeDemo(),
                project_dir=root,
                prefab_dir=root / "prefabs",
            )
            imported_editor = session.editor_action(
                {"action": "import_asset", "path": "assets/cube.obj"}
            )
            self.assertIn("assets/cube.obj", imported_editor["project_assets"])

            forgotten_editor = session.editor_action(
                {"action": "forget_asset", "path": "assets/cube.obj"}
            )
            forgotten = forgotten_editor["forgotten_asset"]
            self.assertEqual(forgotten["path"], "assets/cube.obj")
            self.assertEqual(forgotten["asset"], "project:assets/cube.obj")
            self.assertTrue(forgotten["removed"])
            self.assertEqual(forgotten["count"], 0)
            self.assertEqual(forgotten_editor["project_assets"], [])
            self.assertNotIn(
                "project:assets/cube.obj",
                {asset["id"] for asset in forgotten_editor["assets"]},
            )
            self.assertEqual(load_project(root).manifest.assets, ())
            self.assertTrue(source.is_file())
            self.assertIsNone(
                session.editor_action({"action": "select", "id": None})[
                    "forgotten_asset"
                ]
            )

            restored = session.editor_action(
                {"action": "import_asset", "path": "assets/cube.obj"}
            )
            self.assertEqual(restored["imported_asset"]["count"], 1)
            created = session.editor_action(
                {
                    "action": "create_node",
                    "name": "crate",
                    "mesh": "project:assets/cube.obj",
                }
            )
            crate_id = next(
                node["id"] for node in created["nodes"] if node["name"] == "crate"
            )
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "forget_asset", "path": "assets/cube.obj"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn(crate_id, caught.exception.why)

            session.editor_action({"action": "select", "id": crate_id})
            session.editor_action({"action": "save_prefab", "name": "crate"})
            session.editor_action({"action": "delete_node", "id": crate_id})
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "forget_asset", "path": "assets/cube.obj"}
                )
            self.assertIn("prefab 'crate'", caught.exception.why)

            (assets / "model.gltf").write_text("{}", encoding="utf-8")
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "forget_asset", "path": "assets/model.gltf"}
                )
            self.assertIn("glTF", caught.exception.why)

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "forget_asset", "path": "../escape.obj"}
                )
            self.assertEqual(caught.exception.status, 400)

            bare = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                bare.editor_action(
                    {"action": "forget_asset", "path": "assets/cube.obj"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("--project", caught.exception.fix)

    def test_editor_asset_usages_and_saved_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="usage-demo")
            assets = root / "assets"
            assets.mkdir()
            (assets / "cube.obj").write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 1\nf 1//1 2//1 3//1\n",
                encoding="utf-8",
            )
            session = GameSession(
                CubeDemo(),
                project_dir=root,
                scene_dir=root / "scenes",
                prefab_dir=root / "prefabs",
            )
            session.editor_action(
                {"action": "import_asset", "path": "assets/cube.obj"}
            )
            created = session.editor_action(
                {
                    "action": "create_node",
                    "name": "crate",
                    "mesh": "project:assets/cube.obj",
                }
            )
            crate_id = next(
                node["id"]
                for node in created["nodes"]
                if node["name"] == "crate"
            )
            session.editor_action({"action": "save_scene", "name": "level"})
            session.editor_action({"action": "select", "id": crate_id})
            session.editor_action({"action": "save_prefab", "name": "crate"})

            report = session.editor_action(
                {
                    "action": "asset_usages",
                    "asset": "project:assets/cube.obj",
                }
            )["asset_usages"]
            self.assertEqual(report["asset"], "project:assets/cube.obj")
            self.assertTrue(report["registered"])
            self.assertEqual(report["kind"], "mesh")
            self.assertTrue(report["found"])
            self.assertGreaterEqual(report["references"], 3)
            self.assertIn(
                {"node": crate_id, "field": "mesh"}, report["scene_nodes"]
            )
            self.assertIn("crate", report["prefabs"])
            self.assertIn("level", report["scenes"])
            self.assertIs(report["project_asset"], True)

            by_path = session.editor_action(
                {"action": "asset_usages", "path": "assets/cube.obj"}
            )["asset_usages"]
            self.assertEqual(by_path, report)

            unknown = session.editor_action(
                {"action": "asset_usages", "asset": "mesh.missing"}
            )["asset_usages"]
            self.assertFalse(unknown["registered"])
            self.assertFalse(unknown["found"])
            self.assertEqual(unknown["references"], 0)

            for payload in (
                {"action": "asset_usages"},
                {
                    "action": "asset_usages",
                    "asset": "project:assets/cube.obj",
                    "path": "assets/cube.obj",
                },
            ):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(payload)
                self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "asset_usages", "path": "../escape.obj"}
                )
            self.assertEqual(caught.exception.status, 400)

            session.editor_action({"action": "delete_node", "id": crate_id})
            session.editor_action({"action": "delete_prefab", "name": "crate"})
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "forget_asset", "path": "assets/cube.obj"}
                )
            self.assertIn("scene file 'level'", caught.exception.why)
            session.editor_action({"action": "delete_scene", "name": "level"})
            forgotten = session.editor_action(
                {"action": "forget_asset", "path": "assets/cube.obj"}
            )["forgotten_asset"]
            self.assertTrue(forgotten["removed"])

    def test_editor_build_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="build-demo")
            session = GameSession(CubeDemo(), project_dir=root)
            self.assertIsNone(session.editor()["build"])
            built = session.editor_action(
                {"action": "build_project", "target": "build"}
            )
            build = built["build"]
            self.assertEqual(build["target"], "build")
            self.assertEqual(build["manifest"], "build/BUILD.json")
            self.assertGreater(build["summary"]["files"], 0)
            self.assertTrue((root / "build" / "BUILD.json").is_file())
            self.assertTrue((root / "build" / "run.py").is_file())
            self.assertIsNone(
                session.editor_action({"action": "select", "id": None})["build"]
            )

            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "build_project", "target": "build"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("not empty", caught.exception.why)
            forced = session.editor_action(
                {"action": "build_project", "target": "build", "force": True}
            )
            self.assertEqual(forced["build"]["target"], "build")

            for target in ("../escape", "/absolute"):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(
                        {"action": "build_project", "target": target}
                    )
                self.assertEqual(caught.exception.status, 400)

            bare = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                bare.editor_action(
                    {"action": "build_project", "target": "build"}
                )
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("--project", caught.exception.fix)

    def test_editor_reload_assets_rebinds_scene_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="reload-demo")
            assets = root / "assets"
            assets.mkdir()
            source = assets / "crate.obj"
            source.write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 1\nf 1//1 2//1 3//1\n",
                encoding="utf-8",
            )
            session = GameSession(CubeDemo(), project_dir=root)
            session.editor_action(
                {"action": "import_asset", "path": "assets/crate.obj"}
            )
            created = session.editor_action(
                {
                    "action": "create_node",
                    "name": "crate",
                    "mesh": "project:assets/crate.obj",
                }
            )
            crate_id = next(
                node["id"] for node in created["nodes"] if node["name"] == "crate"
            )
            crate = session.game.scene.find_by_id(crate_id)
            self.assertIsNotNone(crate)
            old_mesh = crate.mesh
            session.editor_action(
                {
                    "action": "transform",
                    "id": crate_id,
                    "position": [1.0, 2.0, 3.0],
                }
            )

            source.write_text(
                "v 0 0 0\nv 2 0 0\nv 0 2 0\nv 0 0 2\nvn 0 0 1\n"
                "f 1//1 2//1 3//1\nf 1//1 3//1 4//1\n",
                encoding="utf-8",
            )
            reloaded_editor = session.editor_action({"action": "reload_assets"})
            reload = reloaded_editor["asset_reload"]
            self.assertTrue(reload["ok"])
            self.assertEqual(reload["checked"], 1)
            self.assertIn("project:assets/crate.obj", reload["reloaded"])
            self.assertGreaterEqual(reload["rebound"], 1)
            self.assertGreaterEqual(reload["history_rebound"], 1)
            record = session.game.assets.require("project:assets/crate.obj")
            self.assertIs(crate.mesh, record.payload)
            self.assertIsNot(crate.mesh, old_mesh)

            session.editor_action({"action": "undo"})
            restored = session.game.scene.find_by_id(crate_id)
            self.assertIsNotNone(restored)
            self.assertIs(restored.mesh, record.payload)

            source.write_text("not a mesh", encoding="utf-8")
            failed = session.editor_action({"action": "reload_assets"})[
                "asset_reload"
            ]
            self.assertFalse(failed["ok"])
            self.assertTrue(failed["failed"])
            self.assertIs(
                session.game.scene.find_by_id(crate_id).mesh, record.payload
            )

            source.unlink()
            missing = session.editor_action({"action": "reload_assets"})[
                "asset_reload"
            ]
            self.assertFalse(missing["ok"])
            self.assertIn("project:assets/crate.obj", missing["missing"])
            self.assertIs(
                session.game.scene.find_by_id(crate_id).mesh, record.payload
            )
            self.assertIsNone(
                session.editor_action(
                    {"action": "select", "id": crate_id}
                )["asset_reload"]
            )

            bare = GameSession(CubeDemo())
            bare.editor()
            bare.game.assets = None
            with self.assertRaises(WebProblem) as caught:
                bare.editor_action({"action": "reload_assets"})
            self.assertEqual(caught.exception.status, 400)
            self.assertIn("AssetRegistry", caught.exception.why)

    def test_editor_reload_rebinds_unchanged_payload_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="reload-identity")
            assets = root / "assets"
            assets.mkdir()
            source = assets / "crate.obj"
            source.write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\nvn 0 0 1\nf 1//1 2//1 3//1\n",
                encoding="utf-8",
            )
            session = GameSession(CubeDemo(), project_dir=root)
            session.editor_action(
                {"action": "import_asset", "path": "assets/crate.obj"}
            )
            created = session.editor_action(
                {
                    "action": "create_node",
                    "name": "crate",
                    "mesh": "project:assets/crate.obj",
                }
            )
            crate_id = next(
                node["id"]
                for node in created["nodes"]
                if node["name"] == "crate"
            )
            crate = session.game.scene.find_by_id(crate_id)
            old_mesh = crate.mesh
            session.editor_action(
                {
                    "action": "transform",
                    "id": crate_id,
                    "position": [1.0, 2.0, 3.0],
                }
            )

            status = source.stat()
            os.utime(source, (status.st_atime, status.st_mtime + 10))
            reloaded = session.editor_action({"action": "reload_assets"})[
                "asset_reload"
            ]
            self.assertTrue(reloaded["ok"])
            self.assertNotIn(
                "project:assets/crate.obj", reloaded["reloaded"]
            )
            self.assertIn(
                "project:assets/crate.obj", reloaded["unchanged"]
            )
            self.assertGreaterEqual(reloaded["rebound"], 1)
            self.assertGreaterEqual(reloaded["history_rebound"], 1)
            record = session.game.assets.require(
                "project:assets/crate.obj"
            )
            self.assertIsNot(record.payload, old_mesh)
            self.assertIs(crate.mesh, record.payload)
            self.assertIs(
                session.game.scene.find_by_id(crate_id).mesh, record.payload
            )

            usages = session.editor_action(
                {
                    "action": "asset_usages",
                    "asset": "project:assets/crate.obj",
                }
            )["asset_usages"]
            self.assertIn(
                {"node": crate_id, "field": "mesh"},
                usages["scene_nodes"],
            )

            session.editor_action({"action": "undo"})
            self.assertIs(
                session.game.scene.find_by_id(crate_id).mesh,
                record.payload,
            )

    def test_editor_preview_animation_and_undo(self):
        session = GameSession(CubeDemo())
        editor = session.editor()
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        original = cube["transform"]["position"]
        clip = {
            "schema": 1,
            "name": "bob",
            "position": {
                cube["id"]: {
                    "interpolation": "linear",
                    "keys": [
                        {"t": 0.0, "v": original},
                        {
                            "t": 1.0,
                            "v": [
                                original[0],
                                original[1] + 2.0,
                                original[2],
                            ],
                        },
                    ],
                }
            },
            "rotation": {},
            "scale": {},
            "events": [],
        }

        previewed = session.editor_action(
            {"action": "preview_animation", "clip": clip, "time": 0.5}
        )
        self.assertEqual(previewed["animation_preview"]["name"], "bob")
        self.assertEqual(previewed["animation_preview"]["time"], 0.5)
        self.assertEqual(previewed["animation_preview"]["track_count"], 1)
        self.assertIn(cube["id"], previewed["animation_preview"]["updated"])
        self.assertEqual(previewed["history"]["undo"], 1)
        moved = next(
            node for node in previewed["nodes"] if node["id"] == cube["id"]
        )
        self.assertAlmostEqual(
            moved["transform"]["position"][1], original[1] + 1.0, places=4
        )

        undone = session.editor_action({"action": "undo"})
        restored = next(
            node for node in undone["nodes"] if node["id"] == cube["id"]
        )
        self.assertEqual(restored["transform"]["position"], original)

        unrecorded = session.editor_action(
            {
                "action": "preview_animation",
                "clip": clip,
                "time": 0.25,
                "record": False,
            }
        )
        self.assertFalse(unrecorded["animation_preview"]["record"])
        self.assertEqual(unrecorded["history"]["undo"], 0)
        moved = next(
            node for node in unrecorded["nodes"] if node["id"] == cube["id"]
        )
        self.assertAlmostEqual(
            moved["transform"]["position"][1],
            original[1] + 0.5,
            places=4,
        )

        for payload in (
            {"action": "preview_animation", "clip": clip, "time": -1.0},
            {"action": "preview_animation", "clip": clip, "time": True},
            {"action": "preview_animation", "clip": [], "time": 0.0},
            {
                "action": "preview_animation",
                "clip": {**clip, "schema": 2},
                "time": 0.0,
            },
            {
                "action": "preview_animation",
                "clip": clip,
                "time": 0.0,
                "record": "yes",
            },
        ):
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(payload)
            self.assertEqual(caught.exception.status, 400)

        session.editor_action({"action": "play_start"})
        with self.assertRaises(WebProblem) as caught:
            session.editor_action(
                {"action": "preview_animation", "clip": clip, "time": 0.0}
            )
        self.assertEqual(caught.exception.status, 400)
        session.editor_action({"action": "play_stop"})

    def test_editor_animation_library_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            animation_dir = Path(directory) / "animations"
            session = GameSession(CubeDemo(), animation_dir=animation_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            original = cube["transform"]["position"]
            clip = {
                "schema": 1,
                "name": "bob",
                "position": {
                    cube["id"]: {
                        "interpolation": "linear",
                        "keys": [
                            {"t": 0.0, "v": original},
                            {
                                "t": 1.0,
                                "v": [
                                    original[0],
                                    original[1] + 2.0,
                                    original[2],
                                ],
                            },
                        ],
                    }
                },
                "rotation": {},
                "scale": {},
                "events": [],
            }
            saved = session.editor_action(
                {"action": "save_animation", "name": "bob", "clip": clip}
            )
            self.assertTrue((animation_dir / "bob.kanim").is_file())
            entry = next(
                item for item in saved["animations"] if item["name"] == "bob"
            )
            self.assertEqual(entry["track_count"], 1)
            self.assertAlmostEqual(entry["duration"], 1.0)

            previewed = session.editor_action(
                {"action": "preview_animation", "name": "bob", "time": 0.5}
            )
            self.assertEqual(
                previewed["animation_preview"]["source"], "library"
            )
            self.assertIn(
                cube["id"], previewed["animation_preview"]["updated"]
            )
            moved = next(
                node for node in previewed["nodes"] if node["id"] == cube["id"]
            )
            self.assertAlmostEqual(
                moved["transform"]["position"][1],
                original[1] + 1.0,
                places=4,
            )
            session.editor_action({"action": "undo"})

            reloaded = GameSession(CubeDemo(), animation_dir=animation_dir)
            names = {item["name"] for item in reloaded.editor()["animations"]}
            self.assertIn("bob", names)

            deleted = session.editor_action(
                {"action": "delete_animation", "name": "bob"}
            )
            self.assertEqual(deleted["animations"], [])
            self.assertEqual(deleted["trash"]["animations"][0]["name"], "bob")
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "preview_animation", "name": "bob", "time": 0.0}
                )
            self.assertEqual(caught.exception.status, 404)

            restored = session.editor_action(
                {
                    "action": "restore_animation",
                    "trash": deleted["trash"]["animations"][0]["trash"],
                }
            )
            self.assertIn(
                "bob", {item["name"] for item in restored["animations"]}
            )
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "preview_animation",
                        "name": "bob",
                        "clip": clip,
                        "time": 0.0,
                    }
                )
            self.assertEqual(caught.exception.status, 400)

            standalone = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                standalone.editor_action(
                    {"action": "save_animation", "name": "bob", "clip": clip}
                )
            self.assertEqual(caught.exception.status, 400)

    def test_editor_state_machine_library_and_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            animation_dir = Path(directory) / "animations"
            session = GameSession(CubeDemo(), animation_dir=animation_dir)
            document = _state_machine_document()
            saved = session.editor_action(
                {
                    "action": "save_state_machine",
                    "name": "locomotion",
                    "machine": document,
                }
            )
            self.assertTrue(
                (animation_dir / "locomotion.kstate").is_file()
            )
            entry = next(
                item
                for item in saved["state_machines"]
                if item["name"] == "locomotion"
            )
            self.assertEqual(entry["states"], 2)
            self.assertEqual(entry["transitions"], 1)

            loaded = session.editor_action(
                {"action": "load_state_machine", "name": "locomotion"}
            )
            loaded_document = loaded["state_machine_document"]
            self.assertEqual(loaded_document["name"], "locomotion")
            self.assertEqual(loaded_document["machine"], document)

            previewed = session.editor_action(
                {
                    "action": "preview_state_machine",
                    "name": "locomotion",
                    "parameters": {"speed": 1.0},
                    "frames": 2,
                    "step": 0.1,
                }
            )
            preview = previewed["state_machine_preview"]
            self.assertEqual(preview["current"], "run")
            self.assertEqual(preview["frames"], 2)
            self.assertAlmostEqual(preview["step"], 0.1, places=4)
            self.assertIn("cube-0", preview["updated"])
            self.assertEqual(previewed["history"]["undo"], 1)
            self.assertIsNone(previewed["state_machine_document"])
            moved = next(
                node
                for node in previewed["nodes"]
                if node["id"] == "cube-0"
            )
            self.assertAlmostEqual(
                moved["transform"]["position"][0], 2.0, places=4
            )

            before = previewed["history"]["undo"]
            unrecorded = session.editor_action(
                {
                    "action": "preview_state_machine",
                    "name": "locomotion",
                    "parameters": {"speed": 1.0},
                    "frames": 1,
                    "step": 0.1,
                    "record": False,
                }
            )
            self.assertFalse(
                unrecorded["state_machine_preview"]["record"]
            )
            self.assertEqual(unrecorded["history"]["undo"], before)

            deleted = session.editor_action(
                {"action": "delete_state_machine", "name": "locomotion"}
            )
            self.assertEqual(deleted["state_machines"], [])
            trash = deleted["trash"]["state_machines"]
            self.assertEqual(trash[0]["name"], "locomotion")
            restored = session.editor_action(
                {
                    "action": "restore_state_machine",
                    "trash": trash[0]["trash"],
                }
            )
            self.assertIn(
                "locomotion",
                {item["name"] for item in restored["state_machines"]},
            )

            bad = dict(document)
            bad["schema"] = 99
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "save_state_machine",
                        "name": "bad",
                        "machine": bad,
                    }
                )
            self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "preview_state_machine", "name": "missing"}
                )
            self.assertEqual(caught.exception.status, 404)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "load_state_machine", "name": "missing"}
                )
            self.assertEqual(caught.exception.status, 404)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "preview_state_machine",
                        "name": "locomotion",
                        "frames": 0,
                    }
                )
            self.assertEqual(caught.exception.status, 400)

            standalone = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                standalone.editor_action(
                    {
                        "action": "save_state_machine",
                        "name": "locomotion",
                        "machine": document,
                    }
                )
            self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                standalone.editor_action(
                    {"action": "load_state_machine", "name": "locomotion"}
                )
            self.assertEqual(caught.exception.status, 400)

    def test_editor_animation_key_authoring(self):
        with tempfile.TemporaryDirectory() as directory:
            animation_dir = Path(directory) / "animations"
            session = GameSession(CubeDemo(), animation_dir=animation_dir)
            editor = session.editor()
            cube = next(
                node for node in editor["nodes"] if node["name"] == "cube-0"
            )
            original = cube["transform"]["position"]
            clip = {
                "schema": 1,
                "name": "bob",
                "position": {},
                "rotation": {},
                "scale": {},
                "events": [],
            }
            session.editor_action(
                {"action": "save_animation", "name": "bob", "clip": clip}
            )
            session.editor_action({"action": "select", "id": cube["id"]})

            first = session.editor_action(
                {
                    "action": "set_animation_key",
                    "name": "bob",
                    "channel": "position",
                    "time": 0.0,
                }
            )
            self.assertEqual(first["animation_key"]["keys"], 1)
            loaded = session.animation_library.load("bob")
            track = dict(loaded.position_tracks)[cube["id"]]
            self.assertEqual(track.times, (0.0,))
            self.assertAlmostEqual(track.values[0].y, original[1])

            value = [original[0], original[1] + 2.0, original[2]]
            second = session.editor_action(
                {
                    "action": "set_animation_key",
                    "name": "bob",
                    "channel": "position",
                    "time": 1.0,
                    "value": value,
                }
            )
            self.assertEqual(second["animation_key"]["keys"], 2)
            replaced = session.editor_action(
                {
                    "action": "set_animation_key",
                    "name": "bob",
                    "channel": "position",
                    "time": 1.0,
                    "value": [original[0], original[1] + 3.0, original[2]],
                }
            )
            self.assertEqual(replaced["animation_key"]["keys"], 2)
            loaded = session.animation_library.load("bob")
            track = dict(loaded.position_tracks)[cube["id"]]
            self.assertEqual(track.times, (0.0, 1.0))
            self.assertAlmostEqual(track.values[1].y, original[1] + 3.0)

            previewed = session.editor_action(
                {"action": "preview_animation", "name": "bob", "time": 1.0}
            )
            moved = next(
                node for node in previewed["nodes"] if node["id"] == cube["id"]
            )
            self.assertAlmostEqual(
                moved["transform"]["position"][1],
                original[1] + 3.0,
                places=4,
            )
            session.editor_action({"action": "undo"})

            removed = session.editor_action(
                {
                    "action": "remove_animation_key",
                    "name": "bob",
                    "channel": "position",
                    "time": 1.0,
                }
            )
            self.assertEqual(removed["animation_key"]["removed"], 1)
            self.assertEqual(removed["animation_key"]["keys"], 1)
            removed_zero = session.editor_action(
                {
                    "action": "remove_animation_key",
                    "name": "bob",
                    "channel": "position",
                    "time": 0.0,
                }
            )
            self.assertEqual(removed_zero["animation_key"]["keys"], 0)
            self.assertEqual(
                session.animation_library.load("bob").position_tracks, ()
            )

            session.editor_action({"action": "select", "id": None})
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "set_animation_key",
                        "name": "bob",
                        "channel": "position",
                        "time": 0.0,
                    }
                )
            self.assertEqual(caught.exception.status, 400)
            session.editor_action({"action": "select", "id": cube["id"]})
            for payload in (
                {
                    "action": "set_animation_key",
                    "name": "bob",
                    "channel": "position",
                    "time": -1.0,
                },
                {
                    "action": "set_animation_key",
                    "name": "bob",
                    "channel": "color",
                    "time": 0.0,
                },
            ):
                with self.assertRaises(WebProblem) as caught:
                    session.editor_action(payload)
                self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "set_animation_key",
                        "name": "missing",
                        "channel": "position",
                        "time": 0.0,
                    }
                )
            self.assertEqual(caught.exception.status, 404)

            standalone = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                standalone.editor_action(
                    {
                        "action": "set_animation_key",
                        "name": "bob",
                        "channel": "position",
                        "time": 0.0,
                    }
                )
            self.assertEqual(caught.exception.status, 400)

    def test_editor_material_library_save_assign_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            material_dir = Path(directory) / "materials"
            session = GameSession(CubeDemo(), material_dir=material_dir)
            editor = session.editor()
            cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
            original_material = cube["material"]

            saved = session.editor_action(
                {
                    "action": "save_material",
                    "name": "gold",
                    "color": [1.0, 0.8, 0.2],
                    "metallic": 1.0,
                    "roughness": 0.3,
                    "emissive": [0.1, 0.0, 0.0],
                }
            )
            self.assertTrue((material_dir / "gold.kmaterial").is_file())
            entry = next(
                item for item in saved["materials"] if item["name"] == "gold"
            )
            self.assertEqual(entry["color"], [1.0, 0.8, 0.2])
            self.assertEqual(entry["metallic"], 1.0)
            registry = session.game.assets
            self.assertIsNotNone(registry.get("material.gold"))

            assigned = session.editor_action(
                {"action": "assign_material", "id": cube["id"], "name": "gold"}
            )
            node = next(
                item for item in assigned["nodes"] if item["id"] == cube["id"]
            )
            self.assertEqual(node["material"], "material.gold")
            asset = next(
                item
                for item in assigned["assets"]
                if item["id"] == "material.gold"
            )
            self.assertEqual(asset["metadata"]["metallic"], 1.0)
            self.assertEqual(asset["metadata"]["color"], [1.0, 0.8, 0.2])

            undone = session.editor_action({"action": "undo"})
            node = next(
                item for item in undone["nodes"] if item["id"] == cube["id"]
            )
            self.assertEqual(node["material"], original_material)

            reloaded = GameSession(CubeDemo(), material_dir=material_dir)
            self.assertIn(
                "gold",
                {item["name"] for item in reloaded.editor()["materials"]},
            )
            self.assertIsNotNone(reloaded.game.assets.get("material.gold"))
            reassigned = reloaded.editor_action(
                {"action": "assign_material", "id": cube["id"], "name": "gold"}
            )
            node = next(
                item
                for item in reassigned["nodes"]
                if item["id"] == cube["id"]
            )
            self.assertEqual(node["material"], "material.gold")

            cleared = session.editor_action(
                {"action": "assign_material", "id": cube["id"], "name": None}
            )
            node = next(
                item for item in cleared["nodes"] if item["id"] == cube["id"]
            )
            self.assertIsNone(node["material"])

            assigned_again = session.editor_action(
                {"action": "assign_material", "id": cube["id"], "name": "gold"}
            )
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {"action": "delete_material", "name": "gold"}
                )
            self.assertEqual(caught.exception.status, 400)

            session.editor_action(
                {"action": "assign_material", "id": cube["id"], "name": None}
            )
            deleted = session.editor_action(
                {"action": "delete_material", "name": "gold"}
            )
            self.assertEqual(deleted["materials"], [])
            self.assertEqual(deleted["trash"]["materials"][0]["name"], "gold")
            self.assertIsNone(session.game.assets.get("material.gold"))
            restored = session.editor_action(
                {
                    "action": "restore_material",
                    "trash": deleted["trash"]["materials"][0]["trash"],
                }
            )
            self.assertIn(
                "gold", {item["name"] for item in restored["materials"]}
            )
            self.assertIsNotNone(session.game.assets.get("material.gold"))
            self.assertIsNotNone(assigned_again["selection"])

            standalone = GameSession(CubeDemo())
            with self.assertRaises(WebProblem) as caught:
                standalone.editor_action(
                    {
                        "action": "save_material",
                        "name": "gold",
                        "color": [1.0, 1.0, 1.0],
                    }
                )
            self.assertEqual(caught.exception.status, 400)
            with self.assertRaises(WebProblem) as caught:
                session.editor_action(
                    {
                        "action": "assign_material",
                        "id": cube["id"],
                        "name": "missing",
                    }
                )
            self.assertEqual(caught.exception.status, 404)

    def test_editor_component_lifecycle_play_mode(self):
        session = GameSession(LifecycleDemo())
        editor = session.editor()
        self.assertEqual(
            editor["component_schemas"]["Ticker"]["lifecycle"],
            ["start", "update", "stop"],
        )
        cube = next(node for node in editor["nodes"] if node["name"] == "cube-0")
        session.editor_action(
            {
                "action": "set_component",
                "id": cube["id"],
                "type": "Ticker",
                "data": {},
            }
        )
        started = session.editor_action({"action": "play_start"})
        self.assertEqual(started["play"]["lifecycle"]["started"], 1)
        self.assertEqual(started["play"]["lifecycle"]["frame"], 0)
        self.assertEqual(
            started["play"]["lifecycle"]["hooks"],
            ["start", "update", "stop"],
        )
        stepped = session.editor_action({"action": "play_step", "frames": 2})
        self.assertEqual(stepped["play"]["lifecycle"]["frame"], 2)
        node = next(node for node in stepped["nodes"] if node["id"] == cube["id"])
        data = next(
            item["data"]
            for item in node["component_data"]
            if item["type"] == "Ticker"
        )
        self.assertEqual(data, {"ticks": 2, "started": 1, "stopped": 0})
        stopped = session.editor_action({"action": "play_stop"})
        self.assertFalse(stopped["play"]["lifecycle"]["active"])
        self.assertEqual(stopped["play"]["lifecycle"]["started"], 0)
        node = next(node for node in stopped["nodes"] if node["id"] == cube["id"])
        data = next(
            item["data"]
            for item in node["component_data"]
            if item["type"] == "Ticker"
        )
        self.assertEqual(data, {"ticks": 0, "started": 0, "stopped": 0})

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
        self.assertIn('role="tree"', text)
        for control in (
            "hierarchy",
            "hierarchy-filter",
            "layer-toggles",
            "asset-filter",
            "play-start",
            "play-pause",
            "play-resume",
            "play-step",
            "play-stop",
            "play-frames",
            "play-actions",
            "play-state",
            "play-snapshot",
            "animation-clip",
            "animation-time",
            "animation-scrub",
            "animation-name",
            "animation-names",
            "animation-preview",
            "animation-sample",
            "animation-play",
            "animation-save",
            "animation-delete",
            "animation-restore",
            "animation-channel",
            "animation-key-set",
            "animation-key-remove",
            "animation-state",
            "state-machine-json",
            "state-machine-name",
            "state-machine-names",
            "state-machine-parameters",
            "state-machine-triggers",
            "state-machine-frames",
            "state-machine-save",
            "state-machine-load",
            "state-machine-preview",
            "state-machine-delete",
            "state-machine-restore",
            "state-machine-state",
            "node-parent",
            "node-create",
            "node-duplicate",
            "selection-copy",
            "selection-paste",
            "selection-lock",
            "selection-unlock",
            "node-delete",
            "selection-toggle-visible",
            "box-select",
            "selection-summary",
            "node-reparent",
            "node-visible",
            "node-tags",
            "node-layer",
            "node-properties",
            "editor-undo",
            "editor-redo",
            "history-steps",
            "history-state",
            "scene-name",
            "scene-names",
            "scene-new-name",
            "scene-save",
            "scene-load",
            "scene-revert",
            "scene-dirty-state",
            "scene-diff",
            "scene-rename",
            "scene-duplicate",
            "scene-delete",
            "scene-restore",
            "scene-settings",
            "scene-settings-apply",
            "scene-validate",
            "validation-state",
            "view-bookmark-name",
            "view-bookmark-select",
            "view-bookmark-save",
            "view-bookmark-apply",
            "view-bookmark-delete",
            "view-bookmark-state",
            "startup-set",
            "startup-clear",
            "startup-state",
            "camera-position",
            "camera-yaw",
            "camera-pitch",
            "camera-fov",
            "camera-settings-apply",
            "light-direction",
            "light-color",
            "light-intensity",
            "ambient-color",
            "fog-density",
            "environment-settings-apply",
            "shadow-toggle",
            "color-toggle",
            "post-toggle",
            "bloom-toggle",
            "sprites-toggle",
            "culling-toggle",
            "prefab-names",
            "prefab-new-name",
            "prefab-rename",
            "prefab-duplicate",
            "prefab-delete",
            "prefab-restore",
            "prefab-revert",
            "prefab-apply",
            "prefab-refresh",
            "prefab-edit",
            "prefab-edit-save",
            "prefab-edit-close",
            "prefab-edit-discard",
            "prefab-edit-state",
            "prefab-overrides",
            "prefab-link",
            "mesh-asset",
            "material-asset",
            "material-name",
            "material-names",
            "material-color",
            "material-metallic",
            "material-roughness",
            "material-emissive",
            "material-specular",
            "material-shininess",
            "material-checker",
            "material-texture",
            "material-texture-preview",
            "material-save",
            "material-assign",
            "material-clear",
            "material-delete",
            "material-restore",
            "material-state",
            "assign-asset",
            "assign-asset-selection",
            "asset-info",
            "asset-preview",
            "import-path",
            "import-asset",
            "import-state",
            "project-assets",
            "find-usages",
            "usage-state",
            "forget-asset",
            "reload-assets",
            "reload-state",
            "build-target",
            "build-force",
            "build-project",
            "build-state",
            "component-type",
            "component-fields",
            "component-hint",
            "component-data",
            "component-set",
            "component-remove",
            "view-reset",
            "view-focus",
            "view-mode",
            "grid-toggle",
            "snap-toggle",
            "snap-move",
            "snap-rotate",
            "snap-scale",
            "projection-mode",
            "layout-reset",
            "gizmo-move",
            "gizmo-rotate",
            "gizmo-scale",
            "gizmo-space",
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
        self.assertIn("copySelection", script)
        self.assertIn("pasteNodes", script)
        self.assertIn("copy_selection", script)
        self.assertIn("paste_nodes", script)
        self.assertIn("setSelectionLocked", script)
        self.assertIn("set_nodes_locked", script)
        self.assertIn("locked_count", script)
        self.assertIn("save_scene", script)
        self.assertIn("rename_scene", script)
        self.assertIn("duplicate_scene", script)
        self.assertIn("diff_scene", script)
        self.assertIn("applySceneSettings", script)
        self.assertIn("validateScene", script)
        self.assertIn("validate_scene", script)
        self.assertIn("validationState", script)
        self.assertIn("setStartupScene", script)
        self.assertIn("set_startup_scene", script)
        self.assertIn("startup_scene", script)
        self.assertIn("startup-state", script)
        self.assertIn("revertScene", script)
        self.assertIn("revert_scene", script)
        self.assertIn("scene_dirty", script)
        self.assertIn("saved_scene", script)
        self.assertIn("scene-dirty-state", script)
        self.assertIn("importAsset", script)
        self.assertIn("import_asset", script)
        self.assertIn("imported_asset", script)
        self.assertIn("import-state", script)
        self.assertIn("import_gltf", script)
        self.assertIn("imported_gltf", script)
        self.assertIn("forgetAsset", script)
        self.assertIn("forget_asset", script)
        self.assertIn("forgotten_asset", script)
        self.assertIn("project_assets", script)
        self.assertIn("project-assets", script)
        self.assertIn("findUsages", script)
        self.assertIn("asset_usages", script)
        self.assertIn("usage-state", script)
        self.assertIn("buildProject", script)
        self.assertIn("build_project", script)
        self.assertIn("build-state", script)
        self.assertIn("reloadAssets", script)
        self.assertIn("reload_assets", script)
        self.assertIn("asset_reload", script)
        self.assertIn("reload-state", script)
        self.assertIn("fillSceneSettings", script)
        self.assertIn("applyCameraSettings", script)
        self.assertIn("applyEnvironmentSettings", script)
        self.assertIn("readNumber", script)
        self.assertIn("restore_scene", script)
        self.assertIn("nudgeSelection", script)
        self.assertIn("ArrowLeft", script)
        self.assertIn("hierarchyFilter", script)
        self.assertIn("renderLayerToggles", script)
        self.assertIn("setLayerVisible", script)
        self.assertIn("set_layer_visible", script)
        self.assertIn("hidden_layers", script)
        self.assertIn("setHiddenLayers", script)
        self.assertIn("saveViewBookmark", script)
        self.assertIn("applyViewBookmark", script)
        self.assertIn("deleteViewBookmark", script)
        self.assertIn("loadViewBookmarks", script)
        self.assertIn("cameraBookmark", script)
        self.assertIn("view-bookmark-state", script)
        self.assertIn("assetFilter", script)
        self.assertIn("assign_asset", script)
        self.assertIn("assignSelectionAssets", script)
        self.assertIn("assign_asset_selection", script)
        self.assertIn("saveMaterial", script)
        self.assertIn("assignMaterial", script)
        self.assertIn("clearMaterial", script)
        self.assertIn("deleteMaterial", script)
        self.assertIn("restoreMaterial", script)
        self.assertIn("save_material", script)
        self.assertIn("assign_material", script)
        self.assertIn("delete_material", script)
        self.assertIn("restore_material", script)
        self.assertIn("fillMaterialForm", script)
        self.assertIn("fillDatalist", script)
        self.assertIn("materialTexturePreview", script)
        self.assertIn("updateMaterialTexturePreview", script)
        self.assertIn("material-texture-preview", script)
        self.assertIn("setSelected", script)
        self.assertIn("selected_ids", script)
        self.assertIn("select_many", script)
        self.assertIn("reparentNodeTo", script)
        self.assertIn("hierarchy-row", script)
        self.assertIn("draggable", script)
        self.assertIn("dragstart", script)
        self.assertIn("dragover", script)
        self.assertIn("dataTransfer", script)
        self.assertIn("collapsedNodes", script)
        self.assertIn("ancestorCollapsed", script)
        self.assertIn("hierarchy-toggle", script)
        self.assertIn("transform_selection", script)
        self.assertIn("toggle_selection_visible", script)
        self.assertIn("delete_selection", script)
        self.assertIn("selectionToggleVisible", script)
        self.assertIn("historyStepCount", script)
        self.assertIn("undo_stack", script)
        self.assertIn("redo_stack", script)
        self.assertIn("edit_prefab", script)
        self.assertIn("save_prefab_edit", script)
        self.assertIn("close_prefab_edit", script)
        self.assertIn("updatePrefabEditButtons", script)
        self.assertIn("refresh_prefab_instances", script)
        self.assertIn("refreshPrefabInstances", script)
        self.assertIn("prefab_refresh", script)
        self.assertIn("payload.ids", script)
        self.assertIn("renderPrefabOverrides", script)
        self.assertIn("revert_prefab_override", script)
        self.assertIn("apply_prefab_override", script)
        self.assertIn("setViewMode", script)
        self.assertIn("toggleViewMode", script)
        self.assertIn("updateViewModeButton", script)
        self.assertIn("toggleGrid", script)
        self.assertIn("toggleSnap", script)
        self.assertIn("syncSnapSteps", script)
        self.assertIn("applySnapSteps", script)
        self.assertIn("snapSteps", script)
        self.assertIn("setSnapSteps", script)
        self.assertIn("toggleProjection", script)
        self.assertIn("updateProjectionButton", script)
        self.assertIn("scheduleLayoutSave", script)
        self.assertIn("restoreLayout", script)
        self.assertIn("saveLayout", script)
        self.assertIn("resetLayout", script)
        self.assertIn("localStorage", script)
        self.assertIn("applyGizmoSelectionTransform", script)
        self.assertIn("applyGizmoSelectionRotation", script)
        self.assertIn("applyGizmoSelectionScale", script)
        self.assertIn("group_rotation", script)
        self.assertIn("group_scale", script)
        self.assertIn("onBoxSelect", script)
        self.assertIn("toggleBoxSelect", script)
        self.assertIn("boxSelect", script)
        self.assertIn("set_selection_properties", script)
        self.assertIn("set_selection_transform", script)
        self.assertIn("selectionSummary", script)
        self.assertIn("onSelect", script)
        self.assertIn("isEditingTarget", script)
        self.assertIn("keydown", script)
        self.assertIn("set_component", script)
        self.assertIn("renderComponentFields", script)
        self.assertIn("updateAssetInfo", script)
        self.assertIn("assetPreview", script)
        self.assertIn("play_start", script)
        self.assertIn("play_pause", script)
        self.assertIn("play_resume", script)
        self.assertIn("playTick", script)
        self.assertIn("startPlayLoop", script)
        self.assertIn("readPlayActions", script)
        self.assertIn("playSnapshot", script)
        self.assertIn("previewAnimation", script)
        self.assertIn("sampleAnimationClip", script)
        self.assertIn("toggleAnimationPlay", script)
        self.assertIn("animationTick", script)
        self.assertIn("stopAnimationPlay", script)
        self.assertIn("record", script)
        self.assertIn("animationDuration", script)
        self.assertIn("syncAnimationTimeline", script)
        self.assertIn("animationScrub", script)
        self.assertIn("saveAnimation", script)
        self.assertIn("deleteAnimation", script)
        self.assertIn("restoreAnimation", script)
        self.assertIn("preview_animation", script)
        self.assertIn("save_animation", script)
        self.assertIn("delete_animation", script)
        self.assertIn("restore_animation", script)
        self.assertIn("setAnimationKey", script)
        self.assertIn("removeAnimationKey", script)
        self.assertIn("set_animation_key", script)
        self.assertIn("remove_animation_key", script)
        self.assertIn("animation_key", script)
        self.assertIn("saveStateMachine", script)
        self.assertIn("previewStateMachine", script)
        self.assertIn("deleteStateMachine", script)
        self.assertIn("restoreStateMachine", script)
        self.assertIn("loadStateMachine", script)
        self.assertIn("load_state_machine", script)
        self.assertIn("state_machine_document", script)
        self.assertIn("save_state_machine", script)
        self.assertIn("preview_state_machine", script)
        self.assertIn("delete_state_machine", script)
        self.assertIn("restore_state_machine", script)
        self.assertIn("state_machine_preview", script)
        self.assertIn("state-machine-state", script)
        self.assertIn("fillStateMachineDatalist", script)
        self.assertIn("animation_preview", script)
        self.assertIn("playFrames", script)
        self.assertIn("set_node", script)
        self.assertIn("onTransform", script)
        self.assertIn("applyGizmoTransform", script)
        self.assertIn("worldDeltaToLocal", script)
        self.assertIn("setEditable", script)
        self.assertIn("revert_prefab", script)
        self.assertIn("apply_prefab", script)
        self.assertIn("revertPrefabInstance", script)
        self.assertIn("applyPrefabInstance", script)
        self.assertIn("onRotate", script)
        self.assertIn("onScale", script)
        self.assertIn("applyGizmoRotation", script)
        self.assertIn("applyGizmoScale", script)
        self.assertIn("setGizmoMode", script)
        self.assertIn("axisAngleQuaternion", script)
        self.assertIn("multiplyQuaternion", script)
        self.assertIn("setGizmoSpace", script)
        self.assertIn("toggleGizmoSpace", script)
        self.assertIn("prefab_link.name", script)
        self.assertIn("prefab_link.instance", script)
        self.assertIn("prefab_instances", script)
        status, _, body = self._request("/viewer.js")
        self.assertEqual(status, 200)
        viewer_script = body.decode("utf-8")
        self.assertIn("resetCamera", viewer_script)
        self.assertIn("cameraStateFromScene", viewer_script)
        self.assertIn("setViewMode", viewer_script)
        self.assertIn("viewMode", viewer_script)
        self.assertIn("buildGridVaos", viewer_script)
        self.assertIn("renderGrid", viewer_script)
        self.assertIn("setGrid", viewer_script)
        self.assertIn("setSnap", viewer_script)
        self.assertIn("snapActive", viewer_script)
        self.assertIn("orthographic", viewer_script)
        self.assertIn("setProjectionPreset", viewer_script)
        self.assertIn("projectionMode", viewer_script)
        self.assertIn("viewPreset", viewer_script)
        self.assertIn("layoutSnapshot", viewer_script)
        self.assertIn("applyLayout", viewer_script)
        self.assertIn("notifyLayoutChange", viewer_script)
        self.assertIn("renderPivots", viewer_script)
        self.assertIn("pivotIcon", viewer_script)
        self.assertIn("focusNode", viewer_script)
        self.assertIn("setSelected", viewer_script)
        self.assertIn("setSelectedIds", viewer_script)
        self.assertIn("selectionOrigin", viewer_script)
        self.assertIn("selectionRoots", viewer_script)
        self.assertIn("previewBasesForSelection", viewer_script)
        self.assertIn("focusSelection", viewer_script)
        self.assertIn("onTransformSelection", viewer_script)
        self.assertIn("onRotateSelection", viewer_script)
        self.assertIn("onScaleSelection", viewer_script)
        self.assertIn("scaleMatrix", viewer_script)
        self.assertIn("setBoxSelect", viewer_script)
        self.assertIn("startBoxDrag", viewer_script)
        self.assertIn("finishBoxDrag", viewer_script)
        self.assertIn("boxSelectionHits", viewer_script)
        self.assertIn("selectionBox", viewer_script)
        self.assertIn("boxBounds", viewer_script)
        self.assertIn("boxProxies", viewer_script)
        self.assertIn("clipNearPolygon", viewer_script)
        self.assertIn("projectViewPoint", viewer_script)
        self.assertIn("projectionMatrix", viewer_script)
        self.assertIn("u_selected", viewer_script)
        self.assertIn("pointerdown", viewer_script)
        self.assertIn("shiftKey", viewer_script)
        self.assertIn("cameraBasis", viewer_script)
        self.assertIn("selectAt", viewer_script)
        self.assertIn("rayBox", viewer_script)
        self.assertIn("lookAt", viewer_script)
        self.assertIn("gizmoAt", viewer_script)
        self.assertIn("beginGizmoDrag", viewer_script)
        self.assertIn("updateGizmoDrag", viewer_script)
        self.assertIn("finishGizmoDrag", viewer_script)
        self.assertIn("renderGizmo", viewer_script)
        self.assertIn("GIZMO_VERTEX_SHADER", viewer_script)
        self.assertIn("setGizmoMode", viewer_script)
        self.assertIn("setGizmoSpace", viewer_script)
        self.assertIn("gizmoSpace", viewer_script)
        self.assertIn("gizmoRing", viewer_script)
        self.assertIn("gizmoScaleArrow", viewer_script)
        self.assertIn("ringDistance", viewer_script)
        self.assertIn("rotationVector", viewer_script)
        self.assertIn("axisAngleMatrix", viewer_script)
        self.assertIn("scaleMatrix", viewer_script)
        status, _, payload = self._json("/api")
        self.assertEqual(status, 200)
        self.assertIn("editor", payload["endpoints"])
        self.assertIn(
            "examples", payload["endpoints"]["editor"]["schema"]
        )

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
