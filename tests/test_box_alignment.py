"""Tests for HBox/VBox alignment and Widget animation infrastructure."""

import sys

sys.path.insert(0, "src")

import pyglet  # noqa: E402

pyglet.options["headless"] = True

from pyggets import HBox, Rect, VBox  # noqa: E402
from pyggets.widgets import Widget  # noqa: E402


class DummyWidget(Widget):
    """A widget with a no-op draw for testing layout positioning."""

    def draw(self, cursor):
        pass


# -- HBox alignment tests --


def test_hbox_default_bottom_aligned():
    """No align param: all children bottom-aligned."""
    tall = DummyWidget(Rect(0, 0, 40, 80), None)
    short = DummyWidget(Rect(0, 0, 40, 20), None)
    hbox = HBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[tall, short])
    hbox.draw((0, 0))

    # Both should share the same bottom (hbox.y + padding)
    assert tall.rect.y == hbox.rect.y + hbox.padding
    assert short.rect.y == hbox.rect.y + hbox.padding


def test_hbox_align_top():
    """align='top': all children top-aligned."""
    tall = DummyWidget(Rect(0, 0, 40, 80), None)
    short = DummyWidget(Rect(0, 0, 40, 20), None)
    hbox = HBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[tall, short], align="top")
    hbox.draw((0, 0))

    top_edge = hbox.rect.y + hbox.rect.height - hbox.padding
    assert tall.rect.y + tall.rect.height == top_edge
    assert short.rect.y + short.rect.height == top_edge


def test_hbox_align_center():
    """align='center': all children vertically centered."""
    tall = DummyWidget(Rect(0, 0, 40, 80), None)
    short = DummyWidget(Rect(0, 0, 40, 20), None)
    hbox = HBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[tall, short], align="center")
    hbox.draw((0, 0))

    # Center of each child should match center of hbox
    hbox_center = hbox.rect.y + hbox.rect.height // 2
    tall_center = tall.rect.y + tall.rect.height // 2
    short_center = short.rect.y + short.rect.height // 2
    assert tall_center == hbox_center
    assert short_center == hbox_center


def test_hbox_child_valign_override():
    """align='top' on HBox + one child valign='bottom': mixed alignment."""
    tall = DummyWidget(Rect(0, 0, 40, 80), None)
    short = DummyWidget(Rect(0, 0, 40, 20), None)
    short.valign = "bottom"
    hbox = HBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[tall, short], align="top")
    hbox.draw((0, 0))

    # tall should be top-aligned
    top_edge = hbox.rect.y + hbox.rect.height - hbox.padding
    assert tall.rect.y + tall.rect.height == top_edge

    # short should be bottom-aligned (overridden)
    assert short.rect.y == hbox.rect.y + hbox.padding


def test_hbox_align_top_not_blocked_by_default():
    """Regression: plain widgets (valign=None) with HBox align='top' must top-align."""
    w1 = DummyWidget(Rect(0, 0, 40, 30), None)
    w2 = DummyWidget(Rect(0, 0, 40, 60), None)
    # Neither widget sets valign — they should use HBox's align
    assert w1.valign is None
    assert w2.valign is None

    hbox = HBox(rect=Rect(0, 0, 0, 0), padding=4, widgets=[w1, w2], align="top")
    hbox.draw((0, 0))

    top_edge = hbox.rect.y + hbox.rect.height - hbox.padding
    assert w1.rect.y + w1.rect.height == top_edge
    assert w2.rect.y + w2.rect.height == top_edge


# -- VBox alignment tests --


def test_vbox_default_left_aligned():
    """No align param: all children left-aligned."""
    wide = DummyWidget(Rect(0, 0, 120, 20), None)
    narrow = DummyWidget(Rect(0, 0, 40, 20), None)
    vbox = VBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[wide, narrow])
    vbox.draw((0, 0))

    assert wide.rect.x == vbox.rect.x + vbox.padding
    assert narrow.rect.x == vbox.rect.x + vbox.padding


