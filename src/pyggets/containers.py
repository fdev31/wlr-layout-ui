"""Layout container widgets for pyggets."""

from dataclasses import replace

import pyglet

from .color import brighten
from .geometry import Rect
from .primitives import makeLabel, makeRectangle
from .shapes import makeRoundedRectangle
from .theme import get_default_theme
from .widgets import Widget

_DEPTH_THRESHOLD = 2


class _Box(Widget):
    """Abstract base class for box layout containers."""

    def __init__(self, rect=None, padding=4, widgets=None, align=None):
        if widgets is None:
            widgets = []
        super().__init__(rect or Rect(0, 0, 0, 0), None)
        self.padding = padding
        self.align = align
        self._depth = 0
        self.rect.width = self.totalpadding
        self.rect.height = self.totalpadding
        self.widgets = []
        for w in widgets:
            self.add(w)

    def add(self, widget):
        """Add a widget to the container. Subclasses must override."""
        msg = "Subclasses must implement add()"
        raise NotImplementedError(msg)

    def __repr__(self):
        return f"<Box = {self.widgets}>"

    @property
    def totalpadding(self):
        """Return double the padding (for both sides)."""
        return self.padding * 2

    def unfocus(self):
        for w in self.widgets:
            w.unfocus()

    def on_mouse_press(self, x, y, button, modifiers):
        for w in self.widgets:
            if w.contains(x, y) and w.on_mouse_press(x, y, button, modifiers):
                return True

    def on_mouse_drag(self, x, y, dx, dy):
        for w in self.widgets:
            if w.on_mouse_drag(x, y, dx, dy):
                return True

    def on_mouse_release(self, x, y):
        for w in self.widgets:
            if w.on_mouse_release(x, y):
                return True

    def on_mouse_scroll(self, x, y, dx, dy):
        for w in self.widgets:
            if w.contains(x, y) and w.on_mouse_scroll(x, y, dx, dy):
                return True

    def on_key_press(self, symbol, modifiers):
        for w in self.widgets:
            if w.focused and w.on_key_press(symbol, modifiers):
                return True

    def on_text(self, text):
        for w in self.widgets:
            if w.focused and w.on_text(text):
                return True

    def draw(self, cursor):
        self.draw_shadow(0, 0, radius=0)

    def _register_child(self, widget):
        """Track nesting depth for child boxes."""
        if isinstance(widget, _Box):
            widget._depth = self._depth + 1

    def _draw_child(self, w, cursor):
        """Draw a child widget, auto-inverting text color at high nesting depth."""
        saved = w._custom_style
        if self._depth >= _DEPTH_THRESHOLD and saved is None:
            tc = self.style.text_color
            lum = 0.299 * tc[0] + 0.587 * tc[1] + 0.114 * tc[2]
            if lum < 128:
                w._custom_style = replace(
                    self.style,
                    text_color=(255 - tc[0], 255 - tc[1], 255 - tc[2], tc[3]),
                )
        w.draw(cursor)
        w._custom_style = saved


