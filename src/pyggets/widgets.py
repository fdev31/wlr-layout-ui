"""Widget base class and concrete widgets for pyggets."""

import time

from pyglet.gl import GL_BLEND, GL_ONE_MINUS_SRC_ALPHA, GL_SCISSOR_TEST, GL_SRC_ALPHA, glBlendFunc, glDisable, glEnable, glScissor
from pyglet.shapes import Circle, Rectangle, Triangle
from pyglet.text import Label as PygletLabel

from .color import brighten
from .geometry import Rect
from .primitives import makeCircle, makeLabel, makeRectangle, makeSprite
from .shapes import RoundedRectangle, makeRoundedRectangle
from .theme import get_default_theme


class _TrackedProperty:
    """Descriptor that auto-calls ``invalidate()`` when a value changes.

    Usage::

        class MyWidget(Widget):
            checked = _TrackedProperty(default=False)

    Writing ``self.checked = True`` will store the value in the instance
    dict under ``_tp_checked`` and call ``self.invalidate()`` if the new
    value differs from the old one.
    """

    def __init__(self, default=None):
        self._default = default
        self._attr: str = ""  # set by __set_name__

    def __set_name__(self, owner, name):
        self._attr = f"_tp_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self._attr, self._default)

    def __set__(self, obj, value):
        old = getattr(obj, self._attr, self._default)
        if value != old:
            object.__setattr__(obj, self._attr, value)
            # Only call invalidate after __init__ has set up the flag
            if hasattr(obj, "_dirty"):
                obj.invalidate()


class _AnimatedFloat:
    """A float value that smoothly interpolates toward a target each frame.

    Create via :meth:`Widget._anim` inside ``__init__``.  Each call to
    :meth:`advance` moves the current value one frame closer to *target*
    using exponential ease-out (same formula as rect animation).

    Attributes:
        value: The current (interpolated) display value.
        target: The value to animate toward.
        snap: When ``abs(target - value) < snap``, snap to the target.
    """

    __slots__ = ("_speed", "snap", "target", "value")

    def __init__(self, initial, speed, snap=0.001):
        self.value = float(initial)
        self.target = float(initial)
        self.snap = snap
        self._speed = speed

    def advance(self):
        """Move *value* one frame toward *target*. Return True if still animating."""
        if abs(self.target - self.value) < self.snap:
            if self.value != self.target:
                self.value = self.target
                return True
            return False
        self.value = (self.value * self._speed + self.target) / (self._speed + 1)
        return True

    def snap_to(self, val):
        """Immediately set both *value* and *target* (skip animation)."""
        self.value = float(val)
        self.target = float(val)


class _AnimatedColor:
    """An RGB color tuple that smoothly interpolates toward a target each frame.

    Create via :meth:`Widget._anim_color` inside ``__init__``.  Per-channel
    interpolation with ``snap=0.5`` (sub-pixel precision for 0-255 values).

    Attributes:
        value: The current (interpolated) RGB tuple of floats.
        target: The RGB tuple to animate toward.
    """

    __slots__ = ("_speed", "target", "value")

    def __init__(self, initial, speed):
        self.value = tuple(float(c) for c in initial)
        self.target = tuple(float(c) for c in initial)
        self._speed = speed

    def advance(self):
        """Move *value* one frame toward *target*. Return True if still animating."""
        s = self._speed
        changed = False
        new = []
        for cv, tv in zip(self.value, self.target, strict=False):
            if abs(tv - cv) < 0.5:
                new.append(tv)
                if cv != tv:
                    changed = True
            else:
                new.append((cv * s + tv) / (s + 1))
                changed = True
        self.value = tuple(new)
        return changed

    @property
    def ints(self):
        """Return the current color as an integer RGB tuple for rendering."""
        return tuple(int(c) for c in self.value)


