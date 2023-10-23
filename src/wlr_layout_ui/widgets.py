from dataclasses import dataclass

import pyglet
from pyglet.shapes import Rectangle, Triangle
from pyglet.text import Label

from .settings import FONT, WIDGETS_RADIUS
from .utils import collidepoint, brighten
from .shapes import RoundedRectangle


@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def topleft(self):
        return (self.left, self.top)

    @property
    def topright(self):
        return (self.right, self.top)

    @property
    def bottomleft(self):
        return (self.left, self.bottom)

    @property
    def bottomright(self):
        return (self.right, self.bottom)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y + self.height

    @property
    def bottom(self):
        return self.y

    @property
    def center(self):
        return self.x + self.width // 2, self.y + self.height // 2

    def contains(self, x, y):
        return collidepoint(
            self.x, self.y, self.x + self.width, self.y + self.height, x, y
        )

    def collide(self, rect):
        # return true if the two rectangles are overlapping in any way
        if rect.left >= self.right:
            return False
        if rect.right <= self.left:
            return False
        if rect.top <= self.bottom:
            return False
        if rect.bottom >= self.top:
            return False
        return True

    def copy(self):
        return Rect(self.x, self.y, self.width, self.height)


@dataclass
class HBox:
    x: int
    y: int
    height: int
    padding: int = 4

    def add(self, width):
        r = Rect(self.x, self.y, width, self.height)
        self.x += width + self.padding
        return r


@dataclass
class VBox:
    x: int
    y: int
    width: int
    padding: int = 4

    def add(self, height):
        r = Rect(self.x, self.y, self.width, height)
        self.y -= height + self.padding
        return r


@dataclass
class Style:
    text_color: tuple[int, int, int, int] = (50, 50, 50, 255)
    color: tuple[int, int, int] = (200, 200, 200)
    highlight: tuple[int, int, int] = (200, 255, 200)
    bold: bool = False


