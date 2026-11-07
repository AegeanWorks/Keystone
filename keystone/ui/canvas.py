"""Screen-space 2D canvas built from clipped color quads and bitmap text."""

from __future__ import annotations

from dataclasses import dataclass

from keystone.ui.font import glyph, line_height, text_width

Color = tuple[float, float, float, float]
Quad = tuple[float, float, float, float, Color]


@dataclass(frozen=True, slots=True)
class TextElement:
    """One text draw call recorded for AI/UI reports."""

    text: str
    x: float
    y: float
    scale: int
    color: Color


@dataclass(frozen=True, slots=True)
class ButtonElement:
    """One interactive button recorded for AI/UI reports."""

    label: str
    action: str
    x: float
    y: float
    width: float
    height: float
    selected: bool
    hovered: bool


class Canvas:
    """Collects UI quads in top-left pixel coordinates and flattens them for GL."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("canvas width and height must be positive")
        self.width = width
        self.height = height
        self.quads: list[Quad] = []
        self.text_elements: list[TextElement] = []
        self.buttons: list[ButtonElement] = []

    @property
    def labels(self) -> list[str]:
        """Return the drawn text values in draw order."""
        return [element.text for element in self.text_elements]

    def _add(self, x: float, y: float, width: float, height: float, color: Color) -> None:
        left = max(0.0, x)
        top = max(0.0, y)
        right = min(float(self.width), x + width)
        bottom = min(float(self.height), y + height)
        if right > left and bottom > top:
            self.quads.append((left, top, right - left, bottom - top, color))

    def rect(self, x: float, y: float, width: float, height: float, color: Color) -> None:
        """Append an axis-aligned filled rectangle, clipped to the canvas."""
        if width <= 0 or height <= 0:
            raise ValueError("rectangle width and height must be positive")
        self._add(x, y, width, height, color)

    def text(self, x: float, y: float, text: str, color: Color, scale: int = 2) -> None:
        """Append bitmap text; lowercase is drawn as uppercase."""
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
            raise ValueError("text scale must be a positive integer")
        value = str(text).upper()
        self.text_elements.append(TextElement(value, x, y, scale, color))
        cursor = x
        for character in value:
            rows = glyph(character)
            for row_index, row in enumerate(rows):
                column = 0
                while column < len(row):
                    if row[column] != "#":
                        column += 1
                        continue
                    start = column
                    while column < len(row) and row[column] == "#":
                        column += 1
                    self._add(
                        cursor + start * scale,
                        y + row_index * scale,
                        (column - start) * scale,
                        scale,
                        color,
                    )
            cursor += text_width(character, scale) + scale

    def add_button(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str,
        action: str,
        selected: bool = False,
        hovered: bool = False,
    ) -> None:
        """Record button metadata; drawing stays with the widgets module."""
        if width > 0 and height > 0:
            self.buttons.append(
                ButtonElement(label.upper(), action, x, y, width, height, selected, hovered)
            )

    def vertices(self) -> list[float]:
        """Return interleaved x, y, r, g, b, a vertices for six triangles per quad."""
        values: list[float] = []
        for x, y, width, height, (red, green, blue, alpha) in self.quads:
            corners = ((x, y), (x + width, y), (x + width, y + height), (x, y), (x + width, y + height), (x, y + height))
            for corner_x, corner_y in corners:
                values.extend((corner_x, corner_y, red, green, blue, alpha))
        return values

    def measured_height(self, scale: int = 2) -> int:
        """Return the line height matching a text call at the same scale."""
        return line_height(scale)
