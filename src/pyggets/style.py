"""Style definitions for pyggets widgets."""

from dataclasses import dataclass


@dataclass
class Style:
    """Visual style for a widget.

    The first five fields (text_color through weight) are the original
    style properties.  The remaining fields cover colors that were
    previously hardcoded inside widget draw methods, enabling full
    theme control.
    """

    # --- core (original) fields ---
    text_color: tuple[int, int, int, int] = (50, 50, 50, 255)
    color: tuple[int, int, int] = (200, 200, 200)
    highlight: tuple[int, int, int] = (200, 255, 200)
    on_accent: tuple[int, int, int, int] = (20, 20, 20, 255)
    weight: str = "normal"

    # --- extended fields (previously hardcoded) ---
    surface: tuple = (50, 50, 50)
    """Inner background for Panel and TextInput."""

    surface_text: tuple = (220, 220, 220, 255)
    """Text color inside TextInput and Tooltip."""

    placeholder_text: tuple = (120, 120, 120, 200)
    """TextInput placeholder text color."""

    knob_color: tuple = (255, 255, 255)
    """Toggle knob and Slider handle color."""

    shadow: tuple = (0, 0, 0, 80)
    """Widget / box drop-shadow color."""

    scrollbar: tuple = (180, 180, 180, 120)
    """ScrollBox scrollbar indicator color."""

    backdrop: tuple = (0, 0, 0, 150)
    """Modal semi-transparent backdrop color."""

    tooltip_bg: tuple = (40, 40, 40, 255)
    """Tooltip background color."""

    dropdown_bg: tuple = (100, 100, 100)
    """Background color for expanded dropdown option rows."""
