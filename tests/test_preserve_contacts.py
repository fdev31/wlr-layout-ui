"""Tests for _resize_screen anchor-based position preservation.

Verifies that when a monitor changes resolution:
- A monitor to the right follows the right edge
- A monitor below follows the bottom edge
- A monitor centered above stays horizontally centered
- A monitor to the left does NOT move
- A monitor vertically centered on the right stays vertically centered
- Corner-anchored monitors maintain their anchor point
"""

import sys
from types import SimpleNamespace

sys.path.insert(0, "src")

from pyggets import Rect
from wlr_layout_ui.gui import UI


class MockScreen:
    """Minimal screen-like object with target_rect, hashable for use as dict key."""

    def __init__(self, x, y, w, h):
        self.target_rect = Rect(x, y, w, h)

    def __hash__(self):
        return id(self)


def _make_screen(x, y, w, h):
    """Create a minimal screen-like object with target_rect."""
    return MockScreen(x, y, w, h)


def _make_ui(changed, *others):
    """Create a minimal UI-like object with selected_item and gui_screens."""
    all_screens = [changed, *others]
    ui = SimpleNamespace(selected_item=changed, gui_screens=all_screens)
    UI._detect_anchors(ui)
    return ui


# ---------------------------------------------------------------------------
# Edge contact: monitor to the right
# ---------------------------------------------------------------------------


def test_right_monitor_follows_wider():
    """Monitor B to the right of A: A grows wider → B shifts right."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(100, 0, 100, 80)  # touching a.right
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 150, 80)  # A grows from 100 to 150

    assert a.target_rect.width == 150
    assert b.target_rect.x == 150, f"B should follow A's right edge, got x={b.target_rect.x}"


def test_right_monitor_follows_narrower():
    """Monitor B to the right of A: A shrinks → B shifts left."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(100, 0, 100, 80)
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 60, 80)  # A shrinks from 100 to 60

    assert a.target_rect.width == 60
    assert b.target_rect.x == 60, f"B should follow A's right edge, got x={b.target_rect.x}"


# ---------------------------------------------------------------------------
# Edge contact: monitor below
# ---------------------------------------------------------------------------


def test_below_monitor_follows_taller():
    """Monitor B below A: A grows taller → B shifts down."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(0, 80, 100, 80)  # touching a.bottom
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 100, 120)  # A grows from 80 to 120

    assert a.target_rect.height == 120
    assert b.target_rect.y == 120, f"B should follow A's bottom edge, got y={b.target_rect.y}"


def test_below_monitor_follows_shorter():
    """Monitor B below A: A shrinks → B shifts up."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(0, 80, 100, 80)
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 100, 50)  # A shrinks from 80 to 50

    assert a.target_rect.height == 50
    assert b.target_rect.y == 50, f"B should follow A's bottom edge, got y={b.target_rect.y}"


# ---------------------------------------------------------------------------
# Horizontal centering: monitor centered above
# ---------------------------------------------------------------------------


