"""First-person expedition: procedural overworld, dungeon and scene assembly."""

from __future__ import annotations

import math
import random

from keystone.atmosphere import Atmosphere, apply_atmosphere
from keystone.beams import mask_to_rgb
from keystone.combat import ENEMY_TYPES
from keystone.geometry import Material, MeshData
from keystone.gpu.context import GLContext
from keystone.math3d import Quat, Vec3
from keystone.mesh_builder import MeshBuilder
from keystone.primitives import cone, cube, cylinder, plane, sphere
from keystone.procedural.noise import rand01
from keystone.scene import DirectionalLight, Node, PointLight, Scene, Transform
from keystone.sim.world import MoveIntent, World

STONE = Material(color=Vec3(0.42, 0.4, 0.45), specular=0.2, shininess=16.0)
WATER = Material(color=Vec3(0.08, 0.24, 0.36), specular=0.8, shininess=96.0)
PORTAL = Material(color=Vec3(0.15, 0.75, 0.7), specular=1.0, shininess=128.0)
TERRAIN = Material(color=Vec3(1.0, 1.0, 1.0), specular=0.03, shininess=4.0)
CRYSTAL = Material(color=Vec3(1.0, 0.72, 0.22), specular=1.0, shininess=128.0)
EMITTER = Material(color=Vec3(1.0, 0.18, 0.1), specular=1.0, shininess=128.0)
RECEIVER_OPEN = Material(color=Vec3(1.0, 0.85, 0.15), specular=1.0, shininess=128.0)
RECEIVER_LOCKED = Material(color=Vec3(0.2, 1.0, 0.5), specular=1.0, shininess=128.0)
DYE = Material(color=Vec3(0.2, 1.0, 0.3), specular=1.0, shininess=96.0)
MIRROR = Material(color=Vec3(0.75, 0.82, 0.95), specular=1.0, shininess=128.0)


