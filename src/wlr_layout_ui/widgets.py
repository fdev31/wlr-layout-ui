from dataclasses import dataclass

from pyglet.shapes import Triangle

from .settings import FONT, WIDGETS_RADIUS
from .utils import brighten, Rect
from .shapes import RoundedRectangle
from .factories import makeRectangle, makeLabel


class Widget:
    def __init__(self, rect, style):
        self.rect = rect
        self.style = style if style else Style()
        self.valign = "bottom"
        self.halign = "left"
        self.margin = 0

    def set_alignment(self, vert="center", horiz="center"):
        self.valign = vert
        self.halign = horiz

    def update_alignment(self, x, y, width, height):
        if self.halign == "center":
            self.rect.x = (width - self.rect.width) // 2
        elif self.halign == "right":
            self.rect.x = width - self.rect.width - self.margin
        elif self.halign == "left":
            self.rect.x = self.margin
        else:
            raise ValueError(f"Unknown horizontal alignment: {self.halign}")

        if self.valign == "center":
            self.rect.y = (height - self.rect.height) // 2
        elif self.valign == "top":
            self.rect.y = height - self.rect.height - self.margin
        elif self.valign == "bottom":
            self.rect.y = self.margin
        else:
            raise ValueError(f"Unknown vertical alignment: {self.valign}")

        self.rect.x += x
        self.rect.y += y

    def unfocus(self):
        return

    def draw(self, cursor):
        raise NotImplementedError()

    def draw_shadow(self, offX=3, offY=3, color=(0, 0, 0, 80), radius=0):
        r = RoundedRectangle(
            Rect(
                self.rect.x + offX,
                self.rect.y - offY,
                self.rect.width,
                self.rect.height,
            ),
            radius=radius,
            color=color,
        )
        r.draw()

    def contains(self, x, y):
        return self.rect.contains(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        return


class _Box(Widget):
    def __init__(self, rect=None, padding=4, widgets=[]):
        super().__init__(rect or Rect(0, 0, 0, 0), None)
        self.padding = padding
        self.rect.width = self.totalpadding
        self.rect.height = self.totalpadding
        self.widgets = []
        for w in widgets:
            self.add(w)

    def __repr__(self):
        return f"<Box = {self.widgets}>"

    @property
    def totalpadding(self):
        return self.padding * 2

    def unfocus(self):
        for w in self.widgets:
            w.unfocus()

    def on_mouse_press(self, x, y, button, modifiers):
        for w in self.widgets:
            if w.contains(x, y) and w.on_mouse_press(x, y, button, modifiers):
                return True

    def draw(self, cursor):
        self.draw_shadow(0, 0, (255, 255, 255, 80), radius=0)


class HBox(_Box):
    def add(self, widget):
        self.widgets.append(widget)
        if len(self.widgets) > 1:
            self.rect.width += self.padding
        self.rect.width += widget.rect.width
        self.rect.height = max(widget.rect.height + self.totalpadding, self.rect.height)

    def draw(self, cursor):
        super().draw(cursor)
        x_off = self.padding
        for i, w in enumerate(self.widgets):
            w.rect.y = self.rect.y + self.padding
            w.rect.x = self.rect.x + x_off
            x_off += w.rect.width + self.padding
            w.draw(cursor)


class VBox(_Box):
    def add(self, widget):
        self.widgets.append(widget)
        if len(self.widgets) > 1:
            self.rect.height += self.padding
        self.rect.height += widget.rect.height
        self.rect.width = max(widget.rect.width + self.totalpadding, self.rect.width)

    def draw(self, cursor):
        super().draw(cursor)
        y_off = self.padding
        for w in reversed(self.widgets):
            w.rect.x = self.rect.x + self.padding
            w.rect.y = self.rect.y + y_off
            y_off += w.rect.height + self.padding
            w.draw(cursor)


# }}}


@dataclass
class Style:
    text_color: tuple[int, int, int, int] = (50, 50, 50, 255)
    color: tuple[int, int, int] = (200, 200, 200)
    highlight: tuple[int, int, int] = (200, 255, 200)
    bold: bool = False


class Dropdown(Widget):  # {{{
    def __init__(self, rect, label, options, style=None, onchange=None, invert=False):
        super().__init__(rect, style)
        self.invert = invert
        self.options = options
        self.selected_index = 0
        self.expanded = False
        self.label = label
        self.onchange = onchange
        self.radius = WIDGETS_RADIUS

        # Dimensions
        self.triangle_size = int(rect.height * 0.5)

    def __repr__(self):
        return f"<Dropdown::{self.label} = {self.options}>"

    def contains(self, x, y):
        if self.expanded:
            if self.invert:
                return (
                    self.rect.x < x < self.rect.right
                    and self.rect.y + self.rect.height
                    < y
                    < self.rect.y + (self.rect.height * (len(self.options) + 1))
                )
            else:
                return (
                    self.rect.x < x < self.rect.right
                    and self.rect.y + self.rect.height
                    > y
                    > self.rect.y - (self.rect.height * (len(self.options) + 1))
                )
        else:
            return self.rect.contains(x, y)

    def get_triangle(self):
        triangle_x = self.rect.x + self.rect.width - self.triangle_size - 4
        show_down = self.expanded
        if self.invert:
            show_down = not show_down
        if not show_down:
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

        color = self.style.color

        is_hovered = self.rect.contains(*cursor)
        if is_hovered:
            color = brighten(color)

        r = RoundedRectangle(self.rect, self.radius, color)
        r.draw()
        rect = self.rect

        if self.expanded:
            makeRectangle(
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
        makeLabel(
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
                    option_y = self.rect.y + ((i + 1) * self.rect.height)
                else:
                    option_y = self.rect.y - (i + 1) * self.rect.height
                option_height = self.rect.height
                if x_match and option_y < cursor[1] < option_y + option_height:
                    color = self.style.highlight
                else:
                    color = self.style.color
                makeRectangle(
                    option_x, option_y, self.rect.width, option_height, color=color
                ).draw()

                label = option["name"]

                makeLabel(
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

        x_matches = self.rect.x < x < self.rect.x + self.rect.width
        if self.invert:
            y_matches = self.rect.y + menu_height + self.rect.height > y > self.rect.y
        else:
            y_matches = self.rect.y - menu_height < y < self.rect.y + self.rect.height
        if x_matches and y_matches:
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
                        option_y = self.rect.y + ((i + 1) * self.rect.height)
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


# }}}


class Button(Widget):  # {{{
    def __init__(
        self,
        rect,
        label,
        style=None,
        action=lambda: None,
        togglable=False,
        toggled_label=None,
    ):
        super().__init__(rect, style)
        self.action = action
        self.togglable = togglable
        self.toggled = False
        self.label = label
        self.radius = WIDGETS_RADIUS
        self.toggled_label = toggled_label

    def __repr__(self):
        return f"<Button {self.label}>"

    def draw(self, cursor):
        # Draw rounded borders using circles and rectangles
        rect = self.rect
        style = self.style
        self.text = makeLabel(
            self.toggled_label if self.toggled_label and self.toggled else self.label,
            x=rect.x + rect.width // 2,
            y=rect.y + rect.height // 2,
            anchor_x="center",
            anchor_y="center",
            color=style.text_color,
            bold=style.bold,
            font_name=FONT,
        )

        if self.togglable and self.toggled:
            color = list(style.highlight)
        else:
            color = list(style.color)

        if self.rect.contains(*cursor):
            color = brighten(color)

        r = RoundedRectangle(self.rect, self.radius, color)
        r.draw()
        self.text.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.action and self.rect.contains(x, y):
            self.toggled = not self.toggled
            self.action()
            return True


# }}}
