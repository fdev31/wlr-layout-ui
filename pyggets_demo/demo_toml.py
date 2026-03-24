#!/usr/bin/env python3
"""TOML-driven demo application showcasing all pyggets widgets, one per page.

This is the declarative counterpart to demo.py: every page's widget tree is
defined in a TOML file under demo_pages/, while this Python file provides
navigation, event dispatch, and imperative controller logic.
"""

import sys

sys.path.insert(0, "src")


import pyglet

from pyggets import (
    Button,
    Dropdown,
    Modal,
    Rect,
    Style,
    Theme,
    Tooltip,
    get_default_theme,
    load_ui,
    makeLabel,
    makeRectangle,
    open_file,
    pick_directory,
    save_file,
    set_default_theme,
)

# -- Theme setup ---------------------------------------------------------
_DEMO_DARK = Theme(
    font_name="Free Sans",
    widget_radius=4,
    default_style=Style(
        text_color=(220, 220, 220, 255),
        color=(90, 90, 90),
        highlight=(100, 190, 130),
        dropdown_bg=(110, 110, 110),
    ),
)

THEMES = [
    {"name": "Demo Dark", "value": _DEMO_DARK},
    {"name": "Dark", "value": Theme.dark()},
    {"name": "High Contrast", "value": Theme.high_contrast()},
    {"name": "Light", "value": Theme.light()},
    {"name": "Light HC", "value": Theme.light_high_contrast()},
]

set_default_theme(_DEMO_DARK)


# -- Demo layout config --------------------------------------------------


class DemoLayout:
    """Central config for demo page layout -- replaces scattered constants."""

    NAV_HEIGHT = 40
    HEADER_HEIGHT = 40

    def __init__(self, window_w=800, window_h=600, padding=20):
        self.padding = padding
        self.update(window_w, window_h)

    def update(self, window_w, window_h):
        """Recompute derived values after a resize."""
        self.window_w = window_w
        self.window_h = window_h
        self.x = self.padding
        self.w = window_w - 2 * self.padding
        self.content_top = window_h - self.HEADER_HEIGHT - self.padding
        self.content_bottom = self.NAV_HEIGHT + self.padding


layout = DemoLayout()


# -- Status feedback line ------------------------------------------------
_status = {"text": "Interact with a widget to see feedback here"}


def set_status(msg):
    _status["text"] = msg


def get_status():
    return _status["text"]


# -- Drawing helper ------------------------------------------------------


def _draw_label(text, x, y, font_size=14, **kw: object):
    """Draw a transient label using the current theme's font and text color."""
    theme = get_default_theme()
    style = theme.default_style
    kw.setdefault("color", style.text_color)
    kw.setdefault("anchor_y", "center")
    makeLabel(
        text,
        x=x,
        y=y,
        font_name=theme.font_name,
        font_size=font_size,
        **kw,
    ).draw()


# -- DemoController (all page handler methods) ---------------------------


