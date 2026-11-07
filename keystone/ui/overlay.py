"""Game-agnostic human overlay: HUD, controls help and pause menu."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from keystone.ui.canvas import Canvas
from keystone.ui.font import line_height, text_width, truncate_text
from keystone.ui.menu import PauseMenu
from keystone.ui.widgets import ACCENT, ALERT, DIM, TEXT, button, panel

SCALE = 2
MENU_WIDTH = 360


@dataclass(frozen=True, slots=True)
class HudState:
    """Presentation-only snapshot the overlay needs for one frame."""

    game: str
    status: str
    fps: float
    frame: int
    elapsed: float
    width: int
    height: int
    paused: bool = False
    pointer: tuple[float, float] | None = None
    draw_calls: int = 0
    triangles: int = 0
    shadow_calls: int = 0
    post_enabled: int = 0
    bloom_enabled: int = 0
    audio_voices: int = 0
    anim_clips: int = 0
    particles: int = 0
    sprites: int = 0
    culled: int = 0


class HumanOverlay:
    """Builds the pixel UI, pause menu and button hitboxes."""

    def __init__(self) -> None:
        self.visible = True
        self.menu = PauseMenu()
        self.hits: list[tuple[float, float, float, float, str]] = []

    def toggle(self) -> None:
        self.visible = not self.visible

    def hit_test(self, x: float, y: float) -> str | None:
        """Return the action of the button under the pointer, if any."""
        for left, top, width, height, action in self.hits:
            if left <= x < left + width and top <= y < top + height:
                return action
        return None

    def _menu(self, canvas: Canvas, state: HudState, scale: int, line: int) -> None:
        if state.width < 160 or state.height < 120:
            label = "PAUSED"
            canvas.text(
                max(0, (state.width - text_width(label, 1)) // 2),
                max(0, (state.height - line_height(1)) // 2),
                label,
                ALERT,
                1,
            )
            return
        margin = 12 if scale == SCALE else 6
        pad = 8 * scale
        width = max(1, min(state.width - 2 * margin, MENU_WIDTH if scale == SCALE else 300))
        title_scale = 4 if scale == SCALE else 2
        button_height = line + 8
        gap = 6 if scale == SCALE else 4
        menu_height = len(self.menu.items) * button_height + (len(self.menu.items) - 1) * gap
        hint_height = 20
        height = pad * 2 + line_height(title_scale) + 6 * scale + menu_height + 8 * scale + hint_height
        left = (state.width - width) // 2
        top = (state.height - height) // 2
        panel(canvas, left, top, width, height, (0.04, 0.025, 0.025, 0.88))
        canvas.text(left + pad, top + pad, "PAUSED", ALERT, title_scale)
        button_width = width - pad * 2
        button_y = top + pad + line_height(title_scale) + 6 * scale
        for index, item in enumerate(self.menu.items):
            y = button_y + index * (button_height + gap)
            hovered = (
                state.pointer is not None
                and left + pad <= state.pointer[0] < left + pad + button_width
                and y <= state.pointer[1] < y + button_height
            )
            button(canvas, left + pad, y, button_width, button_height, item.label, scale, index == self.menu.index, hovered)
            canvas.add_button(
                left + pad,
                y,
                button_width,
                button_height,
                item.label,
                item.action,
                index == self.menu.index,
                hovered,
            )
            self.hits.append((float(left + pad), float(y), float(button_width), float(button_height), item.action))
        hint_y = button_y + menu_height + 4 * scale
        canvas.text(left + pad, hint_y, "UP/DOWN OR W/S SELECT", DIM, 1)
        canvas.text(left + pad, hint_y + 9, "ENTER CONFIRM   CLICK CHOOSE", DIM, 1)

    def build(self, state: HudState, game_draw: Callable[[Canvas, HudState], None] | None = None) -> Canvas:
        canvas = Canvas(state.width, state.height)
        self.hits = []
        if not self.visible:
            return canvas
        if game_draw is not None:
            game_draw(canvas, state)
        scale = SCALE if state.width >= 620 and state.height >= 360 else 1
        line = 9 * scale
        margin = 12 if scale == SCALE else 6
        game = truncate_text(state.game or "game", state.width // 2, scale)
        status = truncate_text(state.status or "ready", state.width // 2, scale)
        left_width = max(
            1,
            min(
                state.width - 2 * margin,
                max(text_width("KEYSTONE", scale), text_width(game, scale), text_width(status, scale)) + 12 * scale,
            ),
        )
        left_height = line * 3 + 6 * scale
        panel(canvas, margin, margin, left_width, left_height)
        canvas.text(margin + 6 * scale, margin + 4 * scale, "KEYSTONE", ACCENT, scale)
        canvas.text(margin + 6 * scale, margin + 4 * scale + line, game, TEXT, scale)
        canvas.text(margin + 6 * scale, margin + 4 * scale + line * 2, status, DIM, scale)

        candidates = (
            (True, f"FPS {state.fps:.0f}" if state.fps > 0 else "FPS --"),
            (True, f"FRAME {state.frame}"),
            (True, f"TIME {state.elapsed:.1f}S"),
            (True, f"{state.width}X{state.height}"),
            (state.draw_calls != 0 or state.triangles != 0, f"DRAW {state.draw_calls} TRI {state.triangles}"),
            (state.shadow_calls != 0, f"SHADOW {state.shadow_calls} PASS"),
            (state.post_enabled != 0, "POST GRADE"),
            (state.bloom_enabled != 0, "BLOOM GLOW"),
            (state.audio_voices != 0, f"AUDIO {state.audio_voices} VOX"),
            (state.anim_clips != 0, f"ANIM {state.anim_clips} CLIP" if state.anim_clips != 1 else "ANIM 1 CLIP"),
            (state.particles != 0, f"FX {state.particles} LIVE"),
            (state.sprites != 0, f"SPRITE {state.sprites} DRAWN"),
            (state.culled != 0, f"CULL {state.culled} OFFSCREEN"),
        )
        values = [value for shown, value in candidates if shown]
        right_width = max(text_width(value, scale) for value in values) + 12 * scale
        right_height = line * len(values) + 6 * scale
        right_x = state.width - margin - right_width
        panel(canvas, right_x, margin, right_width, right_height)
        for index, value in enumerate(values):
            color = ACCENT if index == 0 else TEXT if index < 3 else DIM
            canvas.text(right_x + 6 * scale, margin + 4 * scale + line * index, value, color, scale)

        help_lines = (
            "WASD MOVE  MOUSE LOOK  E/Q UP/DOWN",
            "P PAUSE  H HIDE UI  F1 CURSOR  ESC QUIT",
        )
        if state.width >= 620:
            help_width = max(text_width(item, scale) for item in help_lines) + 12 * scale
            help_height = line * 2 + 6 * scale
            help_y = state.height - margin - help_height
            panel(canvas, margin, help_y, help_width, help_height)
            for index, item in enumerate(help_lines):
                canvas.text(margin + 6 * scale, help_y + 4 * scale + line * index, item, TEXT if index else DIM, scale)

        if state.paused:
            self._menu(canvas, state, scale, line)
        return canvas
