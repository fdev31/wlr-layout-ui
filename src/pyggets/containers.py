"""Layout container widgets for pyggets."""

from __future__ import annotations

import logging
from dataclasses import replace

import pyglet
from pyglet.gl import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    glBlendFunc,
    glClear,
    glClearColor,
    glDisable,
    glEnable,
    glViewport,
)
from pyglet.image import Texture
from pyglet.image.buffer import Framebuffer
from pyglet.math import Mat4

from .color import brighten
from .geometry import Rect
from .primitives import makeLabel, makeRectangle
from .shapes import makeRoundedRectangle
from .theme import get_default_theme
from .widgets import Widget, _TrackedProperty

_log = logging.getLogger(__name__)

_DEPTH_THRESHOLD = 2


# ---------------------------------------------------------------------------
# FBO surface cache
# ---------------------------------------------------------------------------


def _get_window():
    """Return the active pyglet Window (first in ``pyglet.app.windows``).

    Returns ``None`` if no window exists yet (e.g. during tests).
    """
    for w in pyglet.app.windows:
        return w
    return None


class _FBOCache:
    """Off-screen framebuffer cache for a container widget.

    Renders the container's children into a texture once while the subtree
    is clean, then blits the cached texture on subsequent frames to avoid
    redundant draw calls.

    Usage inside a container's ``draw()``::

        if self._fbo_cache.can_blit():
            self._fbo_cache.blit()
        else:
            self._fbo_cache.begin(self.rect)
            # ... draw children normally ...
            self._fbo_cache.end()
            self._fbo_cache.blit()

    The cache is invalidated (via :meth:`invalidate`) whenever the
    container's ``_dirty`` flag is set, or when the container's rect
    changes size.
    """

    __slots__ = ("_fbo", "_rect_snap", "_saved_proj", "_saved_viewport", "_tex", "_th", "_tw", "_valid")

    def __init__(self):
        self._fbo: Framebuffer | None = None
        self._tex: Texture | None = None
        self._tw = 0
        self._th = 0
        self._valid = False
        self._saved_proj = None
        self._saved_viewport = None
        # Snapshot of the container rect when we last rendered into the FBO.
        # If the rect moves (but doesn't resize), we just need to re-blit at
        # the new position — no re-render needed.
        self._rect_snap: tuple[int, int, int, int] | None = None

    # -- lifecycle --

    def _ensure(self, width: int, height: int) -> bool:
        """Ensure the FBO/texture exist at the required size.

        Returns True if a new FBO was allocated (caller must re-render).
        """
        w = max(1, int(width))
        h = max(1, int(height))
        if self._fbo is not None and self._tw == w and self._th == h:
            return False
        self._destroy()
        self._tex = Texture.create(w, h)
        self._fbo = Framebuffer()
        self._fbo.attach_texture(self._tex)
        if not self._fbo.is_complete:
            _log.warning("FBO incomplete (%dx%d), disabling cache", w, h)
            self._destroy()
            return False
        self._tw, self._th = w, h
        self._valid = False
        return True

    def _destroy(self):
        if self._fbo is not None:
            self._fbo.delete()
            self._fbo = None
        if self._tex is not None:
            self._tex.delete()
            self._tex = None
        self._tw = self._th = 0
        self._valid = False
        self._rect_snap = None

    def delete(self):
        """Release GL resources.  Safe to call multiple times."""
        self._destroy()

    # -- render cycle --

    def can_blit(self) -> bool:
        """Return True if the cached texture is still valid and can be blitted."""
        return self._valid and self._fbo is not None

    def invalidate(self):
        """Mark the cached surface as stale (needs re-render)."""
        self._valid = False

    def begin(self, rect: Rect) -> bool:
        """Begin rendering into the off-screen framebuffer.

        Sets up the FBO, viewport, and projection so that child widgets
        can draw at their normal absolute screen coordinates while the
        output goes into the FBO texture.

        Returns True if the FBO is ready; False if FBO setup failed
        (caller should fall back to direct rendering).
        """
        window = _get_window()
        if window is None:
            return False

        self._ensure(rect.width, rect.height)
        if self._fbo is None:
            return False

        # Save window state
        self._saved_proj = window.projection
        self._saved_viewport = window.viewport

        # Bind FBO
        self._fbo.bind()

        # Set viewport to FBO size
        glViewport(0, 0, self._tw, self._th)

        # Set projection so that absolute coords (rect.x .. rect.x+w,
        # rect.y .. rect.y+h) map into the FBO's (0,0)..(w,h) viewport.
        window.projection = Mat4.orthogonal_projection(
            float(rect.x),
            float(rect.x + rect.width),
            float(rect.y),
            float(rect.y + rect.height),
            -8192,
            8192,
        )

        # Clear to transparent
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT)

        self._rect_snap = (rect.x, rect.y, rect.width, rect.height)
        return True

    def end(self):
        """Finish rendering into the FBO and restore window state."""
        window = _get_window()
        if window is None:
            return

        self._fbo.unbind()

        # Restore window state
        window.projection = self._saved_proj
        vp = self._saved_viewport
        glViewport(int(vp[0]), int(vp[1]), int(vp[2]), int(vp[3]))

        self._valid = True

    def blit(self, rect: Rect | None = None):
        """Blit the cached texture to the screen at the container's position.

        If *rect* is provided, uses its x/y for the blit position (allows
        the container to move without re-rendering the FBO contents).
        """
        if self._tex is None or self._rect_snap is None:
            return
        if rect is not None:
            x, y = rect.x, rect.y
        else:
            x, y = self._rect_snap[0], self._rect_snap[1]

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._tex.blit(x, y)
        glDisable(GL_BLEND)


