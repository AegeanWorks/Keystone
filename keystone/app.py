"""Game-agnostic engine runtime: window, fixed step, input, render and capture."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from keystone.clock import FixedStepClock
from keystone.gpu.context import GLContext
from keystone.gpu.renderer import Renderer
from keystone.gpu.ui_renderer import UiRenderer
from keystone.input import ActionState, InputMap
from keystone.plugin import GameModule
from keystone.scene import Scene
from keystone.ui.canvas import Canvas
from keystone.ui.overlay import HudState, HumanOverlay
from keystone.ui.report import describe_canvas


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
        scene: Scene | None = None,
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
            self.scene = scene if scene is not None else game.build_scene()
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
        try:
            self._apply_game_bindings()
        except Exception:
            if self.ui_renderer is not None:
                self.ui_renderer.release()
            self.renderer.release()
            self.context.close()
            raise
        self.clock = FixedStepClock()
        self.paused = False
        self._frames = 0
        self._elapsed = 0.0
        self._fps = 0.0
        self._pointer: tuple[float, float] = (0.0, 0.0)
        self._visible = visible
        self._closed = False
        self._captured = visible
        self._pending_pressed: frozenset[str] = frozenset()
        self._pending_clicked = False
        self._pending_yaw = 0.0
        self._pending_pitch = 0.0
        if visible:
            self.context.set_cursor_captured(True)
        else:
            self.input.set_mouse_enabled(False)

    def _apply_game_bindings(self) -> None:
        """Let the game extend the default bindings through an optional hook.

        The engine owns the window, but only the game knows which actions its
        ``actions()`` contract advertises. A game that implements
        ``bind_input(mapping)`` can therefore bind its own buttons instead of
        inheriting a fixed set it can never rebind.
        """
        bind_input = getattr(self.game, "bind_input", None)
        if callable(bind_input):
            bind_input(self.input)

    def __enter__(self) -> Engine:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _set_capture(self, captured: bool) -> None:
        self._captured = captured
        self.context.set_cursor_captured(captured)
        self.input.set_look_enabled(captured)

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

    def _game_particles(self) -> object | None:
        for attribute in ("particles", "fx", "particle_system"):
            system = getattr(self.game, attribute, None)
            if system is not None:
                return system
        return None

    def _draw_ui(self) -> Canvas | None:
        if self.overlay is None or self.ui_renderer is None:
            return None
        stats = getattr(self.renderer, "last_stats", {"draw_calls": 0, "triangles": 0})
        mixer = getattr(self.game, "mixer", None)
        voices = 0
        if mixer is not None and hasattr(mixer, "voice_count"):
            try:
                voices = int(mixer.voice_count())
            except (AttributeError, TypeError, ValueError):
                voices = 0
        anim_clips = 0
        for attribute in ("animations", "animator", "controller"):
            controller = getattr(self.game, attribute, None)
            clips = getattr(controller, "clips", None) if controller is not None else None
            if isinstance(clips, dict):
                anim_clips = len(clips)
                break
        live_fx = 0
        for attribute in ("particles", "fx", "particle_system"):
            system = getattr(self.game, attribute, None)
            if system is None:
                continue
            count = getattr(system, "alive_count", None)
            if callable(count):
                try:
                    live_fx = int(count())
                except (AttributeError, TypeError, ValueError):
                    live_fx = 0
                break
            items = getattr(system, "particles", None)
            if isinstance(items, list):
                live_fx = len(items)
                break
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
            draw_calls=int(stats.get("draw_calls", 0)),
            triangles=int(stats.get("triangles", 0)),
            shadow_calls=int(stats.get("shadow_calls", 0)),
            post_enabled=int(stats.get("post_enabled", 0)),
            bloom_enabled=int(stats.get("bloom_enabled", 0)),
            audio_voices=voices,
            anim_clips=anim_clips,
            particles=live_fx,
            sprites=int(stats.get("sprites", 0)),
            culled=int(stats.get("culled_nodes", 0)),
        )
        draw_game_ui = getattr(self.game, "draw_ui", None)
        canvas = self.overlay.build(state, draw_game_ui if callable(draw_game_ui) else None)
        self.ui_renderer.draw(canvas)
        return canvas

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
            if self.paused:
                self._pending_pressed = frozenset()
                self._pending_clicked = False
                self._pending_yaw = 0.0
                self._pending_pitch = 0.0
            else:
                self._pending_pressed = self._pending_pressed | actions.pressed
                self._pending_clicked = self._pending_clicked or actions.mouse_clicked
                self._pending_yaw += actions.look_yaw
                self._pending_pitch += actions.look_pitch
                for index, dt in enumerate(steps):
                    if index == 0:
                        step_actions = replace(
                            actions,
                            pressed=self._pending_pressed,
                            mouse_clicked=self._pending_clicked,
                            look_yaw=self._pending_yaw,
                            look_pitch=self._pending_pitch,
                        )
                        self._pending_pressed = frozenset()
                        self._pending_clicked = False
                        self._pending_yaw = 0.0
                        self._pending_pitch = 0.0
                    else:
                        step_actions = replace(
                            actions.without_pressed(),
                            look_yaw=0.0,
                            look_pitch=0.0,
                        )
                    self.game.update(dt, step_actions)
                self._elapsed += sum(steps)
            self.renderer.render(self.scene, self._game_particles())
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
        self.renderer.render(self.scene, self._game_particles())
        canvas = self._draw_ui()
        pixels = self.renderer.read_pixels()
        if image_path is not None:
            from keystone.png import write_png

            write_png(image_path, self.renderer.width, self.renderer.height, pixels)
        if report_path is not None:
            from keystone.analysis import analyze_frame, write_report

            ui = describe_canvas(canvas, self.paused, self.overlay.visible) if canvas is not None else None
            system = self._game_particles()
            items = getattr(system, "particles", None) if system is not None else None
            alive = len(items) if isinstance(items, list) else 0
            stats = getattr(self.renderer, "last_stats", {})
            fx = {
                "alive": alive,
                "drawn": int(stats.get("sprites", 0)),
                "enabled": bool(int(stats.get("sprites_enabled", 1))),
            }
            report = analyze_frame(
                self.scene,
                pixels,
                self.renderer.width,
                self.renderer.height,
                image_path,
                ui=ui,
                fx=fx,
            )
            write_report(report_path, report)

    def screenshot(self, path: str | Path) -> None:
        self.capture(path)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        first_error: Exception | None = None
        if self.ui_renderer is not None:
            try:
                self.ui_renderer.release()
            except Exception as exc:  # noqa: BLE001 - cleanup must still close the context
                first_error = first_error or exc
        try:
            self.renderer.release()
        except Exception as exc:  # noqa: BLE001 - cleanup must still close the context
            first_error = first_error or exc
        try:
            self.context.close()
        except Exception as exc:  # noqa: BLE001 - surface the first cleanup failure
            first_error = first_error or exc
        if first_error is not None:
            raise first_error
