import math
import os
import re
import time

import pyglet

from .displaywidget import GuiScreen
from .profiles import load_profiles, save_profile
from .screens import displayInfo, load
from .settings import (
    ALLOW_DESELECT,
    FONT,
    LEGACY,
    PROG_NAME,
    UI_RATIO,
    WINDOW_MARGIN,
    reload_pre_commands,
)
from .utils import (
    Rect,
    compute_bounding_box,
    simplify_model_name,
    config,
    find_matching_mode,
    make_command,
    sorted_frequencies,
    sorted_resolutions,
    trim_rects_flip_y,
)
from .widgets import Button, Dropdown, HBox, Style, VBox, Widget, Spacer


CONFIRM_DELAY = 20


def get_closest_match(float_list, value):
    return min(float_list, key=lambda x: abs(x - value))


def get_size(screen, scale=0):
    "Get the size of the window based on the screen size and UI_RATIO"
    if not scale:
        scale = UI_RATIO
    w, h = ((screen.mode.width / scale) / screen.scale), (
        (screen.mode.height / scale) / screen.scale
    )
    if screen.transform in (1, 3, 5, 7):
        return (h, w)
    return (w, h)


class UI(pyglet.window.Window):
    def __init__(self, width, height):
        super().__init__(width, height, PROG_NAME, resizable=True)
        self.selected_item = None
        self.scale_factor = 1
        self.cursor_coords = (0, 0)
        self.confirmation_needed = False
        self.text_input: str | None = None
        self.error_message = ""
        self.error_message_duration = 0
        self.require_selected_item: set[Widget] = (
            set()
        )  # Items that can't be displayed without a selection

        but_w = 120
        but_h = 28

        # make profiles widgets {{{
        ref_rect = Rect(0, 0, but_w, but_h)
        s_but_style = Style(color=(213, 139, 139))
        act_but_style = Style(color=(139, 233, 202))
        main_but_style = Style(color=(255, 185, 50))
        p_new_but = Button(
            ref_rect.copy(),
            label="Save new",
            style=s_but_style,
            action=lambda: self.set_text_input(self.action_save_new_profile),
        )
        p_save_but = Button(
            ref_rect.copy(),
            style=s_but_style,
            label="Save",
            action=self.action_save_profile,
        )
        p_load_but = Button(
            ref_rect.copy(),
            label="Load",
            style=act_but_style,
            action=self.action_load_selected_profile,
        )
        self.profile_list = Dropdown(ref_rect.copy(), label="Profiles", options=[])

        self.sidepanel = VBox(
            widgets=[
                Button(
                    ref_rect.copy(),
                    label="Apply",
                    action=self.action_save_layout,
                    style=main_but_style,
                ),
                Button(
                    ref_rect.copy(),
                    label="Reload",
                    action=self.action_reload,
                    style=main_but_style,
                ),
                Spacer(
                    ref_rect.copy(),
                    label="Profiles:",
                    style=Style(text_color=(255, 255, 255, 200)),
                ),
                p_new_but,
                p_save_but,
                p_load_but,
                self.profile_list,
            ]
        )
        self.sync_profiles()

        # }}}

        # make main buttons {{{
        ref_rect = Rect(0, 0, but_w, but_h)

        ref_rect.width = int(ref_rect.width * 1.2)
        self.resolutions = Dropdown(
            ref_rect.copy(),
            label="Resolution",
            options=[],
            onchange=self.action_update_screen_spec,
            # invert=True,
        )
        ref_rect.width = int(ref_rect.width * 0.7)
        self.freqs = Dropdown(
            ref_rect.copy(),
            label="Rate",
            options=[],
            onchange=self.action_update_mode,
            # invert=True,
        )

        self.rotation = Dropdown(
            ref_rect.copy(),
            label="Rotation",
            options=[
                {"name": "0", "value": 0},
                {"name": "90", "value": 1},
                {"name": "180", "value": 2},
                {"name": "270", "value": 3},
                {"name": "flip", "value": 4},
                {"name": "flip 90", "value": 5},
                {"name": "flip 180", "value": 6},
                {"name": "flip 270", "value": 7},
            ],
            onchange=self.action_update_rotation,
            # invert=True,
        )
        ref_rect.width = int(ref_rect.width * 0.8)
        self.scale_ratio = Dropdown(
            ref_rect.copy(),
            label="Scale",
            options=[
                {"name": "100%", "value": 1},
                {"name": "90%", "value": 0.833333},
                {"name": "80%", "value": 0.666667},
                {"name": "120%", "value": 1.2},
                {"name": "150%", "value": 1.5},
                {"name": "200%", "value": 2.0},
            ],
            onchange=self.action_update_scale,
            # invert=True,
        )
        ref_rect.width //= 2
        self.on_off_but = Button(
            ref_rect.copy(),
            label="On",
            toggled_label="Off",
            action=self.action_toggle_screen_power,
            style=Style(highlight=(200, 100, 150), color=(100, 200, 150)),
            togglable=True,
        )

        base_widgets: list[Widget] = [
            self.on_off_but,
            self.resolutions,
            self.freqs,
        ]
        if config.get("hyprland"):
            base_widgets.append(self.rotation)
            base_widgets.append(self.scale_ratio)

        self.settings_box = HBox(widgets=base_widgets)
        self.require_selected_item.add(self.settings_box)
        # }}}

        self._widgets: list[Widget] = [
            self.settings_box,
            self.sidepanel,
        ]
        for w in self._widgets:
            w.margin = WINDOW_MARGIN

        # alignment
        self.settings_box.set_alignment("top", "right")
        self.sidepanel.set_alignment("top", "left")

        self.gui_screens: list[GuiScreen] = []
        self.load_screens()
        # Ensure correct positioning
        self.on_resize(width, height)
        self.set_current_modes_as_ref()

    def set_current_modes_as_ref(self):
        "Set original cmd to allow reverting the selected mode"
        self.original_cmd = make_command(
            [s.screen for s in self.gui_screens],
            [s.rect.scaled(UI_RATIO) for s in self.gui_screens],
            not LEGACY,
        )

    @property
    def widgets(self):
        return self.gui_screens + self._widgets

    def set_error(self, message, duration=200):
        self.error_message = message
        self.error_message_duration = duration

    def sync_profiles(self):
        self.profiles = load_profiles()
        self.profile_list.options = [
            {"name": k, "value": v} for k, v in self.profiles.items()
        ]

    def set_text_input(self, action):
        self.validate_text_input = action
        self.text_input = ""

    def load_screens(self):
        width, height = self.get_size()
        gui_screens = self.gui_screens
        gui_screens.clear()

        # make screen widgets {{{
        for screen in sorted(displayInfo, key=lambda s: s.uid):
            # Get the position and mode width and height for this screen
            x, y = screen.position

            max_width = max(m.width for m in screen.available)
            max_height = max(m.height for m in screen.available)

            is_rotated = screen.transform in (1, 3, 5, 7)

            if screen.mode:

                w, h = get_size(screen)
                rect = Rect(
                    int(x / UI_RATIO),
                    -int(y / UI_RATIO) - h,
                    w,
                    h,
                )
            else:
                rect = Rect(
                    int(x / UI_RATIO),
                    int(y / UI_RATIO),
                    int((max_width / UI_RATIO) / screen.scale),
                    int((max_height / UI_RATIO) / screen.scale),
                )

            gs = GuiScreen(screen, rect)
            gs.genColor()
            gui_screens.append(gs)

        max_x = max(s.rect.right for s in gui_screens)
        min_x = min(s.rect.left for s in gui_screens)
        min_y = min(s.rect.top for s in gui_screens)
        max_y = max(s.rect.bottom for s in gui_screens)

        offsetX = (width - (max_x - min_x)) // 2
        offsetY = (height - (max_y - min_y)) // 2

        for screen in gui_screens:
            screen.set_position(screen.rect.x + offsetX, screen.rect.y + offsetY)
        # }}}

    # Layout operations & snapping code {{{
    def center_layout(self, immediate=False):
        all_rects = [screen.target_rect for screen in self.gui_screens]
        avg_x, avg_y = Rect(*compute_bounding_box(all_rects)).center
        win_res = self.get_size()
        offX = (win_res[0] // 2) - avg_x
        offY = (win_res[1] // 2) - avg_y
        for screen in self.gui_screens:
            if immediate:
                screen.set_position(
                    screen.target_rect.x + offX, screen.target_rect.y + offY
                )
            else:
                screen.target_rect.x = screen.target_rect.x + offX
                screen.target_rect.y = screen.target_rect.y + offY

    def snap_active_screen(self):
        active_screen = self.gui_screens[-1]

        for wid in self.gui_screens[:-1]:
            if wid.rect.collide(active_screen.rect):
                # find the pair of corners
                # (one from gui_screen & one from active_screen)
                # which are closest
                other_screen_coords: list[tuple[int, int]] = [
                    wid.rect.topleft,
                    wid.rect.topright,
                    wid.rect.bottomright,
                    wid.rect.bottomleft,
                    (wid.rect.x + wid.rect.width / 2, wid.rect.y),
                    (wid.rect.x + wid.rect.width / 2, wid.rect.y + wid.rect.height),
                    (wid.rect.x, wid.rect.y + wid.rect.height / 2),
                    (wid.rect.x + wid.rect.width, wid.rect.y + wid.rect.height / 2),
                ]
                active_screen_coords: list[tuple[int, int]] = [
                    active_screen.rect.topleft,
                    active_screen.rect.topright,
                    active_screen.rect.bottomright,
                    active_screen.rect.bottomleft,
                    (
                        active_screen.rect.x + active_screen.rect.width / 2,
                        active_screen.rect.y,
                    ),
                    (
                        active_screen.rect.x + active_screen.rect.width / 2,
                        active_screen.rect.y + active_screen.rect.height,
                    ),
                    (
                        active_screen.rect.x,
                        active_screen.rect.y + active_screen.rect.height / 2,
                    ),
                    (
                        active_screen.rect.x + active_screen.rect.width,
                        active_screen.rect.y + active_screen.rect.height / 2,
                    ),
                ]

                def distance(point1: tuple[int, int], point2: tuple[int, int]):
                    a = (point1[0] - point2[0]) ** 2
                    b = (point1[1] - point2[1]) ** 2
                    return math.sqrt(a + b)

                # find which coordinates
                # from active_screen & gui_screen are closest
                min_distance = None
                closest_match = None
                for coord in active_screen_coords:
                    for other_screen_coord in other_screen_coords:
                        if (
                            min_distance is None
                            or distance(coord, other_screen_coord) < min_distance
                        ):
                            min_distance = distance(coord, other_screen_coord)
                            closest_match = other_screen_coord, coord
                assert closest_match is not None
                active_screen.target_rect.x -= closest_match[1][0] - closest_match[0][0]
                active_screen.target_rect.y -= closest_match[1][1] - closest_match[0][1]

    # }}}
    # Gui getters & properties  {{{
    def get_status_text(self):
        if self.text_input is not None:
            return f'Press ENTER to validate "{self.text_input}"'
        elif self.selected_item:
            return simplify_model_name(self.selected_item.screen.name)
        else:
            return "Select a monitor to edit its settings"

    # }}}
    # Event handler methods {{{
    def on_text(self, text):
        if self.text_input is not None:
            self.text_input += text

    def on_key_press(self, symbol, modifiers):
        if self.text_input is None:
            if symbol == 65293:  # return
                if self.confirmation_needed:
                    self.confirmation_needed = False
                    self.set_current_modes_as_ref()
                else:
                    self.action_save_layout()
            elif symbol == 65307 and self.confirmation_needed:  # Escape
                os.system(self.original_cmd)
                self.confirmation_needed = False
                self.reset_sel()
            else:
                super().on_key_press(symbol, modifiers)
        else:
            if symbol == 65288:  # backspace
                self.text_input = self.text_input[:-1]
            elif symbol == 65293:  # return
                self.validate_text_input()
            elif symbol == 65307:  # Escape
                self.text_input = None

    def on_mouse_motion(self, x, y, dx, dy):
        self.cursor_coords = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        active_widget = None
        for wid in self.widgets:
            if wid.on_mouse_press(x, y, button, modifiers):
                active_widget = wid
                break
        else:
            for screen in self.gui_screens:
                if screen.rect.contains(x, y):
                    self.action_select_screen(screen)
                    break
            else:
                if ALLOW_DESELECT:
                    self.selected_item = None

        for wid in self.widgets:
            if wid != active_widget:
                wid.unfocus()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.cursor_coords = (x, y)

        if self.selected_item and self.selected_item.dragging:
            self.selected_item.set_position(
                self.selected_item.rect.x + dx, self.selected_item.rect.y + dy
            )

    def on_resize(self, width, height):
        pyglet.window.Window.on_resize(self, width, height)

        for w in self._widgets:
            w.update_alignment(0, 0, width, height)

        self.center_layout(immediate=True)

        self._confirm_labels = None

    def on_mouse_release(self, x, y, button, modifiers):
        if self.selected_item and self.selected_item.dragging:
            self.snap_active_screen()
            self.selected_item.dragging = False
            self.center_layout()
        if self.selected_item:
            self.on_off_but.toggled = not self.selected_item.screen.active

    def draw_countdown(self):
        delay = time.time() - self.confirmation_needed
        if delay >= CONFIRM_DELAY:
            os.system(self.original_cmd)
            self.confirmation_needed = False
        else:
            color = (200, 200, 200, 255)
            w, h = self.get_size()
            remaining = CONFIRM_DELAY - delay
            ratio = remaining / CONFIRM_DELAY

            pyglet.shapes.Rectangle(
                0,
                h // 2 - 40,
                int(w * ratio),
                10,
                color=(50 + int(200 * (1.0 - ratio)), int(200 * ratio), 100, 255),
            ).draw()
            if getattr(self, "_confirm_labels", None):
                lbl1, lbl2 = self._confirm_labels
            else:
                lbl1 = pyglet.text.HTMLLabel(
                    "Press <b>ENTER</b>",
                    x=WINDOW_MARGIN,
                    y=h // 2 + 40,
                )
                lbl1.set_style("color", color)
                lbl1.font_size = 40
                lbl2 = pyglet.text.Label(
                    "to confirm (or ESCAPE to abort)",
                    font_size=20,
                    color=color,
                    x=WINDOW_MARGIN,
                    y=h // 2,
                )
                self._confirm_labels = (lbl1, lbl2)
            lbl1.draw()
            lbl2.draw()

    def draw_text_input(self):
        w, h = self.get_size()
        pyglet.text.Label(
            "Profile name: ", font_size=24, x=10, y=h // 2 + 40, align="left"
        ).draw()
        text = self.text_input
        if int(time.time() * 1.5) % 2:
            text += "_"
        pyglet.text.Label(
            text,
            font_size=24,
            x=WINDOW_MARGIN,
            y=h // 2,
            align="left",
        ).draw()

    def _can_draw(self, widget):
        return self.selected_item or widget not in self.require_selected_item

    def draw_screens_and_widgets(self):
        # Update focus
        for screen in self.gui_screens:
            is_focused = screen == self.selected_item
            if is_focused != screen.highlighted:
                screen.highlighted = is_focused

        # Widgets
        for w in self.widgets:
            if self._can_draw(w):
                w.draw(self.cursor_coords)

    def on_draw(self):
        self.clear()
        # Draw a grey background
        pyglet.shapes.Rectangle(
            0, 0, self.width, self.height, color=(50, 50, 50, 255)
        ).draw()

        # Higher priority modes
        if self.text_input is not None:
            self.draw_text_input()
        elif self.confirmation_needed:
            self.draw_countdown()
        else:
            self.draw_screens_and_widgets()
            self.draw_status_label()

    def draw_status_label(self):
        text = None
        color = (200, 200, 200, 255)

        if self.error_message:
            self.error_message_duration -= 1
            if self.error_message_duration == 0:
                self.error_message = ""
            else:
                text = self.error_message
                color = (250, 100, 100, 255)
        status_label = pyglet.text.Label(
            text if text else self.get_status_text(),
            x=WINDOW_MARGIN,
            y=WINDOW_MARGIN,
            font_name=FONT,
            color=color,
        )
        status_label.draw()

    # }}}
    # Button actions {{{

    def reset_sel(self):
        self.selected_item = None
        load()
        GuiScreen.cur_color = 0
        self.load_screens()

    def action_reload(self):
        reload_pre_commands()
        time.sleep(0.5)
        self.reset_sel()
        self.center_layout(immediate=True)

    def get_profile_data(self):
        screens_rect = [
            screen.target_rect.scaled(UI_RATIO) for screen in self.gui_screens
        ]
        trim_rects_flip_y(screens_rect)
        ret = []
        for rect, gs in zip(screens_rect, self.gui_screens):
            assert gs.screen.mode
            ret.append(
                {
                    "active": gs.screen.active,
                    "width": gs.screen.mode.width,
                    "height": gs.screen.mode.height,
                    "freq": gs.screen.mode.freq,
                    "x": rect.x,
                    "y": rect.y,
                    "uid": gs.screen.uid,
                    "scale": gs.screen.scale,
                    "transform": gs.screen.transform,
                }
            )
        return ret

    def action_save_new_profile(self):
        assert self.text_input
        save_profile(self.text_input, self.get_profile_data())
        self.sync_profiles()
        self.text_input = None

    def action_save_profile(self):
        if self.profile_list.options:
            save_profile(
                self.profile_list.get_selected_option()["name"], self.get_profile_data()
            )
            self.sync_profiles()
        else:
            self.set_error("No profile selected!")

    def action_load_selected_profile(self):
        if not self.profile_list.options:
            self.set_error("No profile selected!")
            return

        def findScreen(uid):
            for screen in self.gui_screens:
                if screen.screen.uid == uid:
                    return screen

        for screen_info in self.profile_list.get_value():
            # try to match screen info with current screens & update accordingly
            found = findScreen(screen_info["uid"])
            if found:
                info = screen_info.copy()
                found.screen.transform = info.get("transform", 0)
                w, h = get_size(found.screen, scale=info.get("scale", 1))
                rect = Rect(info["x"], -info["y"] - h, w, h)
                srect = rect.scaled(1 / UI_RATIO)
                info.pop("uid")
                found.screen.active = info.pop("active")
                found.screen.mode = find_matching_mode(
                    found.screen.available,
                    (info["width"], info["height"]),
                    info["freq"],
                )
                found.target_rect = srect
        self.center_layout()

    def action_update_scale(self):
        monitor = self.selected_item
        assert monitor
        monitor.screen.scale = self.scale_ratio.get_value()
        monitor.target_rect.width, monitor.target_rect.height = get_size(monitor.screen)

    def action_update_frequencies(self, screen, mode=None):
        if mode is None:
            cur_mode = screen.screen.mode.width, screen.screen.mode.height
        else:
            cur_mode = mode
        freqs = sorted_frequencies(screen.screen.available, cur_mode[0], cur_mode[1])
        self.freqs.options = [{"name": f"{r:.2f} Hz", "value": r} for r in freqs]
        if mode is None:
            self.freqs.selected_index = freqs.index(screen.screen.mode.freq)
        else:
            self.freqs.selected_index = 0

    def action_save_layout(self):
        cmd = make_command(
            [s.screen for s in self.gui_screens],
            [s.rect.scaled(UI_RATIO) for s in self.gui_screens],
            not LEGACY,
        )
        print(cmd)
        if os.system(cmd):
            self.set_error("Failed applying the layout")

        self.confirmation_needed = time.time()

    def action_toggle_screen_power(self):
        if self.selected_item:
            self.selected_item.screen.active = not self.selected_item.screen.active

    def action_update_rotation(self):
        "Update the rotation of the selected screen"
        assert self.selected_item
        self.selected_item.screen.transform = self.rotation.get_value()
        self.selected_item.target_rect.width, self.selected_item.target_rect.height = (
            get_size(self.selected_item.screen)
        )

    def action_update_screen_spec(self):
        self.action_update_frequencies(self.selected_item, self.resolutions.get_value())
        self.action_update_mode()
        self.center_layout()

    def action_update_mode(self):
        assert self.selected_item
        screen = self.selected_item.screen
        screen.mode = find_matching_mode(
            screen.available, self.resolutions.get_value(), self.freqs.get_value()
        )
        self.selected_item.target_rect.width = screen.mode.width // UI_RATIO
        self.selected_item.target_rect.height = screen.mode.height // UI_RATIO

    def action_select_screen(self, screen):
        self.selected_item = screen
        self.selected_item.dragging = True
        # make it last displayed + easy to find
        self.gui_screens.remove(screen)
        self.gui_screens.append(screen)

        cur_mode = screen.screen.mode
        # Update resolution
        res = sorted_resolutions(screen.screen.available)
        self.resolutions.options = [
            {"name": f"{r[0]} x {r[1]}", "value": r} for r in res
        ]
        self.rotation.selected_index = screen.screen.transform
        values = [o["value"] for o in self.scale_ratio.options]
        self.scale_ratio.selected_index = values.index(
            get_closest_match(values, screen.screen.scale)
        )
        i = -1
        for i, r in enumerate(res):
            if r[0] == cur_mode.width and r[1] == cur_mode.height:
                break
        self.resolutions.selected_index = i
        self.rotation.selected_index = screen.screen.transform
        self.action_update_frequencies(screen)

    # }}}
