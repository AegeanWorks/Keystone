"""Built-in demo scene: a lit platform, an orbiting ring and a spinning crystal."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

from keystone.geometry import Material
from keystone.math3d import Quat, Vec3
from keystone.obj_loader import load_obj
from keystone.primitives import cube, plane, sphere
from keystone.scene import DirectionalLight, Node, Scene, Transform

ASSET = Path(__file__).resolve().parent.parent / "assets" / "octahedron.obj"


class Demo:
    """A deterministic scene plus the animation applied by the engine loop."""

    def __init__(self) -> None:
        self.scene = Scene()
        self.scene.background = Vec3(0.055, 0.07, 0.11)
        self.scene.sky = Vec3(0.008, 0.012, 0.032)
        self.scene.ambient = Vec3(0.22, 0.24, 0.3)
        self.scene.fog_density = 0.035
        self.scene.light = DirectionalLight(
            direction=Vec3(-0.45, -1.0, -0.35),
            color=Vec3(1.0, 0.93, 0.82),
            intensity=1.25,
        )
        self.scene.camera.position = Vec3(0.0, 2.4, 7.5)
        self.scene.camera.fov_y = 50.0
        self.scene.camera.look_at(Vec3(0.0, 1.2, 0.0))

        self.scene.add(
            Node(
                "ground",
                mesh=plane(400.0),
                material=Material(
                    color=Vec3(0.2, 0.23, 0.28),
                    specular=0.06,
                    shininess=8.0,
                    checker_scale=0.5,
                ),
            )
        )
        self.scene.add(
            Node(
                "pedestal",
                Transform(position=Vec3(0.0, 0.7, 0.0)),
                mesh=cube(1.4),
                material=Material(color=Vec3(0.25, 0.28, 0.34), specular=0.45, shininess=48.0),
            )
        )
        self.crystal = Node(
            "crystal",
            Transform(position=Vec3(0.0, 2.35, 0.0), scale=Vec3(0.85, 0.85, 0.85)),
            mesh=load_obj(ASSET),
            material=Material(color=Vec3(0.98, 0.76, 0.3), specular=1.0, shininess=128.0),
        )
        self.scene.add(self.crystal)

        orbit = Node("orbit", Transform(position=Vec3(0.0, 1.3, 0.0)))
        self.scene.add(orbit)
        colors = (
            Vec3(0.9, 0.35, 0.15),
            Vec3(0.2, 0.75, 0.85),
            Vec3(0.55, 0.45, 0.9),
        )
        for index in range(6):
            angle = math.tau * index / 6.0
            mesh = cube(0.45) if index % 2 == 0 else sphere(0.32, segments=20, rings=10)
            orbit.add_child(
                Node(
                    f"orbiter-{index}",
                    Transform(position=Vec3(math.cos(angle) * 3.2, 0.0, math.sin(angle) * 3.2)),
                    mesh=mesh,
                    material=Material(color=colors[index % len(colors)], specular=0.55),
                )
            )
        for index, (x, z) in enumerate(((-6.0, -4.0), (6.0, -4.0), (-6.0, 4.0), (6.0, 4.0))):
            self.scene.add(
                Node(
                    f"pillar-{index}",
                    Transform(position=Vec3(x, 0.5, z)),
                    mesh=cube(1.0),
                    material=Material(color=Vec3(0.12, 0.2, 0.24), specular=0.3),
                )
            )
        self._orbit = orbit
        self._crystal_base = self.crystal.transform.position
        self._elapsed = 0.0

    def update(self, dt: float) -> None:
        self._elapsed += dt
        self._orbit.transform = replace(
            self._orbit.transform,
            rotation=Quat.from_axis_angle(Vec3.UP, self._elapsed * 0.35),
        )
        self.crystal.transform = replace(
            self.crystal.transform,
            position=Vec3(
                self._crystal_base.x,
                self._crystal_base.y + math.sin(self._elapsed * 1.4) * 0.18,
                self._crystal_base.z,
            ),
            rotation=Quat.from_axis_angle(
                Vec3(1.0, 1.0, 0.0).normalized(), self._elapsed * 1.2
            ),
        )
