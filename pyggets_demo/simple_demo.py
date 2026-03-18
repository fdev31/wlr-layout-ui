#!/usr/bin/env python3
"""Minimal pyggets demo: title, text, a toggle, and a close button."""

import sys

sys.path.insert(0, "src")

import pyglet

from pyggets import (
    Button,
    Label,
    Rect,
    Style,
    Theme,
    Toggle,
    VBox,
    get_default_theme,
    makeRectangle,
    set_default_theme,
)

# Dark theme
set_default_theme(
    Theme(
        font_name="Free Sans",
        widget_radius=4,
        default_style=Style(
            text_color=(220, 220, 220, 255),
            color=(90, 90, 90),
            highlight=(100, 190, 130),
        ),
    )
)

# Build UI as a single VBox
ui = VBox(
    rect=Rect(20, 20, 0, 0),
    padding=8,
    widgets=[
        Label(Rect(0, 0, 360, 32), text="pyggets", font_size=22),
        Label(Rect(0, 0, 360, 20), text="A lightweight widget toolkit for pyglet."),
        Label(Rect(0, 0, 360, 20), text="No dependencies beyond pyglet itself."),
        Toggle(Rect(0, 0, 250, 28), label="Dark mode", toggled=True),
        Button(Rect(0, 0, 120, 32), "Close", action=pyglet.app.exit),
    ],
)


class SimpleDemo(pyglet.window.Window):
    def __init__(self):
        super().__init__(400, 250, "pyggets - Simple Demo", resizable=False)
        self.cursor = (0, 0)

    def on_draw(self):
        self.clear()
        style = get_default_theme().default_style
        bg = style.surface
        bg_rgba = (*bg[:3], 255) if len(bg) < 4 else bg
        makeRectangle(0, 0, self.width, self.height, color=bg_rgba).draw()
        ui.draw(self.cursor)

    def on_mouse_motion(self, x, y, dx, dy):
        self.cursor = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        ui.on_mouse_press(x, y, button, modifiers)


if __name__ == "__main__":
    SimpleDemo()
    pyglet.app.run()
