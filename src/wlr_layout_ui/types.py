from dataclasses import dataclass, field
from typing import Tuple

# Re-export Rect and collidepoint from pyggets for backward compatibility
from pyggets import Rect, collidepoint  # noqa: F401


@dataclass
class Mode:
    width: int
    height: int
    freq: float

    def __repr__(self):
        return f"{self.width}x{self.height}@{self.freq:.2f}Hz"


@dataclass
class Screen:
    uid: str
    name: str
    active: bool = False
    position: Tuple[int, int] = (0, 0)
    mode: Mode | None = None
    scale: float = 1
    available: list[Mode] = field(default_factory=list)
    transform: int = 0

    def __repr__(self):
        return "<Screen{} {} [{}]>".format("*" if self.active else "", self.name, self.mode)
