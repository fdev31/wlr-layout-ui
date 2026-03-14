"""Internal icon path resolution."""

from pathlib import Path

ICON_DIR = Path(__file__).parent


def icon_path(name: str) -> str:
    """Return the absolute path to a bundled icon PNG by name.

    Args:
        name: Icon filename (e.g. ``"save.png"``).

    Returns:
        Absolute filesystem path as a string, suitable for passing
        to ``Button(icon=...)`` or ``makeSprite(...)``.
    """
    return str(ICON_DIR / name)
