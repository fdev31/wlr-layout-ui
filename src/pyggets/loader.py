"""Declarative UI loader for pyggets.

Load widget trees from TOML files or strings, with automatic controller
method binding for event handlers.  Optionally includes window specs and
theme definitions.

Usage::

    from pyggets import load_ui

    class MyController:
        def on_save(self):
            print("saved")
        def on_name_change(self, text):
            print(f"name: {text}")

    result = load_ui("my_ui.toml", MyController())
    # result.widgets  -> list of top-level widget instances
    # result.refs     -> {"save_btn": <Button>, ...}
    # result.window   -> WindowSpec or None
    # result.themes   -> {"dark": Theme, ...} or None
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

import tomli

from .containers import HBox, Modal, Panel, ScrollBox, VBox
from .geometry import Rect
from .style import Style
from .theme import Theme
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
)

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class WindowSpec:
    """Window configuration parsed from a ``[window]`` TOML section."""

    width: int = 800
    height: int = 600
    title: str = "pyggets"
    resizable: bool = True


@dataclass
class UIResult:
    """Return type for :func:`load_ui`.

    Attributes:
        widgets: Top-level widget instances.
        refs: Mapping of widget ``id`` strings to their instances.
        window: Window configuration, or ``None`` if the TOML had no
            ``[window]`` section.
        themes: Named theme definitions, or ``None`` if the TOML had no
            ``[theme.*]`` sections.
    """

    widgets: list = field(default_factory=list)
    refs: dict[str, object] = field(default_factory=dict)
    window: WindowSpec | None = None
    themes: dict[str, Theme] | None = None


# ---------------------------------------------------------------------------
# Widget registry
# ---------------------------------------------------------------------------

WIDGET_REGISTRY: dict[str, type] = {
    "Button": Button,
    "Image": Image,
    "Label": Label,
    "Checkbox": Checkbox,
    "Toggle": Toggle,
    "Slider": Slider,
    "ProgressBar": ProgressBar,
    "RadioGroup": RadioGroup,
    "Separator": Separator,
    "TextInput": TextInput,
    "Dropdown": Dropdown,
    "Spacer": Spacer,
    "Tooltip": Tooltip,
    "HBox": HBox,
    "VBox": VBox,
    "Panel": Panel,
    "ScrollBox": ScrollBox,
    "Modal": Modal,
}

# Keys that carry a handler reference (string -> controller method).
_HANDLER_KEYS = {"action", "onchange", "onsubmit", "on_close"}

# Keys consumed by the loader itself (not forwarded to widget constructors).
_META_KEYS = {"type", "id", "width", "height", "x", "y", "children", "style", "valign", "halign", "fill", "margin", "target"}

# Widget types whose children map to a single ``content`` kwarg.
_CONTENT_WIDGETS = {ScrollBox, Modal}

# Widget types that accept ``widgets=`` for their children.
_CONTAINER_WIDGETS = {HBox, VBox, Panel}

# Mapping from preset name strings to Theme classmethods.
_THEME_PRESETS: dict[str, str] = {
    "dark": "dark",
    "light": "light",
    "high_contrast": "high_contrast",
    "light_high_contrast": "light_high_contrast",
}


def register_widget(name: str, cls: type) -> None:
    """Register a custom widget class so it can be referenced in TOML.

    Args:
        name: The type name used in TOML (e.g. ``"MyWidget"``).
        cls: The widget class.
    """
    WIDGET_REGISTRY[name] = cls


# ---------------------------------------------------------------------------
# Internal builder helpers
# ---------------------------------------------------------------------------


def _parse_toml(toml_source: str | Path) -> dict:
    """Parse a TOML source (file path or inline string) into a dict."""
    source_path = None
    if isinstance(toml_source, Path):
        source_path = toml_source
    elif isinstance(toml_source, str):
        candidate = Path(toml_source)
        is_toml_content = "\n" in toml_source or toml_source.lstrip().startswith(("[", "#"))
        if not is_toml_content and candidate.exists():
            source_path = candidate

    if source_path is not None:
        return tomli.loads(source_path.read_text(encoding="utf-8"))
    return tomli.loads(toml_source)


def _resolve_handler(name: str, controller: object | None, widget_desc: str) -> callable:
    """Resolve a handler string to a method on the controller."""
    if controller is None:
        msg = f"Widget {widget_desc} references handler '{name}' but no controller was provided"
        raise ValueError(msg)
    if not hasattr(controller, name):
        ctrl_name = type(controller).__name__
        msg = f"Controller '{ctrl_name}' has no method '{name}' (referenced by {widget_desc})"
        raise AttributeError(msg)
    return getattr(controller, name)


def _build_style(spec: dict, *, base: Style | None = None) -> Style:
    """Build a ``Style`` from a TOML dict, optionally merging over a base."""
    if base is not None:
        # Start from a copy of base, override with spec values.
        kwargs = {}
        for f in fields(Style):
            if f.name in spec:
                val = spec[f.name]
                kwargs[f.name] = tuple(val) if isinstance(val, list) else val
            else:
                kwargs[f.name] = getattr(base, f.name)
        return Style(**kwargs)

    # No base -- original behavior.
    kwargs = {}
    for f in fields(Style):
        if f.name in spec:
            val = spec[f.name]
            kwargs[f.name] = tuple(val) if isinstance(val, list) else val
    return Style(**kwargs)


def _build_rect(spec: dict) -> Rect:
    """Extract a ``Rect`` from a widget spec dict."""
    x = spec.get("x", 0)
    y = spec.get("y", 0)
    w = spec.get("width", 0)
    h = spec.get("height", 0)
    return Rect(x, y, w, h)


def _widget_desc(spec: dict) -> str:
    """Return a short human-readable description of a widget spec for errors."""
    wtype = spec.get("type", "?")
    wid = spec.get("id")
    label = spec.get("label") or spec.get("text") or spec.get("title") or ""
    parts = [wtype]
    if wid:
        parts.append(f"id={wid!r}")
    if label:
        parts.append(repr(label))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Window spec builder
# ---------------------------------------------------------------------------


def _build_window_spec(spec: dict) -> WindowSpec:
    """Build a ``WindowSpec`` from a ``[window]`` TOML table."""
    valid_keys = {f.name for f in fields(WindowSpec)}
    kwargs = {k: v for k, v in spec.items() if k in valid_keys}
    return WindowSpec(**kwargs)


# ---------------------------------------------------------------------------
# Theme builder
# ---------------------------------------------------------------------------


def _build_theme(spec: dict) -> Theme:
    """Build a ``Theme`` from a single theme spec dict.

    If a ``preset`` key is present, the theme starts from the named
    built-in preset (e.g. ``"dark"``, ``"light"``) and overrides are
    merged on top.  Otherwise a fresh ``Theme()`` is constructed.
    """
    preset_name = spec.get("preset")
    if preset_name:
        method_name = _THEME_PRESETS.get(preset_name)
        if method_name is None:
            msg = f"Unknown theme preset '{preset_name}'. Available: {', '.join(sorted(_THEME_PRESETS))}"
            raise ValueError(msg)
        base_theme = getattr(Theme, method_name)()
    else:
        base_theme = Theme()

    # Override top-level Theme fields.
    font_name = spec.get("font_name", base_theme.font_name)
    widget_radius = spec.get("widget_radius", base_theme.widget_radius)

    # Build style, merging over the base theme's style if present.
    style_spec = spec.get("style")
    style = _build_style(style_spec, base=base_theme.default_style) if style_spec else base_theme.default_style

    return Theme(font_name=font_name, widget_radius=widget_radius, default_style=style)


def _build_themes(theme_data: dict) -> dict[str, Theme]:
    """Build themes from the ``[theme]`` or ``[theme.*]`` TOML section.

    Supports two shapes:

    1. **Named themes** -- each key under ``[theme]`` is a sub-table
       defining a named theme::

           [theme.dark]
           preset = "dark"
           [theme.dark.style]
           highlight = [100, 190, 130]

    2. **Single unnamed theme** -- the ``[theme]`` table itself contains
       theme fields directly (no sub-tables that look like theme defs).
       This is stored under the key ``"default"``::

           [theme]
           font_name = "Free Sans"
           [theme.style]
           color = [90, 90, 90]
    """
    # Heuristic: if every value in theme_data is a dict that isn't "style",
    # treat them as named sub-themes.  Otherwise it's a single theme.
    sub_tables = {k: v for k, v in theme_data.items() if isinstance(v, dict) and k != "style"}

    if sub_tables and len(sub_tables) == len([k for k in theme_data if k != "style"]):
        # Looks like named themes (all non-"style" keys are dicts).
        # But we need to distinguish {"font_name": "X", "style": {...}}
        # (single theme) from {"dark": {...}, "light": {...}} (named).
        # Check if any non-style key is a scalar -- if so, single theme.
        scalar_keys = [k for k, v in theme_data.items() if not isinstance(v, dict)]
        if scalar_keys:
            return {"default": _build_theme(theme_data)}
        return {name: _build_theme(spec) for name, spec in theme_data.items() if name != "style"}

    return {"default": _build_theme(theme_data)}


# ---------------------------------------------------------------------------
# Widget builder
# ---------------------------------------------------------------------------


def build_widget(
    spec: dict,
    controller: object | None = None,
    _refs: dict[str, object] | None = None,
    _pending_tooltips: list | None = None,
) -> object:
    """Build a single widget (and its children) from a spec dict.

    Args:
        spec: A dict describing the widget.  Must contain a ``"type"`` key.
        controller: Optional object whose methods are bound as event handlers.

    Returns:
        The constructed widget instance.

    This function is recursive: container specs with ``"children"`` produce
    nested widget trees.
    """
    if _refs is None:
        _refs = {}
    if _pending_tooltips is None:
        _pending_tooltips = []

    wtype_name = spec.get("type")
    if not wtype_name:
        msg = f"Widget spec missing 'type' key: {spec}"
        raise ValueError(msg)

    cls = WIDGET_REGISTRY.get(wtype_name)
    if cls is None:
        msg = f"Unknown widget type '{wtype_name}'. Registered types: {', '.join(sorted(WIDGET_REGISTRY))}"
        raise ValueError(msg)

    desc = _widget_desc(spec)

    # --- Collect constructor kwargs ---
    kwargs: dict = {}

    # Rect
    rect = _build_rect(spec)
    # Containers with auto-sizing don't need a rect when they have children,
    # but standalone widgets always need one.  Tooltip creates its own rect
    # internally and does not accept one.
    needs_rect = cls not in _CONTAINER_WIDGETS and cls is not Tooltip
    if needs_rect:
        kwargs["rect"] = rect

    # For containers: if explicit size was given, pass the rect.
    if cls in _CONTAINER_WIDGETS and (spec.get("width") or spec.get("height")):
        kwargs["rect"] = rect

    # Style
    if "style" in spec:
        kwargs["style"] = _build_style(spec["style"])

    # Children -> build recursively
    child_specs = spec.get("children", [])
    built_children = []
    for child_spec in child_specs:
        child = build_widget(child_spec, controller, _refs, _pending_tooltips)
        built_children.append(child)

    if built_children:
        if cls in _CONTENT_WIDGETS:
            # ScrollBox and Modal take a single `content` widget.
            # If multiple children, wrap them in a VBox.
            if len(built_children) == 1:
                kwargs["content"] = built_children[0]
            else:
                kwargs["content"] = VBox(widgets=built_children)
        elif cls in _CONTAINER_WIDGETS:
            kwargs["widgets"] = built_children

    # Tooltip special handling: resolve target by id or use previous sibling
    if cls is Tooltip:
        target_id = spec.get("target")
        if target_id:
            if target_id not in _refs:
                # Defer resolution -- store for later
                _pending_tooltips.append((spec, None))
            kwargs["target"] = _refs.get(target_id)
        # If no target and no id reference, caller should handle via
        # the sibling convention (see load_ui).

    # Handler keys -> resolve to controller methods
    for hkey in _HANDLER_KEYS:
        if hkey in spec:
            val = spec[hkey]
            if isinstance(val, str):
                kwargs[hkey] = _resolve_handler(val, controller, desc)
            else:
                # Allow passing callables directly when using build_widget()
                # from Python (not from TOML).
                kwargs[hkey] = val

    # All remaining keys are passed through as constructor kwargs.
    for key, val in spec.items():
        if key in _META_KEYS or key in _HANDLER_KEYS:
            continue
        # TOML arrays -> tuples (e.g. color = [200, 100, 100])
        kwargs[key] = tuple(val) if isinstance(val, list) else val

    # --- Instantiate ---
    widget = cls(**kwargs)

    # Post-construction attributes (not constructor params)
    if "valign" in spec:
        widget.valign = spec["valign"]
    if "halign" in spec:
        widget.halign = spec["halign"]
    if "fill" in spec:
        widget.fill = spec["fill"]
    if "margin" in spec:
        widget.margin = spec["margin"]

    # Store in refs
    wid = spec.get("id")
    if wid:
        _refs[wid] = widget

    return widget


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_theme(toml_source: str | Path) -> dict[str, Theme]:
    """Load one or more themes from a TOML file or string.

    Args:
        toml_source: A filesystem path (``str`` or ``Path``) to a ``.toml``
            file, **or** a TOML-formatted string.

    Returns:
        A ``dict`` mapping theme names to ``Theme`` instances.  A single
        unnamed theme is stored under the key ``"default"``.

    Example TOML (named themes with preset)::

        [theme.my_dark]
        preset = "dark"
        font_name = "Monospace"

        [theme.my_dark.style]
        highlight = [100, 190, 130]

        [theme.my_light]
        preset = "light"

    Example TOML (single unnamed theme)::

        [theme]
        font_name = "Free Sans"
        widget_radius = 4

        [theme.style]
        text_color = [220, 220, 220, 255]
        color = [90, 90, 90]
    """
    data = _parse_toml(toml_source)
    theme_data = data.get("theme")
    if not theme_data:
        msg = "No [theme] section found in TOML source"
        raise ValueError(msg)
    return _build_themes(theme_data)


def load_ui(
    toml_source: str | Path,
    controller: object | None = None,
) -> UIResult:
    """Load a widget tree from a TOML file or string.

    Args:
        toml_source: A filesystem path (``str`` or ``Path``) to a ``.toml``
            file, **or** a TOML-formatted string.  If the string contains a
            newline or doesn't look like a path, it is parsed directly.
        controller: An object whose methods are used as event handlers.
            Method names are referenced by string in the TOML (e.g.
            ``action = "on_save"`` resolves to ``controller.on_save``).

    Returns:
        A :class:`UIResult` with ``widgets``, ``refs``, ``window``, and
        ``themes`` attributes.

    The TOML file may contain any combination of these top-level sections:

    - ``[window]`` -- window configuration (width, height, title, resizable).
    - ``[theme]`` or ``[theme.*]`` -- theme definitions (see :func:`load_theme`).
    - ``[[widget]]`` -- widget tree definitions.

    Example TOML::

        [window]
        width = 400
        height = 250
        title = "My App"

        [theme]
        preset = "dark"
        font_name = "Free Sans"

        [theme.style]
        highlight = [100, 190, 130]

        [[widget]]
        type = "VBox"
        padding = 6

          [[widget.children]]
          type = "Button"
          id   = "ok_btn"
          label = "OK"
          width = 100
          height = 28
          action = "on_ok"
    """
    data = _parse_toml(toml_source)

    # --- Window spec ---
    window_spec = None
    if "window" in data:
        window_spec = _build_window_spec(data["window"])

    # --- Themes ---
    themes = None
    if "theme" in data:
        themes = _build_themes(data["theme"])

    # --- Widgets ---
    widget_specs = data.get("widget", [])
    if not isinstance(widget_specs, list):
        widget_specs = [widget_specs]

    refs: dict[str, object] = {}
    pending_tooltips: list = []
    widgets: list = []

    prev_widget = None
    for spec in widget_specs:
        widget = build_widget(spec, controller, refs, pending_tooltips)
        widgets.append(widget)

        # Tooltip sibling convention: if this is a Tooltip without an
        # explicit target, bind it to the immediately preceding widget.
        if isinstance(widget, Tooltip) and widget.target is None and prev_widget is not None:
            widget.target = prev_widget

        prev_widget = widget

    # Second pass: resolve any pending tooltip targets that referenced
    # widgets defined later in the file.
    for spec, _ in pending_tooltips:
        target_id = spec.get("target")
        if target_id and target_id in refs:
            wid = spec.get("id")
            if wid and wid in refs:
                refs[wid].target = refs[target_id]

    return UIResult(widgets=widgets, refs=refs, window=window_spec, themes=themes)


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


def run_ui(result: UIResult) -> None:
    """Create a window from *result* and run the pyglet application loop.

    This is a convenience wrapper that eliminates all window boilerplate
    when displaying a UI loaded from TOML.  It:

    * applies the first theme in ``result.themes`` (if any),
    * creates a ``pyglet.window.Window`` from ``result.window``,
    * draws a theme-coloured background and the root widget,
    * forwards every mouse/keyboard event to the root widget, and
    * starts ``pyglet.app.run()``.

    Example::

        from pyggets import load_ui, run_ui
        result = load_ui("my_app.toml", controller)
        run_ui(result)
    """
    import pyglet  # noqa: PLC0415

    from .primitives import makeRectangle  # noqa: PLC0415
    from .theme import get_default_theme, set_default_theme  # noqa: PLC0415

    # Apply themes ---------------------------------------------------------
    if result.themes:
        set_default_theme(next(iter(result.themes.values())))

    # Create window --------------------------------------------------------
    ws = result.window or WindowSpec()
    window = pyglet.window.Window(ws.width, ws.height, ws.title, resizable=ws.resizable)

    # The root widget is the first (and usually only) top-level widget.
    ui = result.widgets[0]
    cursor = [0, 0]

    # Event handlers -------------------------------------------------------
    @window.event
    def on_draw():
        window.clear()
        style = get_default_theme().default_style
        bg = style.surface
        bg_rgba = (*bg[:3], 255) if len(bg) < 4 else bg
        makeRectangle(0, 0, window.width, window.height, color=bg_rgba).draw()
        ui.draw(tuple(cursor))

    @window.event
    def on_mouse_motion(x, y, _dx, _dy):
        cursor[:] = [x, y]

    @window.event
    def on_mouse_press(x, y, button, modifiers):
        ui.on_mouse_press(x, y, button, modifiers)

    @window.event
    def on_mouse_drag(x, y, dx, dy, _buttons, _modifiers):
        cursor[:] = [x, y]
        ui.on_mouse_drag(x, y, dx, dy)

    @window.event
    def on_mouse_release(x, y, _button, _modifiers):
        ui.on_mouse_release(x, y)

    @window.event
    def on_mouse_scroll(x, y, dx, dy):
        ui.on_mouse_scroll(x, y, dx, dy)

    @window.event
    def on_key_press(symbol, modifiers):
        ui.on_key_press(symbol, modifiers)

    @window.event
    def on_text(text):
        ui.on_text(text)

    pyglet.app.run()
