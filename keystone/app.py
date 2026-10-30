"""Engine runtime: window loop, fly controls and screenshot capture."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from keystone.gpu.context import GLContext
from keystone.gpu.renderer import Renderer
from keystone.scene import Scene

Update = Callable[[float], None]
Controls = Callable[[float, GLContext], None]
Status = Callable[[], str]


class Engine:
    """Bind one scene to one OpenGL context and drive the frame loop."""

    def __init__(
        self,
        scene: Scene,
        width: int = 960,
        height: int = 540,
        visible: bool = True,
        msaa: int = 0,
        title: str = "Keystone",
    ) -> None:
        self.scene = scene
        self._visible = visible
        self.context = GLContext(width, height, title, visible, msaa)
        try:
            self.renderer = Renderer(width, height)
        except Exception:
            self.context.close()
            raise
        self._closed = False
        self._captured = False
        self._f1_was_down = False
        self._last_cursor = self.context.cursor_position()
        if visible:
            self.context.set_cursor_captured(True)
            self._captured = True

    def __enter__(self) -> Engine:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _process_input(self, dt: float) -> None:
        if self.context.should_close() or self.context.key_down("escape"):
            return
        speed = (12.0 if self.context.key_down("left_shift") else 5.0) * dt
        forward = int(self.context.key_down("w")) - int(self.context.key_down("s"))
        right = int(self.context.key_down("d")) - int(self.context.key_down("a"))
        up = int(self.context.key_down("e")) - int(self.context.key_down("q"))
        if forward or right or up:
            self.scene.camera.move(forward * speed, right * speed, up * speed)
        yaw = (int(self.context.key_down("right")) - int(self.context.key_down("left"))) * 1.6 * dt
        pitch = (int(self.context.key_down("up")) - int(self.context.key_down("down"))) * 1.6 * dt
        if yaw or pitch:
            self.scene.camera.rotate(yaw, pitch)
        f1_down = self.context.key_down("f1")
        if f1_down and not self._f1_was_down:
            self._captured = not self._captured
            self.context.set_cursor_captured(self._captured)
        self._f1_was_down = f1_down
        x, y = self.context.cursor_position()
        dx, dy = x - self._last_cursor[0], y - self._last_cursor[1]
        self._last_cursor = (x, y)
        if self._captured and (dx or dy):
            self.scene.camera.rotate(dx * 0.0025, -dy * 0.0025)

    def run(
        self,
        update: Update | None = None,
        max_frames: int = 0,
        controls: Controls | None = None,
        status: Status | None = None,
    ) -> int:
        """Render until the window closes or max_frames (0 = unlimited) is reached."""
        if max_frames < 0:
            raise ValueError("max_frames cannot be negative")
        frames = 0
        fps_start = self.context.time()
        fps_frames = 0
        last = fps_start
        while not self.context.should_close():
            if max_frames and frames >= max_frames:
                break
            self.context.poll_events()
            width, height = self.context.framebuffer_size()
            if (width, height) != (self.renderer.width, self.renderer.height):
                self.renderer.resize(width, height)
            now = self.context.time()
            dt = min(max(now - last, 0.0), 0.05)
            last = now
            if self._visible:
                if self.context.key_down("escape"):
                    self.context.request_close()
                if controls is None:
                    self._process_input(dt)
                else:
                    controls(dt, self.context)
            if update is not None:
                update(dt)
            self.renderer.render(self.scene)
            if self._visible:
                self.context.swap_buffers()
            frames += 1
            fps_frames += 1
            if self._visible and now - fps_start >= 0.5:
                fps = fps_frames / max(now - fps_start, 1e-6)
                detail = f" | {status()}" if status is not None else ""
                self.context.set_title(
                    f"Keystone{detail} | {fps:.0f} FPS | {self.renderer.width}x{self.renderer.height}"
                )
                fps_start = now
                fps_frames = 0
        return frames

    def screenshot(self, path: str | Path) -> None:
        self.renderer.render(self.scene)
        self.renderer.save_png(path)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.renderer.release()
        self.context.close()
