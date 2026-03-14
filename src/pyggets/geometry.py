"""Geometry primitives for pyggets widgets."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Rect:
    """A rectangle defined by position and dimensions."""

    x: int
    y: int
    width: int
    height: int

    def __hash__(self):
        return hash(self.as_tuple())

    @property
    def topleft(self):
        return (self.left, self.top)

    @property
    def topright(self):
        return (self.right, self.top)

    @property
    def bottomleft(self):
        return (self.left, self.bottom)

    @property
    def bottomright(self):
        return (self.right, self.bottom)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y + self.height

    @property
    def bottom(self):
        return self.y

    @property
    def center(self):
        return self.x + self.width // 2, self.y + self.height // 2

    def contains(self, x, y):
        """Return True if the point (x, y) is inside this rectangle."""
        return collidepoint(self.x, self.y, self.x + self.width, self.y + self.height, x, y)

    def collide(self, rect):
        """Return True if the two rectangles overlap."""
        if rect.left >= self.right:
            return False
        if rect.right <= self.left:
            return False
        if rect.top <= self.bottom:
            return False
        return not rect.bottom >= self.top

    def copy(self):
        """Return a copy of this rectangle."""
        return Rect(self.x, self.y, self.width, self.height)

    def as_tuple(self):
        """Return the rectangle as a tuple (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    # Keep backward compatibility with the old name
    asTuple: ClassVar = as_tuple

    def scaled(self, factor):
        """Return a new rectangle scaled by the given factor."""
        return Rect(
            int(self.x * factor),
            int(self.y * factor),
            int(self.width * factor),
            int(self.height * factor),
        )


def collidepoint(x: float, y: float, x2: float, y2: float, xp: float, yp: float):
    """Return True if the point is inside the rectangle defined by (x, y) and (x2, y2)."""
    assert x < x2
    assert y < y2
    return x < xp < x2 and y < yp < y2
