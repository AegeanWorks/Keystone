"""First-person space scene and controls over the renderer-independent SpaceWorld."""

from __future__ import annotations

import math
import random

from keystone.geometry import Material
from keystone.gpu.context import GLContext
from keystone.math3d import Vec3
from keystone.mesh_builder import MeshBuilder
from keystone.primitives import sphere
from keystone.scene import DirectionalLight, Node, Scene, Transform
from keystone.sim.world import MoveIntent
from keystone.space import GATE, SpaceWorld

STAR = Material(color=Vec3(1.0, 0.83, 0.3), specular=1.0, shininess=128.0)
PLANET = Material(color=Vec3(0.7, 0.7, 0.7), specular=0.15, shininess=24.0)
GATE_MATERIAL = Material(color=Vec3(0.15, 0.85, 1.0), specular=1.0, shininess=128.0)
STARFIELD = Material(color=Vec3(0.8, 0.85, 1.0), specular=0.0, shininess=1.0)
VOID = Material(color=Vec3(0.02, 0.02, 0.04), specular=0.0, shininess=1.0)


class SpaceExpedition:
    """A free-flight ship, an orbiting system and a jump gate."""

    def __init__(self, seed: int = 7) -> None:
        self.world = SpaceWorld(seed)
        self.scene = Scene()
        self.scene.camera.fov_y = 70.0
        self._intent = MoveIntent()
        self._body_nodes: dict[str, Node] = {}
        self._system_id = ""
        self._captured = True
        self._last_cursor: tuple[float, float] | None = None
        self._scan_was_down = False
        self._jump_was_down = False
        self._f1_was_down = False
        self._sphere = sphere(1.0, segments=20, rings=12)
        self._starfield = self._build_starfield(seed)
        self._build_system()

    def _build_starfield(self, seed: int) -> object:
        rng = random.Random(seed + 4242)
        builder = MeshBuilder()
        for _ in range(180):
            angle = rng.uniform(0.0, math.tau)
            height = rng.uniform(-0.9, 0.9)
            radius = math.sqrt(1.0 - height * height)
            distance = rng.uniform(105.0, 125.0)
            builder.add_box(
                math.cos(angle) * radius * distance,
                height * distance,
                math.sin(angle) * radius * distance,
                0.22,
                0.22,
                0.22,
                (0.65, 0.72, 0.95),
            )
        return builder.build()

    def _build_system(self) -> None:
        self.scene.root = Node()
        self._body_nodes = {}
        self._system_id = self.world.system_id
        self.scene.add(Node("starfield", mesh=self._starfield, material=STARFIELD))
        for body in self.world.system.bodies:
            if body.kind == "star":
                material = STAR
            else:
                material = Material(color=Vec3(*body.color), specular=0.2, shininess=32.0)
            node = Node(f"body-{body.body_id}", mesh=self._sphere, material=material)
            self.scene.add(node)
            self._body_nodes[body.body_id] = node
        self._add_gate()
        self.scene.background = Vec3(0.002, 0.003, 0.01)
        self.scene.sky = Vec3(0.001, 0.002, 0.008)
        self.scene.ambient = Vec3(0.06, 0.07, 0.1)
        self.scene.fog_density = 0.0
        self.scene.light = DirectionalLight(
            direction=Vec3(-0.3, -1.0, -0.35),
            color=Vec3(1.0, 0.96, 0.9),
            intensity=0.9,
        )
        self.scene.point_light = None
        self._sync()

    def _add_gate(self) -> None:
        gate = MeshBuilder()
        for index in range(16):
            angle = math.tau * index / 16.0
            gate.add_box(
                GATE.x + math.cos(angle) * 4.0,
                GATE.y + math.sin(angle) * 4.0,
                GATE.z,
                0.22,
                0.22,
                0.22,
                (0.1, 0.7, 0.95),
            )
        self.scene.add(Node("jump-gate", mesh=gate.build(), material=GATE_MATERIAL))

    def _sync(self) -> None:
        for body in self.world.system.bodies:
            x, y, z = body.position(self.world.time)
            self._body_nodes[body.body_id].transform = Transform(
                position=Vec3(x, y, z),
                scale=Vec3(body.radius, body.radius, body.radius),
            )
        camera = self.scene.camera
        camera.position = self.world.ship.position
        camera.yaw = self.world.ship.yaw
        camera.pitch = self.world.ship.pitch

    def step(self, dt: float, intent: MoveIntent | None = None) -> list[str]:
        events = self.world.step(dt, intent or MoveIntent())
        if self.world.system_id != self._system_id:
            self._build_system()
        else:
            self._sync()
        return events

    def update(self, dt: float) -> None:
        intent = self._intent
        self._intent = MoveIntent()
        self.step(dt, intent)

    def handle_input(self, dt: float, context: GLContext) -> None:
        forward = int(context.key_down("w")) - int(context.key_down("s"))
        right = int(context.key_down("d")) - int(context.key_down("a"))
        up = int(context.key_down("r")) - int(context.key_down("f"))
        turn = (int(context.key_down("right")) - int(context.key_down("left"))) * 1.5 * dt
        pitch = (int(context.key_down("up")) - int(context.key_down("down"))) * 1.5 * dt
        x, y = context.cursor_position()
        if self._last_cursor is None:
            self._last_cursor = (x, y)
        dx, dy = x - self._last_cursor[0], y - self._last_cursor[1]
        self._last_cursor = (x, y)
        if self._captured:
            turn += dx * 0.0025
            pitch -= dy * 0.0025
        scan = context.key_down("e") and not self._scan_was_down
        jump = context.key_down("j") and not self._jump_was_down
        self._scan_was_down = context.key_down("e")
        self._jump_was_down = context.key_down("j")
        f1 = context.key_down("f1")
        if f1 and not self._f1_was_down:
            self._captured = not self._captured
            context.set_cursor_captured(self._captured)
            self._last_cursor = None
        self._f1_was_down = f1
        self._intent = MoveIntent(
            forward=float(forward),
            right=float(right),
            up=float(up),
            turn=turn,
            pitch=pitch,
            scan=scan,
            jump=jump,
            sprint=context.key_down("left_shift"),
        )

    def status(self) -> str:
        return self.world.status()
