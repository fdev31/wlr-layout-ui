"""Theme configuration for pyggets widgets."""

from __future__ import annotations

from dataclasses import dataclass, field

from .style import Style


@dataclass
class Theme:
    """Global theme configuration for pyggets widgets.

    Widgets read their defaults from the active theme. You can override
    individual values by creating a new Theme and calling set_default_theme().
    """

    font_name: str = "Free Sans"
    widget_radius: int = 3
    default_style: Style = field(default_factory=Style)

    @classmethod
    def dark(cls) -> Theme:
        """Return a dark theme preset (the default appearance)."""
        return cls(
            default_style=Style(
                text_color=(200, 200, 200, 255),
                color=(80, 80, 80),
                highlight=(100, 200, 100),
                on_accent=(20, 20, 20, 255),
                surface=(50, 50, 50),
                surface_text=(220, 220, 220, 255),
                placeholder_text=(120, 120, 120, 200),
                knob_color=(255, 255, 255),
                shadow=(0, 0, 0, 80),
                scrollbar=(180, 180, 180, 120),
                backdrop=(0, 0, 0, 150),
                tooltip_bg=(40, 40, 40, 255),
                dropdown_bg=(100, 100, 100),
            ),
        )

    @classmethod
    def light(cls) -> Theme:
        """Return a light theme preset."""
        return cls(
            default_style=Style(
                text_color=(30, 30, 30, 255),
                color=(210, 210, 210),
                highlight=(80, 180, 120),
                on_accent=(255, 255, 255, 255),
                surface=(240, 240, 240),
                surface_text=(30, 30, 30, 255),
                placeholder_text=(150, 150, 150, 200),
                knob_color=(255, 255, 255),
                shadow=(0, 0, 0, 40),
                scrollbar=(100, 100, 100, 120),
                backdrop=(0, 0, 0, 100),
                tooltip_bg=(50, 50, 50, 240),
                dropdown_bg=(225, 225, 225),
            ),
        )

    @classmethod
    def light_high_contrast(cls) -> Theme:
        """Return a high-contrast light theme preset for accessibility.

        Features pure black text on near-white backgrounds, bold accent
        colors, and strong separators for maximum readability.
        """
        return cls(
            default_style=Style(
                text_color=(0, 0, 0, 255),
                color=(200, 200, 200),
                highlight=(0, 120, 200),
                on_accent=(255, 255, 255, 255),
                surface=(245, 245, 245),
                surface_text=(0, 0, 0, 255),
                placeholder_text=(100, 100, 100, 255),
                knob_color=(255, 255, 255),
                shadow=(0, 0, 0, 100),
                scrollbar=(60, 60, 60, 200),
                backdrop=(0, 0, 0, 180),
                tooltip_bg=(20, 20, 20, 255),
                dropdown_bg=(220, 220, 220),
            ),
        )

    @classmethod
    def high_contrast(cls) -> Theme:
        """Return a high-contrast theme preset for accessibility.

        Features stronger color differences, bolder borders, brighter
        text, and a vivid accent color for maximum readability.
        """
        return cls(
            default_style=Style(
                text_color=(255, 255, 255, 255),
                color=(60, 60, 60),
                highlight=(0, 200, 255),
                on_accent=(0, 0, 0, 255),
                surface=(10, 10, 10),
                surface_text=(255, 255, 255, 255),
                placeholder_text=(160, 160, 160, 255),
                knob_color=(255, 255, 255),
                shadow=(0, 0, 0, 160),
                scrollbar=(220, 220, 220, 200),
                backdrop=(0, 0, 0, 200),
                tooltip_bg=(20, 20, 20, 255),
                dropdown_bg=(90, 90, 90),
            ),
        )


_default_theme = Theme()


def get_default_theme() -> Theme:
    """Return the current default theme."""
    return _default_theme


def set_default_theme(theme: Theme) -> None:
    """Set the default theme used by all widgets that don't specify one explicitly."""
    global _default_theme  # noqa: PLW0603
    _default_theme = theme
