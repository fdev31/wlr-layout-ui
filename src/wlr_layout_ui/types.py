from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Mode:
    width: int
    height: int
    freq: float

    def __repr__(self):
        return "%dx%d@%.2fHz" % (self.width, self.height, self.freq)


@dataclass
class Screen:
    uid: str
    name: str
    active: bool = False
    position: Tuple[int, int] = (0, 0)
    mode: None | Mode = None
    scale: float = 1
    available: list[Mode] = field(default_factory=list)
    transform: int = 0

    def __repr__(self):
        return "<Screen{} {} [{}]>".format("*" if self.active else "", self.name, self.mode)


@dataclass
class Rect:  # {{{
    x: int
    y: int
    width: int
    height: int

    def __hash__(self):
        return int("%d%d%d%d" % self.asTuple())

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
        return collidepoint(self.x, self.y, self.x + self.width, self.y + self.height, x, y)

    def collide(self, rect):
        # return true if the two rectangles are overlapping in any way
        if rect.left >= self.right:
            return False
        if rect.right <= self.left:
            return False
        if rect.top <= self.bottom:
            return False
        return not rect.bottom >= self.top

    def copy(self):
        return Rect(self.x, self.y, self.width, self.height)

    def asTuple(self):
        return (self.x, self.y, self.width, self.height)

    def scaled(self, factor):
        return Rect(
            self.x * factor,
            self.y * factor,
            self.width * factor,
            self.height * factor,
        )


# }}}


def collidepoint(x: float, y: float, x2: float, y2: float, xp: float, yp: float):
    """Return True if the point is inside the rectangle."""
    assert x < x2
    assert y < y2
    return x < xp < x2 and y < yp < y2
