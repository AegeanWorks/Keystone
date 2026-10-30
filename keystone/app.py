"""Game-agnostic engine runtime: window, fixed step, input, render and capture."""

from __future__ import annotations

from pathlib import Path

from keystone.clock import FixedStepClock
from keystone.gpu.context import GLContext
from keystone.gpu.renderer import Renderer
from keystone.gpu.ui_renderer import UiRenderer
from keystone.input import ActionState, InputMap
from keystone.plugin import GameModule
from keystone.scene import Scene
from keystone.ui.overlay import HudState, HumanOverlay


class Engine:
    """Owns the runtime around one external GameModule."""

    def __init__(
        self,
        game: GameModule,
        width: int = 960,
        height: int = 540,
        visible: bool = True,
        msaa: int = 0,
        title: str = "Keystone",
        ui: bool = False,
    ) -> None:
        self.game = game
        self.context = GLContext(width, height, title, visible, msaa)
        try:
            self.renderer = Renderer(width, height)
        except Exception:
            self.context.close()
            raise
        self.ui_renderer: UiRenderer | None = None
        self.overlay: HumanOverlay | None = HumanOverlay() if ui else None
        try:
            if ui:
                self.ui_renderer = UiRenderer()
            self.scene = game.build_scene()
        except Exception:
            if self.ui_renderer is not None:
                self.ui_renderer.release()
            self.renderer.release()
            self.context.close()
            raise
        if not isinstance(self.scene, Scene):
            if self.ui_renderer is not None:
                self.ui_renderer.release()
            self.renderer.release()
            self.context.close()
            raise TypeError("GameModule.build_scene() must return a Scene")
        self.input = InputMap()
        self.clock = FixedStepClock()
        self.paused = False
        self._frames = 0
        self._elapsed = 0.0
        self._fps = 0.0
        self._pointer: tuple[float, float] = (0.0, 0.0)
        self._visible = visible
        self._closed = False
        self._captured = visible
        if visible:
            self.context.set_cursor_captured(True)
        else:
            self.input.set_mouse_enabled(False)

    def __enter__(self) -> Engine:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _set_capture(self, captured: bool) -> None:
        self._captured = captured
        self.context.set_cursor_captured(captured)
        self.input.set_mouse_enabled(captured)

    def _handle_system_actions(self, actions: ActionState) -> None:
        if "quit" in actions.pressed:
            self.context.request_close()
        if "toggle_capture" in actions.pressed and not self.paused:
            self._set_capture(not self._captured)
        if "toggle_ui" in actions.pressed and self.overlay is not None:
            self.overlay.toggle()
        if "pause" in actions.pressed:
            self.toggle_pause()
        if self.paused and self.overlay is not None and self.overlay.visible:
            menu = self.overlay.menu
            if actions.pressed & {"look_up", "forward"}:
                menu.move(-1)
            elif actions.pressed & {"look_down", "back"}:
                menu.move(1)
            if "confirm" in actions.pressed:
                self.apply_ui_action(menu.action())
            if actions.mouse_clicked:
                action = self.overlay.hit_test(*actions.pointer)
                if action is not None:
                    self.apply_ui_action(action)

    def toggle_pause(self) -> None:
        """Pause or resume gameplay; release the cursor while the menu is open."""
        self.paused = not self.paused
        self._set_capture(self._visible and not self.paused)

    def apply_ui_action(self, action: str) -> bool:
        """Run a named UI action; returns False when the action is unknown."""
        if action == "pause":
            self.toggle_pause()
            return True
        if action == "resume":
            if self.paused:
                self.toggle_pause()
            return True
        if action == "toggle_ui" and self.overlay is not None:
            self.overlay.toggle()
            return True
        if action == "quit":
            self.context.request_close()
            return True
        return False

    def _draw_ui(self) -> None:
        if self.overlay is None or self.ui_renderer is None:
            return
        state = HudState(
            game=getattr(self.game, "name", "game"),
            status=self.game.status(),
            fps=self._fps,
            frame=self._frames,
            elapsed=self._elapsed,
            width=self.renderer.width,
            height=self.renderer.height,
            paused=self.paused,
            pointer=self._pointer,
        )
        self.ui_renderer.draw(self.overlay.build(state))

    def run(self, max_frames: int = 0) -> int:
        """Run until the window closes or max_frames (0 = unlimited) is reached."""
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
            if self._visible:
                steps = self.clock.advance(now)
                frame_dt = min(max(now - last, 0.0), 0.1)
            else:
                steps = [self.clock.step]
                frame_dt = self.clock.step
            last = now
            actions = self.input.sample(self.context, frame_dt)
            self._pointer = actions.pointer
            self._handle_system_actions(actions)
            if self.context.should_close():
                break
            if not self.paused:
                for index, dt in enumerate(steps):
                    self.game.update(dt, actions if index == 0 else actions.without_pressed())
                self._elapsed += sum(steps)
            self.renderer.render(self.scene)
            self._draw_ui()
            if self._visible:
                self.context.swap_buffers()
            frames += 1
            self._frames = frames
            fps_frames += 1
            if self._visible and now - fps_start >= 0.5:
                fps = fps_frames / max(now - fps_start, 1e-6)
                self._fps = fps
                self.context.set_title(
                    f"Keystone | {self.game.status()} | {fps:.0f} FPS | {self.renderer.width}x{self.renderer.height}"
                )
                fps_start = now
                fps_frames = 0
        return frames

    def capture(self, image_path: str | Path | None, report_path: str | Path | None = None) -> None:
        self.renderer.render(self.scene)
        self._draw_ui()
        pixels = self.renderer.read_pixels()
        if image_path is not None:
            from keystone.png import write_png

            write_png(image_path, self.renderer.width, self.renderer.height, pixels)
        if report_path is not None:
            from keystone.analysis import analyze_frame, write_report

            report = analyze_frame(
                self.scene,
                pixels,
                self.renderer.width,
                self.renderer.height,
                image_path,
            )
            write_report(report_path, report)

    def screenshot(self, path: str | Path) -> None:
        self.capture(path)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.ui_renderer is not None:
            self.ui_renderer.release()
        self.renderer.release()
        self.context.close()
