"""Tests for the keyboard focus system (``FocusManager`` + per-widget keys).

Covers depth-first flattening, traversal wrap-around, focus exclusivity, and the
ENTER / edit-mode / arrow key behavior of each actionable widget.  All tests run
headless (see ``conftest.py`` which sets ``pyglet.options["headless"] = True``).
"""

from pyggets import Button, Checkbox, Dropdown, FocusManager, RadioGroup, Rect, Slider, Toggle, VBox
from pyggets.widgets import (
    _KEY_DOWN,
    _KEY_ESCAPE,
    _KEY_LEFT,
    _KEY_RETURN,
    _KEY_RIGHT,
    _KEY_TAB,
    _KEY_UP,
    _MOD_SHIFT,
)


def _opts(*names):
    """Build Dropdown options (a list of ``{"name", "value"}`` dicts)."""
    return [{"name": n, "value": i} for i, n in enumerate(names)]


# -- 1. Flattening order ---------------------------------------------------


def test_flattening_order_depth_first():
    """A nested VBox flattens depth-first into the focus order."""
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    s = Slider(Rect(0, 0, 100, 20))
    t = Toggle(Rect(0, 0, 60, 20))
    inner = VBox(widgets=[c, s])
    root = VBox(widgets=[b, inner, t])
    fm = FocusManager(root)
    assert fm._order == [b, c, s, t]


# -- 2. Traversal wrap-around ---------------------------------------------


def test_traversal_next_wraps_to_first():
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    t = Toggle(Rect(0, 0, 60, 20))
    fm = FocusManager([b, c, t])
    fm.focus_first()
    assert fm.current is b
    fm.focus_next()
    assert fm.current is c
    fm.focus_next()
    assert fm.current is t
    fm.focus_next()  # wraps to index 0
    assert fm.current is b


def test_traversal_prev_wraps_to_last():
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    t = Toggle(Rect(0, 0, 60, 20))
    fm = FocusManager([b, c, t])
    fm.focus_first()
    assert fm.current is b
    fm.focus_prev()  # from index 0 wraps to last (index 2)
    assert fm.current is t


# -- 3. Focus exclusivity --------------------------------------------------


def test_focus_exclusivity():
    """After each focus_next exactly one widget is focused."""
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    t = Toggle(Rect(0, 0, 60, 20))
    widgets = [b, c, t]
    fm = FocusManager(widgets)
    fm.focus_first()
    for _ in range(5):  # more than len to exercise wrap-around
        fm.focus_next()
        focused = [w for w in widgets if w.focused]
        assert len(focused) == 1


# -- 4. Button ENTER -------------------------------------------------------


def test_button_enter_activates():
    fired = []
    b = Button(Rect(0, 0, 100, 30), action=lambda: fired.append(1))
    fm = FocusManager([b])
    fm.focus_first()
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert fired == [1]


# -- 5. Toggle ENTER -------------------------------------------------------


def test_toggle_enter_flips_and_fires():
    changes = []
    t = Toggle(Rect(0, 0, 60, 20), onchange=changes.append)
    fm = FocusManager([t])
    fm.focus_first()
    assert t.toggled is False
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert t.toggled is True
    assert changes == [True]


# -- 6. Checkbox ENTER -----------------------------------------------------


def test_checkbox_enter_flips_and_fires():
    changes = []
    c = Checkbox(Rect(0, 0, 100, 30), onchange=changes.append)
    fm = FocusManager([c])
    fm.focus_first()
    assert c.checked is False
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert c.checked is True
    assert changes == [True]


# -- 7. Slider edit mode ---------------------------------------------------


def test_slider_not_editing_right_moves_focus():
    s = Slider(Rect(0, 0, 200, 20), value=50)
    b = Button(Rect(0, 0, 100, 30))
    fm = FocusManager([s, b])
    fm.focus_first()
    assert s.editing is False
    assert fm.handle_key(_KEY_RIGHT, 0) is True
    assert fm.current is b  # focus moved, not value
    assert s.value == 50  # value unchanged


def test_slider_enter_enters_editing():
    s = Slider(Rect(0, 0, 200, 20), value=50)
    fm = FocusManager([s])
    fm.focus_first()
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert s.editing is True


def test_slider_editing_right_increases():
    changes = []
    s = Slider(Rect(0, 0, 200, 20), value=50, onchange=changes.append)
    fm = FocusManager([s])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # enter editing
    assert fm.handle_key(_KEY_RIGHT, 0) is True
    assert s.value == 51  # default step is 1
    assert changes == [51]


def test_slider_editing_left_decreases():
    changes = []
    s = Slider(Rect(0, 0, 200, 20), value=50, onchange=changes.append)
    fm = FocusManager([s])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # enter editing
    assert fm.handle_key(_KEY_LEFT, 0) is True
    assert s.value == 49
    assert changes == [49]


def test_slider_exit_editing():
    s = Slider(Rect(0, 0, 200, 20), value=50)
    fm = FocusManager([s])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # enter editing
    assert s.editing is True
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert s.editing is False


def test_slider_escape_exits_editing():
    s = Slider(Rect(0, 0, 200, 20), value=50)
    fm = FocusManager([s])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # enter editing
    assert fm.handle_key(_KEY_ESCAPE, 0) is True
    assert s.editing is False


# -- 8. Dropdown -----------------------------------------------------------


def test_dropdown_enter_expands():
    dd = Dropdown(Rect(0, 0, 100, 30), "sel", _opts("a", "b", "c"))
    fm = FocusManager([dd])
    fm.focus_first()
    assert dd.expanded is False
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert dd.expanded is True


