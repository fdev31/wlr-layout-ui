"""Tests that loading a profile refreshes the top panel for the selected screen.

Regression test: switching profiles (e.g. via TAB) used to leave the
resolution / rate / transform / scale dropdowns showing stale values.
"""

import pytest

from wlr_layout_ui import screens, settings
from wlr_layout_ui.gui import UI
from wlr_layout_ui.types import Mode, Screen


def _make_screen(uid, name, modes, cur_mode, scale=1.0, transform=0, position=(0, 0)):
    return Screen(
        uid=uid,
        name=name,
        active=True,
        position=position,
        mode=cur_mode,
        scale=scale,
        available=modes,
        transform=transform,
    )


def _build_ui():
    settings.SCREEN_SCALE = 8

    modes_a = [Mode(1920, 1080, 60.0), Mode(2560, 1440, 60.0)]
    screen_a = _make_screen("HDMI-A-1", "Monitor A", modes_a, modes_a[0], scale=1.0, transform=0, position=(0, 0))
    modes_b = [Mode(1920, 1080, 60.0), Mode(2560, 1440, 144.0)]
    screen_b = _make_screen("DP-1", "Monitor B", modes_b, modes_b[0], scale=1.0, transform=0, position=(1920, 0))

    screens.displayInfo.clear()
    screens.displayInfo.extend([screen_a, screen_b])

    return UI(800, 600)


def _profile_entry(uid, name, width, height, freq, x, y, scale, transform, active=True):
    return {
        "name": name,
        "active": active,
        "width": width,
        "height": height,
        "freq": freq,
        "x": x,
        "y": y,
        "uid": uid,
        "scale": scale,
        "transform": transform,
    }


def test_profile_load_updates_panel():
    ui = _build_ui()

    gs_a = next(gs for gs in ui.gui_screens if gs.screen.uid == "HDMI-A-1")
    ui.action_select_screen(gs_a)

    # Panel reflects the initial mode (1920x1080, scale 1.0, transform 0)
    assert ui.resolutions.get_selected_option()["value"] == (1920, 1080)
    assert ui.scale_ratio.get_selected_option()["value"] == pytest.approx(1.0)
    assert ui.rotation.get_selected_option()["value"] == 0

    # A profile that changes screen A to 2560x1440@60, scale 1.25, transform 1
    profile_data = [
        _profile_entry("HDMI-A-1", "Monitor A", 2560, 1440, 60.0, 0, 0, 1.25, 1),
        _profile_entry("DP-1", "Monitor B", 1920, 1080, 60.0, 2560, 0, 1.0, 0),
    ]
    ui.profile_list.options = [{"name": "test_profile", "value": profile_data}]
    ui.profile_list.selected_index = 0

    # Simulate the mouse having been released after selection
    gs_a.dragging = False

    ui.action_load_selected_profile()

    # Screen data updated
    assert gs_a.screen.mode.width == 2560
    assert gs_a.screen.mode.height == 1440
    assert gs_a.screen.scale == pytest.approx(1.25)
    assert gs_a.screen.transform == 1

    # Panel refreshed to match
    assert ui.resolutions.get_selected_option()["value"] == (2560, 1440)
    assert ui.scale_ratio.get_selected_option()["value"] == pytest.approx(1.25)
    assert ui.rotation.get_selected_option()["value"] == 1

    # Loading a profile must not re-enter drag mode (no unwanted side effects)
    assert gs_a.dragging is False


def test_tab_cycle_updates_panel():
    ui = _build_ui()

    gs_a = next(gs for gs in ui.gui_screens if gs.screen.uid == "HDMI-A-1")
    ui.action_select_screen(gs_a)

    profiles = [
        [
            _profile_entry("HDMI-A-1", "Monitor A", 1920, 1080, 60.0, 0, 0, 1.0, 0),
            _profile_entry("DP-1", "Monitor B", 1920, 1080, 60.0, 1920, 0, 1.0, 0),
        ],
        [
            _profile_entry("HDMI-A-1", "Monitor A", 2560, 1440, 144.0, 0, 0, 1.6, 3),
            _profile_entry("DP-1", "Monitor B", 2560, 1440, 60.0, 2560, 0, 1.0, 0),
        ],
    ]
    ui.profile_list.options = [{"name": "p0", "value": profiles[0]}, {"name": "p1", "value": profiles[1]}]
    ui.profile_list.selected_index = 0

    # Simulate the mouse having been released after selection
    gs_a.dragging = False

    # Simulate TAB: advance selection then load
    ui.profile_list.selected_index = 1
    ui.action_load_selected_profile()

    assert gs_a.screen.mode.width == 2560
    assert gs_a.screen.mode.height == 1440
    assert ui.resolutions.get_selected_option()["value"] == (2560, 1440)
    assert ui.scale_ratio.get_selected_option()["value"] == pytest.approx(1.6)
    assert ui.rotation.get_selected_option()["value"] == 3
    assert gs_a.dragging is False
