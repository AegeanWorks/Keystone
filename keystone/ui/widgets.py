"""Small immediate-mode UI widgets: panels, buttons and HUD layout rows.

Games write the same table, row, bar and badge code for every HUD. These
helpers measure text with the shared font metric and clamp every draw to the
canvas, so a row anchored to the right edge of a 390-pixel phone viewport and
one at 960x540 both stay visible instead of clipping mid-label.
"""

from __future__ import annotations

import math

from keystone.ui.canvas import Canvas, Color
from keystone.ui.font import line_height, text_width, truncate_text

BACKGROUND: Color = (0.035, 0.045, 0.065, 0.72)
ACCENT: Color = (1.0, 0.72, 0.25, 1.0)
TEXT: Color = (0.92, 0.94, 0.97, 1.0)
DIM: Color = (0.60, 0.66, 0.74, 1.0)
ALERT: Color = (1.0, 0.44, 0.38, 1.0)
HOVER: Color = (1.0, 0.72, 0.25, 0.24)
DARK_TEXT: Color = (0.05, 0.06, 0.08, 1.0)
TRACK: Color = (0.10, 0.12, 0.18, 0.9)


def _row_right(canvas: Canvas, x: float, width: float) -> float:
    """Right edge of a row, clamped to the canvas."""
    return min(x + width, float(canvas.width))


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


def label_row(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    label: str,
    value: str,
    scale: int = 2,
    label_color: Color = TEXT,
    value_color: Color = DIM,
) -> int:
    """Draw a label on the left and its value on the right of one row.

    The row never extends past the canvas edge: the value is trimmed to the
    row and the label is trimmed to whatever space the value leaves, so a
    HUD line cannot overlap or clip. Returns the row height in pixels.
    """
    if width <= 0 or x >= canvas.width:
        return 0
    right = _row_right(canvas, x, width)
    available = right - x
    gap = 2 * scale
    value_text = truncate_text(value, int(available), scale) if available > 0 else ""
    value_width = text_width(value_text, scale) if value_text else 0
    label_space = available - (value_width + gap if value_text else 0)
    label_text = truncate_text(label, int(label_space), scale) if label_space > 0 else ""
    if label_text:
        canvas.text(x, y, label_text, label_color, scale)
    if value_text:
        canvas.text(right - value_width, y, value_text, value_color, scale)
    return line_height(scale)


def table(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    rows: tuple[tuple[str, str], ...] | list[tuple[str, str]],
    scale: int = 2,
    gap: int = 4,
    label_color: Color = TEXT,
    value_color: Color = DIM,
) -> int:
    """Draw stacked label/value rows and return the total height used."""
    if isinstance(gap, bool) or not isinstance(gap, int) or gap < 0:
        raise ValueError("table gap must be a non-negative integer")
    step = line_height(scale) + gap
    cursor = y
    for label, value in rows:
        label_row(canvas, x, cursor, width, label, value, scale, label_color, value_color)
        cursor += step
    return max(0, len(rows) * step - gap)


def progress_bar(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    value: float,
    scale: int = 2,
    fill_color: Color = ACCENT,
    track_color: Color = TRACK,
) -> None:
    """Draw a horizontal bar filled to ``value`` (clamped to 0..1)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("progress value must be a finite number")
    if width <= 0 or height <= 0:
        return
    panel(canvas, x, y, width, height, track_color)
    filled = max(0.0, min(1.0, float(value))) * width
    if filled > 0.0:
        canvas.rect(x, y, filled, height, fill_color)


def badge(
    canvas: Canvas,
    x: float,
    y: float,
    label: str,
    scale: int = 2,
    color: Color = ACCENT,
    text_color: Color = DARK_TEXT,
) -> int:
    """Draw a small filled label capsule and return its measured width."""
    value = str(label).upper()
    padding = 2 * scale
    width = text_width(value, scale) + 2 * padding
    height = line_height(scale) + padding
    panel(canvas, x, y, width, height, color)
    canvas.text(x + padding, y + padding // 2, value, text_color, scale)
    return width
