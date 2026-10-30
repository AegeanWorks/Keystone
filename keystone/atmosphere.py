"""Day/night atmosphere derived from a normalized world clock."""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.math3d import Vec3
from keystone.scene import DirectionalLight, Scene

DAY_SKY = Vec3(0.24, 0.43, 0.72)
NIGHT_SKY = Vec3(0.02, 0.03, 0.08)
DAY_HORIZON = Vec3(0.6, 0.72, 0.86)
NIGHT_HORIZON = Vec3(0.07, 0.08, 0.13)
DAWN = Vec3(0.78, 0.42, 0.22)


@dataclass(frozen=True, slots=True)
class Atmosphere:
    """Lighting and sky colors for one moment of the day."""

    daylight: float
    night: float
    warm: float
    ambient: Vec3
    sky: Vec3
    horizon: Vec3
    light_direction: Vec3
    light_color: Vec3
    intensity: float

    @classmethod
    def at(cls, day_fraction: float) -> Atmosphere:
        if not 0.0 <= day_fraction < 1.0:
            raise ValueError("day_fraction must be in [0, 1)")
        phase = math.tau * (day_fraction - 0.25)
        sun_elevation = math.sin(phase)
        daylight = max(0.0, min(1.0, (sun_elevation + 0.1) * 2.6))
        night = 1.0 - daylight
        warm = max(0.0, 1.0 - abs(sun_elevation) * 2.8)
        sky = NIGHT_SKY.lerp(DAY_SKY, daylight).lerp(DAWN, warm * 0.18)
        horizon = NIGHT_HORIZON.lerp(DAY_HORIZON, daylight).lerp(DAWN, warm * 0.6)
        ambient = Vec3(
            0.12 + 0.18 * daylight + 0.05 * warm,
            0.13 + 0.2 * daylight,
            0.18 + 0.22 * daylight,
        )
        elevation = max(0.12, sun_elevation)
        direction = Vec3(-0.45, -elevation, -0.55).normalized()
        light_color = Vec3(1.0, 0.93, 0.82).lerp(Vec3(0.55, 0.65, 1.0), night * 0.65)
        intensity = 0.2 + 1.2 * daylight
        return cls(daylight, night, warm, ambient, sky, horizon, direction, light_color, intensity)


def apply_atmosphere(scene: Scene, atmosphere: Atmosphere) -> None:
    scene.sky = atmosphere.sky
    scene.background = atmosphere.horizon
    scene.ambient = atmosphere.ambient
    scene.light = DirectionalLight(
        direction=atmosphere.light_direction,
        color=atmosphere.light_color,
        intensity=atmosphere.intensity,
    )