def test_vbox_align_right():
    """align='right': all children right-aligned."""
    wide = DummyWidget(Rect(0, 0, 120, 20), None)
    narrow = DummyWidget(Rect(0, 0, 40, 20), None)
    vbox = VBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[wide, narrow], align="right")
    vbox.draw((0, 0))

    right_edge = vbox.rect.x + vbox.rect.width - vbox.padding
    assert wide.rect.x + wide.rect.width == right_edge
    assert narrow.rect.x + narrow.rect.width == right_edge


def test_vbox_child_halign_override():
    """align='right' on VBox + one child halign='left': mixed alignment."""
    wide = DummyWidget(Rect(0, 0, 120, 20), None)
    narrow = DummyWidget(Rect(0, 0, 40, 20), None)
    narrow.halign = "left"
    vbox = VBox(rect=Rect(10, 10, 0, 0), padding=4, widgets=[wide, narrow], align="right")
    vbox.draw((0, 0))

    right_edge = vbox.rect.x + vbox.rect.width - vbox.padding
    assert wide.rect.x + wide.rect.width == right_edge
    assert narrow.rect.x == vbox.rect.x + vbox.padding


# -- Widget property tests --


def test_widget_valign_halign_default_none():
    """Fresh Widget has valign=None, halign=None."""
    w = DummyWidget(Rect(0, 0, 10, 10), None)
    assert w.valign is None
    assert w.halign is None


def test_set_alignment_sets_values():
    """set_alignment() stores values correctly."""
    w = DummyWidget(Rect(0, 0, 10, 10), None)
    w.set_alignment("top", "right")
    assert w.valign == "top"
    assert w.halign == "right"


def test_update_alignment_defaults_when_none():
    """update_alignment() with None defaults to bottom-left."""
    w = DummyWidget(Rect(0, 0, 50, 50), None)
    w.update_alignment(0, 0, 800, 600)
    # bottom-left with margin=0: x=0, y=0
    assert w.rect.x == 0
    assert w.rect.y == 0


# -- Animation tests --


def test_animation_step():
    """_animation_step() moves rect toward target."""
    w = DummyWidget(Rect(0, 0, 100, 100), None)
    w.target_rect = Rect(100, 100, 200, 200)

    still_animating = w._animation_step()
    assert still_animating is True

    # Rect should have moved toward target but not reached it yet
    assert 0 < w.rect.x < 100
    assert 0 < w.rect.y < 100
    assert 100 < w.rect.width < 200
    assert 100 < w.rect.height < 200


def test_animate_to():
    """animate_to(x=100) sets target_rect with only x changed."""
    w = DummyWidget(Rect(10, 20, 30, 40), None)
    w.animate_to(x=100)

    assert w.target_rect is not None
    assert w.target_rect.x == 100
    # Other values copied from original rect
    assert w.target_rect.y == 20
    assert w.target_rect.width == 30
    assert w.target_rect.height == 40


def test_find_matching_mode_exact():
    """find_matching_mode returns exact match when available."""
    from wlr_layout_ui.types import Mode
    from wlr_layout_ui.utils import find_matching_mode

    modes = [Mode(1920, 1080, 60.0), Mode(1920, 1080, 120.0), Mode(2560, 1440, 60.0)]
    assert find_matching_mode(modes, (1920, 1080), 60.0) == modes[0]
    assert find_matching_mode(modes, (1920, 1080), 120.0) == modes[1]
    assert find_matching_mode(modes, (2560, 1440), 60.0) == modes[2]


def test_find_matching_mode_fallback_closest_freq():
    """find_matching_mode falls back to closest frequency at same resolution."""
    from wlr_layout_ui.types import Mode
    from wlr_layout_ui.utils import find_matching_mode

    modes = [Mode(1920, 1080, 119.88), Mode(1920, 1080, 144.0)]
    result = find_matching_mode(modes, (1920, 1080), 60.0)
    # 119.88 is closer to 60.0 than 144.0
    assert result == modes[0]


def test_find_matching_mode_no_match():
    """find_matching_mode returns None when no resolution matches."""
    from wlr_layout_ui.types import Mode
    from wlr_layout_ui.utils import find_matching_mode

    modes = [Mode(1920, 1080, 60.0)]
    assert find_matching_mode(modes, (2560, 1440), 60.0) is None
