"""Compose boxes and quads into a single indexed MeshData."""

from __future__ import annotations

from keystone.geometry import MeshData
from keystone.math3d import Mat4, Vec3


class MeshBuilder:
    """Accumulates flat-shaded quads and boxes, then builds one mesh."""

    def __init__(self) -> None:
        self._positions: list[tuple[float, float, float]] = []
        self._normals: list[tuple[float, float, float]] = []
        self._uvs: list[tuple[float, float]] = []
        self._colors: list[tuple[float, float, float]] = []
        self._indices: list[int] = []
        self._joints: list[tuple[int, ...]] = []
        self._weights: list[tuple[float, ...]] = []
        self._skin_joints: tuple[str, ...] | None = None
        self._skin_inverse_bind: tuple[tuple[float, ...], ...] | None = None
        self._mode: str | None = None

    def _require_mode(self, mode: str) -> None:
        if self._mode is None:
            self._mode = mode
        elif self._mode != mode:
            raise ValueError(f"cannot mix {self._mode} and {mode} geometry in one builder")

    def add_quad(
        self,
        p0: tuple[float, float, float],
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        p3: tuple[float, float, float],
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> MeshBuilder:
        self._require_mode("plain")
        a, b, c = Vec3(*p0), Vec3(*p1), Vec3(*p2)
        normal = (b - a).cross(c - a).normalized()
        if normal.length_squared() < 1e-12:
            raise ValueError("quad corners are collinear or degenerate")
        base = len(self._positions)
        for point, uv in ((p0, (0.0, 1.0)), (p1, (1.0, 1.0)), (p2, (1.0, 0.0)), (p3, (0.0, 0.0))):
            self._positions.append(point)
            self._normals.append((normal.x, normal.y, normal.z))
            self._uvs.append(uv)
            self._colors.append(color)
        self._indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))
        return self

    def add_mesh(
        self,
        mesh: MeshData,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        scale: float = 1.0,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> MeshBuilder:
        """Merge another mesh under a uniform scale and translation."""
        self._require_mode("plain")
        if scale <= 0.0:
            raise ValueError("mesh scale must be positive")
        base = len(self._positions)
        ox, oy, oz = offset
        for index, position in enumerate(mesh.positions):
            self._positions.append(
                (position[0] * scale + ox, position[1] * scale + oy, position[2] * scale + oz)
            )
            self._normals.append(mesh.normals[index])
            self._uvs.append(mesh.uvs[index] if mesh.uvs else (0.0, 0.0))
            source = mesh.colors[index] if mesh.colors else (1.0, 1.0, 1.0)
            self._colors.append(
                (source[0] * color[0], source[1] * color[1], source[2] * color[2])
            )
        self._indices.extend(base + index for index in mesh.indices)
        return self

    def add_mesh_matrix(
        self,
        mesh: MeshData,
        matrix: Mat4,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> MeshBuilder:
        """Merge a mesh transformed by a world matrix (positions + normals)."""
        self._require_mode("plain")
        if not isinstance(matrix, Mat4):
            raise TypeError("matrix must be a Mat4")
        # Normals need transpose(inverse(M)), matching gpu.renderer.normal_matrix.
        inverse = matrix.inverse()
        base = len(self._positions)
        for index, position in enumerate(mesh.positions):
            point = matrix.transform_point(Vec3(*position))
            raw = Vec3(*mesh.normals[index])
            normal = Vec3(
                inverse.m[0] * raw.x + inverse.m[1] * raw.y + inverse.m[2] * raw.z,
                inverse.m[4] * raw.x + inverse.m[5] * raw.y + inverse.m[6] * raw.z,
                inverse.m[8] * raw.x + inverse.m[9] * raw.y + inverse.m[10] * raw.z,
            ).normalized()
            self._positions.append((point.x, point.y, point.z))
            self._normals.append((normal.x, normal.y, normal.z))
            self._uvs.append(mesh.uvs[index] if mesh.uvs else (0.0, 0.0))
            source = mesh.colors[index] if mesh.colors else (1.0, 1.0, 1.0)
            self._colors.append(
                (source[0] * color[0], source[1] * color[1], source[2] * color[2])
            )
        self._indices.extend(base + index for index in mesh.indices)
        return self

    def add_skinned_mesh(self, mesh: MeshData) -> MeshBuilder:
        """Concatenate a skinned mesh verbatim (positions, joints, weights).

        Members merged this way must share the joint-name list and the
        inverse bind matrices; the merged node reuses their common world
        matrix so deformation is unchanged.
        """
        self._require_mode("skin")
        if not isinstance(mesh, MeshData) or not mesh.skinned:
            raise ValueError("add_skinned_mesh needs a skinned MeshData")
        if self._skin_joints is None:
            self._skin_joints = tuple(mesh.skin_joints)
            self._skin_inverse_bind = tuple(mesh.skin_inverse_bind)
        elif tuple(mesh.skin_joints) != self._skin_joints:
            raise ValueError("skinned merge members must share the joint-name list")
        elif tuple(mesh.skin_inverse_bind) != self._skin_inverse_bind:
            raise ValueError("skinned merge members must share the inverse bind matrices")
        base = len(self._positions)
        for index, position in enumerate(mesh.positions):
            self._positions.append(position)
            self._normals.append(mesh.normals[index])
            self._uvs.append(mesh.uvs[index] if mesh.uvs else (0.0, 0.0))
            source = mesh.colors[index] if mesh.colors else (1.0, 1.0, 1.0)
            self._colors.append(source)
            self._joints.append(tuple(mesh.joints[index]))
            self._weights.append(tuple(mesh.weights[index]))
        self._indices.extend(base + index for index in mesh.indices)
        return self

    def add_box(
        self,
        cx: float,
        cy: float,
        cz: float,
        sx: float,
        sy: float,
        sz: float,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> MeshBuilder:
        if sx <= 0.0 or sy <= 0.0 or sz <= 0.0:
            raise ValueError("box dimensions must be positive")
        x0, x1 = cx - sx / 2.0, cx + sx / 2.0
        y0, y1 = cy - sy / 2.0, cy + sy / 2.0
        z0, z1 = cz - sz / 2.0, cz + sz / 2.0
        faces = (
            ((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)),
            ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)),
            ((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)),
            ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),
            ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
            ((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)),
        )
        for face in faces:
            self.add_quad(*face, color)
        return self

    def is_empty(self) -> bool:
        return not self._indices

    def build(self) -> MeshData:
        if not self._indices:
            raise ValueError("mesh builder has no geometry")
        if self._mode == "skin":
            return MeshData(
                tuple(self._positions),
                tuple(self._normals),
                tuple(self._uvs),
                tuple(self._indices),
                tuple(self._colors),
                tuple(self._joints),
                tuple(self._weights),
                self._skin_joints or (),
                self._skin_inverse_bind or (),
            )
        return MeshData(
            tuple(self._positions),
            tuple(self._normals),
            tuple(self._uvs),
            tuple(self._indices),
            tuple(self._colors),
        )