class DemoController:
    """Controller whose methods are auto-bound to TOML-loaded widgets."""

    def __init__(self):
        self.refs = {}

    # -- Button page --
    def on_btn_click(self):
        set_status("Button clicked!")

    def on_btn_toggle(self):
        btn = self.refs.get("btn_toggle")
        if btn:
            set_status(f"Toggle is now {'ON' if btn.toggled else 'OFF'}")

    def on_btn_bold(self):
        set_status("Bold button pressed!")

    # -- Checkbox page --
    def on_notifications(self, v):
        set_status(f"Notifications: {'ON' if v else 'OFF'}")

    def on_dark_mode(self, v):
        set_status(f"Dark mode: {'ON' if v else 'OFF'}")

    def on_auto_save(self, v):
        set_status(f"Auto-save: {'ON' if v else 'OFF'}")

    # -- Toggle page --
    def on_wifi(self, v):
        set_status(f"Wi-Fi: {'ON' if v else 'OFF'}")

    def on_bluetooth(self, v):
        set_status(f"Bluetooth: {'ON' if v else 'OFF'}")

    def on_airplane(self, v):
        set_status(f"Airplane: {'ON' if v else 'OFF'}")

    # -- Slider page --
    def on_slide(self, v):
        lbl = self.refs.get("value_label")
        if lbl:
            lbl.text = f"Value: {int(v)}"
        set_status(f"Slider value: {int(v)}")

    # -- ProgressBar page --
    def on_pb_slide(self, v):
        pb = self.refs.get("pb_dynamic")
        if pb:
            pb.set_value(v)
        set_status(f"Progress: {int(v)}%")

    # -- Dropdown page --
    def on_dropdown_fruit(self):
        dd = self.refs.get("dd_fruit")
        if dd:
            set_status(f"[{dd.get_selected_index()}] {dd.get_selected_option()['name']} = {dd.get_value()}")

    def on_dropdown_inverted(self):
        dd = self.refs.get("dd_inverted")
        if dd:
            set_status(f"[{dd.get_selected_index()}] {dd.get_selected_option()['name']} = {dd.get_value()}")

    # -- RadioGroup page --
    def on_rg_size(self, _i):
        rg = self.refs.get("rg_size")
        if rg:
            set_status(f"Size: {rg.get_value()}")

    def on_rg_color(self, _i):
        rg = self.refs.get("rg_color")
        if rg:
            set_status(f"Color: {rg.get_value()}")

    # -- TextInput page --
    def on_text_submit(self, text):
        lbl = self.refs.get("result_label")
        if lbl:
            lbl.text = f'Submitted: "{text}"'
        set_status(f"Text submitted: {text}")

    # -- Tooltip page --
    def on_tooltip_btn(self):
        set_status("Button with tooltip clicked!")

    def on_tooltip_btn2(self):
        set_status("Quick tooltip button clicked!")

    # -- Modal page --
    def on_open_modal(self):
        modal = self.refs.get("modal")
        modal_input = self.refs.get("modal_input")
        if modal:
            if modal_input:
                modal_input.set_text("")
                modal_input.focus()
            modal.show()
            set_status("Modal opened")

    def on_modal_submit(self, text):
        lbl = self.refs.get("modal_result")
        modal = self.refs.get("modal")
        if lbl:
            lbl.text = f'Modal submitted: "{text}"'
        set_status(f"Modal input: {text}")
        if modal:
            modal.hide()

    def on_modal_close(self):
        set_status("Modal dismissed")

    # -- File Dialog page --
    def on_open_file(self):
        paths = open_file(
            title="Open File",
            filters=[("Images", [(0, "*.png"), (0, "*.jpg"), (0, "*.gif")]), ("All files", [(0, "*")])],
        )
        lbl = self.refs.get("fd_result")
        if lbl:
            if paths:
                lbl.text = "Opened:\n" + "\n".join(paths)
            else:
                lbl.text = "Open cancelled."
        set_status(f"open_file -> {paths!r}")

    def on_save_file(self):
        path = save_file(
            title="Save File",
            current_name="untitled.txt",
            filters=[("Text files", [(0, "*.txt")]), ("All files", [(0, "*")])],
        )
        lbl = self.refs.get("fd_result")
        if lbl:
            lbl.text = f"Save: {path}" if path else "Save cancelled."
        set_status(f"save_file -> {path!r}")

    def on_pick_dir(self):
        path = pick_directory(title="Select Folder")
        lbl = self.refs.get("fd_result")
        if lbl:
            lbl.text = f"Directory: {path}" if path else "Pick cancelled."
        set_status(f"pick_directory -> {path!r}")

    # -- TOML Loader page --
    def on_name_submit(self, text):
        set_status(f"[TOML] Name submitted: {text}")

    def on_volume(self, value):
        set_status(f"[TOML] Volume: {int(value)}")

    def on_quality(self, index):
        names = ["Low", "Medium", "High"]
        set_status(f"[TOML] Quality: {names[index]}")

    def on_apply(self):
        set_status("[TOML] Settings applied!")

    def on_reset(self):
        set_status("[TOML] Settings reset!")


