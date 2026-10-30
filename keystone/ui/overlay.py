"""Game-agnostic human overlay: HUD, controls help and pause banner."""

from __future__ import annotations

from dataclasses import dataclass

from keystone.ui.canvas import Canvas, Color
from keystone.ui.font import text_width

BACKGROUND: Color = (0.035, 0.045, 0.065, 0.72)
ACCENT: Color = (1.0, 0.72, 0.25, 1.0)
TEXT: Color = (0.92, 0.94, 0.97, 1.0)
DIM: Color = (0.60, 0.66, 0.74, 1.0)
ALERT: Color = (1.0, 0.44, 0.38, 1.0)

SCALE = 2


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


class HumanOverlay:
    """Builds the pixel UI and tracks whether the person hid it."""

    def __init__(self) -> None:
        self.visible = True

    def toggle(self) -> None:
        self.visible = not self.visible

    @staticmethod
    def _panel(canvas: Canvas, x: int, y: int, width: int, height: int, color: Color = BACKGROUND) -> None:
        canvas.rect(x, y, width, height, color)

    @staticmethod
    def _truncate(text: str, width: int, scale: int) -> str:
        if text_width(text, scale) <= width:
            return text
        limit = max(0, (width // (6 * scale)) - 1)
        return text[:limit]

    def build(self, state: HudState) -> Canvas:
        canvas = Canvas(state.width, state.height)
        if not self.visible:
            return canvas
        scale = SCALE if state.width >= 620 and state.height >= 360 else 1
        line = 9 * scale
        margin = 12 if scale == SCALE else 6
        game = self._truncate(state.game or "game", state.width // 2, scale)
        status = self._truncate(state.status or "ready", state.width // 2, scale)
        left_width = max(
            1,
            min(
                state.width - 2 * margin,
                max(text_width("KEYSTONE", scale), text_width(game, scale), text_width(status, scale)) + 12 * scale,
            ),
        )
        left_height = line * 3 + 6 * scale
        self._panel(canvas, margin, margin, left_width, left_height)
        canvas.text(margin + 6 * scale, margin + 4 * scale, "KEYSTONE", ACCENT, scale)
        canvas.text(margin + 6 * scale, margin + 4 * scale + line, game, TEXT, scale)
        canvas.text(margin + 6 * scale, margin + 4 * scale + line * 2, status, DIM, scale)

        values = (
            f"FPS {state.fps:.0f}" if state.fps > 0 else "FPS --",
            f"FRAME {state.frame}",
            f"TIME {state.elapsed:.1f}S",
            f"{state.width}X{state.height}",
        )
        right_width = max(text_width(value, scale) for value in values) + 12 * scale
        right_height = line * 4 + 6 * scale
        right_x = state.width - margin - right_width
        self._panel(canvas, right_x, margin, right_width, right_height)
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
            self._panel(canvas, margin, help_y, help_width, help_height)
            for index, item in enumerate(help_lines):
                canvas.text(margin + 6 * scale, help_y + 4 * scale + line * index, item, TEXT if index else DIM, scale)

        if state.paused:
            title_scale = 4 if scale == SCALE else 2
            hint = "PRESS P TO RESUME"
            banner_width = max(
                1,
                min(
                    state.width - 2 * margin,
                    max(text_width("PAUSED", title_scale), text_width(hint, scale)) + 8 * scale,
                ),
            )
            banner_height = (line * 4) + 4 * scale
            banner_x = (state.width - banner_width) // 2
            banner_y = (state.height - banner_height) // 2
            self._panel(canvas, banner_x, banner_y, banner_width, banner_height, (0.05, 0.02, 0.02, 0.82))
            canvas.text(banner_x + 6 * scale, banner_y + 4 * scale, "PAUSED", ALERT, title_scale)
            canvas.text(
                banner_x + 6 * scale,
                banner_y + 4 * scale + line * 2,
                hint,
                TEXT,
                scale,
            )
        return canvas
