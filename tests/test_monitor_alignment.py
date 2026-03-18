"""Tests for monitor alignment and output coordinate correctness.

Verifies that:
- Two edge-to-edge monitors produce correct non-overlapping positions
- The full pipeline (UI coords → scaled → trim_rects_flip_y → command) is correct
"""

import re
import sys

sys.path.insert(0, "src")

from pyggets import Rect  # noqa: E402
from wlr_layout_ui.settings import UI_RATIO  # noqa: E402
from wlr_layout_ui.types import Mode, Screen  # noqa: E402
from wlr_layout_ui.utils import make_command_hyprland, make_command_legacy, trim_rects_flip_y  # noqa: E402


def _parse_hyprland_positions(cmd: str) -> dict[str, tuple[int, int]]:
    """Parse hyprctl batch command and return {uid: (x, y)} for each monitor."""
    positions = {}
    for match in re.finditer(r"keyword monitor (\S+?),\S+?,(\d+)x(\d+),", cmd):
        uid, x, y = match.group(1), int(match.group(2)), int(match.group(3))
        positions[uid] = (x, y)
    return positions


def _parse_legacy_positions(cmd: str) -> dict[str, tuple[int, int]]:
    """Parse wlr-randr/xrandr command and return {uid: (x, y)} for each monitor."""
    positions = {}
    for match in re.finditer(r"--output (\S+) --on --pos (\d+)[,x](\d+)", cmd):
        uid, x, y = match.group(1), int(match.group(2)), int(match.group(3))
        positions[uid] = (x, y)
    return positions


def _make_screen(uid: str, width: int = 1920, height: int = 1080, freq: float = 60.0) -> Screen:
    """Create a Screen with a single mode, active by default."""
    mode = Mode(width, height, freq)
    return Screen(uid=uid, name=uid, active=True, mode=mode, available=[mode])


# ---------------------------------------------------------------------------
# trim_rects_flip_y tests
# ---------------------------------------------------------------------------


def test_trim_rects_flip_y_two_monitors_horizontal():
    """Two monitors side-by-side: Y-flip should place both at y=0."""
    # Same height, side by side
    rects = [Rect(0, 0, 1920, 1080), Rect(1920, 0, 1920, 1080)]
    trim_rects_flip_y(rects)
    # Both should be at y=0 (same height, aligned at bottom in Y-up = top in Y-down)
    assert rects[0].x == 0
    assert rects[0].y == 0
    assert rects[1].x == 1920
    assert rects[1].y == 0


def test_trim_rects_flip_y_two_monitors_vertical():
    """Two monitors stacked: Y-flip converts Y-up to Y-down coordinates."""
    # In Y-up: monitor A is on top (y=1080), monitor B is on bottom (y=0)
    rects = [Rect(0, 1080, 1920, 1080), Rect(0, 0, 1920, 1080)]
    trim_rects_flip_y(rects)
    # After flip to Y-down: A should be at y=0 (top), B at y=1080 (bottom)
    assert rects[0].y == 0
    assert rects[1].y == 1080


def test_trim_rects_flip_y_preserves_relative_gap():
    """A gap between monitors in Y-up is preserved after Y-flip."""
    gap = 8
    # In Y-up: A at top (y=1080+gap), B at bottom (y=0)
    rects = [Rect(0, 1080 + gap, 1920, 1080), Rect(0, 0, 1920, 1080)]
    trim_rects_flip_y(rects)
    # After flip: A at y=0, B at y=1080+gap
    assert rects[0].y == 0
    assert rects[1].y == 1080 + gap


# ---------------------------------------------------------------------------
# Horizontal alignment tests (full pipeline through make_command)
# ---------------------------------------------------------------------------