class Widget:
    """Base class for all pyggets widgets.

    Attributes:
        rect: Current position and size.
        target_rect: If set, the widget animates toward this rect each frame.
        style: Visual style (colors, weight).
        valign: Vertical alignment override for use inside HBox (None = use parent's align).
        halign: Horizontal alignment override for use inside VBox (None = use parent's align).
        fill: Fill mode for stretching inside containers.
              False = no fill; "both" = stretch on both axes;
              "width" = stretch horizontally; "height" = stretch vertically.
        margin: Margin used by update_alignment() for window-level positioning.
        focused: Whether the widget currently has keyboard focus.
        _dirty: Whether the widget needs to be re-rendered.
        _parent: The parent container widget, if any.
        _hovered: Whether the mouse cursor is currently over this widget.
        _animations: Registry of :class:`_AnimatedFloat` / :class:`_AnimatedColor`
            instances, keyed by name.
    """

    ANIMATION_SPEED = 8  # frames to approach target (higher = slower)

    def __init__(self, rect, style=None):
        self.rect = rect
        self.target_rect = None
        self._custom_style = style  # None means "use the active theme"
        self.valign = None
        self.halign = None
        self.fill: bool | str = False  # False, "both", "width", or "height"
        self.margin = 0
        self.focused = False
        self._dirty = True
        self._parent = None
        self._hovered = False
        self._animations: dict[str, _AnimatedFloat | _AnimatedColor] = {}

    @property
    def style(self):
        """Return the widget's style.

        If a custom style was set explicitly, it is returned unchanged.
        Otherwise the active theme's default style is used, so changing
        the theme at runtime is reflected immediately.
        """
        return self._custom_style if self._custom_style else get_default_theme().default_style

    @style.setter
    def style(self, value):
        """Set an explicit custom style, or ``None`` to follow the theme."""
        self._custom_style = value
        self.invalidate()

    def invalidate(self):
        """Mark this widget as needing a re-render.

        Also notifies the parent container so it can propagate the dirty
        flag up the widget tree.
        """
        self._dirty = True
        if self._parent is not None:
            self._parent.invalidate()

    def _update_hover(self, cursor):
        """Track hover state and auto-invalidate on change.

        Call this at the start of ``draw()`` to keep ``_hovered`` up to date.
        Returns the current hover state for convenience.
        """
        was = self._hovered
        self._hovered = self.rect.contains(*cursor)
        if was != self._hovered:
            self.invalidate()
        return self._hovered

    # -- Animation helpers --------------------------------------------------

    def _anim(self, name, initial, snap=0.001):
        """Register and return a new :class:`_AnimatedFloat`.

        Call in ``__init__`` to create a named scalar animation::

            self._expand = self._anim("expand", 0.0)

        The animation is automatically advanced by :meth:`_advance_animations`.
        """
        a = _AnimatedFloat(initial, speed=self.ANIMATION_SPEED, snap=snap)
        self._animations[name] = a
        return a

    def _anim_color(self, name, initial):
        """Register and return a new :class:`_AnimatedColor`.

        Call in ``__init__`` to create a named color animation::

            self._track_col = self._anim_color("track_col", style.color)

        The animation is automatically advanced by :meth:`_advance_animations`.
        """
        a = _AnimatedColor(initial, speed=self.ANIMATION_SPEED)
        self._animations[name] = a
        return a

    def _advance_animations(self):
        """Advance all registered animations one frame.

        Call at the top of ``draw()`` before reading animation values.
        Returns True if any animation is still in progress.
        """
        still_going = False
        for a in self._animations.values():
            if a.advance():
                still_going = True
        return still_going

    # -- Alignment -----------------------------------------------------------

    def set_alignment(self, vert="center", horiz="center"):
        """Set the widget's alignment within its parent."""
        self.valign = vert
        self.halign = horiz

    def update_alignment(self, x, y, width, height):
        """Update the widget's position based on its alignment settings.

        Used for top-level positioning within a window (called by gui.py on_resize).
        Defaults to bottom-left when valign/halign are None.
        """
        halign = self.halign or "left"
        valign = self.valign or "bottom"

        if halign == "center":
            self.rect.x = (width - self.rect.width) // 2
        elif halign == "right":
            self.rect.x = width - self.rect.width - self.margin
        elif halign == "left":
            self.rect.x = self.margin
        else:
            msg = f"Unknown horizontal alignment: {halign}"
            raise ValueError(msg)

        if valign == "center":
            self.rect.y = (height - self.rect.height) // 2
        elif valign == "top":
            self.rect.y = height - self.rect.height - self.margin
        elif valign == "bottom":
            self.rect.y = self.margin
        else:
            msg = f"Unknown vertical alignment: {valign}"
            raise ValueError(msg)

        self.rect.x += x
        self.rect.y += y

    def animate_to(self, x=None, y=None, width=None, height=None):
        """Set a target rect to animate toward.

        Only the provided attributes are changed; others keep their current target.
        """
        if self.target_rect is None:
            self.target_rect = self.rect.copy()
        if x is not None:
            self.target_rect.x = x
        if y is not None:
            self.target_rect.y = y
        if width is not None:
            self.target_rect.width = width
        if height is not None:
            self.target_rect.height = height

    def _animation_step(self):
        """Advance rect one frame toward target_rect.

        Uses exponential ease-out: each frame moves ~1/(speed+1) of remaining distance.
        Returns True if still animating.
        """
        if self.target_rect is None or self.rect == self.target_rect:
            return False
        s = self.ANIMATION_SPEED
        for var in ("x", "y", "width", "height"):
            cv = getattr(self.rect, var)
            tv = getattr(self.target_rect, var)
            if cv != tv:
                if abs(tv - cv) <= 1:
                    setattr(self.rect, var, tv)
                else:
                    tgt = (cv * s + tv) / (s + 1)
                    setattr(self.rect, var, int(min(tv, tgt) if cv < tv else max(tv, tgt)))
        return self.rect != self.target_rect

    def focus(self):
        """Called when the widget gains focus."""
        self.focused = False  # base class does not accept focus

    def unfocus(self):
        """Called when the widget loses focus."""
        self.focused = False

    def draw(self, cursor):
        """Draw the widget. Must be overridden by subclasses."""
        raise NotImplementedError

    def draw_shadow(self, offX=3, offY=3, color=None, radius=0):
        """Draw a shadow behind the widget.

        If *color* is None, falls back to ``self.style.shadow``.
        """
        if color is None:
            color = self.style.shadow
        r = makeRoundedRectangle(
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

    @staticmethod
    def draw_fade_overlay(x, y, width, height, bg_color, steps=8) -> None:
        """Draw a gradient overlay that fades text from visible to background color.

        Draws `steps` vertical strips from left (transparent) to right (opaque),
        creating a smooth fade-to-background effect for cropped text.

        Args:
            x: Left edge of the fade zone.
            y: Bottom edge of the fade zone.
            width: Width of the fade zone.
            height: Height of the fade zone.
            bg_color: The background color to fade into (RGB or RGBA tuple).
            steps: Number of gradient strips (more = smoother).
        """
        if width <= 0 or height <= 0:
            return
        r, g, b = bg_color[0], bg_color[1], bg_color[2]
        strip_w = width / steps
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for i in range(steps):
            alpha = int(255 * (i + 1) / steps)
            sx = x + strip_w * i
            makeRectangle(sx, y, strip_w + 1, height, color=(r, g, b, alpha)).draw()
        glDisable(GL_BLEND)

    def contains(self, x, y):
        """Return True if the point (x, y) is inside this widget."""
        return self.rect.contains(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        """Handle a mouse press event. Return True if handled."""
        return

    def on_mouse_drag(self, x, y, dx, dy):
        """Handle a mouse drag event. Return True if handled."""
        return

    def on_mouse_release(self, x, y):
        """Handle a mouse release event. Return True if handled."""
        return

    def on_mouse_scroll(self, x, y, dx, dy):
        """Handle a mouse scroll event. Return True if handled."""
        return

    def on_key_press(self, symbol, modifiers):
        """Handle a key press event. Return True if handled."""
        return

    def on_text(self, text):
        """Handle text input. Return True if handled."""
        return


class Dropdown(Widget):
    """A dropdown selector widget with expandable option list."""

    expanded = _TrackedProperty(default=False)
    selected_index = _TrackedProperty(default=0)

    def __init__(self, rect, label, options, style=None, onchange=None, invert=False):
        super().__init__(rect, style)
        self.invert = invert
        self.options = options
        self.selected_index = 0
        self.expanded = False
        self._expand = self._anim("expand", 0.0)
        self.label = label
        self.onchange = onchange
        self.radius = get_default_theme().widget_radius

        # Dimensions
        self.triangle_size = int(rect.height * 0.5)

    def __repr__(self):
        return f"<Dropdown::{self.label} = {self.options}>"

    def contains(self, x, y):
        if self.expanded:
            visible_h = self._expand.value * self.rect.height * len(self.options)
            if self.invert:
                return self.rect.x < x < self.rect.right and self.rect.y < y < self.rect.y + self.rect.height + visible_h
            else:
                return self.rect.x < x < self.rect.right and self.rect.y - visible_h < y < self.rect.y + self.rect.height
        else:
            return self.rect.contains(x, y)

    def get_triangle(self):
        """Build and return the triangle indicator shape."""
        triangle_x = self.rect.x + self.rect.width - self.triangle_size - 4
        show_down = self.expanded
        if self.invert:
            show_down = not show_down
        if not show_down:
            triangle_y = self.rect.y + (self.rect.height // 2) - int(0.5 * self.triangle_size)
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
        # Set animation targets and advance
        self._expand.target = 1.0 if self.expanded else 0.0
        self._advance_animations()

        color = self.style.color

        is_hovered = self.rect.contains(*cursor)
        if is_hovered:
            color = brighten(color)

        r = makeRoundedRectangle(self.rect, self.radius, color)
        r.draw()
        rect = self.rect

        if self._expand.value > 0:
            # Fill rounded corners at the junction between button and options
            if self.invert:
                # Options expand above: fill top corners of button
                makeRectangle(
                    rect.x,
                    rect.y + rect.height - self.radius,
                    rect.width,
                    self.radius,
                    color=color,
                ).draw()
            else:
                # Options expand below: fill bottom corners of button
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

        # Text area: from left padding to before the triangle indicator
        text_left = int(self.rect.x + 10)
        text_right = int(self.rect.x + self.rect.width - self.triangle_size - 8)
        text_w = text_right - text_left
        fade_w = min(20, text_w // 3)

        # Selected option label (scissor-clipped with fade)
        glEnable(GL_SCISSOR_TEST)
        glScissor(text_left, int(self.rect.y), text_w, int(self.rect.height))
        makeLabel(
            text,
            x=self.rect.x + 10,
            y=self.rect.y + self.rect.height // 2,
            anchor_x="left",
            anchor_y="center",
            color=self.style.text_color,
        ).draw()
        glDisable(GL_SCISSOR_TEST)

        # Fade overlay on the right edge of the text area
        if fade_w > 0:
            Widget.draw_fade_overlay(
                text_right - fade_w,
                int(self.rect.y),
                fade_w,
                int(self.rect.height),
                color,
            )

        # Triangle button
        if self.options:
            self.get_triangle().draw()

        x_match = self.rect.x < cursor[0] < self.rect.x + self.rect.width
        font_name = get_default_theme().font_name

        # Expanded options (drawn during expand AND collapse animation)
        if self._expand.value > 0:
            total_options_h = self.rect.height * len(self.options)
            visible_h = int(self._expand.value * total_options_h)

            # Compute reveal scissor region
            if self.invert:
                reveal_y = int(self.rect.y + self.rect.height)
                reveal_h = visible_h
            else:
                reveal_y = int(self.rect.y) - visible_h
                reveal_h = visible_h

            glEnable(GL_SCISSOR_TEST)
            glScissor(int(self.rect.x), reveal_y, int(self.rect.width), reveal_h)

            for i, option in enumerate(self.options):
                option_x = self.rect.x
                option_y = self.rect.y + (i + 1) * self.rect.height if self.invert else self.rect.y - (i + 1) * self.rect.height
                option_height = self.rect.height
                hovered = self.expanded and x_match and option_y < cursor[1] < option_y + option_height
                opt_color = self.style.highlight if hovered else self.style.dropdown_bg
                makeRectangle(option_x, option_y, self.rect.width, option_height, color=opt_color).draw()

                label = option["name"]
                text_color = self.style.on_accent if hovered else self.style.text_color

                # Intersect per-option text scissor with reveal scissor
                opt_sy = int(option_y)
                opt_sh = int(option_height)
                clip_y = max(opt_sy, reveal_y)
                clip_top = min(opt_sy + opt_sh, reveal_y + reveal_h)
                clip_h = max(0, clip_top - clip_y)
                glScissor(int(option_x), clip_y, int(self.rect.width), clip_h)
                makeLabel(
                    label,
                    x=option_x + 10,
                    y=option_y + option_height // 2,
                    color=text_color,
                    anchor_x="left",
                    anchor_y="center",
                    weight="bold" if i == self.selected_index else "normal",
                    font_name=font_name,
                ).draw()

                # Restore reveal scissor for next option background
                glScissor(int(self.rect.x), reveal_y, int(self.rect.width), reveal_h)

                # Fade overlay on right edge of option text
                opt_fade_right = int(option_x + self.rect.width)
                opt_fade_w = min(20, int(self.rect.width) // 3)
                if opt_fade_w > 0:
                    Widget.draw_fade_overlay(
                        opt_fade_right - opt_fade_w,
                        int(option_y),
                        opt_fade_w,
                        int(option_height),
                        opt_color,
                    )

            glDisable(GL_SCISSOR_TEST)

    def unfocus(self):
        self.expanded = False

    def on_mouse_press(self, x, y, button, modifiers):
        menu_height = 0
        if self.expanded:
            menu_height = self.rect.height * len(self.options)

        x_matches = self.rect.x < x < self.rect.x + self.rect.width
        if self.invert:
            y_matches = self.rect.y < y < self.rect.y + self.rect.height + menu_height
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
                for i, _option in enumerate(self.options):
                    option_y = self.rect.y + (i + 1) * self.rect.height if self.invert else self.rect.y - (i + 1) * self.rect.height
                    if option_y < y < option_y + self.rect.height:
                        self.selected_index = i
                        self.expanded = False
                        break
            if old_index != self.selected_index and self.onchange:
                self.onchange()
            return True

    def get_value(self):
        """Return the value of the currently selected option."""
        return self.get_selected_option()["value"]

    def get_selected_option(self):
        """Return the currently selected option dict."""
        return self.options[self.selected_index]

    def get_selected_index(self):
        """Return the index of the currently selected option."""
        return self.selected_index


class Spacer(Widget):
    """An empty space in the layout, with an optional label."""

    def __init__(self, rect, label="", style=None):
        super().__init__(rect, style)
        self.label = label

    def draw(self, cursor):
        if self.label:
            makeLabel(
                self.label,
                x=self.rect.x + self.rect.width // 2,
                y=self.rect.y + self.rect.height // 2,
                anchor_x="center",
                anchor_y="center",
                color=self.style.text_color,
            ).draw()

    def __repr__(self):
        return f"<Spacer {self.label}>"


class Image(Widget):
    """A widget that displays an image from a file path.

    The image is scaled to fit within the widget rect while preserving
    its aspect ratio, and centered within the available space.
    """

    def __init__(self, rect, path, style=None):
        super().__init__(rect, style)
        self.path = path

    def __repr__(self):
        return f"<Image {self.path!r}>"

    def draw(self, cursor):
        sprite = makeSprite(
            self.path,
            self.rect.x,
            self.rect.y,
            width=self.rect.width,
            height=self.rect.height,
        )
        # Center the scaled image within the rect
        actual_w = sprite.width
        actual_h = sprite.height
        sprite.x = self.rect.x + (self.rect.width - actual_w) // 2
        sprite.y = self.rect.y + (self.rect.height - actual_h) // 2
        sprite.draw()


class Button(Widget):
    """A clickable button widget with optional toggle behavior and icon."""

    def __init__(
        self,
        rect,
        label="",
        style=None,
        action=lambda: None,
        togglable=False,
        toggled_label=None,
        icon=None,
        icon_size=None,
    ):
        super().__init__(rect, style)
        self.action = action
        self.togglable = togglable
        self.toggled = False
        self.label = label
        self.radius = get_default_theme().widget_radius
        self.toggled_label = toggled_label
        self.icon = icon  # file path to icon image, or None
        self.icon_size = icon_size  # px, defaults to rect.height - 8

    def __repr__(self):
        return f"<Button {self.label}>"

    def draw(self, cursor):
        rect = self.rect
        style = self.style
        font_name = get_default_theme().font_name
        is_toggled = self.togglable and self.toggled
        text_color = style.on_accent if is_toggled else style.text_color

        color = list(style.highlight) if is_toggled else list(style.color)

        if self.rect.contains(*cursor):
            color = brighten(color)

        r = makeRoundedRectangle(self.rect, self.radius, tuple(color))
        r.draw()

        label_text = self.toggled_label if self.toggled_label and self.toggled else self.label
        icon_sz = self.icon_size or (rect.height - 8)
        icon_gap = 6  # gap between icon and text

        if self.icon and label_text:
            # Icon + text mode: icon on left, text on right, group centered
            icon_sprite = makeSprite(self.icon, 0, 0, width=icon_sz, height=icon_sz)
            actual_icon_w = icon_sprite.width
            actual_icon_h = icon_sprite.height

            # Create a label to measure text width
            text_label = makeLabel(
                label_text,
                x=0,
                y=0,
                anchor_x="left",
                anchor_y="center",
                color=text_color,
                weight=style.weight,
                font_name=font_name,
            )
            text_w = text_label.content_width

            total_w = actual_icon_w + icon_gap + text_w
            start_x = rect.x + (rect.width - total_w) // 2

            # Draw icon centered vertically
            icon_x = start_x
            icon_y = rect.y + (rect.height - actual_icon_h) // 2
            drawn_sprite = makeSprite(self.icon, icon_x, icon_y, width=icon_sz, height=icon_sz)
            drawn_sprite.x = icon_x
            drawn_sprite.y = icon_y
            drawn_sprite.draw()

            # Draw text
            self.text = makeLabel(
                label_text,
                x=start_x + actual_icon_w + icon_gap,
                y=rect.y + rect.height // 2,
                anchor_x="left",
                anchor_y="center",
                color=text_color,
                weight=style.weight,
                font_name=font_name,
            )
            self.text.draw()

        elif self.icon:
            # Icon only mode: centered in button
            icon_sprite = makeSprite(self.icon, 0, 0, width=icon_sz, height=icon_sz)
            actual_icon_w = icon_sprite.width
            actual_icon_h = icon_sprite.height
            icon_x = rect.x + (rect.width - actual_icon_w) // 2
            icon_y = rect.y + (rect.height - actual_icon_h) // 2
            drawn_sprite = makeSprite(self.icon, icon_x, icon_y, width=icon_sz, height=icon_sz)
            drawn_sprite.x = icon_x
            drawn_sprite.y = icon_y
            drawn_sprite.draw()

        else:
            # Text only mode (original behavior)
            self.text = makeLabel(
                label_text,
                x=rect.x + rect.width // 2,
                y=rect.y + rect.height // 2,
                anchor_x="center",
                anchor_y="center",
                color=text_color,
                weight=style.weight,
                font_name=font_name,
            )
            self.text.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.action and self.rect.contains(x, y):
            self.toggled = not self.toggled
            self.invalidate()
            self.action()
            return True


class Label(Widget):
    """A static text display widget."""

    def __init__(self, rect, text="", style=None, font_size=None, anchor_x="left", anchor_y="center", weight=None):
        super().__init__(rect, style)
        self.text = text
        self.font_size = font_size
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        self.weight = weight

    def __repr__(self):
        return f"<Label {self.text!r}>"

    def draw(self, cursor):
        if not self.text:
            return
        # Position label based on anchor
        if self.anchor_x == "center":
            x = self.rect.x + self.rect.width // 2
        elif self.anchor_x == "right":
            x = self.rect.x + self.rect.width
        else:
            x = self.rect.x

        if self.anchor_y == "center":
            y = self.rect.y + self.rect.height // 2
        elif self.anchor_y == "top":
            y = self.rect.y + self.rect.height
        else:
            y = self.rect.y

        kw = {}
        if self.font_size is not None:
            kw["font_size"] = self.font_size
        if "\n" in self.text:
            kw["multiline"] = True
            kw["width"] = int(self.rect.width)
        weight = self.weight if self.weight is not None else self.style.weight
        makeLabel(
            self.text,
            x=x,
            y=y,
            anchor_x=self.anchor_x,
            anchor_y=self.anchor_y,
            color=self.style.text_color,
            weight=weight,
            font_name=get_default_theme().font_name,
            **kw,
        ).draw()


class Separator(Widget):
    """A thin horizontal or vertical line divider."""

    def __init__(self, rect, orientation="horizontal", style=None, color=None):
        super().__init__(rect, style)
        self.orientation = orientation
        self.line_color = color

    def __repr__(self):
        return f"<Separator {self.orientation}>"

    def draw(self, cursor):
        color = self.line_color if self.line_color else self.style.text_color[:3]
        if self.orientation == "horizontal":
            y = self.rect.y + self.rect.height // 2
            makeRectangle(self.rect.x, y, self.rect.width, 1, color=color).draw()
        else:
            x = self.rect.x + self.rect.width // 2
            makeRectangle(x, self.rect.y, 1, self.rect.height, color=color).draw()


class Checkbox(Widget):
    """A toggle checkbox with an optional label."""

    checked = _TrackedProperty(default=False)

    def __init__(self, rect, label="", checked=False, style=None, onchange=None):
        super().__init__(rect, style)
        self.label = label
        self.checked = checked
        self.onchange = onchange
        self._box_size = min(rect.height, rect.width, 20)
        # Animation state
        self._check = self._anim("check", 1.0 if checked else 0.0)

        # Owned pyglet primitives for the animated check indicator
        self._check_shape = Rectangle(0, 0, 1, 1, color=self.style.highlight)
        self._label_shape = None
        if self.label:
            self._label_shape = PygletLabel(
                self.label,
                x=0,
                y=0,
                anchor_x="left",
                anchor_y="center",
                color=self.style.text_color,
                font_name=get_default_theme().font_name,
            )

    def __repr__(self):
        return f"<Checkbox {self.label!r} checked={self.checked}>"

    @property
    def _box_rect(self):
        """Return the Rect of the checkbox square."""
        return Rect(
            self.rect.x,
            self.rect.y + (self.rect.height - self._box_size) // 2,
            self._box_size,
            self._box_size,
        )

    def draw(self, cursor):
        box = self._box_rect
        is_hovered = self.rect.contains(*cursor)

        # Draw the box outline
        outline_color = brighten(self.style.color) if is_hovered else self.style.color
        makeRoundedRectangle(box, get_default_theme().widget_radius, outline_color).draw()

        # Animate check indicator scale (0.0 = hidden, 1.0 = full size)
        self._check.target = 1.0 if self.checked else 0.0
        self._advance_animations()

        # Draw check indicator (inner filled square, scaled by _check.value)
        if self._check.value > 0.01:
            full_margin = max(3, self._box_size // 5)
            # Invert t: margin shrinks from center as t grows
            margin = int(full_margin + (1.0 - self._check.value) * (self._box_size // 2 - full_margin))
            ix = box.x + margin
            iy = box.y + margin
            iw = box.width - 2 * margin
            ih = box.height - 2 * margin
            if iw > 0 and ih > 0:
                self._check_shape.x = ix
                self._check_shape.y = iy
                self._check_shape.width = iw
                self._check_shape.height = ih
                self._check_shape.color = self.style.highlight
                self._check_shape.draw()

        # Draw label
        if self._label_shape is not None:
            self._label_shape.x = box.x + self._box_size + 6
            self._label_shape.y = self.rect.y + self.rect.height // 2
            self._label_shape.color = self.style.text_color
            self._label_shape.font_name = get_default_theme().font_name
            self._label_shape.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.rect.contains(x, y):
            self.checked = not self.checked
            if self.onchange:
                self.onchange(self.checked)
            return True


class Toggle(Widget):
    """An on/off sliding toggle switch."""

    toggled = _TrackedProperty(default=False)

    def __init__(self, rect, label="", toggled=False, style=None, onchange=None):
        super().__init__(rect, style)
        self.label = label
        self.toggled = toggled
        self.onchange = onchange
        # Track dimensions derived from rect height
        self._track_height = max(rect.height * 2 // 3, 8)
        self._track_width = rect.height  # pill width matches height
        self._knob_radius = self._track_height // 2
        # Animation state
        self._knob = self._anim("knob", 1.0 if toggled else 0.0)
        self._track_col = self._anim_color(
            "track_col",
            self.style.highlight if toggled else self.style.color,
        )
        self._knob_col = self._anim_color(
            "knob_col",
            self.style.knob_color if toggled else (160, 160, 160),
        )

        # Owned pyglet primitives — created once, updated in-place each frame
        r = self._knob_radius
        init_color = self._track_col.ints
        self._track_left = Circle(0, 0, r, color=init_color)
        self._track_right = Circle(0, 0, r, color=init_color)
        self._track_fill = Rectangle(0, 0, max(1, self._track_width - 2 * r), self._track_height, color=init_color)
        knob_init = self._knob_col.ints
        self._knob_shape = Circle(0, 0, max(1, r - 2), color=knob_init)
        self._label_shape = None
        if self.label:
            self._label_shape = PygletLabel(
                self.label,
                x=0,
                y=0,
                anchor_x="left",
                anchor_y="center",
                color=self.style.text_color,
                font_name=get_default_theme().font_name,
            )

    def __repr__(self):
        return f"<Toggle {self.label!r} toggled={self.toggled}>"

    def draw(self, cursor):
        is_hovered = self.rect.contains(*cursor)
        track_y = self.rect.y + (self.rect.height - self._track_height) // 2

        # Set animation targets and advance all at once
        self._knob.target = 1.0 if self.toggled else 0.0
        self._track_col.target = self.style.highlight if self.toggled else self.style.color
        self._knob_col.target = self.style.knob_color if self.toggled else (160, 160, 160)
        self._advance_animations()

        track_color = self._track_col.ints
        if is_hovered:
            track_color = brighten(track_color)

        # Update track shapes in place
        r = self._knob_radius
        self._track_left.x = self.rect.x + r
        self._track_left.y = track_y + r
        self._track_left.color = track_color
        self._track_left.draw()

        self._track_right.x = self.rect.x + self._track_width - r
        self._track_right.y = track_y + r
        self._track_right.color = track_color
        self._track_right.draw()

        self._track_fill.x = self.rect.x + r
        self._track_fill.y = track_y
        self._track_fill.color = track_color
        self._track_fill.draw()

        # Knob — interpolate x between off and on positions
        knob_color = self._knob_col.ints
        off_x = self.rect.x + r
        on_x = self.rect.x + self._track_width - r
        knob_x = int(off_x + self._knob.value * (on_x - off_x))
        self._knob_shape.x = knob_x
        self._knob_shape.y = track_y + r
        self._knob_shape.color = knob_color
        self._knob_shape.draw()

        # Label
        if self._label_shape is not None:
            self._label_shape.x = self.rect.x + self._track_width + 6
            self._label_shape.y = self.rect.y + self.rect.height // 2
            self._label_shape.color = self.style.text_color
            self._label_shape.font_name = get_default_theme().font_name
            self._label_shape.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.rect.contains(x, y):
            self.toggled = not self.toggled
            if self.onchange:
                self.onchange(self.toggled)
            return True


class ProgressBar(Widget):
    """A non-interactive progress indicator."""

    def __init__(self, rect, value=0, max_value=100, style=None, show_text=False):
        super().__init__(rect, style)
        self.value = value
        self.max_value = max_value
        self.show_text = show_text
        self.radius = get_default_theme().widget_radius
        # Animation state
        self._ratio = self._anim("ratio", value / max_value if max_value else 0.0)

        # Owned primitives for the animated fill bar (avoids cache thrash)
        self._fill_rect = Rect(rect.x, rect.y, 1, rect.height)
        self._fill_shape = RoundedRectangle(self._fill_rect, self.radius, self.style.highlight)
        self._pct_label = None
        if self.show_text:
            self._pct_label = PygletLabel(
                "0%",
                x=0,
                y=0,
                anchor_x="center",
                anchor_y="center",
                color=self.style.on_accent,
                font_name=get_default_theme().font_name,
            )

    def __repr__(self):
        return f"<ProgressBar {self.value}/{self.max_value}>"

    def set_value(self, v):
        """Set the current progress value."""
        self.value = max(0, min(v, self.max_value))
        self.invalidate()

    def get_value(self):
        """Return the current progress value."""
        return self.value

    def draw(self, cursor):
        # Background track
        makeRoundedRectangle(self.rect, self.radius, self.style.color).draw()

        # Animate fill ratio
        self._ratio.target = min(self.value / self.max_value, 1.0) if self.max_value > 0 else 0.0
        self._advance_animations()

        # Filled portion — update owned shape in place
        if self._ratio.value > 0.005:
            fill_width = max(int(self.rect.width * self._ratio.value), self.radius * 2)
            self._fill_rect.x = self.rect.x
            self._fill_rect.y = self.rect.y
            self._fill_rect.width = fill_width
            self._fill_rect.height = self.rect.height
            self._fill_shape.color = tuple(self.style.highlight)
            self._fill_shape.draw()

        # Percentage text
        if self._pct_label is not None and self.max_value > 0:
            pct = int(100 * self.value / self.max_value)
            self._pct_label.text = f"{pct}%"
            self._pct_label.x = self.rect.x + self.rect.width // 2
            self._pct_label.y = self.rect.y + self.rect.height // 2
            self._pct_label.color = self.style.on_accent
            self._pct_label.font_name = get_default_theme().font_name
            self._pct_label.draw()


class RadioGroup(Widget):
    """A group of mutually exclusive radio buttons."""

    selected_index = _TrackedProperty(default=0)

    def __init__(self, rect, options, selected_index=0, style=None, onchange=None, orientation="vertical"):
        super().__init__(rect, style)
        self.options = list(options)  # list of str labels
        self.selected_index = selected_index
        self.onchange = onchange
        self.orientation = orientation
        if self.options:
            divisor = len(self.options) * 2 if orientation == "vertical" else 2
            self._radio_radius = min(rect.height // divisor, 8)
        else:
            self._radio_radius = 8
        # Animation state: per-option dot scale (0.0 = hidden, 1.0 = full)
        self._dots = [self._anim(f"dot_{i}", 1.0 if i == selected_index else 0.0) for i in range(len(self.options))]

    def __repr__(self):
        sel = self.options[self.selected_index] if self.options else None
        return f"<RadioGroup selected={sel!r}>"

    def get_value(self):
        """Return the label of the currently selected option."""
        return self.options[self.selected_index] if self.options else None

    def get_selected_index(self):
        """Return the index of the currently selected option."""
        return self.selected_index

    def _item_rects(self):
        """Yield (index, Rect) for each radio option."""
        if not self.options:
            return
        if self.orientation == "vertical":
            item_h = self.rect.height // len(self.options)
            for i in range(len(self.options)):
                # Top-to-bottom: first option at top
                y = self.rect.y + self.rect.height - (i + 1) * item_h
                yield i, Rect(self.rect.x, y, self.rect.width, item_h)
        else:
            item_w = self.rect.width // len(self.options)
            for i in range(len(self.options)):
                x = self.rect.x + i * item_w
                yield i, Rect(x, self.rect.y, item_w, self.rect.height)

    def draw(self, cursor):
        r = self._radio_radius
        font_name = get_default_theme().font_name

        # Set all dot targets, then advance all at once
        for i in range(len(self.options)):
            self._dots[i].target = 1.0 if i == self.selected_index else 0.0
        self._advance_animations()

        for i, item_rect in self._item_rects():
            cy = item_rect.y + item_rect.height // 2
            cx = item_rect.x + r + 2

            # Outer circle (outline)
            makeCircle(cx, cy, r, color=self.style.color).draw()

            # Inner circle (scaled by dot animation value)
            if self._dots[i].value > 0.01:
                inner_r = max(1, int((r - 3) * self._dots[i].value))
                makeCircle(cx, cy, inner_r, color=self.style.highlight).draw()

            # Label
            makeLabel(
                self.options[i],
                x=cx + r + 6,
                y=cy,
                anchor_x="left",
                anchor_y="center",
                color=self.style.text_color,
                font_name=font_name,
            ).draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if not self.rect.contains(x, y):
            return
        for i, item_rect in self._item_rects():
            if item_rect.contains(x, y):
                if i != self.selected_index:
                    self.selected_index = i
                    if self.onchange:
                        self.onchange(i)
                return True


class Slider(Widget):
    """A horizontal value slider with a draggable handle."""

    value = _TrackedProperty(default=50)
    _dragging = _TrackedProperty(default=False)

    def __init__(self, rect, min_val=0, max_val=100, value=50, style=None, onchange=None):
        super().__init__(rect, style)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.onchange = onchange
        self._dragging = False
        self._handle_radius = min(rect.height // 2, 8)
        self._track_height = max(rect.height // 4, 2)
        # Animation state
        self._display = self._anim("display", float(value), snap=0.5)

        # Owned pyglet primitives
        self._track_bg = Rectangle(0, 0, max(1, rect.width), self._track_height, color=self.style.color)
        self._track_fill_shape = Rectangle(0, 0, 1, self._track_height, color=self.style.highlight)
        self._handle_shape = Circle(0, 0, self._handle_radius, color=self.style.knob_color)

    def __repr__(self):
        return f"<Slider {self.value} [{self.min_val}-{self.max_val}]>"

    def get_value(self):
        """Return the current slider value."""
        return self.value

    def set_value(self, v):
        """Set the slider value, clamped to [min_val, max_val]."""
        self.value = max(self.min_val, min(v, self.max_val))

    def _value_to_x(self, value=None):
        """Convert a value to an x pixel position."""
        if value is None:
            value = self.value
        if self.max_val == self.min_val:
            return self.rect.x
        ratio = (value - self.min_val) / (self.max_val - self.min_val)
        usable = self.rect.width - 2 * self._handle_radius
        return int(self.rect.x + self._handle_radius + ratio * usable)

    def _x_to_value(self, x):
        """Convert an x pixel position to a value."""
        usable = self.rect.width - 2 * self._handle_radius
        if usable <= 0:
            return self.min_val
        clamped_x = max(self.rect.x + self._handle_radius, min(x, self.rect.x + self.rect.width - self._handle_radius))
        ratio = (clamped_x - self.rect.x - self._handle_radius) / usable
        return self.min_val + ratio * (self.max_val - self.min_val)

    def draw(self, cursor):
        track_y = self.rect.y + (self.rect.height - self._track_height) // 2
        handle_y = self.rect.y + self.rect.height // 2

        # Animate display value (snap immediately during drag)
        if self._dragging:
            self._display.snap_to(float(self.value))
        else:
            self._display.target = float(self.value)
            self._advance_animations()

        handle_x = self._value_to_x(self._display.value)

        # Background track
        self._track_bg.x = self.rect.x
        self._track_bg.y = track_y
        self._track_bg.width = self.rect.width
        self._track_bg.color = self.style.color
        self._track_bg.draw()

        # Filled portion (from left to handle)
        fill_w = handle_x - self.rect.x
        if fill_w > 0:
            self._track_fill_shape.x = self.rect.x
            self._track_fill_shape.y = track_y
            self._track_fill_shape.width = fill_w
            self._track_fill_shape.color = self.style.highlight
            self._track_fill_shape.draw()

        # Handle
        handle_color = brighten(self.style.highlight) if self._dragging else self.style.knob_color
        self._handle_shape.x = handle_x
        self._handle_shape.y = handle_y
        self._handle_shape.color = handle_color
        self._handle_shape.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.rect.contains(x, y):
            self._dragging = True
            self.value = self._x_to_value(x)
            if self.onchange:
                self.onchange(self.value)
            return True

    def on_mouse_drag(self, x, y, dx, dy):
        if self._dragging:
            self.value = self._x_to_value(x)
            if self.onchange:
                self.onchange(self.value)
            return True

    def on_mouse_release(self, x, y):
        if self._dragging:
            self._dragging = False
            return True


class Tooltip(Widget):
    """A hover tooltip that appears over a target widget after a delay."""

    def __init__(self, target, text, style=None, delay=0.5):
        # Tooltip has no meaningful rect of its own; it positions dynamically
        super().__init__(Rect(0, 0, 0, 0), style)
        self.target = target
        self.text = text
        self.delay = delay
        self._hover_start = 0.0
        self._was_hovering = False

    def __repr__(self):
        return f"<Tooltip {self.text!r}>"

    def contains(self, x, y):
        # Tooltip is not interactive
        return False

    def draw(self, cursor):
        is_hovering = self.target.rect.contains(*cursor)

        if is_hovering and not self._was_hovering:
            self._hover_start = time.time()
        self._was_hovering = is_hovering

        if not is_hovering:
            return

        elapsed = time.time() - self._hover_start
        if elapsed < self.delay:
            return

        # Draw tooltip near cursor
        font_name = get_default_theme().font_name
        padding = 4
        lines = self.text.split("\n")
        # Estimate text width roughly (8px per char is a reasonable approximation)
        est_width = max(len(line) for line in lines) * 8 + 2 * padding
        est_height = 20 * len(lines)

        tip_x = cursor[0] + 12
        tip_y = cursor[1] + 16

        bg_rect = Rect(tip_x, tip_y, est_width, est_height)
        # Dark background
        makeRoundedRectangle(bg_rect, 2, self.style.tooltip_bg).draw()

        # Derive tooltip text color from background luminance for readability
        tb = self.style.tooltip_bg
        tip_lum = 0.299 * tb[0] + 0.587 * tb[1] + 0.114 * tb[2]
        tip_text_color = (240, 240, 240, 255) if tip_lum < 128 else (20, 20, 20, 255)

        makeLabel(
            self.text,
            x=tip_x + padding,
            y=tip_y + est_height // 2,
            anchor_x="left",
            anchor_y="center",
            color=tip_text_color,
            font_name=font_name,
            multiline=True,
            width=est_width,
        ).draw()


# Key constants used by TextInput
_KEY_BACKSPACE = 65288
_KEY_RETURN = 65293
_KEY_ESCAPE = 65307


class TextInput(Widget):
    """A single-line text input field (minimal placeholder implementation)."""

    text = _TrackedProperty(default="")
    focused = _TrackedProperty(default=False)

    def __init__(self, rect, placeholder="", text="", style=None, onsubmit=None):
        super().__init__(rect, style)
        self.placeholder = placeholder
        self.text = text
        self.onsubmit = onsubmit
        self.radius = get_default_theme().widget_radius

    def __repr__(self):
        return f"<TextInput {self.text!r}>"

    def get_text(self):
        """Return the current text content."""
        return self.text

    def set_text(self, t):
        """Set the text content."""
        self.text = t

    def focus(self):
        """Accept focus -- TextInput is keyboard-interactive."""
        self.focused = True

    def unfocus(self):
        """Release focus."""
        self.focused = False

    def draw(self, cursor):
        is_hovered = self.rect.contains(*cursor)

        # Border color indicates focus state
        if self.focused:
            border_color = self.style.highlight
        elif is_hovered:
            border_color = brighten(self.style.color)
        else:
            border_color = self.style.color

        # Background
        makeRoundedRectangle(self.rect, self.radius, border_color).draw()
        # Inner background (creates a border effect)
        inner_margin = 2
        inner = Rect(
            self.rect.x + inner_margin,
            self.rect.y + inner_margin,
            self.rect.width - 2 * inner_margin,
            self.rect.height - 2 * inner_margin,
        )
        makeRoundedRectangle(inner, max(0, self.radius - 1), self.style.surface).draw()

        font_name = get_default_theme().font_name
        text_x = self.rect.x + 6
        text_y = self.rect.y + self.rect.height // 2

        if self.text or self.focused:
            display_text = self.text
            # Blinking cursor when focused
            if self.focused and int(time.time() * 2) % 2:
                display_text += "|"
            makeLabel(
                display_text,
                x=text_x,
                y=text_y,
                anchor_x="left",
                anchor_y="center",
                color=self.style.surface_text,
                font_name=font_name,
            ).draw()
        elif self.placeholder:
            # Dimmed placeholder
            makeLabel(
                self.placeholder,
                x=text_x,
                y=text_y,
                anchor_x="left",
                anchor_y="center",
                color=self.style.placeholder_text,
                font_name=font_name,
            ).draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.rect.contains(x, y):
            self.focus()
            return True

    def on_key_press(self, symbol, modifiers):
        if not self.focused:
            return
        if symbol == _KEY_BACKSPACE:
            self.text = self.text[:-1]
            return True
        if symbol == _KEY_RETURN:
            if self.onsubmit:
                self.onsubmit(self.text)
            return True
        if symbol == _KEY_ESCAPE:
            self.unfocus()
            return True

    def on_text(self, text):
        if not self.focused:
            return
        # Filter out control characters
        if text and ord(text[0]) >= 32:
            self.text += text
            return True
