"""GLFW window and OpenGL 3.3 context lifecycle with deterministic teardown."""

from __future__ import annotations

import re

import glfw
from OpenGL import GL

MIN_VERSION = (3, 3)

_KEYS = {
    "w": glfw.KEY_W,
    "a": glfw.KEY_A,
    "s": glfw.KEY_S,
    "d": glfw.KEY_D,
    "q": glfw.KEY_Q,
    "e": glfw.KEY_E,
    "space": glfw.KEY_SPACE,
    "left_shift": glfw.KEY_LEFT_SHIFT,
    "up": glfw.KEY_UP,
    "down": glfw.KEY_DOWN,
    "left": glfw.KEY_LEFT,
    "right": glfw.KEY_RIGHT,
    "escape": glfw.KEY_ESCAPE,
    "f1": glfw.KEY_F1,
}


def require_opengl_33(version: str) -> None:
    """Refuse a context that cannot run the 3.3 core shader pipeline."""
    match = re.search(r"(\d+)\.(\d+)", version or "")
    if not match or (int(match.group(1)), int(match.group(2))) < MIN_VERSION:
        raise RuntimeError(
            f"OpenGL 3.3 is required, but the driver reports '{version or 'unknown'}'.\n"
            "Why: Keystone's shaders use GLSL 330 core features unavailable on older contexts.\n"
            "Fix: update the GPU driver, or run on a machine with OpenGL 3.3 or newer."
        )


class GLContext:
    """A hidden or visible GLFW window owning one OpenGL 3.3 core context."""

    def __init__(
        self,
        width: int = 960,
        height: int = 540,
        title: str = "Keystone",
        visible: bool = True,
        msaa: int = 0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("window width and height must be positive")
        self.width = width
        self.height = height
        self._window = None
        self._started_glfw = False
        if not glfw.init():
            raise RuntimeError(
                "GLFW could not initialize a window system.\n"
                "Why: no display or window manager is available to the process.\n"
                "Fix: run on a desktop session with a GPU driver, or use headless mode with a virtual display."
            )
        self._started_glfw = True
        try:
            glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
            glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
            glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
            glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
            glfw.window_hint(glfw.VISIBLE, glfw.TRUE if visible else glfw.FALSE)
            if msaa > 0:
                glfw.window_hint(glfw.SAMPLES, msaa)
            self._window = glfw.create_window(width, height, title, None, None)
            if not self._window:
                raise RuntimeError(
                    "Could not create an OpenGL 3.3 window.\n"
                    "Why: the driver refused a 3.3 core profile context.\n"
                    "Fix: update the GPU driver, then retry; check `glxinfo` or the vendor control panel."
                )
            glfw.make_context_current(self._window)
            glfw.swap_interval(1)
            require_opengl_33(self._version_string())
        except Exception:
            self.close()
            raise

    def __enter__(self) -> GLContext:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _version_string(self) -> str:
        raw = GL.glGetString(GL.GL_VERSION)
        return raw.decode("utf-8", errors="replace") if raw else ""

    def version(self) -> str:
        return self._version_string()

    def should_close(self) -> bool:
        return bool(glfw.window_should_close(self._window))

    def request_close(self) -> None:
        glfw.set_window_should_close(self._window, True)

    def poll_events(self) -> None:
        glfw.poll_events()

    def swap_buffers(self) -> None:
        glfw.swap_buffers(self._window)

    def time(self) -> float:
        return glfw.get_time()

    def key_down(self, name: str) -> bool:
        if name not in _KEYS:
            raise ValueError(f"unknown key '{name}'; add it to GLContext._KEYS")
        return glfw.get_key(self._window, _KEYS[name]) == glfw.PRESS

    def cursor_position(self) -> tuple[float, float]:
        return glfw.get_cursor_pos(self._window)

    def set_cursor_captured(self, captured: bool) -> None:
        mode = glfw.CURSOR_DISABLED if captured else glfw.CURSOR_NORMAL
        glfw.set_input_mode(self._window, glfw.CURSOR, mode)

    def set_title(self, title: str) -> None:
        glfw.set_window_title(self._window, title)

    def framebuffer_size(self) -> tuple[int, int]:
        self.width, self.height = glfw.get_framebuffer_size(self._window)
        return self.width, self.height

    def close(self) -> None:
        if self._window is not None:
            glfw.destroy_window(self._window)
            self._window = None
        if self._started_glfw:
            glfw.terminate()
            self._started_glfw = False
