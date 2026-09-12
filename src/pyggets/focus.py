"""Keyboard focus management for pyggets widgets."""

from __future__ import annotations

from .widgets import (
    _KEY_DOWN,
    _KEY_LEFT,
    _KEY_RIGHT,
    _KEY_TAB,
    _KEY_UP,
    _MOD_SHIFT,
    Widget,
)


class FocusManager:
    """Manages keyboard focus traversal across a widget tree.

    Builds a flat, depth-first focus order from one or more root widgets and
    provides traversal (next/prev/first) plus a single :meth:`handle_key`
    entry point that routes keys to the focused widget or moves focus.
    """

    def __init__(self, root: Widget | list[Widget] | tuple[Widget, ...]):
        self._roots: list[Widget] = list(root) if isinstance(root, (list, tuple)) else [root]
        self._order: list[Widget] = self._flatten()
        self._index = -1

    def _flatten(self) -> list[Widget]:
        out: list[Widget] = []
        for r in self._roots:
            self._collect(r, out)
        return out

    def _collect(self, w: Widget, out: list[Widget]) -> None:
        if getattr(w, "focusable", False):
            out.append(w)
        for child in w.focusable_children():
            self._collect(child, out)

    @property
    def current(self) -> Widget | None:
        if 0 <= self._index < len(self._order):
            return self._order[self._index]
        return None

    def _set(self, i: int) -> None:
        cur = self.current
        if cur is not None:
            cur.unfocus()
        self._index = i
        cur = self.current
        if cur is not None:
            cur.focus()

    def focus_next(self) -> None:
        if not self._order:
            return
        self._set((self._index + 1) % len(self._order))

    def focus_prev(self) -> None:
        if not self._order:
            return
        self._set((self._index - 1) % len(self._order))

    def focus_first(self) -> None:
        if self._order:
            self._set(0)

    def handle_key(self, symbol: int, modifiers: int) -> bool:
        w = self.current
        if w is not None and w.on_key_press(symbol, modifiers):
            return True
        if symbol in (_KEY_LEFT, _KEY_UP):
            self.focus_prev()
            return True
        if symbol in (_KEY_RIGHT, _KEY_DOWN):
            self.focus_next()
            return True
        if symbol == _KEY_TAB:
            (self.focus_prev if modifiers & _MOD_SHIFT else self.focus_next)()
            return True
        return False
