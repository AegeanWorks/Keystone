"""Small immediate-mode UI widgets: panels and labelled buttons."""

from __future__ import annotations

from keystone.ui.canvas import Canvas, Color
from keystone.ui.font import line_height, truncate_text

BACKGROUND: Color = (0.035, 0.045, 0.065, 0.72)
ACCENT: Color = (1.0, 0.72, 0.25, 1.0)
TEXT: Color = (0.92, 0.94, 0.97, 1.0)
DIM: Color = (0.60, 0.66, 0.74, 1.0)
ALERT: Color = (1.0, 0.44, 0.38, 1.0)
HOVER: Color = (1.0, 0.72, 0.25, 0.24)
DARK_TEXT: Color = (0.05, 0.06, 0.08, 1.0)


def panel(canvas: Canvas, x: int, y: int, width: int, height: int, color: Color = BACKGROUND) -> None:
    """Draw a background panel; non-positive sizes are ignored."""
    if width > 0 and height > 0:
        canvas.rect(x, y, width, height, color)


def button(
    canvas: Canvas,
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    scale: int,
    selected: bool,
    hovered: bool,
) -> None:
    """Draw one menu button with selected and pointer-hover states."""
    if width <= 0 or height <= 0:
        return
    fill = ACCENT if selected else HOVER if hovered else (0.08, 0.10, 0.14, 0.85)
    panel(canvas, x, y, width, height, fill)
    if selected or hovered:
        canvas.rect(x, y, 2 * scale, height, ACCENT)
    color = DARK_TEXT if selected else TEXT
    text = truncate_text(label, width - 8 * scale, scale)
    canvas.text(x + 8 * scale, y + (height - line_height(scale)) // 2, text, color, scale)