class Expedition:
    """Owns one seeded World and the scene that renders its current mode."""

    def __init__(self, seed: int = 7, size: int = 96, layout: str = "auto") -> None:
        self.world = World(seed, size, layout)
        self.scene = Scene()
        self.scene.camera.fov_y = 65.0
        self._intent = MoveIntent()
        self._mode = self.world.mode
        self._lock_version = -1
        self._captured = True
        self._last_cursor: tuple[float, float] | None = None
        self._e_was_down = False
        self._f1_was_down = False
        self._terrain_mesh = self.world.terrain.mesh()
        self._water_mesh = plane(self.world.terrain.size)
        self._tree_trunks, self._tree_crowns, self._rocks, self._path = self._build_scenery_meshes()
        self._dungeon_floor, self._dungeon_walls, self._dungeon_ceiling = self._build_dungeon_meshes()
        self._enemy_meshes = {
            "crawler": cone(1.0, 2.0, segments=7),
            "stalker": sphere(1.0, segments=9, rings=6),
            "bulwark": cube(2.0),
            "splitter": sphere(1.0, segments=9, rings=6),
            "bomber": sphere(1.0, segments=9, rings=6),
            "warlord": cube(2.0),
        }
        self._enemy_materials = {
            key: Material(color=Vec3(*spec.color), specular=0.45, shininess=48.0)
            for key, spec in ENEMY_TYPES.items()
        }
        self._enemy_nodes: dict[int, Node] = {}
        self._rebuild()

    def _build_scenery_meshes(self) -> tuple[MeshData, MeshData, MeshData, MeshData]:
        trunk = MeshBuilder()
        crown = MeshBuilder()
        rocks = MeshBuilder()
        path = MeshBuilder()
        rng = random.Random(self.world.seed + 99)
        terrain = self.world.terrain
        spawn = terrain.spawn
        radius = min(terrain.size / 2.0 - 2.0, 38.0)
        trunk_mesh = cylinder(0.12, 1.1, segments=7)
        crown_mesh = cone(0.75, 1.6, segments=7)
        rock_mesh = sphere(0.35, segments=8, rings=5)
        placed = 0
        attempts = 0
        while placed < 90 and attempts < 900:
            attempts += 1
            x = spawn[0] + rng.uniform(-radius, radius)
            z = spawn[1] + rng.uniform(-radius, radius)
            if not terrain.is_walkable(x, z):
                continue
            if math.hypot(x - spawn[0], z - spawn[1]) < 2.5:
                continue
            if math.hypot(x - terrain.entrance[0], z - terrain.entrance[1]) < 2.5:
                continue
            if self._distance_to_path(x, z) < 1.8:
                continue
            height = terrain.height_at(x, z)
            scale = rng.uniform(0.75, 1.35)
            trunk.add_mesh(
                trunk_mesh,
                offset=(x, height + 0.55 * scale, z),
                scale=scale,
                color=(0.3, 0.2, 0.12),
            )
            crown.add_mesh(
                crown_mesh,
                offset=(x, height + 1.9 * scale, z),
                scale=scale,
                color=(0.16 + rng.uniform(0.0, 0.08), 0.3 + rng.uniform(0.0, 0.1), 0.14),
            )
            placed += 1
        if placed == 0:
            x, z = spawn[0] + 2.5, spawn[1]
            trunk.add_mesh(trunk_mesh, offset=(x, terrain.height_at(x, z) + 0.55, z), color=(0.3, 0.2, 0.12))
            crown.add_mesh(crown_mesh, offset=(x, terrain.height_at(x, z) + 1.9, z), color=(0.18, 0.32, 0.16))
        rocks_placed = 0
        for index in range(16):
            angle = math.tau * index / 16.0
            x = spawn[0] + math.cos(angle) * (5.0 + index % 4)
            z = spawn[1] + math.sin(angle) * (5.0 + index % 4)
            if terrain.is_walkable(x, z) and self._distance_to_path(x, z) >= 1.5:
                rocks.add_mesh(
                    rock_mesh,
                    offset=(x, terrain.height_at(x, z) + 0.15, z),
                    scale=0.85 + 0.3 * (index % 3),
                    color=(0.36, 0.35, 0.34),
                )
                rocks_placed += 1
        if rocks_placed == 0:
            x, z = spawn[0] + 1.5, spawn[1] + 1.5
            rocks.add_mesh(rock_mesh, offset=(x, terrain.height_at(x, z) + 0.15, z), color=(0.36, 0.35, 0.34))
        start = (spawn[0], spawn[1])
        end = terrain.entrance
        length = math.hypot(end[0] - start[0], end[1] - start[1]) or 1.0
        dx, dz = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        px, pz = -dz * 0.45, dx * 0.45
        steps = 24
        for index in range(steps):
            t0, t1 = index / steps, (index + 1) / steps
            ax, az = start[0] + dx * length * t0, start[1] + dz * length * t0
            bx, bz = start[0] + dx * length * t1, start[1] + dz * length * t1
            path.add_quad(
                (ax - px, terrain.height_at(ax, az) + 0.04, az - pz),
                (ax + px, terrain.height_at(ax, az) + 0.04, az + pz),
                (bx + px, terrain.height_at(bx, bz) + 0.04, bz + pz),
                (bx - px, terrain.height_at(bx, bz) + 0.04, bz - pz),
                (0.4, 0.33, 0.24),
            )
        return trunk.build(), crown.build(), rocks.build(), path.build()

    def _distance_to_path(self, x: float, z: float) -> float:
        ax, az = self.world.terrain.spawn
        bx, bz = self.world.terrain.entrance
        vx, vz = bx - ax, bz - az
        length_sq = vx * vx + vz * vz
        if length_sq <= 1e-9:
            return math.hypot(x - ax, z - az)
        t = max(0.0, min(1.0, ((x - ax) * vx + (z - az) * vz) / length_sq))
        return math.hypot(x - (ax + vx * t), z - (az + vz * t))

    def _build_dungeon_meshes(self) -> tuple[MeshData, MeshData, MeshData]:
        dungeon = self.world.dungeon
        floor = MeshBuilder()
        walls = MeshBuilder()
        ceiling = MeshBuilder()
        wall_cells: set[tuple[int, int]] = set()
        for y in range(dungeon.height):
            for x in range(dungeon.width):
                if not dungeon.is_walkable(x, y):
                    continue
                weave_color = self.world.weave.floor_color(x, y) if self.world.weave else None
                if weave_color is None:
                    shade = 0.22 + rand01(x, y, dungeon.seed) * 0.08
                    color = (shade, shade * 0.95, shade * 1.12)
                else:
                    color = tuple(min(1.0, component * 0.9 + 0.08) for component in weave_color)
                floor.add_quad(
                    (float(x), 0.0, float(y)),
                    (float(x), 0.0, float(y + 1)),
                    (float(x + 1), 0.0, float(y + 1)),
                    (float(x + 1), 0.0, float(y)),
                    color,
                )
                shade = 0.12 + rand01(x, y, dungeon.seed + 5) * 0.05
                ceiling.add_quad(
                    (float(x), 3.0, float(y)),
                    (float(x + 1), 3.0, float(y)),
                    (float(x + 1), 3.0, float(y + 1)),
                    (float(x), 3.0, float(y + 1)),
                    (shade, shade * 0.96, shade * 1.1),
                )
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    if not dungeon.is_walkable(x + dx, y + dy):
                        wall_cells.add((x + dx, y + dy))
        for x, y in sorted(wall_cells):
            shade = 0.5 + rand01(x, y, dungeon.seed + 17) * 0.14
            walls.add_box(
                x + 0.5,
                1.5,
                y + 0.5,
                1.0,
                3.0,
                1.0,
                (shade, shade * 0.98, shade * 1.08),
            )
        return floor.build(), walls.build(), ceiling.build()

    def _rebuild(self) -> None:
        self._enemy_nodes = {}
        self.scene.root = Node()
        if self.world.mode == "overworld":
            self._build_overworld()
        else:
            self._build_dungeon()
        self._apply_visuals()
        self._lock_version = self.world.light_lock.version
        self._sync_enemies()

    def _build_overworld(self) -> None:
        self.scene.add(Node("terrain", mesh=self._terrain_mesh, material=TERRAIN))
        self.scene.add(
            Node(
                "water",
                Transform(position=Vec3(0.0, self.world.terrain.water + 0.02, 0.0)),
                mesh=self._water_mesh,
                material=WATER,
            )
        )
        self.scene.add(Node("trees-trunks", mesh=self._tree_trunks, material=TERRAIN))
        self.scene.add(Node("trees-crowns", mesh=self._tree_crowns, material=TERRAIN))
        self.scene.add(Node("rocks", mesh=self._rocks, material=TERRAIN))
        self.scene.add(Node("path", mesh=self._path, material=TERRAIN))
        self._add_portal()
        self._add_light_lock()

    def _add_portal(self) -> None:
        x, z = self.world.terrain.entrance
        ground = self.world.terrain.height_at(x, z)
        dx = x - self.world.terrain.spawn[0]
        dz = z - self.world.terrain.spawn[1]
        length = math.hypot(dx, dz) or 1.0
        px, pz = -dz / length, dx / length
        for side in (-1, 1):
            self.scene.add(
                Node(
                    f"portal-post-{side}",
                    Transform(
                        position=Vec3(x + px * 0.9 * side, ground + 1.2, z + pz * 0.9 * side),
                        scale=Vec3(0.35, 2.4, 0.35),
                    ),
                    mesh=cube(1.0),
                    material=STONE,
                )
            )
        angle = math.atan2(-pz, px)
        self.scene.add(
            Node(
                "portal-lintel",
                Transform(
                    position=Vec3(x, ground + 2.4, z),
                    rotation=Quat.from_axis_angle(Vec3.UP, angle),
                    scale=Vec3(2.15, 0.25, 0.35),
                ),
                mesh=cube(1.0),
                material=STONE,
            )
        )
        self.scene.add(
            Node(
                "portal-rune",
                Transform(position=Vec3(x, ground + 1.4, z)),
                mesh=sphere(0.22, segments=12, rings=8),
                material=PORTAL,
            )
        )

    def _add_light_lock(self) -> None:
        lock = self.world.light_lock
        ox, oz = lock.origin
        ground = self.world.terrain.height_at(ox, oz)
        height = ground + 1.35
        self.scene.add(
            Node(
                "light-emitter",
                Transform(position=Vec3(ox - 3.0, height, oz)),
                mesh=cube(0.32),
                material=EMITTER,
            )
        )
        receiver_material = RECEIVER_LOCKED if lock.solved else RECEIVER_OPEN
        self.scene.add(
            Node(
                "light-receiver",
                Transform(position=Vec3(ox - 3.0, height, oz + 2.0)),
                mesh=cube(0.32),
                material=receiver_material,
            )
        )
        self.scene.add(
            Node(
                "light-dye",
                Transform(position=Vec3(ox - 1.0, height, oz + 1.0)),
                mesh=sphere(0.14, segments=10, rings=7),
                material=DYE,
            )
        )
        for (x, z), orientation in lock.mirrors.items():
            angle = math.pi / 4.0 if orientation == "/" else -math.pi / 4.0
            self.scene.add(
                Node(
                    f"light-mirror-{x}-{z}",
                    Transform(
                        position=Vec3(ox + x, height, oz + z),
                        rotation=Quat.from_axis_angle(Vec3.UP, angle),
                        scale=Vec3(0.08, 1.0, 0.5),
                    ),
                    mesh=cube(1.0),
                    material=MIRROR,
                )
            )
        beams = MeshBuilder()
        for segment in lock.trace():
            sx, sz = segment.start
            ex, ez = segment.end
            wx0, wz0 = ox + sx, oz + sz
            wx1, wz1 = ox + ex, oz + ez
            beams.add_box(
                (wx0 + wx1) / 2.0,
                height,
                (wz0 + wz1) / 2.0,
                abs(wx1 - wx0) + 0.05,
                0.05,
                abs(wz1 - wz0) + 0.05,
                mask_to_rgb(segment.mask),
            )
        self.scene.add(Node("light-beams", mesh=beams.build(), material=TERRAIN))

    def _build_dungeon(self) -> None:
        self.scene.add(Node("dungeon-floor", mesh=self._dungeon_floor, material=TERRAIN))
        self.scene.add(Node("dungeon-walls", mesh=self._dungeon_walls, material=TERRAIN))
        self.scene.add(Node("dungeon-ceiling", mesh=self._dungeon_ceiling, material=TERRAIN))
        spawn_room = self.world.dungeon.rooms[0]
        for index, room in enumerate(self.world.dungeon.rooms[1:4], 1):
            x, z = room.x + 1.0, room.y + 1.0
            self.scene.add(
                Node(
                    f"crystal-{index}",
                    Transform(position=Vec3(x + 0.5, 1.1, z + 0.5)),
                    mesh=sphere(0.14, segments=10, rings=7),
                    material=CRYSTAL,
                )
            )
        for index, (dx, dz) in enumerate(((1, 1), (spawn_room.w - 2, spawn_room.h - 2))):
            x, z = spawn_room.x + dx, spawn_room.y + dz
            self.scene.add(
                Node(
                    f"torch-{index}",
                    Transform(position=Vec3(x + 0.5, 1.8, z + 0.5)),
                    mesh=sphere(0.12, segments=8, rings=6),
                    material=CRYSTAL,
                )
            )
        x, z = self.world.dungeon.exit
        self.scene.add(
            Node(
                "exit-rune",
                Transform(
                    position=Vec3(x + 0.5, 1.1, z + 0.5),
                    scale=Vec3(0.8, 2.0, 0.15),
                ),
                mesh=cube(1.0),
                material=PORTAL,
            )
        )

    def _apply_visuals(self) -> None:
        apply_atmosphere(self.scene, Atmosphere.at(self.world.day_fraction))
        camera = self.scene.camera
        camera.position = self.world.eye_position()
        camera.yaw = self.world.player.yaw
        camera.pitch = self.world.player.pitch
        if self.world.mode == "dungeon":
            self.scene.fog_density = 0.055
            self.scene.sky = Vec3(0.005, 0.005, 0.012)
            self.scene.background = Vec3(0.015, 0.015, 0.025)
            self.scene.ambient = Vec3(0.28, 0.28, 0.36)
            self.scene.light = DirectionalLight(
                direction=Vec3(-0.3, -1.0, -0.4),
                color=Vec3(0.8, 0.85, 1.0),
                intensity=0.65,
            )
            self.scene.point_light = PointLight(
                position=camera.position,
                color=Vec3(1.0, 0.68, 0.32),
                intensity=1.35,
                radius=9.0,
            )
        else:
            self.scene.fog_density = 0.012
            self.scene.point_light = None

    def _sync_enemies(self) -> None:
        living = {id(enemy): enemy for enemy in self.world.combat.enemies if enemy.hp > 0}
        for key in list(self._enemy_nodes):
            if key not in living:
                node = self._enemy_nodes.pop(key)
                if node.parent is not None:
                    node.parent.remove_child(node)
        for key, enemy in living.items():
            node = self._enemy_nodes.get(key)
            if node is None:
                node = Node(f"enemy-{key}", mesh=self._enemy_meshes[enemy.spec.key], material=self._enemy_materials[enemy.spec.key])
                self.scene.add(node)
                self._enemy_nodes[key] = node
            height = self.world.terrain.height_at(enemy.x, enemy.z) if self.world.mode == "overworld" else 0.0
            radius = enemy.spec.radius
            node.transform = Transform(
                position=Vec3(enemy.x, height + radius, enemy.z),
                scale=Vec3(radius, radius, radius),
            )

    def status(self) -> str:
        light = "open" if self.world.light_lock.solved else "sealed"
        return f"{self.world.mode} | {self.world.combat.status()} | light {light}"

    def step(self, dt: float, intent: MoveIntent | None = None) -> list[str]:
        events = self.world.step(dt, intent or MoveIntent())
        if self.world.mode != self._mode:
            self._mode = self.world.mode
            self._rebuild()
        elif self.world.light_lock.version != self._lock_version:
            self._rebuild()
        else:
            self._apply_visuals()
        self._sync_enemies()
        return events

    def update(self, dt: float) -> None:
        intent = self._intent
        self._intent = MoveIntent()
        self.step(dt, intent)

    def handle_input(self, dt: float, context: GLContext) -> None:
        forward = int(context.key_down("w")) - int(context.key_down("s"))
        right = int(context.key_down("d")) - int(context.key_down("a"))
        turn = (int(context.key_down("right")) - int(context.key_down("left"))) * 1.6 * dt
        pitch = (int(context.key_down("up")) - int(context.key_down("down"))) * 1.6 * dt
        x, y = context.cursor_position()
        if self._last_cursor is None:
            self._last_cursor = (x, y)
        dx, dy = x - self._last_cursor[0], y - self._last_cursor[1]
        self._last_cursor = (x, y)
        if self._captured:
            turn += dx * 0.0025
            pitch -= dy * 0.0025
        interact = context.key_down("e") and not self._e_was_down
        self._e_was_down = context.key_down("e")
        f1 = context.key_down("f1")
        if f1 and not self._f1_was_down:
            self._captured = not self._captured
            context.set_cursor_captured(self._captured)
            self._last_cursor = None
        self._f1_was_down = f1
        self._intent = MoveIntent(
            forward=float(forward),
            right=float(right),
            turn=turn,
            pitch=pitch,
            interact=interact,
            sprint=context.key_down("left_shift"),
        )