def test_horizontal_alignment_no_gap():
    """Monitor A (width=W) at left, Monitor B to the right → B.x == W, no overlap."""
    W = 1920
    H = 1080  # same height for simplicity
    screen_a = _make_screen("HDMI-A-1", width=W, height=H)
    screen_b = _make_screen("DP-1", width=2560, height=H)

    # UI coordinates: A at x=0, B at x=W/UI_RATIO (edge-to-edge, Y-up)
    ui_w_a = W // UI_RATIO
    ui_h = H // UI_RATIO
    rect_a = Rect(0, 0, ui_w_a, ui_h)
    rect_b = Rect(ui_w_a, 0, 2560 // UI_RATIO, ui_h)

    # Scale back to real pixels
    real_rects = [rect_a.scaled(UI_RATIO), rect_b.scaled(UI_RATIO)]

    cmd = make_command_hyprland([screen_a, screen_b], real_rects)
    positions = _parse_hyprland_positions(cmd)

    assert positions["HDMI-A-1"] == (0, 0), f"Expected (0, 0), got {positions['HDMI-A-1']}"
    assert positions["DP-1"][0] == W, f"Expected x={W}, got x={positions['DP-1'][0]}"


# ---------------------------------------------------------------------------
# Vertical alignment tests (full pipeline through make_command)
# ---------------------------------------------------------------------------


def test_vertical_alignment_no_gap():
    """Monitor A (height=H) on top, Monitor B below → B.y == H (Y-down output)."""
    H = 1440
    screen_a = _make_screen("HDMI-A-1", width=2560, height=H)
    screen_b = _make_screen("DP-1", width=2560, height=H)

    ui_h = H // UI_RATIO  # 180
    ui_w = 2560 // UI_RATIO  # 320

    # Y-up UI: A is on top (y=ui_h), B is on bottom (y=0)
    rect_a = Rect(0, ui_h, ui_w, ui_h)
    rect_b = Rect(0, 0, ui_w, ui_h)

    real_rects = [rect_a.scaled(UI_RATIO), rect_b.scaled(UI_RATIO)]

    cmd = make_command_hyprland([screen_a, screen_b], real_rects)
    positions = _parse_hyprland_positions(cmd)

    assert positions["HDMI-A-1"] == (0, 0), f"Expected (0, 0), got {positions['HDMI-A-1']}"
    assert positions["DP-1"] == (0, H), f"Expected (0, {H}), got {positions['DP-1']}"


def test_vertical_alignment_with_8px_gap():
    """With 8px margin, Monitor B below should be at y == H + 8 (Y-down output)."""
    H = 1440
    screen_a = _make_screen("HDMI-A-1", width=2560, height=H)
    screen_b = _make_screen("DP-1", width=2560, height=H)

    ui_h = H // UI_RATIO
    ui_w = 2560 // UI_RATIO
    gap_ui = 8.0 / UI_RATIO  # 1.0 UI pixels = 8 real pixels

    rect_a = Rect(0, ui_h + gap_ui, ui_w, ui_h)
    rect_b = Rect(0, 0, ui_w, ui_h)

    real_rects = [rect_a.scaled(UI_RATIO), rect_b.scaled(UI_RATIO)]

    cmd = make_command_hyprland([screen_a, screen_b], real_rects)
    positions = _parse_hyprland_positions(cmd)

    assert positions["HDMI-A-1"] == (0, 0)
    assert positions["DP-1"] == (0, H + 8), f"Expected (0, {H + 8}), got {positions['DP-1']}"


# ---------------------------------------------------------------------------
# Legacy command (wlr-randr / xrandr) tests
# ---------------------------------------------------------------------------


def test_legacy_horizontal_alignment_no_gap():
    """Legacy command: Monitor B at x == W for edge-to-edge."""
    W = 1920
    H = 1080
    screen_a = _make_screen("HDMI-A-1", width=W, height=H)
    screen_b = _make_screen("DP-1", width=2560, height=H)

    ui_w_a = W // UI_RATIO
    ui_h = H // UI_RATIO
    rect_a = Rect(0, 0, ui_w_a, ui_h)
    rect_b = Rect(ui_w_a, 0, 2560 // UI_RATIO, ui_h)

    real_rects = [rect_a.scaled(UI_RATIO), rect_b.scaled(UI_RATIO)]

    cmd = make_command_legacy([screen_a, screen_b], real_rects, wayland=True)
    positions = _parse_legacy_positions(cmd)

    assert positions["HDMI-A-1"] == (0, 0)
    assert positions["DP-1"][0] == W


# ---------------------------------------------------------------------------
# Hyprland command format tests
# ---------------------------------------------------------------------------


def test_hyprland_no_trailing_semicolon():
    """The hyprctl batch command should not have a trailing semicolon."""
    screen_a = _make_screen("HDMI-A-1")
    screen_b = _make_screen("DP-1")

    rects = [Rect(0, 0, 1920, 1080), Rect(1920, 0, 1920, 1080)]
    cmd = make_command_hyprland([screen_a, screen_b], rects)

    # Should end with the closing quote, not '; "'
    assert cmd.endswith('"')
    assert not cmd.endswith('; "')
    assert "; ;" not in cmd


def test_hyprland_single_monitor_no_semicolon():
    """A single monitor should produce no semicolons at all."""
    screen = _make_screen("HDMI-A-1")
    rects = [Rect(0, 0, 1920, 1080)]
    cmd = make_command_hyprland([screen], rects)

    assert ";" not in cmd


def test_hyprland_disabled_monitor():
    """Disabled monitors should appear as 'keyword monitor UID,disable'."""
    screen = _make_screen("HDMI-A-1")
    screen.active = False
    rects = [Rect(0, 0, 1920, 1080)]
    cmd = make_command_hyprland([screen], rects)

    assert "HDMI-A-1,disable" in cmd


# ---------------------------------------------------------------------------
# Rect.scaled correctness
# ---------------------------------------------------------------------------


def test_rect_scaled_preserves_integer_coords():
    """Scaling integer UI coords by UI_RATIO gives exact integer results."""
    r = Rect(240, 135, 320, 180)
    scaled = r.scaled(UI_RATIO)
    assert scaled.x == 1920
    assert scaled.y == 1080
    assert scaled.width == 2560
    assert scaled.height == 1440


# ---------------------------------------------------------------------------
# Collide: edge-to-edge should NOT collide
# ---------------------------------------------------------------------------


def test_collide_edge_to_edge_horizontal():
    """Two rects touching at x boundary should not collide."""
    a = Rect(0, 0, 100, 100)
    b = Rect(100, 0, 100, 100)
    assert not a.collide(b), "Edge-to-edge rects should NOT collide"
    assert not b.collide(a), "Edge-to-edge rects should NOT collide (reverse)"


def test_collide_edge_to_edge_vertical():
    """Two rects touching at y boundary should not collide."""
    a = Rect(0, 0, 100, 100)
    b = Rect(0, 100, 100, 100)
    assert not a.collide(b), "Edge-to-edge rects should NOT collide"
    assert not b.collide(a), "Edge-to-edge rects should NOT collide (reverse)"


def test_collide_overlapping():
    """Two overlapping rects should collide."""
    a = Rect(0, 0, 100, 100)
    b = Rect(50, 50, 100, 100)
    assert a.collide(b)
    assert b.collide(a)
