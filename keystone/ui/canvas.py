"""Screen-space 2D canvas built from clipped color quads and bitmap text."""

from __future__ import annotations

from keystone.ui.font import glyph, line_height, text_width

Color = tuple[float, float, float, float]
Quad = tuple[float, float, float, float, Color]


class Canvas:
    """Collects UI quads in top-left pixel coordinates and flattens them for GL."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("canvas width and height must be positive")
        self.width = width
        self.height = height
        self.quads: list[Quad] = []
        self.labels: list[str] = []

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
        if scale < 1:
            raise ValueError("text scale must be at least 1")
        value = str(text).upper()
        self.labels.append(value)
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
