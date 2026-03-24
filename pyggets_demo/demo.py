#!/usr/bin/env python3
"""Demo application showcasing all pyggets widgets, one per page."""

import sys

sys.path.insert(0, "src")


import pyglet

from pyggets import (
    Button,
    Checkbox,
    Dropdown,
    HBox,
    Image,
    Label,
    Modal,
    Panel,
    ProgressBar,
    RadioGroup,
    Rect,
    ScrollBox,
    Separator,
    Slider,
    Spacer,
    Style,
    TextInput,
    Theme,
    Toggle,
    Tooltip,
    VBox,
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

    @property
    def gap(self):
        return self.padding // 2


layout = DemoLayout()


# -- Status feedback line ------------------------------------------------
_status = {"text": "Interact with a widget to see feedback here"}


def set_status(msg):
    _status["text"] = msg


def get_status():
    return _status["text"]


# -- Status helper factories (DRY: violations #5, #6, #7, #19) ----------


def _toggle_status(name, prefix=""):
    """Return an onchange callback for Toggle / checkbox-as-toggle widgets."""
    return lambda v: set_status(f"{prefix}{name}: {'ON' if v else 'OFF'}")


def _value_status(name, prefix=""):
    """Return an onchange callback that prints the raw value."""
    return lambda v: set_status(f"{prefix}{name}: {v}")


def _dropdown_status(dd):
    """Return an onchange callback that prints selected dropdown info."""
    return lambda: set_status(f"[{dd.get_selected_index()}] {dd.get_selected_option()['name']} = {dd.get_value()}")


# -- Page builder helpers (DRY: violations #1, #2, #3, #4, #16, #20) ----


class PageBuilder:
    """Eliminates per-page preamble boilerplate and manual y-positioning."""

    def __init__(self):
        self.L = layout
        self.gap = layout.gap
        self.y = layout.content_top

    def place(self, cls, w, h, **kw: object):
        """Create a widget at current y, advance downward."""
        widget = cls(Rect(self.L.x, self.y - h, w, h), **kw)
        self.y -= h + self.gap
        return widget

    def skip(self, height):
        """Skip extra vertical space."""
        self.y -= height

    def desc(self, text, height=None):
        """Add a description label. Auto-sizes height for multiline."""
        if height is None:
            height = max(24, 24 * text.count("\n") + 24)
        return self.place(Label, self.L.w, height, text=text)

    def result_label(self, text, height=24):
        """Create a label with deferred y (caller sets .rect.y later)."""
        return Label(Rect(self.L.x, 0, self.L.w, height), text=text)

    def finalize_label(self, lbl, height=None):
        """Set the deferred label's y to current position."""
        h = height or lbl.rect.height
        lbl.rect.y = self.y - h


def _make_buttons(labels, w=100, h=28):
    """Create a list of simple buttons with identical dimensions."""
    return [Button(Rect(0, 0, w, h), name) for name in labels]


def _fill_spacer(**kw: object):
    """Create a Spacer with fill='width'."""
    s = Spacer(Rect(0, 0, 10, 28), **kw)
    s.fill = "width"
    return s


def _scroll_items(n, width, text_fmt, fill=None):
    """Generate n Label widgets for a ScrollBox, optionally with fill."""
    items = [Label(Rect(0, 0, width, 24), text=text_fmt.format(i=i + 1)) for i in range(n)]
    if fill:
        for lbl in items:
            lbl.fill = fill
    return items


# -- Page builders -------------------------------------------------------
# Each returns a list of widgets that support draw(cursor) and event methods.


def tip(widget, text):
    """Return [widget, Tooltip] pair for inline use with *-unpacking."""
    return [widget, Tooltip(widget, text, delay=0.3)]


def page_image():
    """Page: Image"""
    pb = PageBuilder()
    L = pb.L

    pb.desc("Image widget loads a PNG and scales to fit, preserving aspect ratio.")

    # Large image
    lbl_large = pb.place(Label, 200, 20, text="200 x 150:", font_size=11)
    img_large = pb.place(Image, 200, 150, path="demo_assets/sample.png")

    # Row with smaller images side by side
    lbl_med = Label(Rect(L.x + 240, lbl_large.rect.y, 100, 20), text="64 x 64:", font_size=11)
    img_med = Image(Rect(L.x + 240, img_large.rect.y + (150 - 64), 64, 64), path="demo_assets/sample.png")

    lbl_icons = Label(Rect(L.x + 340, lbl_large.rect.y, 120, 20), text="Icons (24x24):", font_size=11)
    icon_y = img_large.rect.y + (150 - 24)
    img_folder = Image(Rect(L.x + 340, icon_y, 24, 24), path="demo_assets/folder.png")
    img_settings = Image(Rect(L.x + 374, icon_y, 24, 24), path="demo_assets/settings.png")
    img_star = Image(Rect(L.x + 408, icon_y, 24, 24), path="demo_assets/star.png")

    return [
        *tip(img_large, "Image(path='sample.png', 200x150)\nScaled to fit, aspect ratio preserved"),
        *tip(img_med, "Image(path='sample.png', 64x64)\nSame image, smaller target rect"),
        *tip(img_folder, "Image(path='folder.png', 24x24)\nFolder icon at native size"),
        lbl_large,
        lbl_med,
        lbl_icons,
        img_settings,
        img_star,
    ]


def page_button():
    """Page: Button"""
    pb = PageBuilder()

    btn1 = pb.place(Button, 160, 32, label="Click me", action=lambda: set_status("Button clicked!"))

    btn2 = pb.place(
        Button,
        160,
        32,
        label="Toggle me",
        togglable=True,
        toggled_label="Toggled ON",
        action=lambda: set_status(f"Toggle is now {'ON' if btn2.toggled else 'OFF'}"),
    )

    btn3 = pb.place(
        Button,
        200,
        32,
        label="Bold style",
        style=Style(
            text_color=(255, 255, 100, 255),
            color=(80, 60, 120),
            highlight=(140, 100, 200),
            weight="bold",
        ),
        action=lambda: set_status("Bold button pressed!"),
    )

    btn4 = pb.place(
        Button,
        200,
        32,
        label="Open Folder",
        icon="demo_assets/folder.png",
        action=lambda: set_status("Icon+text button clicked!"),
    )

    btn5 = pb.place(
        Button,
        40,
        40,
        icon="demo_assets/settings.png",
        action=lambda: set_status("Icon-only button clicked!"),
    )

    desc = pb.desc("Buttons support click actions, toggle mode, custom styles, and icons.")
    return [
        *tip(btn1, "Button(rect, 'Click me', action=...)\nRounded rect, brightens on hover"),
        *tip(btn2, "Button(togglable=True, toggled_label=...)\nAlternates label, green when toggled"),
        *tip(btn3, "Button(style=Style(weight='bold'))\nCustom purple/yellow bold text"),
        *tip(btn4, "Button(icon='folder.png', label='Open Folder')\nIcon on the left, text on the right"),
        *tip(btn5, "Button(icon='settings.png')\nIcon only, no text label"),
        desc,
    ]


def page_label():
    """Page: Label"""
    pb = PageBuilder()

    l1 = pb.place(Label, pb.L.w, 28, text="Left-anchored label (default)")
    l2 = pb.place(Label, pb.L.w, 28, text="Center-anchored label", anchor_x="center")
    l3 = pb.place(Label, pb.L.w, 28, text="Right-anchored label", anchor_x="right")
    l4 = pb.place(Label, pb.L.w, 36, text="Large font (20pt)", font_size=20)
    l5 = pb.place(Label, pb.L.w, 24, text="Small font (10pt)", font_size=10)
    return [
        *tip(l1, "Label(anchor_x='left')\nDefault left-aligned text"),
        *tip(l2, "Label(anchor_x='center')\nText centered in rect width"),
        *tip(l3, "Label(anchor_x='right')\nText right-aligned in rect"),
        *tip(l4, "Label(font_size=20)\nLarger 20pt text"),
        *tip(l5, "Label(font_size=10)\nSmaller 10pt text"),
    ]


def page_dropdown():
    """Page: Dropdown"""
    pb = PageBuilder()
    options = [
        {"name": "Apple", "value": "apple"},
        {"name": "Banana", "value": "banana"},
        {"name": "Cherry", "value": "cherry"},
        {"name": "Date", "value": "date"},
    ]

    desc = pb.desc("Normal dropdown (expands down) and inverted (expands up)")

    dd1 = pb.place(Dropdown, 200, 28, label="Fruit", options=list(options))
    dd1.onchange = _dropdown_status(dd1)

    # Leave room for dd1 to expand down before placing the inverted one
    pb.skip(100)

    dd2 = pb.place(Dropdown, 200, 28, label="Inverted", options=list(options), invert=True)
    dd2.onchange = _dropdown_status(dd2)

    return [
        *tip(dd1, "Dropdown('Fruit', options=[...], onchange=...)\nExpands option list downward on click"),
        *tip(dd2, "Dropdown('Inverted', invert=True)\nExpands option list upward on click"),
        desc,
    ]


def page_checkbox():
    """Page: Checkbox"""
    pb = PageBuilder()

    cb1 = pb.place(Checkbox, 250, 28, label="Enable notifications", onchange=_value_status("Notifications"))
    cb2 = pb.place(Checkbox, 250, 28, label="Dark mode", checked=True, onchange=_value_status("Dark mode"))
    cb3 = pb.place(Checkbox, 250, 28, label="Auto-save", onchange=_value_status("Auto-save"))
    return [
        *tip(cb1, "Checkbox(label=..., onchange=...)\nBox with inner fill when checked"),
        *tip(cb2, "Checkbox(checked=True)\nStarts checked, inner square visible"),
        *tip(cb3, "Checkbox(label='Auto-save')\nUnchecked box, click to toggle"),
    ]


def page_toggle():
    """Page: Toggle"""
    pb = PageBuilder()

    t1 = pb.place(Toggle, 250, 28, label="Wi-Fi", toggled=True, onchange=_toggle_status("Wi-Fi"))
    t2 = pb.place(Toggle, 250, 28, label="Bluetooth", onchange=_toggle_status("Bluetooth"))
    t3 = pb.place(Toggle, 250, 28, label="Airplane mode", onchange=_toggle_status("Airplane"))
    return [
        *tip(t1, "Toggle(toggled=True, onchange=...)\nPill track with knob on right, green"),
        *tip(t2, "Toggle(label='Bluetooth')\nGrey pill track, knob on left"),
        *tip(t3, "Toggle(label='Airplane mode')\nSame as above, independent state"),
    ]


def page_slider():
    """Page: Slider"""
    pb = PageBuilder()

    value_label = Label(Rect(pb.L.x + 420, pb.y - 28, 120, 28), text="Value: 50")

    def on_slide(v):
        value_label.text = f"Value: {int(v)}"
        set_status(f"Slider value: {int(v)}")

    s1 = pb.place(Slider, 400, 28, min_val=0, max_val=100, value=50, onchange=on_slide)

    s2 = pb.place(
        Slider,
        400,
        28,
        min_val=-50,
        max_val=50,
        value=0,
        style=Style(
            text_color=(220, 220, 220, 255),
            color=(70, 70, 70),
            highlight=(200, 100, 100),
        ),
    )

    desc = pb.desc("Drag the handle to change the value. Second slider has custom red style.")
    return [
        *tip(s1, "Slider(0..100, value=50, onchange=...)\nTrack with draggable white circle handle"),
        *tip(s2, "Slider(-50..50, style=Style(highlight=red))\nRed-tinted fill and track"),
        value_label,
        desc,
    ]


def page_progressbar():
    """Page: ProgressBar"""
    pb = PageBuilder()

    pb1 = pb.place(ProgressBar, 400, 24, value=75, show_text=True)
    pb2 = pb.place(ProgressBar, 400, 24, value=30)
    pb3 = pb.place(ProgressBar, 400, 16, value=100, show_text=True)

    def on_slide(v):
        pb2.set_value(v)
        set_status(f"Progress: {int(v)}%")

    ctrl = pb.place(Slider, 400, 28, min_val=0, max_val=100, value=30, onchange=on_slide)

    desc = pb.desc("Use the slider to control the middle bar. Top and bottom are static.")
    return [
        *tip(pb1, "ProgressBar(value=75, show_text=True)\nFilled bar with '75%' text centered"),
        *tip(pb2, "ProgressBar(value=30)\nPartially filled bar, no text"),
        *tip(pb3, "ProgressBar(value=100, show_text=True)\nFully filled, shorter height"),
        *tip(ctrl, "Slider controlling pb2\nDrag to update the middle bar"),
        desc,
    ]


def page_radiogroup():
    """Page: RadioGroup"""
    pb = PageBuilder()

    lbl1 = pb.place(Label, 200, 24, text="Vertical:")
    # Place the horizontal label manually (side by side)
    lbl2 = Label(Rect(pb.L.x + 250, lbl1.rect.y, 200, 24), text="Horizontal:")

    rg1 = pb.place(RadioGroup, 200, 120, options=["Small", "Medium", "Large", "Extra Large"], selected_index=1)
    rg1.onchange = lambda _i: set_status(f"Size: {rg1.get_value()}")

    rg2 = RadioGroup(
        Rect(pb.L.x + 250, rg1.rect.y + 120 - 32, 400, 32),
        options=["Red", "Green", "Blue"],
        orientation="horizontal",
    )
    rg2.onchange = lambda _i: set_status(f"Color: {rg2.get_value()}")

    return [
        *tip(rg1, "RadioGroup(vertical, 4 options, selected=1)\nStacked circles, filled dot when selected"),
        *tip(rg2, "RadioGroup(horizontal, 3 options)\nSide-by-side circles with labels"),
        lbl1,
        lbl2,
    ]


def page_separator():
    """Page: Separator"""
    pb = PageBuilder()
    L = pb.L

    l1 = pb.place(Label, L.w, 24, text="Above the horizontal separator")
    sep_h = pb.place(Separator, L.w, 4, orientation="horizontal")
    l2 = pb.place(Label, L.w, 24, text="Below the horizontal separator")
    pb.skip(pb.gap)

    half_w = L.w // 2
    sep_v = Separator(
        Rect(L.x + half_w, pb.y - 100, 4, 100),
        orientation="vertical",
        color=(200, 100, 100),
    )
    l3 = Label(Rect(L.x, pb.y - 50, half_w, 24), text="Left of vertical", anchor_x="center")
    l4 = Label(Rect(L.x + half_w + 10, pb.y - 50, half_w - 10, 24), text="Right of vertical")
    return [
        l1,
        *tip(sep_h, "Separator(horizontal)\nThin horizontal line across full width"),
        l2,
        *tip(sep_v, "Separator(vertical, color=(200,100,100))\nThin red vertical line"),
        l3,
        l4,
    ]


def page_textinput():
    """Page: TextInput"""
    pb = PageBuilder()

    result_label = pb.result_label("Type and press Enter to submit")

    def on_submit(text):
        result_label.text = f'Submitted: "{text}"'
        set_status(f"Text submitted: {text}")

    ti1 = pb.place(TextInput, 350, 28, placeholder="Type something here...", onsubmit=on_submit)
    ti2 = pb.place(TextInput, 350, 28, placeholder="Another input (no submit handler)", text="Pre-filled")

    pb.finalize_label(result_label)
    ti1.focus()
    return [
        *tip(ti1, "TextInput(placeholder=..., onsubmit=...)\nBordered field with blinking cursor when focused"),
        *tip(ti2, "TextInput(text='Pre-filled')\nPre-populated editable field, click to focus"),
        result_label,
    ]


def page_tooltip():
    """Page: Tooltip"""
    pb = PageBuilder()

    btn = pb.place(Button, 200, 32, label="Hover over me", action=lambda: set_status("Button with tooltip clicked!"))
    ttip = Tooltip(btn, "This is a tooltip! It appears after 0.5s hover.")

    btn2 = Button(
        Rect(pb.L.x + 250, btn.rect.y, 200, 32),
        "Quick tooltip",
        action=lambda: set_status("Quick tooltip button clicked!"),
    )
    ttip2 = Tooltip(btn2, "Instant tooltip!", delay=0.1)

    desc = pb.desc("Hover over the buttons to see tooltips appear after a delay.")
    return [btn, ttip, btn2, ttip2, desc]


def page_spacer():
    """Page: Spacer"""
    pb = PageBuilder()
    L = pb.L

    box = HBox(
        rect=Rect(L.x, pb.y - 28, 0, 0),
        padding=4,
        widgets=[
            *_make_buttons(["Left", "Middle", "Right"]),
        ],
    )
    # Interleave fill spacers between buttons
    box.widgets = [
        box.widgets[0],
        _fill_spacer(label="---"),
        box.widgets[1],
        _fill_spacer(),
        box.widgets[2],
    ]
    box.rect.width = L.w
    pb.skip(28 + pb.gap)

    # Same layout without fill for comparison
    box2 = HBox(
        rect=Rect(L.x, pb.y - 28, 0, 0),
        padding=4,
        widgets=[
            Button(Rect(0, 0, 100, 28), "Left"),
            Spacer(Rect(0, 0, 60, 28), label="---"),
            Button(Rect(0, 0, 100, 28), "Middle"),
            Spacer(Rect(0, 0, 60, 28)),
            Button(Rect(0, 0, 100, 28), "Right"),
        ],
    )
    pb.skip(28 + pb.gap)

    desc = pb.desc(
        "Top: Spacers with fill='width' stretch to fill the HBox (explicit width).\nBottom: Same layout without fill (fixed 60px spacers)."
    )
    return [
        *tip(box, "HBox(width=L.w) + Spacer(fill='width')\nSpacers stretch to fill remaining space"),
        *tip(box2, "HBox with fixed-size Spacers (no fill)\nSame layout, spacers stay at 60px"),
        desc,
    ]


def page_panel():
    """Page: Panel"""
    pb = PageBuilder()
    L = pb.L

    panel_h = 130
    panel = Panel(
        title="Settings Panel",
        padding=6,
        widgets=[
            Checkbox(Rect(0, 0, 250, 24), label="Option A", checked=True),
            Checkbox(Rect(0, 0, 250, 24), label="Option B"),
            Separator(Rect(0, 0, 250, 4)),
            Toggle(Rect(0, 0, 250, 24), label="Advanced mode"),
        ],
    )
    panel.rect.x = L.x
    panel.rect.y = pb.y - panel_h

    panel2 = Panel(
        title="Horizontal",
        padding=6,
        orientation="horizontal",
        widgets=_make_buttons(["One", "Two", "Three"], w=80),
    )
    panel2.rect.x = L.x + 300
    panel2.rect.y = pb.y - 60
    pb.skip(panel_h + pb.gap)

    desc = pb.desc("Panels are bordered containers with optional title. Vertical or horizontal.")
    return [
        *tip(panel, "Panel(title='Settings', vertical)\nBordered box with title bar and stacked children"),
        *tip(panel2, "Panel(title='Horizontal', horizontal)\nSide-by-side children layout"),
        desc,
    ]


def page_scrollbox():
    """Page: ScrollBox"""
    pb = PageBuilder()
    L = pb.L

    desc = pb.desc("Left: Labels with fill='width' stretch to VBox width. Right: fixed-width labels.")

    # Left ScrollBox -- labels with fill="width"
    fill_content = VBox(padding=2, widgets=_scroll_items(20, 100, "  Item {i}: fill='width'", fill="width"))
    sb_fill = ScrollBox(Rect(L.x, pb.y - 200, 350, 200), content=fill_content)

    # Right ScrollBox -- fixed-width labels (original behavior)
    content = VBox(padding=2, widgets=_scroll_items(20, 350, "  Item {i}: fixed width"))
    sb = ScrollBox(Rect(L.x + 380, pb.y - 200, 350, 200), content=content)
    return [
        *tip(sb_fill, "ScrollBox + VBox(fill='width' labels)\nLabels stretch to fill VBox width"),
        *tip(sb, "ScrollBox + VBox(fixed-width labels)\nOriginal fixed-width behavior"),
        desc,
    ]


def page_modal():
    """Page: Modal"""
    pb = PageBuilder()
    L = pb.L

    result_label = pb.result_label("Click the button to open a modal dialog.")

    modal_input = TextInput(Rect(0, 0, 300, 28), placeholder="Enter your name...")
    modal = Modal(
        Rect(0, 0, L.window_w, L.window_h),
        title="Example Modal",
        content=modal_input,
        on_close=lambda: set_status("Modal dismissed"),
    )

    def on_submit(text):
        result_label.text = f'Modal submitted: "{text}"'
        set_status(f"Modal input: {text}")
        modal.hide()

    modal_input.onsubmit = on_submit

    def show_modal():
        modal_input.set_text("")
        modal_input.focus()
        modal.show()
        set_status("Modal opened")

    btn = pb.place(Button, 200, 32, label="Open Modal", action=show_modal)

    pb.finalize_label(result_label)
    return [
        *tip(btn, "Modal(title=..., content=TextInput)\nClick to show centered overlay dialog"),
        result_label,
        modal,
    ]


def page_containers():
    """Page: HBox & VBox"""
    L = layout

    # -- HBox demo --
    hbox = HBox(padding=6, widgets=_make_buttons(["H-1", "H-2", "H-3"], w=80))
    hbox_section = VBox(
        padding=4,
        widgets=[
            Label(Rect(0, 0, 200, 24), text="HBox (left to right):"),
            hbox,
        ],
    )

    # -- VBox demo --
    vbox = VBox(
        padding=6,
        widgets=[
            Button(Rect(0, 0, 120, 28), "V-1"),
            Button(Rect(0, 0, 120, 28), "V-2"),
            Button(Rect(0, 0, 120, 28), "V-3"),
        ],
    )
    vbox_section = VBox(
        padding=4,
        widgets=[
            Label(Rect(0, 0, 200, 24), text="VBox (bottom to top):"),
            vbox,
        ],
    )

    # Top row: HBox demo + VBox demo side by side
    top_row = HBox(padding=L.padding, align="top", widgets=[hbox_section, vbox_section])

    # -- Nested example: 3 VBoxes (10, 1, 5 items) inside an HBox --
    def _make_col(prefix, n):
        return VBox(padding=2, widgets=[Label(Rect(0, 0, 90, 18), text=f"{prefix}-{i + 1}", font_size=10) for i in range(n)])

    col_a, col_b, col_c = _make_col("A", 10), _make_col("B", 1), _make_col("C", 5)
    col_b.valign = "bottom"
    nested_cols = HBox(padding=6, align="top", widgets=[col_a, col_b, col_c])
    lbl_nested = VBox(
        padding=4,
        widgets=[
            Label(Rect(0, 0, 180, 20), text="Nested layout:", font_size=11),
            Label(Rect(0, 0, 180, 18), text="3 VBoxes in HBox", font_size=10),
            Label(Rect(0, 0, 180, 18), text="align='top'", font_size=10),
            Label(Rect(0, 0, 180, 18), text="B: valign=bottom", font_size=10),
        ],
    )
    lbl_nested.valign = "top"
    nested = HBox(padding=8, align="top", widgets=[lbl_nested, nested_cols])

    # Page layout: stack sections vertically
    page = VBox(
        rect=Rect(L.x, L.content_bottom, 0, 0),
        padding=L.padding,
        widgets=[nested, top_row],
    )

    return [
        *tip(page, "Page laid out with a VBox -- no manual y-offsets"),
        *tip(hbox, "HBox(padding=6, widgets=[3 buttons])\nLeft-to-right layout with shadow outline"),
        *tip(vbox, "VBox(padding=6, widgets=[3 buttons])\nBottom-to-top layout with shadow outline"),
        *tip(nested, "HBox(widgets=[VBox(10), VBox(1), VBox(5)])\nNested layout with varying child counts"),
    ]


# -- TOML loader demo ----------------------------------------------------

_LOADER_TOML = """\
[[widget]]
type = "Label"
text = "This entire UI is loaded from a TOML string:"
width = 400
height = 20
font_size = 11

[[widget]]
type = "Panel"
title = "Settings (from TOML)"
padding = 6
orientation = "vertical"

  [[widget.children]]
  type = "TextInput"
  id = "name_input"
  placeholder = "Enter your name..."
  width = 280
  height = 28
  onsubmit = "on_name_submit"

  [[widget.children]]
  type = "Checkbox"
  id = "dark_mode"
  label = "Dark mode"
  checked = false
  width = 250
  height = 28
  onchange = "on_dark_mode"

  [[widget.children]]
  type = "Toggle"
  label = "Notifications"
  width = 200
  height = 24
  onchange = "on_notifications"

  [[widget.children]]
  type = "Slider"
  id = "volume"
  min_val = 0
  max_val = 100
  value = 60
  width = 260
  height = 24
  onchange = "on_volume"

  [[widget.children]]
  type = "Separator"
  orientation = "horizontal"
  width = 260
  height = 10

  [[widget.children]]
  type = "RadioGroup"
  options = ["Low", "Medium", "High"]
  selected_index = 1
  width = 200
  height = 72
  onchange = "on_quality"
  orientation = "vertical"

  [[widget.children]]
  type = "HBox"
  padding = 4

    [[widget.children.children]]
    type = "Button"
    label = "Apply"
    width = 100
    height = 28
    action = "on_apply"

    [[widget.children.children]]
    type = "Button"
    label = "Reset"
    width = 100
    height = 28
    action = "on_reset"
"""


class _LoaderController:
    """Controller whose methods are auto-bound to widgets loaded from TOML."""

    def on_name_submit(self, text):
        set_status(f"[TOML] Name submitted: {text}")

    on_dark_mode = _toggle_status("Dark mode", prefix="[TOML] ")
    on_notifications = _toggle_status("Notifications", prefix="[TOML] ")

    def on_volume(self, value):
        set_status(f"[TOML] Volume: {int(value)}")

    def on_quality(self, index):
        names = ["Low", "Medium", "High"]
        set_status(f"[TOML] Quality: {names[index]}")

    def on_apply(self):
        set_status("[TOML] Settings applied!")

    def on_reset(self):
        set_status("[TOML] Settings reset!")


_loader_ctrl = _LoaderController()


def page_loader():
    """Page: TOML Loader"""
    pb = PageBuilder()

    result = load_ui(_LOADER_TOML, _loader_ctrl)

    # Position the loaded widgets in the demo page layout
    for w in result.widgets:
        h = max(w.rect.height, 20)
        w.rect.x = pb.L.x
        w.rect.y = pb.y - h
        pb.y -= h + pb.gap

    return result.widgets


def page_filedialog():
    """Page: File Dialog"""
    pb = PageBuilder()

    result_label = pb.result_label("Click a button to open a native file dialog.", height=72)

    def do_open():
        paths = open_file(
            title="Open File",
            filters=[("Images", [(0, "*.png"), (0, "*.jpg"), (0, "*.gif")]), ("All files", [(0, "*")])],
        )
        if paths:
            result_label.text = "Opened:\n" + "\n".join(paths)
        else:
            result_label.text = "Open cancelled."
        set_status(f"open_file -> {paths!r}")

    def do_save():
        path = save_file(
            title="Save File",
            current_name="untitled.txt",
            filters=[("Text files", [(0, "*.txt")]), ("All files", [(0, "*")])],
        )
        result_label.text = f"Save: {path}" if path else "Save cancelled."
        set_status(f"save_file -> {path!r}")

    def do_pick_dir():
        path = pick_directory(title="Select Folder")
        result_label.text = f"Directory: {path}" if path else "Pick cancelled."
        set_status(f"pick_directory -> {path!r}")

    actions = [("Open File", do_open), ("Save File", do_save), ("Pick Directory", do_pick_dir)]
    tips_text = [
        "open_file(filters=[Images, All])\nOpens native file picker via XDG Portal",
        "save_file(current_name='untitled.txt')\nOpens native save dialog via XDG Portal",
        "pick_directory()\nOpens native folder picker via XDG Portal",
    ]

    btns = []
    for (label, action), tip_text in zip(actions, tips_text):
        btn = pb.place(Button, 160, 32, label=label, action=action)
        btns.extend(tip(btn, tip_text))

    pb.finalize_label(result_label, height=72)
    return [*btns, result_label]


# -- Page registry -------------------------------------------------------
PAGES = [
    ("Button", page_button),
    ("Label", page_label),
    ("Image", page_image),
    ("Dropdown", page_dropdown),
    ("Checkbox", page_checkbox),
    ("Toggle", page_toggle),
    ("Slider", page_slider),
    ("ProgressBar", page_progressbar),
    ("RadioGroup", page_radiogroup),
    ("Separator", page_separator),
    ("TextInput", page_textinput),
    ("Tooltip", page_tooltip),
    ("Spacer", page_spacer),
    ("Panel", page_panel),
    ("ScrollBox", page_scrollbox),
    ("Modal", page_modal),
    ("HBox & VBox", page_containers),
    ("TOML Loader", page_loader),
    ("File Dialog", page_filedialog),
]


# -- Drawing helpers (DRY: violations #13, #14, #15) ---------------------


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


# -- Demo Window ---------------------------------------------------------


class DemoApp(pyglet.window.Window):
    def __init__(self):
        super().__init__(layout.window_w, layout.window_h, "pyggets Demo", resizable=True, vsync=True)
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
        """Load the current page's widgets."""
        _name, builder = PAGES[self.page_index]
        self.page_widgets = builder()

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

    # -- Event dispatch helpers (DRY: violations #11, #12) --

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

        # Background (uses surface color from active theme)
        bg = style.surface
        bg_rgba = (bg[0], bg[1], bg[2], 255) if len(bg) < 4 else bg
        makeRectangle(0, 0, L.window_w, L.window_h, color=bg_rgba).draw()

        # Header
        page_name = PAGES[self.page_index][0]
        _draw_label(page_name, L.window_w // 2, L.window_h - 24, font_size=18, anchor_x="center", weight="bold")

        # Page counter (right of prev button)
        _draw_label(f"{self.page_index + 1}/{len(PAGES)}", 115, 20, anchor_x="left")

        # Separator lines
        for sep_y in (L.NAV_HEIGHT, L.window_h - L.HEADER_HEIGHT):
            makeRectangle(0, sep_y, L.window_w, 1, color=style.color).draw()

        # Navigation buttons + theme dropdown
        self.btn_prev.draw(cursor)
        self.btn_next.draw(cursor)
        if not self.theme_dropdown.expanded and self.theme_dropdown._expand.value <= 0:
            self.theme_dropdown.draw(cursor)

        # Status bar (just above the nav separator) -- drawn before overlays
        # so expanded dropdowns render on top of it
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

        # Page widgets -- multi-pass draw:
        #   1. Normal widgets (defer expanded dropdowns, modals, and tooltips)
        #   2. Expanded dropdowns (overlay on top)
        #   3. Modals (highest z-order)
        #   4. Tooltips (absolute topmost layer)
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

        # Unfocus all page widgets except the one that handled the click,
        # and collapse theme dropdown when clicking elsewhere
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
