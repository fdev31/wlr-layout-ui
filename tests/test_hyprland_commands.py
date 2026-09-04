"""Tests for hyprland IPC command generation.

Verifies both the legacy keyword format and the new Lua hl.monitor() format.
"""

import sys

sys.path.insert(0, "src")

from pyggets import Rect
from wlr_layout_ui.types import Mode, Screen
from wlr_layout_ui.utils import (
    _make_command_hyprland_lua,
    _make_command_hyprland_old,
)


def _make_screen(uid="DP-1", active=True, mode=None, scale=1.0, transform=0):
    """Create a minimal Screen for testing."""
    return Screen(uid=uid, name=f"test-{uid}", active=active, mode=mode, scale=scale, transform=transform)


def _make_rect(x=0, y=0, width=1920, height=1080):
    """Create a minimal Rect for testing."""
    return Rect(x, y, width, height)


class TestOldSyntax:
    """Tests for the fallback hl.monitor() syntax (single quotes)."""

    def test_full_command(self):
        # trim_rects_flip_y normalizes positions to bounding box, so (1920, 0) becomes (0, 0)
        screen = _make_screen(mode=Mode(1920, 1080, 60.0), scale=1.5, transform=1)
        rect = _make_rect(1920, 0)
        cmd = " ".join(_make_command_hyprland_old([screen], [rect]))
        assert "hyprctl eval" in cmd
        assert "hl.monitor" in cmd
        assert "output = 'DP-1'" in cmd
        assert "mode = '1920x1080@60.00Hz'" in cmd
        assert "position = '0x0'" in cmd
        assert "scale = 1.500000" in cmd
        assert "transform = 1" in cmd

    def test_disabled_monitor(self):
        screen = _make_screen(active=False)
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_old([screen], [rect]))
        assert "output = 'DP-1'" in cmd
        assert "disabled = true" in cmd

    def test_multiple_monitors(self):
        s1 = _make_screen(uid="DP-1", mode=Mode(1920, 1080, 60.0), scale=1.0)
        s2 = _make_screen(uid="HDMI-A-1", mode=Mode(2560, 1440, 144.0), scale=2.0, transform=2)
        r1 = _make_rect(0, 0)
        r2 = _make_rect(1920, 0)
        cmd = " ".join(_make_command_hyprland_old([s1, s2], [r1, r2]))
        assert "output = 'DP-1'" in cmd
        assert "output = 'HDMI-A-1'" in cmd
        assert "mode = '1920x1080@60.00Hz'" in cmd
        assert "mode = '2560x1440@144.00Hz'" in cmd
        assert "position = '0x0'" in cmd
        assert "position = '1920x0'" in cmd

    def test_semicolon_separator(self):
        s1 = _make_screen(mode=Mode(1920, 1080, 60.0))
        s2 = _make_screen(uid="HDMI-A-1", mode=Mode(1920, 1080, 60.0))
        r1 = _make_rect(0, 0)
        r2 = _make_rect(1920, 0)
        cmd = " ".join(_make_command_hyprland_old([s1, s2], [r1, r2]))
        assert " ; " in cmd


class TestLuaSyntax:
    """Tests for the new Lua hl.monitor() syntax (double quotes)."""

    def test_full_command(self):
        # Use two monitors so trim_rects_flip_y produces non-zero position for second monitor
        s1 = _make_screen(uid="DP-1", mode=Mode(1920, 1080, 60.0))
        s2 = _make_screen(uid="HDMI-A-1", mode=Mode(1920, 1080, 60.0), scale=1.5, transform=1)
        r1 = _make_rect(0, 0)
        r2 = _make_rect(1920, 0)
        cmd = " ".join(_make_command_hyprland_lua([s1, s2], [r1, r2]))
        assert "hyprctl eval" in cmd
        assert 'output="DP-1"' in cmd
        assert 'output="HDMI-A-1"' in cmd
        assert 'mode="1920x1080@60.00Hz"' in cmd
        assert 'position="0x0"' in cmd
        assert 'position="1920x0"' in cmd
        assert "scale=1.5" in cmd
        assert "transform=1" in cmd

    def test_disabled_monitor(self):
        screen = _make_screen(active=False)
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_lua([screen], [rect]))
        assert 'disabled=true' in cmd

    def test_default_scale_omitted(self):
        screen = _make_screen(mode=Mode(1920, 1080, 60.0), scale=1.0)
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_lua([screen], [rect]))
        assert "scale=1" in cmd

    def test_position_always_included(self):
        screen = _make_screen(mode=Mode(1920, 1080, 60.0))
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_lua([screen], [rect]))
        assert 'position="0x0"' in cmd

    def test_default_transform_omitted(self):
        screen = _make_screen(mode=Mode(1920, 1080, 60.0), transform=0)
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_lua([screen], [rect]))
        assert "transform=0" in cmd

    def test_multiple_monitors(self):
        s1 = _make_screen(uid="DP-1", mode=Mode(1920, 1080, 60.0))
        s2 = _make_screen(uid="HDMI-A-1", mode=Mode(2560, 1440, 144.0), scale=2.0, transform=2)
        r1 = _make_rect(0, 0)
        r2 = _make_rect(1920, 0)
        cmd = " ".join(_make_command_hyprland_lua([s1, s2], [r1, r2]))
        assert 'output="DP-1"' in cmd
        assert 'output="HDMI-A-1"' in cmd
        assert 'mode="2560x1440@144.00Hz"' in cmd
        assert 'position="0x0"' in cmd
        assert "scale=2" in cmd

    def test_semicolon_separator(self):
        s1 = _make_screen(mode=Mode(1920, 1080, 60.0))
        s2 = _make_screen(uid="HDMI-A-1", mode=Mode(1920, 1080, 60.0))
        r1 = _make_rect(0, 0)
        r2 = _make_rect(1920, 0)
        cmd = " ".join(_make_command_hyprland_lua([s1, s2], [r1, r2]))
        assert "'" in cmd
        assert " ; " in cmd

    def test_scale_precision(self):
        screen = _make_screen(mode=Mode(1920, 1080, 60.0), scale=1.25)
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_lua([screen], [rect]))
        assert "scale=1.25" in cmd
        assert "scale=1.250000" not in cmd

    def test_scale_precision_trailing_zeros(self):
        screen = _make_screen(mode=Mode(1920, 1080, 60.0), scale=1.5)
        rect = _make_rect()
        cmd = " ".join(_make_command_hyprland_lua([screen], [rect]))
        assert "scale=1.5" in cmd
