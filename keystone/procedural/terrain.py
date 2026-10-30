"""Procedural island heightfield with per-vertex biome colors."""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.geometry import MeshData
from keystone.math3d import Vec3
from keystone.procedural.noise import fbm

SAND = (0.76, 0.68, 0.48)
GRASS = (0.27, 0.45, 0.2)
FOREST = (0.17, 0.32, 0.16)
ROCK = (0.42, 0.41, 0.4)
SNOW = (0.88, 0.9, 0.94)


@dataclass(frozen=True, slots=True)
class Terrain:
    """A square, island-shaped heightfield sampled once per grid point."""

    seed: int
    size: int
    water: float
    heights: tuple[tuple[float, ...], ...]
    spawn: tuple[float, float]
    entrance: tuple[float, float]

    @classmethod
    def generate(cls, seed: int, size: int = 96, water: float = 0.0) -> Terrain:
        if size < 8:
            raise ValueError("terrain size must be at least 8")
        half = size / 2.0
        heights: list[tuple[float, ...]] = []
        for z in range(size + 1):
            row: list[float] = []
            for x in range(size + 1):
                wx, wz = x - half, z - half
                distance = math.hypot(wx, wz) / half
                height = (fbm(x * 0.038, z * 0.038, seed, 5) - 0.45) * 8.0 + 1.8
                height += (fbm(x * 0.16, z * 0.16, seed + 7, 3) - 0.5) * 1.6
                if distance > 0.65:
                    height -= (distance - 0.65) ** 2 * 26.0
                row.append(round(height, 5))
            heights.append(tuple(row))
        provisional = cls(seed, size, water, tuple(heights), (0.0, 0.0), (0.0, 0.0))
        spawn = provisional._find_spawn()
        entrance = provisional._find_entrance(spawn)
        return cls(seed, size, water, tuple(heights), spawn, entrance)

    def _find_spawn(self) -> tuple[float, float]:
        half = self.size / 2.0
        best: tuple[float, float] | None = None
        best_score = float("inf")
        for gz in range(2, self.size - 1):
            for gx in range(2, self.size - 1):
                wx, wz = gx - half, gz - half
                if not self.is_walkable(wx, wz):
                    continue
                score = (wx - 2.0) ** 2 + (wz - 2.0) ** 2
                if score < best_score:
                    best, best_score = (wx, wz), score
        if best is None:
            raise ValueError("terrain generated no walkable spawn point")
        return best

    def _find_entrance(self, spawn: tuple[float, float]) -> tuple[float, float]:
        for radius in range(6, 18):
            for step in range(24):
                angle = math.tau * step / 24.0
                x = spawn[0] + math.cos(angle) * radius
                z = spawn[1] + math.sin(angle) * radius
                if self.is_walkable(x, z):
                    return (round(x, 3), round(z, 3))
        return spawn

    def height_at(self, x: float, z: float) -> float:
        """Bilinearly sample the heightfield at world coordinates."""
        half = self.size / 2.0
        gx, gz = x + half, z + half
        if not (0.0 <= gx <= self.size and 0.0 <= gz <= self.size):
            return self.water - 2.0
        x0, z0 = min(int(gx), self.size - 1), min(int(gz), self.size - 1)
        fx, fz = gx - x0, gz - z0
        h00 = self.heights[z0][x0]
        h10 = self.heights[z0][x0 + 1]
        h01 = self.heights[z0 + 1][x0]
        h11 = self.heights[z0 + 1][x0 + 1]
        top = h00 + (h10 - h00) * fx
        bottom = h01 + (h11 - h01) * fx
        return top + (bottom - top) * fz

    def normal_at(self, x: float, z: float) -> Vec3:
        step = 0.5
        dx = self.height_at(x - step, z) - self.height_at(x + step, z)
        dz = self.height_at(x, z - step) - self.height_at(x, z + step)
        return Vec3(dx, 2.0 * step, dz).normalized()

    def is_water(self, x: float, z: float) -> bool:
        return self.height_at(x, z) < self.water + 0.15

    def is_walkable(self, x: float, z: float) -> bool:
        half = self.size / 2.0
        if not (-half <= x <= half and -half <= z <= half):
            return False
        return not self.is_water(x, z) and self.normal_at(x, z).y >= 0.45

    def color_at(self, x: int, z: int) -> tuple[float, float, float]:
        height = self.heights[z][x]
        normal = self.normal_at(x - self.size / 2.0, z - self.size / 2.0)
        if height < self.water + 0.35:
            return SAND
        if height > 5.6:
            return SNOW
        if normal.y < 0.55:
            return ROCK
        mix = fbm(x * 0.18, z * 0.18, self.seed + 31, 2)
        if mix > 0.62:
            return FOREST
        tint = 0.92 + mix * 0.16
        return (GRASS[0] * tint, GRASS[1] * tint, GRASS[2] * tint)

    def mesh(self) -> MeshData:
        side = self.size + 1
        half = self.size / 2.0
        positions: list[tuple[float, float, float]] = []
        normals: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float]] = []
        uvs: list[tuple[float, float]] = []
        for z in range(side):
            for x in range(side):
                wx, wz = x - half, z - half
                positions.append((wx, self.heights[z][x], wz))
                normal = self.normal_at(wx, wz)
                normals.append((normal.x, normal.y, normal.z))
                colors.append(self.color_at(x, z))
                uvs.append((x / self.size, z / self.size))
        indices: list[int] = []
        for z in range(self.size):
            for x in range(self.size):
                a = z * side + x
                b = a + 1
                c = a + side
                d = c + 1
                indices.extend((a, c, b, b, c, d))
        return MeshData(tuple(positions), tuple(normals), tuple(uvs), tuple(indices), tuple(colors))