class HBox(_Box):
    """Horizontal box layout container. Children are placed left-to-right."""

    def add(self, widget):
        """Add a widget to the right side of the box."""
        self.widgets.append(widget)
        self._register_child(widget)
        if len(self.widgets) > 1:
            self.rect.width += self.padding
        self.rect.width += widget.rect.width
        self.rect.height = max(widget.rect.height + self.totalpadding, self.rect.height)

    def draw(self, cursor):
        super().draw(cursor)

        # -- Fill logic (main axis = width, cross axis = height) --
        fill_children = [w for w in self.widgets if w.fill in ("both", "width")]
        if fill_children:
            fixed_width = sum(w.rect.width for w in self.widgets if w not in fill_children)
            gap_space = self.padding * (len(self.widgets) - 1) if len(self.widgets) > 1 else 0
            remaining = self.rect.width - self.totalpadding - fixed_width - gap_space
            per_child = max(0, remaining // len(fill_children))
            for w in fill_children:
                w.rect.width = per_child

        x_off = self.padding
        for _i, w in enumerate(self.widgets):
            # Cross-axis fill (height)
            if w.fill in ("both", "height"):
                w.rect.height = self.rect.height - self.totalpadding

            child_align = getattr(w, "valign", None) or self.align
            if child_align == "top":
                w.rect.y = self.rect.y + self.rect.height - self.padding - w.rect.height
            elif child_align == "center":
                w.rect.y = self.rect.y + (self.rect.height - w.rect.height) // 2
            else:  # bottom (default)
                w.rect.y = self.rect.y + self.padding
            w.rect.x = self.rect.x + x_off
            x_off += w.rect.width + self.padding
            self._draw_child(w, cursor)


class VBox(_Box):
    """Vertical box layout container. Children are placed bottom-to-top."""

    def add(self, widget):
        """Add a widget to the top of the box."""
        self.widgets.append(widget)
        self._register_child(widget)
        if len(self.widgets) > 1:
            self.rect.height += self.padding
        self.rect.height += widget.rect.height
        self.rect.width = max(widget.rect.width + self.totalpadding, self.rect.width)

    def draw(self, cursor):
        super().draw(cursor)

        # -- Fill logic (main axis = height, cross axis = width) --
        fill_children = [w for w in self.widgets if w.fill in ("both", "height")]
        if fill_children:
            fixed_height = sum(w.rect.height for w in self.widgets if w not in fill_children)
            gap_space = self.padding * (len(self.widgets) - 1) if len(self.widgets) > 1 else 0
            remaining = self.rect.height - self.totalpadding - fixed_height - gap_space
            per_child = max(0, remaining // len(fill_children))
            for w in fill_children:
                w.rect.height = per_child

        y_off = self.padding
        for w in reversed(self.widgets):
            # Cross-axis fill (width)
            if w.fill in ("both", "width"):
                w.rect.width = self.rect.width - self.totalpadding

            child_align = getattr(w, "halign", None) or self.align
            if child_align == "right":
                w.rect.x = self.rect.x + self.rect.width - self.padding - w.rect.width
            elif child_align == "center":
                w.rect.x = self.rect.x + (self.rect.width - w.rect.width) // 2
            else:  # left (default)
                w.rect.x = self.rect.x + self.padding
            w.rect.y = self.rect.y + y_off
            y_off += w.rect.height + self.padding
            self._draw_child(w, cursor)


class Panel(_Box):
    """A titled container with a visible border.

    Behaves like a VBox or HBox depending on the orientation parameter,
    with an optional title drawn at the top.
    """

    def __init__(self, title="", padding=4, widgets=None, style=None, orientation="vertical"):
        self._title = title
        self._orientation = orientation
        self._title_height = 22 if title else 0
        super().__init__(padding=padding, widgets=widgets)
        if style:
            self.style = style
        self.radius = get_default_theme().widget_radius

    @property
    def totalpadding(self):
        return self.padding * 2 + self._title_height

    def add(self, widget):
        """Add a widget to the panel."""
        self.widgets.append(widget)
        self._register_child(widget)
        if self._orientation == "vertical":
            if len(self.widgets) > 1:
                self.rect.height += self.padding
            self.rect.height += widget.rect.height
            self.rect.width = max(widget.rect.width + self.padding * 2, self.rect.width)
        else:
            if len(self.widgets) > 1:
                self.rect.width += self.padding
            self.rect.width += widget.rect.width
            self.rect.height = max(widget.rect.height + self.totalpadding, self.rect.height)

    def draw(self, cursor):
        # Bordered background
        is_hovered = self.rect.contains(*cursor)
        bg_color = brighten(self.style.color, 5) if is_hovered else self.style.color
        makeRoundedRectangle(self.rect, self.radius, bg_color).draw()

        # Inner area
        inner_margin = 2
        inner = Rect(
            self.rect.x + inner_margin,
            self.rect.y + inner_margin,
            self.rect.width - 2 * inner_margin,
            self.rect.height - 2 * inner_margin,
        )
        makeRoundedRectangle(inner, max(0, self.radius - 1), self.style.surface).draw()

        # Title
        if self._title:
            font_name = get_default_theme().font_name
            makeLabel(
                self._title,
                x=self.rect.x + self.padding + 2,
                y=self.rect.y + self.rect.height - self._title_height // 2 - self.padding,
                anchor_x="left",
                anchor_y="center",
                color=self.style.text_color,
                font_name=font_name,
            ).draw()

        # Children (same logic as VBox/HBox depending on orientation)
        if self._orientation == "vertical":
            # Fill logic (main axis = height, cross axis = width)
            fill_children = [w for w in self.widgets if w.fill in ("both", "height")]
            if fill_children:
                fixed_height = sum(w.rect.height for w in self.widgets if w not in fill_children)
                gap_space = self.padding * (len(self.widgets) - 1) if len(self.widgets) > 1 else 0
                remaining = self.rect.height - self.totalpadding - fixed_height - gap_space
                per_child = max(0, remaining // len(fill_children))
                for w in fill_children:
                    w.rect.height = per_child

            y_off = self.padding
            for w in reversed(self.widgets):
                # Cross-axis fill (width)
                if w.fill in ("both", "width"):
                    w.rect.width = self.rect.width - self.padding * 2
                w.rect.x = self.rect.x + self.padding
                w.rect.y = self.rect.y + y_off
                y_off += w.rect.height + self.padding
                self._draw_child(w, cursor)
        else:
            # Fill logic (main axis = width, cross axis = height)
            fill_children = [w for w in self.widgets if w.fill in ("both", "width")]
            if fill_children:
                fixed_width = sum(w.rect.width for w in self.widgets if w not in fill_children)
                gap_space = self.padding * (len(self.widgets) - 1) if len(self.widgets) > 1 else 0
                remaining = self.rect.width - self.padding * 2 - fixed_width - gap_space
                per_child = max(0, remaining // len(fill_children))
                for w in fill_children:
                    w.rect.width = per_child

            x_off = self.padding
            for w in self.widgets:
                # Cross-axis fill (height)
                if w.fill in ("both", "height"):
                    w.rect.height = self.rect.height - self.totalpadding
                w.rect.y = self.rect.y + self.padding
                w.rect.x = self.rect.x + x_off
                x_off += w.rect.width + self.padding
                self._draw_child(w, cursor)


class ScrollBox(Widget):
    """A scrollable container (minimal placeholder implementation).

    Wraps a single content widget (typically a VBox) and clips rendering
    to the visible area. Scrolls via mouse wheel.
    """

    def __init__(self, rect, content=None, style=None):
        super().__init__(rect, style)
        self.content = content
        self.scroll_offset = 0
        self._scroll_speed = 20
        self._scrollbar_width = 6

    def __repr__(self):
        return f"<ScrollBox offset={self.scroll_offset}>"

    @property
    def _max_scroll(self):
        if not self.content:
            return 0
        return max(0, self.content.rect.height - self.rect.height)

    def unfocus(self):
        if self.content:
            self.content.unfocus()

    def draw(self, cursor):
        if not self.content:
            return

        # Enable scissor clipping to our rect
        pyglet.gl.glEnable(pyglet.gl.GL_SCISSOR_TEST)
        pyglet.gl.glScissor(int(self.rect.x), int(self.rect.y), int(self.rect.width), int(self.rect.height))

        # Position content with scroll offset
        self.content.rect.x = self.rect.x
        self.content.rect.y = self.rect.y - self.scroll_offset
        # Stretch content to fill ScrollBox width (leave room for scrollbar)
        if self._max_scroll > 0:
            self.content.rect.width = self.rect.width - self._scrollbar_width
        else:
            self.content.rect.width = self.rect.width

        self.content.draw(cursor)

        pyglet.gl.glDisable(pyglet.gl.GL_SCISSOR_TEST)

        # Draw scrollbar indicator if content overflows
        if self._max_scroll > 0:
            bar_w = self._scrollbar_width - 2
            bar_height = max(20, int(self.rect.height * self.rect.height / self.content.rect.height))
            bar_y_range = self.rect.height - bar_height
            bar_y_ratio = self.scroll_offset / self._max_scroll if self._max_scroll else 0
            bar_y = self.rect.y + self.rect.height - bar_height - int(bar_y_ratio * bar_y_range)
            bar_x = self.rect.x + self.rect.width - self._scrollbar_width + 1
            makeRectangle(bar_x, bar_y, bar_w, bar_height, color=self.style.scrollbar).draw()

    def on_mouse_scroll(self, x, y, dx, dy):
        if self.rect.contains(x, y) and self._max_scroll > 0:
            self.scroll_offset = max(0, min(self.scroll_offset - int(dy * self._scroll_speed), self._max_scroll))
            return True

    def on_mouse_press(self, x, y, button, modifiers):
        if not self.rect.contains(x, y) or not self.content:
            return
        # Adjust y for scroll offset and pass through
        adjusted_y = y + self.scroll_offset
        return self.content.on_mouse_press(x, adjusted_y, button, modifiers)

    def on_key_press(self, symbol, modifiers):
        if self.content:
            return self.content.on_key_press(symbol, modifiers)

    def on_text(self, text):
        if self.content:
            return self.content.on_text(text)


class Modal(Widget):
    """An overlay dialog (minimal placeholder implementation).

    Draws a semi-transparent backdrop and a centered panel with content.
    Blocks interaction with background widgets.
    """

    def __init__(self, rect, title="", content=None, style=None, on_close=None):
        super().__init__(rect, style)
        self.title = title
        self.content = content
        self.on_close = on_close
        self._visible = False
        self.radius = get_default_theme().widget_radius
        self._title_height = 24 if title else 0
        self._padding = 8

    def __repr__(self):
        return f"<Modal {self.title!r} visible={self._visible}>"

    def show(self):
        """Make the modal visible."""
        self._visible = True

    def hide(self):
        """Hide the modal."""
        self._visible = False
        if self.content:
            self.content.unfocus()

    def is_visible(self):
        """Return whether the modal is currently visible."""
        return self._visible

    def _panel_rect(self):
        """Return the Rect of the centered dialog panel."""
        content_h = self.content.rect.height if self.content else 0
        content_w = self.content.rect.width if self.content else 0
        panel_w = max(content_w + 2 * self._padding, 200)
        panel_h = content_h + self._title_height + 2 * self._padding
        panel_x = self.rect.x + (self.rect.width - panel_w) // 2
        panel_y = self.rect.y + (self.rect.height - panel_h) // 2
        return Rect(panel_x, panel_y, panel_w, panel_h)

    def contains(self, x, y):
        # When visible, the modal captures all clicks
        return self._visible

    def draw(self, cursor):
        if not self._visible:
            return

        # Semi-transparent backdrop
        makeRectangle(self.rect.x, self.rect.y, self.rect.width, self.rect.height, color=self.style.backdrop).draw()

        panel = self._panel_rect()
        font_name = get_default_theme().font_name

        # Panel background
        makeRoundedRectangle(panel, self.radius, self.style.color).draw()

        # Title
        if self.title:
            makeLabel(
                self.title,
                x=panel.x + self._padding,
                y=panel.y + panel.height - self._title_height // 2 - 2,
                anchor_x="left",
                anchor_y="center",
                color=self.style.text_color,
                font_name=font_name,
                weight="bold",
            ).draw()
            # Separator line below title
            sep_y = panel.y + panel.height - self._title_height - 2
            makeRectangle(panel.x + 4, sep_y, panel.width - 8, 1, color=self.style.text_color[:3]).draw()

        # Content
        if self.content:
            self.content.rect.x = panel.x + self._padding
            self.content.rect.y = panel.y + self._padding
            self.content.draw(cursor)

    def on_mouse_press(self, x, y, button, modifiers):
        if not self._visible:
            return

        panel = self._panel_rect()
        if panel.contains(x, y):
            # Dispatch to content
            if self.content:
                return self.content.on_mouse_press(x, y, button, modifiers)
            return True
        else:
            # Click outside panel dismisses
            if self.on_close:
                self.on_close()
            self.hide()
            return True

    def on_key_press(self, symbol, modifiers):
        if not self._visible:
            return
        # Escape closes the modal
        if symbol == 65307:  # KEY_ESCAPE
            if self.on_close:
                self.on_close()
            self.hide()
            return True
        if self.content:
            return self.content.on_key_press(symbol, modifiers)

    def on_text(self, text):
        if not self._visible:
            return
        if self.content:
            return self.content.on_text(text)

    def unfocus(self):
        if self.content:
            self.content.unfocus()
