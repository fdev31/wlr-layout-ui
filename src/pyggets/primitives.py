"""Cached factory functions for pyglet drawing primitives."""

from functools import lru_cache

import pyglet
from pyglet.shapes import Circle, Rectangle
from pyglet.text import Label

# Max entries for shape/label caches.  High enough to cover a typical UI
# frame without thrashing, low enough to bound memory during animations
# where colour/position values change every frame.
_SHAPE_CACHE_SIZE = 512
_LABEL_CACHE_SIZE = 256


@lru_cache(maxsize=_SHAPE_CACHE_SIZE)
def makeCircle(x, y, r, color):
    """Create a cached pyglet Circle."""
    return Circle(x, y, r, color=color)


@lru_cache(maxsize=_SHAPE_CACHE_SIZE)
def makeRectangle(x, y, w, h, color):
    """Create a cached pyglet Rectangle."""
    return Rectangle(x, y, w, h, color=color)


@lru_cache(maxsize=_LABEL_CACHE_SIZE)
def makeLabel(text, x, y, color=None, **kw):  # noqa: ANN003
    """Create a cached pyglet Label."""
    if color is None:
        color = (0, 0, 0)
    return Label(text, x=x, y=y, color=color, **kw)


@lru_cache(maxsize=None)
def _loadImage(path):
    """Load and cache a pyglet image from a file path."""
    return pyglet.image.load(path)


@lru_cache(maxsize=_SHAPE_CACHE_SIZE)
def makeSprite(path, x, y, width=None, height=None):
    """Create a cached pyglet Sprite from an image file.

    The image is scaled to fit within the given *width* and *height* while
    preserving its aspect ratio.  If neither *width* nor *height* is
    provided the image is drawn at its native resolution.

    Args:
        path: Filesystem path to the image file.
        x: X position (left edge) of the sprite.
        y: Y position (bottom edge) of the sprite.
        width: Target width to fit into (or ``None``).
        height: Target height to fit into (or ``None``).

    Returns:
        A ``pyglet.sprite.Sprite`` instance positioned and scaled appropriately.
    """
    img = _loadImage(path)
    sprite = pyglet.sprite.Sprite(img, x=x, y=y)

    if width is not None or height is not None:
        native_w = img.width
        native_h = img.height
        if width is not None and height is not None:
            # Fit inside the box, preserving aspect ratio
            scale = min(width / native_w, height / native_h)
        elif width is not None:
            scale = width / native_w
        else:
            scale = height / native_h
        sprite.scale = scale

    return sprite