def test_centered_monitor_stays_centered_wider():
    """Monitor B centered above A: A grows wider → B re-centers."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(10, -40, 80, 40)  # centered: (100-80)//2 = 10
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 200, 80)  # A grows from 100 to 200

    # B should be re-centered: (200-80)//2 = 60
    assert b.target_rect.x == 60, f"B should be re-centered, got x={b.target_rect.x}"


def test_centered_monitor_stays_centered_narrower():
    """Monitor B centered above A: A shrinks → B re-centers."""
    a = _make_screen(0, 0, 200, 80)
    b = _make_screen(60, -40, 80, 40)  # centered: (200-80)//2 = 60
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 100, 80)  # A shrinks from 200 to 100

    # B should be re-centered: (100-80)//2 = 10
    assert b.target_rect.x == 10, f"B should be re-centered, got x={b.target_rect.x}"


# ---------------------------------------------------------------------------
# Monitor to the left should NOT move
# ---------------------------------------------------------------------------


def test_left_monitor_does_not_move():
    """Monitor B to the left of A: A changes width → B stays put."""
    a = _make_screen(100, 0, 100, 80)
    b = _make_screen(0, 0, 100, 80)  # b.right == a.left == 100
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 150, 80)  # A grows wider (extends right)

    # B is to the left, a.left didn't change, B should not move
    assert b.target_rect.x == 0, f"B should not move, got x={b.target_rect.x}"
    assert b.target_rect.y == 0


# ---------------------------------------------------------------------------
# Vertical centering: monitor to the right, vertically centered
# ---------------------------------------------------------------------------


def test_vertical_centering_preserved():
    """Monitor B to the right, vertically centered on A: A changes height → B re-centers."""
    a = _make_screen(0, 0, 100, 100)
    b = _make_screen(100, 30, 80, 40)  # vertically centered: (100-40)//2 = 30
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 100, 200)  # A grows taller

    # B should be vertically re-centered: (200-40)//2 = 80
    assert b.target_rect.y == 80, f"B should be vertically centered, got y={b.target_rect.y}"


def test_vertical_centering_preserved_shrink():
    """Monitor B to the right, vertically centered: A shrinks → B re-centers."""
    a = _make_screen(0, 0, 100, 200)
    b = _make_screen(100, 80, 80, 40)  # vertically centered: (200-40)//2 = 80
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 100, 100)  # A shrinks

    # B should be vertically re-centered: (100-40)//2 = 30
    assert b.target_rect.y == 30, f"B should be vertically centered, got y={b.target_rect.y}"


# ---------------------------------------------------------------------------
# Corner contact: monitor at bottom-right
# ---------------------------------------------------------------------------


def test_corner_contact_both_axes():
    """Monitor B at bottom-right of A: both x and y follow."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(100, 80, 100, 80)  # touching right and bottom
    ui = _make_ui(a, b)

    UI._resize_screen(ui, 150, 120)  # A grows in both dimensions

    assert b.target_rect.x == 150, f"B.x should follow right edge, got {b.target_rect.x}"
    assert b.target_rect.y == 120, f"B.y should follow bottom edge, got {b.target_rect.y}"


# ---------------------------------------------------------------------------
# Corner anchor: small screen on top of big screen (bottom-right to top-right)
# ---------------------------------------------------------------------------


def test_corner_anchor_small_on_top_shrink():
    """B sits on top of A with B's bottom-right anchored to A's top-right.
    B shrinks → B moves to maintain the anchor point."""
    a = _make_screen(0, 0, 400, 300)
    b = _make_screen(200, -100, 200, 100)  # B.bottom_right == A.top_right == (400, 0)
    ui = _make_ui(b, a)

    UI._resize_screen(ui, 150, 80)  # B shrinks

    # B's bottom-right should still be at (400, 0)
    assert b.target_rect.x + b.target_rect.width == 400, f"B.right should be 400, got {b.target_rect.x + b.target_rect.width}"
    assert b.target_rect.y + b.target_rect.height == 0, f"B.bottom should be 0, got {b.target_rect.y + b.target_rect.height}"
    # A should not move
    assert a.target_rect.x == 0
    assert a.target_rect.y == 0


def test_corner_anchor_small_on_top_grow():
    """B sits on top of A with B's bottom-right anchored to A's top-right.
    B grows → B moves to maintain the anchor point."""
    a = _make_screen(0, 0, 400, 300)
    b = _make_screen(200, -100, 200, 100)
    ui = _make_ui(b, a)

    UI._resize_screen(ui, 300, 150)  # B grows

    # B's bottom-right should still be at (400, 0)
    assert b.target_rect.x + b.target_rect.width == 400, f"B.right should be 400, got {b.target_rect.x + b.target_rect.width}"
    assert b.target_rect.y + b.target_rect.height == 0, f"B.bottom should be 0, got {b.target_rect.y + b.target_rect.height}"
    # A should not move
    assert a.target_rect.x == 0
    assert a.target_rect.y == 0


# ---------------------------------------------------------------------------
# Multiple monitors
# ---------------------------------------------------------------------------


def test_chain_of_monitors_horizontal():
    """A-B-C in a row: A grows → B and C both shift right."""
    a = _make_screen(0, 0, 100, 80)
    b = _make_screen(100, 0, 100, 80)
    c = _make_screen(200, 0, 100, 80)
    ui = _make_ui(a, b, c)

    UI._resize_screen(ui, 150, 80)  # A grows from 100 to 150

    assert b.target_rect.x == 150, f"B should follow A, got x={b.target_rect.x}"
    assert c.target_rect.x == 250, f"C should follow B, got x={c.target_rect.x}"