class Dropdown:
    def __init__(
        self, rect, label, options, onchange=None, style=Style(), invert=False
    ):
        self.invert = invert
        self.options = options
        self.selected_index = 0
        self.expanded = False
        self.style = style
        self.label = label
        self.onchange = onchange
        self.rect = rect
        self.radius = WIDGETS_RADIUS

        # Dimensions
        self.triangle_size = int(rect.height * 0.5)

    def get_triangle(self):
        triangle_x = self.rect.x + self.rect.width - self.triangle_size - 4
        if not self.expanded:
            margin = self.rect.height - self.triangle_size
            triangle_y = (
                self.rect.y + (self.rect.height // 2) - int(0.5 * self.triangle_size)
            )
            return Triangle(
                triangle_x,
                triangle_y + self.triangle_size,
                triangle_x + self.triangle_size,
                triangle_y + self.triangle_size,
                triangle_x + self.triangle_size / 2,
                triangle_y,
                color=self.style.text_color,
            )
        else:
            margin = (self.rect.height - self.triangle_size) // 2
            triangle_y = self.rect.y + self.rect.height - margin
            return Triangle(
                triangle_x,
                triangle_y - self.triangle_size,
                triangle_x + self.triangle_size,
                triangle_y - self.triangle_size,
                triangle_x + self.triangle_size / 2,
                triangle_y,
                color=self.style.text_color,
            )

    def draw(self, cursor):
        # Dropdown box

        is_hovered = self.rect.contains(*cursor)

        color = list(self.style.color)

        if is_hovered:
            color = brighten(color)

        RoundedRectangle(self.rect, self.radius, color).draw()
        rect = self.rect

        if self.expanded:
            Rectangle(
                rect.x,
                rect.y,
                rect.width,
                self.radius,
                color=color,
            ).draw()

        if self.expanded:
            text = self.label + ":"
        elif not self.options or self.selected_index < 0:
            text = "No " + self.label
        else:
            text = self.options[self.selected_index]["name"]

        # Selected option
        Label(
            text,
            x=self.rect.x + 10,
            y=self.rect.y + self.rect.height // 2,
            anchor_x="left",
            anchor_y="center",
            color=self.style.text_color,
        ).draw()

        # Triangle button
        if self.options:
            self.get_triangle().draw()

        x_match = self.rect.x < cursor[0] < self.rect.x + self.rect.width

        # Expanded options
        if self.expanded:
            for i, option in enumerate(self.options):
                option_x = self.rect.x
                if self.invert:
                    option_y = self.rect.y + i * self.rect.height
                else:
                    option_y = self.rect.y - (i + 1) * self.rect.height
                option_height = self.rect.height
                if x_match and option_y < cursor[1] < option_y + option_height:
                    color = self.style.highlight
                else:
                    color = self.style.color
                Rectangle(
                    option_x, option_y, self.rect.width, option_height, color=color
                ).draw()

                label = option["name"]

                Label(
                    label,
                    x=option_x + 10,
                    y=option_y + option_height // 2,
                    color=self.style.text_color,
                    anchor_x="left",
                    anchor_y="center",
                    bold=i == self.selected_index,
                    font_name=FONT,
                ).draw()

    def unfocus(self):
        self.expanded = False

    def on_mouse_press(self, x, y, button, modifiers):
        # FIXME: inverted mode is probably broken
        menu_height = 0
        if self.expanded:
            menu_height = self.rect.height * (len(self.options) + 1)
        if self.invert:
            menu_height *= -1

        x_matches = self.rect.x < x < self.rect.x + self.rect.width
        if x_matches and self.rect.y - menu_height < y < self.rect.y + self.rect.height:
            if not self.options:
                self.expanded = False
                return True
            old_index = self.selected_index
            # Dropdown button clicked
            if self.rect.y < y < self.rect.y + self.rect.height:
                self.expanded = not self.expanded
            else:
                # Check which option is clicked
                for i, option in enumerate(self.options):
                    if self.invert:
                        option_y = self.rect.y + (i + 1) * self.rect.height
                    else:
                        option_y = self.rect.y - (i + 1) * self.rect.height
                    if option_y < y < option_y + self.rect.height:
                        self.selected_index = i
                        self.expanded = False
                        break
            if old_index != self.selected_index:
                if self.onchange:
                    self.onchange()
            return True

    def get_value(self):
        return self.get_selected_option()["value"]

    def get_selected_option(self):
        return self.options[self.selected_index]

    def get_selected_index(self):
        return self.selected_index


class Button:
    def __init__(
        self,
        rect,
        label,
        action=lambda: None,
        style=Style(),
        togglable=False,
        toggled_label=None,
    ):
        self.style = style
        self.action = action
        self.togglable = togglable
        self.toggled = False
        self.rect = rect
        self.style = style
        self.label = label
        self.radius = WIDGETS_RADIUS
        self.toggled_label = toggled_label

    @property
    def ex(self):
        return self.rect.x + self.rect.width

    @property
    def ey(self):
        return self.rect.y + self.rect.height

    def contains(self, x, y):
        return self.rect.x < x < self.ex and self.rect.y < y < self.ey

    def unfocus(self):
        return

    def draw(self, cursor):
        # Draw rounded borders using circles and rectangles
        rect = self.rect
        style = self.style
        self.text = Label(
            self.toggled_label if self.toggled_label and self.toggled else self.label,
            x=rect.x + rect.width // 2,
            y=rect.y + rect.height // 2,
            anchor_x="center",
            anchor_y="center",
            color=style.text_color,
            bold=style.bold,
            font_name=FONT,
        )
        contains = self.contains(*cursor)

        if self.togglable and self.toggled:
            color = list(style.highlight)
        else:
            color = list(style.color)

        if contains:
            color = brighten(color)

        RoundedRectangle(self.rect, self.radius, color).draw()
        self.text.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.action and self.contains(x, y):
            self.toggled = not self.toggled
            self.action()
            return True
