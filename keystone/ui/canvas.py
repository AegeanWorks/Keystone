"""Screen-space 2D canvas built from clipped color quads and bitmap text."""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.texture import TextureData
from keystone.ui.font import glyph, line_height, text_width, truncate_text, wrap_text

Color = tuple[float, float, float, float]
Quad = tuple[float, float, float, float, Color]
WHITE: Color = (1.0, 1.0, 1.0, 1.0)


@dataclass(frozen=True, slots=True)
class TextElement:
    """One text draw call recorded for AI/UI reports."""

    text: str
    x: float
    y: float
    scale: int
    color: Color


@dataclass(frozen=True, slots=True)
class ImageElement:
    """One textured quad recorded for GL and AI/UI reports."""

    x: float
    y: float
    width: float
    height: float
    texture: TextureData
    color: Color
    u0: float
    v0: float
    u1: float
    v1: float


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
        self.images: list[ImageElement] = []
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

    def image(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        texture: TextureData,
        color: Color = WHITE,
        u0: float = 0.0,
        v0: float = 0.0,
        u1: float = 1.0,
        v1: float = 1.0,
    ) -> None:
        """Append a textured quad, clipped to the canvas with adjusted UVs."""
        if not isinstance(texture, TextureData):
            raise TypeError("image texture must be a TextureData")
        for label, value in (("x", x), ("y", y), ("width", width), ("height", height)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"image {label} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"image {label} must be finite")
        if width <= 0 or height <= 0:
            raise ValueError("image width and height must be positive")
        if (
            isinstance(color, (str, bytes))
            or not isinstance(color, (tuple, list))
            or len(color) != 4
        ):
            raise TypeError("image color must have four channels")
        channels = []
        for channel in color:
            if isinstance(channel, bool) or not isinstance(channel, (int, float)):
                raise TypeError("image color channels must be numbers")
            if not math.isfinite(channel):
                raise ValueError("image color channels must be finite")
            channels.append(float(channel))
        coords = []
        for label, value in (("u0", u0), ("v0", v0), ("u1", u1), ("v1", v1)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"image {label} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"image {label} must be finite")
            coords.append(float(value))
        left_u, top_v, right_u, bottom_v = coords
        if not (0.0 <= left_u < right_u <= 1.0 and 0.0 <= top_v < bottom_v <= 1.0):
            raise ValueError("image UVs must satisfy 0 <= u0 < u1 <= 1 and 0 <= v0 < v1 <= 1")
        left = max(0.0, x)
        top = max(0.0, y)
        right = min(float(self.width), x + width)
        bottom = min(float(self.height), y + height)
        if right <= left or bottom <= top:
            return
        u_span = right_u - left_u
        v_span = bottom_v - top_v
        self.images.append(
            ImageElement(
                left,
                top,
                right - left,
                bottom - top,
                texture,
                (channels[0], channels[1], channels[2], channels[3]),
                left_u + (left - x) / width * u_span,
                top_v + (top - y) / height * v_span,
                left_u + (right - x) / width * u_span,
                top_v + (bottom - y) / height * v_span,
            )
        )

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

    def text_width(self, text: str, scale: int = 2) -> int:
        """Pixel width of a text run at this canvas scale (shared font metric)."""
        return text_width(text, scale)

    def line_height(self, scale: int = 2) -> int:
        """Pixel height of one text line at this canvas scale."""
        return line_height(scale)

    def fit_text(self, text: str, width: float, scale: int = 2) -> str:
        """Trim text so it fits ``width`` pixels at this scale.

        Widgets and HUD rows use this instead of guessing: a label that cannot
        fit is cut at a glyph boundary rather than clipped mid-pixel.
        """
        return truncate_text(text, int(width), scale)

    def text_right(
        self,
        right: float,
        y: float,
        text: str,
        color: Color,
        scale: int = 2,
    ) -> None:
        """Append text whose right edge sits at ``right``."""
        self.text(right - text_width(text, scale), y, text, color, scale)

    def text_center(
        self,
        center: float,
        y: float,
        text: str,
        color: Color,
        scale: int = 2,
    ) -> None:
        """Append text horizontally centred on ``center``."""
        self.text(center - text_width(text, scale) / 2, y, text, color, scale)

    def paragraph(
        self,
        x: float,
        y: float,
        width: float,
        text: str,
        color: Color,
        scale: int = 2,
        line_gap: int = 0,
    ) -> int:
        """Draw wrapped text and return the height it consumed.

        A width of zero or less draws nothing, matching the layout widgets;
        explicit newlines and blank lines keep their spacing.
        """
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
            raise ValueError("text scale must be a positive integer")
        if isinstance(line_gap, bool) or not isinstance(line_gap, int) or line_gap < 0:
            raise ValueError("paragraph line gap must be a non-negative integer")
        if isinstance(width, bool) or not isinstance(width, (int, float)):
            raise TypeError("paragraph width must be a real number")
        if width <= 0:
            return 0
        lines = wrap_text(str(text), int(width), scale)
        step = line_height(scale) + line_gap
        for index, line in enumerate(lines):
            if line:
                self.text(x, y + index * step, line, color, scale)
        return len(lines) * line_height(scale) + max(0, len(lines) - 1) * line_gap

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
