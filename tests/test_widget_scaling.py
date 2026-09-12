"""Tests that Slider/Toggle/Checkbox/RadioGroup recompute derived pixel
metrics and owned-shape sizes when the UI scale changes.

The widgets cache metrics (track thickness, knob radius, box size, ...) derived
from their rect and own persistent pyglet shapes.  ``resize()`` must recompute
those from the current rect (with fixed caps scaled by the theme scale) so the
widgets scale correctly instead of staying at their base size.
"""

from dataclasses import replace

from pyggets import Checkbox, RadioGroup, Rect, Slider, Toggle
from pyggets.theme import get_default_theme, set_default_theme


def _set_scale(scale: float):
    set_default_theme(replace(get_default_theme(), scale=scale))


# -- Slider --


def test_slider_scale1_metrics():
    """At scale 1 the metrics match the original (pre-refactor) values."""
    s = Slider(Rect(0, 0, 200, 20), value=50)
    assert s._handle_radius == 8  # min(20 // 2, 8)
    assert s._track_height == 5  # max(20 // 4, 2)
    assert s._track_bg.height == 5
    assert s._handle_shape.radius == 8


def test_slider_scale2_metrics():
    """At scale 2 the handle cap (8) and track thickness scale up."""
    s = Slider(Rect(0, 0, 200, 20), value=50)
    _set_scale(2.0)
    s.rect.width = 400
    s.rect.height = 40
    s.resize()
    assert s._handle_radius == 16  # min(40 // 2, int(8 * 2))
    assert s._track_height == 10  # max(40 // 4, 2)
    assert s._track_bg.height == 10
    assert s._track_fill_shape.height == 10
    assert s._handle_shape.radius == 16


# -- Toggle --


def test_toggle_scale1_metrics():
    t = Toggle(Rect(0, 0, 60, 20))
    assert t._track_height == 13  # max(20 * 2 // 3, 8)
    assert t._track_width == 20
    assert t._knob_radius == 6  # 13 // 2
    assert t._track_left.radius == 6
    assert t._track_fill.height == 13
    assert t._track_fill.width == 8  # 20 - 2 * 6


def test_toggle_scale2_metrics():
    t = Toggle(Rect(0, 0, 60, 20))
    _set_scale(2.0)
    t.rect.width = 120
    t.rect.height = 40
    t.resize()
    assert t._track_height == 26  # max(40 * 2 // 3, 8)
    assert t._track_width == 40
    assert t._knob_radius == 13  # 26 // 2
    assert t._track_left.radius == 13
    assert t._track_right.radius == 13
    assert t._track_fill.height == 26
    assert t._track_fill.width == 14  # 40 - 2 * 13
    assert t._knob_shape.radius == 11  # 13 - 2


# -- Checkbox --


def test_checkbox_scale1_metrics():
    c = Checkbox(Rect(0, 0, 40, 20))
    assert c._box_size == 20  # min(20, 40, int(20 * 1))


def test_checkbox_scale2_metrics():
    c = Checkbox(Rect(0, 0, 40, 20))
    _set_scale(2.0)
    c.rect.width = 80
    c.rect.height = 40
    c.resize()
    assert c._box_size == 40  # min(40, 80, int(20 * 2))


# -- RadioGroup --


def test_radiogroup_scale1_metrics():
    r = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"])
    # vertical: divisor = 3 * 2 = 6 -> min(80 // 6, 8) = 8
    assert r._radio_radius == 8


def test_radiogroup_scale2_metrics():
    r = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"])
    _set_scale(2.0)
    r.rect.height = 160
    r.resize()
    # min(160 // 6, int(8 * 2)) = min(26, 16) = 16
    assert r._radio_radius == 16


# -- General behaviour --


def test_resize_idempotent():
    """Calling resize() repeatedly is stable."""
    s = Slider(Rect(0, 0, 200, 20), value=50)
    _set_scale(1.5)
    s.rect.height = 30
    s.resize()
    first = (s._handle_radius, s._track_height)
    s.resize()
    assert (s._handle_radius, s._track_height) == first


def test_draw_after_scale():
    """draw() runs without error after a scale change (it calls resize())."""
    s = Slider(Rect(0, 0, 200, 20), value=50)
    t = Toggle(Rect(0, 0, 60, 20))
    c = Checkbox(Rect(0, 0, 40, 20), label="x")
    r = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"])

    _set_scale(2.0)
    for w in (s, t, c, r):
        w.rect.width *= 2
        w.rect.height *= 2

    s.draw((10, 10))
    t.draw((10, 10))
    c.draw((10, 10))
    r.draw((10, 10))