def test_dropdown_down_increments_clamped():
    dd = Dropdown(Rect(0, 0, 100, 30), "sel", _opts("a", "b", "c"))
    fm = FocusManager([dd])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # expand from 0
    assert dd.selected_index == 0
    assert fm.handle_key(_KEY_DOWN, 0) is True
    assert dd.selected_index == 1
    assert fm.handle_key(_KEY_DOWN, 0) is True
    assert dd.selected_index == 2
    assert fm.handle_key(_KEY_DOWN, 0) is True  # clamped
    assert dd.selected_index == 2


def test_dropdown_up_decrements_clamped():
    dd = Dropdown(Rect(0, 0, 100, 30), "sel", _opts("a", "b", "c"))
    dd.selected_index = 2
    fm = FocusManager([dd])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # expand from 2
    assert fm.handle_key(_KEY_UP, 0) is True
    assert dd.selected_index == 1
    assert fm.handle_key(_KEY_UP, 0) is True
    assert dd.selected_index == 0
    assert fm.handle_key(_KEY_UP, 0) is True  # clamped
    assert dd.selected_index == 0


def test_dropdown_return_collapses_fires_onchange_if_changed():
    changes = []
    dd = Dropdown(Rect(0, 0, 100, 30), "sel", _opts("a", "b", "c"), onchange=lambda: changes.append(1))
    fm = FocusManager([dd])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # expand from 0
    fm.handle_key(_KEY_DOWN, 0)  # index -> 1
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert dd.expanded is False
    assert dd.selected_index == 1
    assert changes == [1]  # fired: index changed from 0 to 1


def test_dropdown_return_no_change_no_onchange():
    changes = []
    dd = Dropdown(Rect(0, 0, 100, 30), "sel", _opts("a", "b", "c"), onchange=lambda: changes.append(1))
    fm = FocusManager([dd])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # expand from 0
    assert fm.handle_key(_KEY_RETURN, 0) is True  # collapse, no move
    assert dd.expanded is False
    assert dd.selected_index == 0
    assert changes == []  # not fired


def test_dropdown_escape_collapses_no_onchange():
    changes = []
    dd = Dropdown(Rect(0, 0, 100, 30), "sel", _opts("a", "b", "c"), onchange=lambda: changes.append(1))
    fm = FocusManager([dd])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # expand from 0
    fm.handle_key(_KEY_DOWN, 0)  # index -> 1
    assert fm.handle_key(_KEY_ESCAPE, 0) is True
    assert dd.expanded is False
    assert dd.selected_index == 1  # index kept
    assert changes == []  # not fired on escape


# -- 9. RadioGroup ---------------------------------------------------------


def test_radiogroup_enter_enters_editing():
    rg = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"])
    fm = FocusManager([rg])
    fm.focus_first()
    assert rg.editing is False
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert rg.editing is True


def test_radiogroup_down_changes_and_fires():
    changes = []
    rg = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"], onchange=changes.append)
    fm = FocusManager([rg])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # editing
    assert rg.selected_index == 0
    assert fm.handle_key(_KEY_DOWN, 0) is True
    assert rg.selected_index == 1
    assert changes == [1]


def test_radiogroup_up_changes_and_clamps():
    changes = []
    rg = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"], selected_index=2, onchange=changes.append)
    fm = FocusManager([rg])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # editing
    assert rg.selected_index == 2
    assert fm.handle_key(_KEY_UP, 0) is True
    assert rg.selected_index == 1
    assert fm.handle_key(_KEY_UP, 0) is True
    assert rg.selected_index == 0
    assert fm.handle_key(_KEY_UP, 0) is True  # clamped at 0, no extra fire
    assert rg.selected_index == 0
    assert changes == [1, 0]


def test_radiogroup_return_exits_editing():
    rg = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"])
    fm = FocusManager([rg])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # editing
    assert rg.editing is True
    assert fm.handle_key(_KEY_RETURN, 0) is True
    assert rg.editing is False


def test_radiogroup_escape_exits_editing():
    rg = RadioGroup(Rect(0, 0, 100, 80), ["a", "b", "c"])
    fm = FocusManager([rg])
    fm.focus_first()
    fm.handle_key(_KEY_RETURN, 0)  # editing
    assert fm.handle_key(_KEY_ESCAPE, 0) is True
    assert rg.editing is False


# -- 10. handle_key return values ------------------------------------------


def test_handle_key_nav_and_unhandled():
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    fm = FocusManager([b, c])
    fm.focus_first()
    # navigation keys are handled (True)
    assert fm.handle_key(_KEY_RIGHT, 0) is True  # b -> c
    assert fm.handle_key(_KEY_LEFT, 0) is True  # c -> b
    assert fm.handle_key(_KEY_UP, 0) is True  # b -> c (prev from 0 wraps)
    assert fm.handle_key(_KEY_DOWN, 0) is True  # c -> b
    # a plain letter key is not handled (False)
    assert fm.handle_key(65, 0) is False  # 'A'


# -- 11. TAB / Shift+TAB ---------------------------------------------------


def test_tab_moves_next():
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    fm = FocusManager([b, c])
    fm.focus_first()
    assert fm.current is b
    assert fm.handle_key(_KEY_TAB, 0) is True
    assert fm.current is c


def test_shift_tab_moves_prev():
    b = Button(Rect(0, 0, 100, 30))
    c = Checkbox(Rect(0, 0, 100, 30))
    fm = FocusManager([b, c])
    fm.focus_first()
    assert fm.current is b
    assert fm.handle_key(_KEY_TAB, _MOD_SHIFT) is True
    assert fm.current is c  # prev from index 0 wraps to last
