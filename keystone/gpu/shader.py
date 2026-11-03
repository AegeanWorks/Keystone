"""GLSL program compilation, uniform upload and cleanup."""

from __future__ import annotations

from OpenGL import GL

from keystone.math3d import Mat4, Vec3


class ShaderProgram:
    """A linked vertex/fragment program with cached uniform locations."""

    def __init__(self, vertex_source: str, fragment_source: str) -> None:
        self._program = 0
        self._locations: dict[str, int] = {}
        vertex = self._compile(GL.GL_VERTEX_SHADER, vertex_source, "vertex")
        try:
            fragment = self._compile(GL.GL_FRAGMENT_SHADER, fragment_source, "fragment")
        except Exception:
            GL.glDeleteShader(vertex)
            raise
        program = GL.glCreateProgram()
        try:
            GL.glAttachShader(program, vertex)
            GL.glAttachShader(program, fragment)
            GL.glLinkProgram(program)
            if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
                log = GL.glGetProgramInfoLog(program).decode("utf-8", errors="replace")
                raise ValueError(
                    "Shader program failed to link.\n"
                    f"Why: {log.strip()}\n"
                    "Fix: check that every vertex output has a matching fragment input."
                )
        except Exception:
            GL.glDeleteProgram(program)
            raise
        finally:
            GL.glDeleteShader(vertex)
            GL.glDeleteShader(fragment)
        self._program = program

    def _compile(self, stage: int, source: str, label: str) -> int:
        shader = GL.glCreateShader(stage)
        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)
        if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
            log = GL.glGetShaderInfoLog(shader).decode("utf-8", errors="replace")
            GL.glDeleteShader(shader)
            raise ValueError(
                f"{label.capitalize()} shader failed to compile.\n"
                f"Why: {log.strip()}\n"
                "Fix: correct the GLSL named in the log, then rebuild the program."
            )
        return shader

    def use(self) -> None:
        GL.glUseProgram(self._program)

    def _location(self, name: str) -> int:
        if name not in self._locations:
            self._locations[name] = GL.glGetUniformLocation(self._program, name)
        return self._locations[name]

    def set_mat4(self, name: str, matrix: Mat4) -> None:
        GL.glUniformMatrix4fv(self._location(name), 1, GL.GL_FALSE, matrix.flat())

    def set_mat4_array(self, name: str, matrices: list[Mat4] | tuple[Mat4, ...]) -> None:
        """Upload a fixed mat4 array palette (e.g. skinning bones)."""
        flat: list[float] = []
        for matrix in matrices:
            flat.extend(matrix.flat())
        GL.glUniformMatrix4fv(self._location(f"{name}[0]"), len(matrices), GL.GL_FALSE, flat)

    def set_mat3(self, name: str, values: tuple[float, ...]) -> None:
        GL.glUniformMatrix3fv(self._location(name), 1, GL.GL_FALSE, values)

    def set_vec2(self, name: str, x: float, y: float) -> None:
        GL.glUniform2f(self._location(name), x, y)

    def set_vec3(self, name: str, vector: Vec3) -> None:
        GL.glUniform3f(self._location(name), vector.x, vector.y, vector.z)

    def set_float(self, name: str, value: float) -> None:
        GL.glUniform1f(self._location(name), value)

    def set_int(self, name: str, value: int) -> None:
        GL.glUniform1i(self._location(name), value)

    def release(self) -> None:
        if self._program:
            GL.glDeleteProgram(self._program)
            self._program = 0
            self._locations.clear()
