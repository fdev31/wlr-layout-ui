"""Icon assets for wlr-layout-ui.

Provides a helper to resolve icon file paths relative to this package,
so that icons work both in development and when installed as a package.
"""

from ._icons import icon_path

__all__ = ["icon_path"]