# -- Shared layout computation functions --
# These are used by HBox, VBox, and Panel to avoid duplicating layout logic.


def _layout_horizontal(widgets, container_rect, padding, totalpadding):
    """Compute horizontal (left-to-right) layout for *widgets* inside *container_rect*.

    Handles main-axis fill (width), cross-axis fill (height), and
    vertical alignment per child.
    """
    # Main-axis fill (width)
    fill_children = [w for w in widgets if w.fill in ("both", "width")]
    if fill_children:
        fixed_width = sum(w.rect.width for w in widgets if w not in fill_children)
        gap_space = padding * (len(widgets) - 1) if len(widgets) > 1 else 0
        remaining = container_rect.width - totalpadding - fixed_width - gap_space
        per_child = max(0, remaining // len(fill_children))
        for w in fill_children:
            w.rect.width = per_child

    x_off = padding
    for w in widgets:
        # Cross-axis fill (height)
        if w.fill in ("both", "height"):
            w.rect.height = container_rect.height - totalpadding

        child_align = getattr(w, "valign", None)
        if child_align == "top":
            w.rect.y = container_rect.y + container_rect.height - padding - w.rect.height
        elif child_align == "center":
            w.rect.y = container_rect.y + (container_rect.height - w.rect.height) // 2
        else:  # bottom (default)
            w.rect.y = container_rect.y + padding
        w.rect.x = container_rect.x + x_off
        x_off += w.rect.width + padding


def _layout_vertical(widgets, container_rect, padding, totalpadding):
    """Compute vertical (bottom-to-top) layout for *widgets* inside *container_rect*.

    Handles main-axis fill (height), cross-axis fill (width), and
    horizontal alignment per child.
    """
    # Main-axis fill (height)
    fill_children = [w for w in widgets if w.fill in ("both", "height")]
    if fill_children:
        fixed_height = sum(w.rect.height for w in widgets if w not in fill_children)
        gap_space = padding * (len(widgets) - 1) if len(widgets) > 1 else 0
        remaining = container_rect.height - totalpadding - fixed_height - gap_space
        per_child = max(0, remaining // len(fill_children))
        for w in fill_children:
            w.rect.height = per_child

    y_off = padding
    for w in reversed(widgets):
        # Cross-axis fill (width)
        if w.fill in ("both", "width"):
            w.rect.width = container_rect.width - totalpadding

        child_align = getattr(w, "halign", None)
        if child_align == "right":
            w.rect.x = container_rect.x + container_rect.width - padding - w.rect.width
        elif child_align == "center":
            w.rect.x = container_rect.x + (container_rect.width - w.rect.width) // 2
        else:  # left (default)
            w.rect.x = container_rect.x + padding
        w.rect.y = container_rect.y + y_off
        y_off += w.rect.height + padding


class _Box(Widget):
    """Abstract base class for box layout containers.

    Parameters:
        cached: If True, the container renders its children into an
            off-screen FBO and blits the cached texture on subsequent
            frames when the subtree is clean.  This can dramatically
            reduce GL draw calls for large, mostly-static widget trees.
    """

    def __init__(self, rect=None, padding=4, widgets=None, align=None, cached=False):
        if widgets is None:
            widgets = []
        super().__init__(rect or Rect(0, 0, 0, 0), None)
        self.padding = padding
        self.align = align
        self._depth = 0
        self._needs_layout = True
        self._cached = cached
        self._fbo_cache: _FBOCache | None = _FBOCache() if cached else None
        self.rect.width = self.totalpadding
        self.rect.height = self.totalpadding
        self.widgets = []
        for w in widgets:
            self.add(w)

    def add(self, widget):
        """Add a widget to the container. Subclasses must override."""
        msg = "Subclasses must implement add()"
        raise NotImplementedError(msg)

    def remove(self, widget):
        """Remove a widget from the container.

        Clears the widget's parent reference and marks the container
        as needing re-layout.  Does nothing if the widget is not a child.
        """
        if widget not in self.widgets:
            return
        self.widgets.remove(widget)
        widget._parent = None
        self._needs_layout = True
        self.invalidate()

    def __repr__(self):
        return f"<Box = {self.widgets}>"

    @property
    def totalpadding(self):
        """Return double the padding (for both sides)."""
        return self.padding * 2

    def invalidate(self):
        """Mark as dirty and needing re-layout."""
        self._needs_layout = True
        if self._fbo_cache is not None:
            self._fbo_cache.invalidate()
        super().invalidate()

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

    def layout(self):
        """Compute child positions.  Subclasses must override."""
        self._needs_layout = False

    def _subtree_animating(self):
        """Return True if any widget in this subtree has active animations."""
        if self._is_animating():
            return True
        for w in self.widgets:
            if isinstance(w, _Box):
                if w._subtree_animating():
                    return True
            elif w._is_animating():
                return True
        return False

    def _draw_contents(self, cursor):
        """Draw container background and children.

        Subclasses override this instead of :meth:`draw` so that the
        FBO caching layer in :meth:`draw` can wrap the entire output.
        """
        self.draw_shadow(0, 0, radius=0)
        if self._needs_layout:
            self.layout()
        for w in self.widgets:
            self._draw_child(w, cursor)

    def draw(self, cursor):
        fbo = self._fbo_cache
        if fbo is None:
            # No caching — draw directly (the old path).
            self._draw_contents(cursor)
            self._dirty = False
            return

        # --- FBO-cached path ---
        # Can we reuse the cached surface?
        if fbo.can_blit() and not self._dirty and not self._subtree_animating():
            fbo.blit(self.rect)
            return

        # Need to (re-)render into the FBO.
        if fbo.begin(self.rect):
            self._draw_contents(cursor)
            fbo.end()
            self._dirty = False
            fbo.blit(self.rect)
        else:
            # FBO setup failed — fall back to direct rendering.
            self._draw_contents(cursor)
            self._dirty = False

    def _register_child(self, widget):
        """Track nesting depth and parent reference for child widgets."""
        widget._parent = self
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
        self._needs_layout = True

    def layout(self):
        """Position children left-to-right with fill and alignment."""
        # Temporarily patch valign: child.valign takes priority, but fall back
        # to the container's align setting.
        saved_valigns = []
        for w in self.widgets:
            saved_valigns.append(w.valign)
            if w.valign is None and self.align is not None:
                w.valign = self.align
        _layout_horizontal(self.widgets, self.rect, self.padding, self.totalpadding)
        for w, saved in zip(self.widgets, saved_valigns, strict=True):
            w.valign = saved
        self._needs_layout = False


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
        self._needs_layout = True

    def layout(self):
        """Position children bottom-to-top with fill and alignment."""
        saved_haligns = []
        for w in self.widgets:
            saved_haligns.append(w.halign)
            if w.halign is None and self.align is not None:
                w.halign = self.align
        _layout_vertical(self.widgets, self.rect, self.padding, self.totalpadding)
        for w, saved in zip(self.widgets, saved_haligns, strict=True):
            w.halign = saved
        self._needs_layout = False


class Panel(_Box):
    """A titled container with a visible border.

    Behaves like a VBox or HBox depending on the orientation parameter,
    with an optional title drawn at the top.
    """

    def __init__(self, title="", padding=4, widgets=None, style=None, orientation="vertical", cached=False):
        self._title = title
        self._orientation = orientation
        self._title_height = 22 if title else 0
        super().__init__(padding=padding, widgets=widgets, cached=cached)
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
        self._needs_layout = True

    def _inner_layout_rect(self):
        """Return the Rect available for laying out children (inside borders)."""
        return Rect(
            self.rect.x,
            self.rect.y,
            self.rect.width,
            self.rect.height,
        )

    def layout(self):
        """Position children using the appropriate axis layout."""
        layout_rect = self._inner_layout_rect()
        if self._orientation == "vertical":
            # Panel vertical uses padding*2 for cross-axis (width) totalpadding,
            # but the full totalpadding (including title) for main-axis (height).
            _layout_vertical(self.widgets, layout_rect, self.padding, self.totalpadding)
        else:
            _layout_horizontal(self.widgets, layout_rect, self.padding, self.totalpadding)
        self._needs_layout = False

    def _draw_contents(self, cursor):
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

        # Layout if needed, then draw children
        if self._needs_layout:
            self.layout()
        for w in self.widgets:
            self._draw_child(w, cursor)


class ScrollBox(Widget):
    """A scrollable container (minimal placeholder implementation).

    Wraps a single content widget (typically a VBox) and clips rendering
    to the visible area. Scrolls via mouse wheel.
    """

    def __init__(self, rect, content=None, style=None):
        super().__init__(rect, style)
        self.content = content
        if content is not None:
            content._parent = self
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
            self.invalidate()
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

    _visible = _TrackedProperty(default=False)

    def __init__(self, rect, title="", content=None, style=None, on_close=None):
        super().__init__(rect, style)
        self.title = title
        self.content = content
        if content is not None:
            content._parent = self
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