# -- Page registry -------------------------------------------------------
PAGES = [
    ("Button", "button.toml"),
    ("Label", "label.toml"),
    ("Image", "image.toml"),
    ("Dropdown", "dropdown.toml"),
    ("Checkbox", "checkbox.toml"),
    ("Toggle", "toggle.toml"),
    ("Slider", "slider.toml"),
    ("ProgressBar", "progressbar.toml"),
    ("RadioGroup", "radiogroup.toml"),
    ("Separator", "separator.toml"),
    ("TextInput", "textinput.toml"),
    ("Tooltip", "tooltip.toml"),
    ("Spacer", "spacer.toml"),
    ("Panel", "panel.toml"),
    ("ScrollBox", "scrollbox.toml"),
    ("Modal", "modal.toml"),
    ("HBox & VBox", "containers.toml"),
    ("TOML Loader", "loader.toml"),
    ("File Dialog", "filedialog.toml"),
]


# -- Demo Window ---------------------------------------------------------

ctrl = DemoController()


class DemoApp(pyglet.window.Window):
    def __init__(self):
        super().__init__(layout.window_w, layout.window_h, "pyggets Demo (TOML)", resizable=True, vsync=True)
        self.cursor_coords = (0, 0)
        self.page_index = 0
        self.page_widgets = []

        # Navigation buttons
        self.btn_prev = Button(Rect(20, 6, 80, 28), "< Prev", action=self.prev_page)
        self.btn_next = Button(Rect(layout.window_w - 100, 6, 80, 28), "Next >", action=self.next_page)

        # Theme switcher dropdown (centered in nav bar)
        self.theme_dropdown = Dropdown(
            Rect(0, 6, 160, 28),
            "Theme",
            list(THEMES),
            invert=True,
            onchange=self._on_theme_change,
        )
        self._center_theme_dropdown()

        self.load_page()

    def load_page(self):
        """Load the current page's widgets from TOML."""
        _name, filename = PAGES[self.page_index]
        result = load_ui(f"demo_pages/{filename}", ctrl)
        ctrl.refs = result.refs
        self.page_widgets = result.widgets

        # Position root widget(s) in the demo page content area
        L = layout
        for w in self.page_widgets:
            if isinstance(w, Tooltip):
                continue  # Tooltips don't need positioning
            h = max(w.rect.height, 20)
            w.rect.x = L.x
            w.rect.y = L.content_top - h

    def prev_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.load_page()

    def next_page(self):
        if self.page_index < len(PAGES) - 1:
            self.page_index += 1
            self.load_page()

    def _center_theme_dropdown(self):
        """Keep the theme dropdown horizontally centered in the nav bar."""
        self.theme_dropdown.rect.x = (layout.window_w - self.theme_dropdown.rect.width) // 2

    def _on_theme_change(self):
        """Apply the selected theme and reload the current page."""
        theme = THEMES[self.theme_dropdown.selected_index]["value"]
        set_default_theme(theme)
        self.load_page()
        set_status(f"Theme: {THEMES[self.theme_dropdown.selected_index]['name']}")

    # -- Event dispatch helpers --

    def _handle_modal(self, method, *args):
        """Dispatch to visible modal; return True if handled."""
        for w in self.page_widgets:
            if isinstance(w, Modal) and w.is_visible():
                getattr(w, method)(*args)
                return True
        return False

    def _dispatch(self, method, *args, reverse=False):
        """Call method on page widgets until one returns True."""
        widgets = reversed(self.page_widgets) if reverse else self.page_widgets
        return any(getattr(w, method)(*args) for w in widgets)

    # -- Event handlers --

    def on_resize(self, width, height):
        super().on_resize(width, height)
        layout.update(width, height)
        self.btn_next.rect.x = width - 100
        self._center_theme_dropdown()
        self.load_page()

    def on_draw(self):
        self.clear()
        cursor = self.cursor_coords
        L = layout
        style = get_default_theme().default_style

        # Background
        bg = style.surface
        bg_rgba = (bg[0], bg[1], bg[2], 255) if len(bg) < 4 else bg
        makeRectangle(0, 0, L.window_w, L.window_h, color=bg_rgba).draw()

        # Header
        page_name = PAGES[self.page_index][0]
        _draw_label(page_name, L.window_w // 2, L.window_h - 24, font_size=18, anchor_x="center", weight="bold")

        # Page counter
        _draw_label(f"{self.page_index + 1}/{len(PAGES)}", 115, 20, anchor_x="left")

        # Separator lines
        for sep_y in (L.NAV_HEIGHT, L.window_h - L.HEADER_HEIGHT):
            makeRectangle(0, sep_y, L.window_w, 1, color=style.color).draw()

        # Navigation buttons + theme dropdown
        self.btn_prev.draw(cursor)
        self.btn_next.draw(cursor)
        if not self.theme_dropdown.expanded and self.theme_dropdown._expand.value <= 0:
            self.theme_dropdown.draw(cursor)

        # Status bar
        status = get_status()
        if status:
            _draw_label(
                status,
                L.window_w // 2,
                L.NAV_HEIGHT + 10,
                font_size=13,
                anchor_x="center",
                anchor_y="bottom",
                color=(255, 255, 100, 255),
                weight="bold",
            )

        # Page widgets -- multi-pass draw
        modals = []
        overlays = []
        tooltips = []
        for w in self.page_widgets:
            if isinstance(w, Modal):
                modals.append(w)
            elif isinstance(w, Tooltip):
                tooltips.append(w)
            elif isinstance(w, Dropdown) and (w.expanded or w._expand.value > 0):
                overlays.append(w)
            else:
                w.draw(cursor)
        for w in overlays:
            w.draw(cursor)

        # Theme dropdown drawn after page widgets when expanded/collapsing
        if self.theme_dropdown.expanded or self.theme_dropdown._expand.value > 0:
            self.theme_dropdown.draw(cursor)

        for m in modals:
            m.draw(cursor)

        for t in tooltips:
            t.draw(cursor)

    def on_mouse_motion(self, x, y, dx, dy):
        self.cursor_coords = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if self._handle_modal("on_mouse_press", x, y, button, modifiers):
            return

        # Navigation
        if self.btn_prev.on_mouse_press(x, y, button, modifiers):
            return
        if self.btn_next.on_mouse_press(x, y, button, modifiers):
            return
        if self.theme_dropdown.on_mouse_press(x, y, button, modifiers):
            return

        # Page widgets (reverse order so last-drawn gets priority)
        active = None
        for w in reversed(self.page_widgets):
            if w.on_mouse_press(x, y, button, modifiers):
                active = w
                break

        # Unfocus all page widgets except the one that handled the click
        self.theme_dropdown.unfocus()
        for w in self.page_widgets:
            if w != active:
                w.unfocus()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.cursor_coords = (x, y)
        self._dispatch("on_mouse_drag", x, y, dx, dy)

    def on_mouse_release(self, x, y, button, modifiers):
        self._dispatch("on_mouse_release", x, y)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self._dispatch("on_mouse_scroll", x, y, scroll_x, scroll_y)

    def on_key_press(self, symbol, modifiers):
        if self._handle_modal("on_key_press", symbol, modifiers):
            return

        # Left/Right arrow keys for page navigation
        if symbol == pyglet.window.key.LEFT:
            self.prev_page()
            return
        if symbol == pyglet.window.key.RIGHT:
            self.next_page()
            return

        if not self._dispatch("on_key_press", symbol, modifiers):
            super().on_key_press(symbol, modifiers)

    def on_text(self, text):
        if self._handle_modal("on_text", text):
            return
        self._dispatch("on_text", text)


def main():
    DemoApp()
    pyglet.app.run()


if __name__ == "__main__":
    main()
