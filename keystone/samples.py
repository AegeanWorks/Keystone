"""A minimal game-agnostic sample used to smoke-test the engine."""

from __future__ import annotations

import math
from dataclasses import replace

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Quat, Vec3
from keystone.particles import Emitter, ParticleSystem
from keystone.primitives import cube, plane, sphere
from keystone.scene import DirectionalLight, Node, PointLight, Scene, Transform
from keystone.texture import TextureData


class CubeDemo:
    """A rotating cube scene; contains no combat, puzzles or genre rules."""

    name = "cube-demo"

    def __init__(self) -> None:
        self.scene = Scene()
        self.assets = AssetRegistry()
        self.particles = ParticleSystem()
        self._time = 0.0
        self._cubes: list[Node] = []

    def build_scene(self) -> Scene:
        self.scene = Scene()
        self.assets = AssetRegistry()
        self.particles = ParticleSystem()
        self.particles.add(
            Emitter(
                name="fountain",
                rate=0.0,
                lifetime=1.6,
                speed=1.8,
                spread=0.45,
                direction=Vec3(0.0, 1.0, 0.0),
                gravity=Vec3(0.0, -2.2, 0.0),
                size=1.0,
                seed=7,
            )
        )
        self.particles.burst("fountain", 64, Vec3(0.0, 1.5, 0.0))
        self.assets.register("mesh.cube", cube(1.4))
        self.assets.register("mesh.plane", plane(20.0))
        self.assets.register("mesh.sphere", sphere(1.0, segments=24, rings=14))
        checker = TextureData.checker(64, (0.10, 0.12, 0.16), (0.18, 0.20, 0.25), name="floor-checker")
        self.assets.register("texture.floor-checker", checker)
        self.assets.register(
            "material.floor",
            Material(color=Vec3(1.0, 1.0, 1.0), specular=0.08, shininess=8.0, texture=checker),
        )
        colors = ((0.9, 0.4, 0.2), (0.2, 0.7, 0.8), (0.6, 0.45, 0.9))
        for index, color in enumerate(colors):
            self.assets.register(
                f"material.cube.{index}",
                Material(color=Vec3(*color), specular=0.4, shininess=48.0),
            )
        self.assets.register(
            "material.orb",
            Material(color=Vec3(0.95, 0.78, 0.3), specular=0.8, shininess=96.0),
        )
        self.scene.background = Vec3(0.035, 0.045, 0.07)
        self.scene.sky = Vec3(0.01, 0.015, 0.04)
        self.scene.ambient = Vec3(0.18, 0.2, 0.26)
        self.scene.fog_density = 0.01
        self.scene.camera.position = Vec3(0.0, 3.5, 9.0)
        self.scene.camera.fov_y = 55.0
        self.scene.camera.look_at(Vec3(0.0, 1.2, 0.0))
        self.scene.light = DirectionalLight(
            direction=Vec3(-0.45, -1.0, -0.35),
            color=Vec3(1.0, 0.93, 0.82),
            intensity=1.1,
        )
        self.scene.point_light = PointLight(
            position=Vec3(3.0, 4.0, 2.0),
            color=Vec3(0.4, 0.7, 1.0),
            intensity=0.8,
            radius=12.0,
        )
        self.scene.add(
            Node(
                "floor",
                id="floor",
                mesh=self.assets.require("mesh.plane").payload,
                material=self.assets.require("material.floor").payload,
            )
        )
        colors = ((0.9, 0.4, 0.2), (0.2, 0.7, 0.8), (0.6, 0.45, 0.9))
        self._cubes = []
        for index, color in enumerate(colors):
            node = Node(
                f"cube-{index}",
                id=f"cube-{index}",
                transform=Transform(position=Vec3((index - 1) * 2.4, 0.75, 0.0)),
                mesh=self.assets.require("mesh.cube").payload,
                material=self.assets.require(f"material.cube.{index}").payload,
            )
            self.scene.add(node)
            self._cubes.append(node)
        self.scene.add(
            Node(
                "orb",
                id="orb",
                transform=Transform(position=Vec3(0.0, 2.5, 0.0), scale=Vec3(0.7, 0.7, 0.7)),
                mesh=self.assets.require("mesh.sphere").payload,
                material=self.assets.require("material.orb").payload,
            )
        )
        return self.scene

    def update(self, dt: float, actions: object) -> None:
        self._time += dt
        self.particles.step(dt)
        for index, node in enumerate(self._cubes):
            node.transform = replace(
                node.transform,
                rotation=Quat.from_axis_angle(Vec3(0.3, 1.0, 0.1).normalized(), self._time * 0.7 + index * 0.8),
            )
        orb = next(node for node in self.scene.traverse() if node.name == "orb")
        orb.transform = replace(orb.transform, position=Vec3(0.0, 2.5 + math.sin(self._time * 1.4) * 0.2, 0.0))
        camera = self.scene.camera
        camera.move(
            getattr(actions, "forward", 0.0) * dt * 4.0,
            getattr(actions, "right", 0.0) * dt * 4.0,
            getattr(actions, "up", 0.0) * dt * 4.0,
        )
        camera.rotate(getattr(actions, "look_yaw", 0.0), getattr(actions, "look_pitch", 0.0))

    def snapshot(self) -> dict[str, object]:
        return {
            "time": round(self._time, 4),
            "camera": {
                "x": round(self.scene.camera.position.x, 3),
                "y": round(self.scene.camera.position.y, 3),
                "z": round(self.scene.camera.position.z, 3),
                "yaw": round(self.scene.camera.yaw, 4),
                "pitch": round(self.scene.camera.pitch, 4),
            },
        }

    def actions(self) -> dict[str, object]:
        return {
            "axes": ["forward", "right", "up", "look_yaw", "look_pitch"],
            "buttons": ["sprint", "toggle_capture", "quit"],
        }

    def status(self) -> str:
        return "cube demo"
