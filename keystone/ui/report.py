"""Serialize a rendered UI canvas into machine-readable report metadata."""

from __future__ import annotations

from keystone.ui.canvas import Canvas


def describe_canvas(canvas: Canvas, paused: bool, visible: bool) -> dict:
    """Return stable top-left pixel metadata for labels and buttons."""
    return {
        "visible": visible,
        "paused": paused,
        "labels": [
            {
                "text": element.text,
                "x": round(element.x, 2),
                "y": round(element.y, 2),
                "scale": element.scale,
                "color": [round(channel, 3) for channel in element.color],
            }
            for element in canvas.text_elements
        ],
        "buttons": [
            {
                "label": element.label,
                "action": element.action,
                "rect": [
                    round(element.x, 2),
                    round(element.y, 2),
                    round(element.width, 2),
                    round(element.height, 2),
                ],
                "selected": element.selected,
                "hovered": element.hovered,
            }
            for element in canvas.buttons
        ],
    }
