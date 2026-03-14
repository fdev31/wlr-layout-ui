"""pyggets - A reusable pyglet widget library.

Provides a set of UI widgets built on top of pyglet for creating
simple GUI applications with buttons, dropdowns, layout containers,
and more.

Usage:
    from pyggets import Widget, Button, Dropdown, HBox, VBox, Rect, Style, Theme

    # Optionally configure a custom theme
    from pyggets import set_default_theme
    set_default_theme(Theme(font_name="My Font", widget_radius=5))
"""

# Color utilities
from .color import brighten

# Containers
from .containers import HBox, Modal, Panel, ScrollBox, VBox

# File dialogs
from .filedialog import open_file, pick_directory, save_file

# Geometry
from .geometry import Rect, collidepoint

# Declarative UI loader
from .loader import UIResult, WindowSpec, build_widget, load_theme, load_ui, register_widget, run_ui

# Drawing primitives
from .primitives import makeCircle, makeLabel, makeRectangle, makeSprite
from .shapes import RoundedRectangle, makeRoundedRectangle

# Style
from .style import Style

# Theme
from .theme import Theme, get_default_theme, set_default_theme

# Widgets
from .widgets import (
    Button,
    Checkbox,
    Dropdown,
    Image,
    Label,
    ProgressBar,
    RadioGroup,
    Separator,
    Slider,
    Spacer,
    TextInput,
    Toggle,
    Tooltip,
    Widget,
)

__all__ = [
    "Button",
    "Checkbox",
    "Dropdown",
    "HBox",
    "Image",
    "Label",
    "Modal",
    "Panel",
    "ProgressBar",
    "RadioGroup",
    "Rect",
    "RoundedRectangle",
    "ScrollBox",
    "Separator",
    "Slider",
    "Spacer",
    "Style",
    "TextInput",
    "Theme",
    "Toggle",
    "Tooltip",
    "UIResult",
    "VBox",
    "Widget",
    "WindowSpec",
    "brighten",
    "build_widget",
    "collidepoint",
    "get_default_theme",
    "load_theme",
    "load_ui",
    "makeCircle",
    "makeLabel",
    "makeRectangle",
    "makeRoundedRectangle",
    "makeSprite",
    "open_file",
    "pick_directory",
    "register_widget",
    "run_ui",
    "save_file",
    "set_default_theme",
]
