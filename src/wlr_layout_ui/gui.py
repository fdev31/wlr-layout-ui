import math
import os
import re

import pyglet

from .widgets import Button, HBox, VBox, Dropdown, Style, Rect
from .settings import FONT, WINDOW_MARGIN, UI_RATIO, LEGACY, PROG_NAME
from .displaywidget import GuiScreen
from .utils import sorted_resolutions, sorted_frequencies, find_matching_mode
from .utils import compute_bounding_box
from .profiles import save_profile, load_profiles
from .screens import Screen

hex_re = re.compile("^[0-9x]+$")


class UI(pyglet.window.Window):
    def set_error(self, message, duration=200):
        self.error_message = message
        self.error_message_duration = duration

    def sync_profiles(self):
        self.profiles = load_profiles()
        self.profile_list.options = [
            {"name": k, "value": v} for k, v in self.profiles.items()
        ]

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
                rect = info.pop("rect")
                info.pop("uid")
                found.screen.active = info.pop("active")
                found.screen.mode.__dict__.update(info)
                found.target_rect = Rect(*rect)
        self.center_layout()

    def on_key_press(self, symbol, modifiers):
        if self.text_input is not None:
            if symbol == 65288:  # backspace
                self.text_input = self.text_input[:-1]
            elif symbol == 65293:  # return
                self.validate_text_input()
            elif symbol == 65307:  # Escape
                self.text_input = None
            elif symbol <= 255:
                self.text_input += chr(symbol)
        else:
            if symbol == 65293:  # return
                self.action_save_layout()
                self.close()
            else:
                super().on_key_press(symbol, modifiers)

    def set_text_input(self, action):
        self.validate_text_input = action
        self.text_input = ""

    def action_save_new_profile(self):
        save_profile(self.text_input, self.gui_screens)
        self.sync_profiles()
        self.text_input = None

    def action_save_profile(self):
        if self.profile_list.options:
            save_profile(
                self.profile_list.get_selected_option()["name"], self.gui_screens
            )
            self.sync_profiles()
        else:
            self.set_error("No profile selected!")

    def __init__(self, width, height, displayInfo):
        super().__init__(width, height, PROG_NAME, resizable=True)
        self.selected_item = None
        self.scale_factor = 1
        self.cursor_coords = (0, 0)
        self.window_size = (width, height)
        self.text_input: str | None = None
        self.error_message = ""
        self.error_message_duration = 0

        but_w = 120
        but_h = 25
        gui_screens: list[GuiScreen] = []
        self.gui_screens = gui_screens

        # make profiles widgets {{{
        pbox = VBox(
            width - but_w - WINDOW_MARGIN, height - WINDOW_MARGIN - but_h, but_w
        )
        s_but_style = Style(color=(213, 139, 139))
        but_style = Style(color=(139, 213, 202))
        p_new_but = Button(
            pbox.add(but_h * 1.1),
            "Save new",
            style=s_but_style,
            action=lambda: self.set_text_input(self.action_save_new_profile),
        )
        p_save_but = Button(
            pbox.add(but_h * 1.1),
            "Save",
            style=s_but_style,
            action=self.action_save_profile,
        )
        p_load_but = Button(
            pbox.add(but_h * 1.1),
            "Load",
            style=but_style,
            action=self.action_load_selected_profile,
        )
        self.profile_list = Dropdown(pbox.add(but_h * 1.1), "Profiles", [])
        self.sync_profiles()

        self.sidepanel = [self.profile_list, p_load_but, p_save_but, p_new_but]
        # }}}

        # make main buttons {{{
        box = HBox(WINDOW_MARGIN, WINDOW_MARGIN, but_h)
        apply_but = Button(
            box.add(but_w * 0.7),
            "Confirm",
            action=self.action_save_layout,
            style=Style(color=(120, 165, 240), bold=True),
        )
        self.resolutions = Dropdown(
            box.add(but_w * 1.1),
            "Resolution",
            [],
            onchange=self.action_update_screen_spec,
            # invert=True,
        )
        self.freqs = Dropdown(
            box.add(but_w * 0.9),
            "Rate",
            [],
            onchange=self.action_update_mode,
            # invert=True,
        )
        self.on_off_but = Button(
            box.add(but_w / 3),
            "On",
            toggled_label="Off",
            action=self.action_toggle_screen_power,
            style=Style(highlight=(200, 100, 150), color=(100, 200, 150)),
            togglable=True,
        )
        # }}}

        # make screen widgets {{{
        for screen in sorted(displayInfo, key=lambda s: s.uid):
            # Get the position and mode width and height for this screen
            x, y = screen.position
            y = height - y

            max_width = max(m.width for m in screen.available)
            max_height = max(m.height for m in screen.available)

            if screen.mode:
                rect = Rect(
                    int(x / UI_RATIO),
                    int(y / UI_RATIO),
                    int(screen.mode.width / UI_RATIO),
                    int(screen.mode.height / UI_RATIO),
                )
            else:
                rect = Rect(
                    int(x / UI_RATIO),
                    int(y / UI_RATIO),
                    int(max_width / UI_RATIO),
                    int(max_height / UI_RATIO),
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

        self.widgets: list[Dropdown | Button] = [
            apply_but,
            self.on_off_but,
            self.resolutions,
            self.freqs,
        ] + self.sidepanel

    # Event handler methods {{{
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
            # else:
            # NOTE: enables screen unfocusing:
            #     self.selected_item = None

        for wid in self.widgets:
            if wid != active_widget:
                wid.unfocus()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.selected_item and self.selected_item.dragging:
            self.selected_item.set_position(
                self.selected_item.rect.x + dx, self.selected_item.rect.y + dy
            )

    def on_resize(self, width, height):
        pyglet.window.Window.on_resize(self, width, height)
        old_height = self.window_size[1]
        for wid in self.widgets:
            if wid not in self.sidepanel:
                wid.rect.y = height - WINDOW_MARGIN - wid.rect.height

        for wid in self.sidepanel:
            wid.rect.x = width - WINDOW_MARGIN - wid.rect.width
            wid.rect.y -= old_height - height

        self.center_layout(immediate=True)
        self.window_size = self.get_size()

    def on_mouse_release(self, x, y, button, modifiers):
        if self.selected_item and self.selected_item.dragging:
            self.snap_active_screen()
            self.selected_item.dragging = False
            self.center_layout()
        if self.selected_item:
            self.on_off_but.toggled = not self.selected_item.screen.active

    def on_draw(self):
        self.clear()
        # Draw a grey background
        pyglet.shapes.Rectangle(
            0, 0, self.width, self.height, color=(50, 50, 50, 255)
        ).draw()
        # Higher priority modes
        if self.text_input is not None:
            w, h = self.get_size()
            pyglet.text.Label(
                "Profile name: ", font_size=24, x=10, y=h // 2 + 40, align="left"
            ).draw()
            pyglet.text.Label(
                self.text_input + "|",
                font_size=24,
                x=WINDOW_MARGIN,
                y=h // 2,
                align="left",
            ).draw()
            return
        # Standard display
        for screen in self.gui_screens:
            screen.highlighted = screen == self.selected_item
            screen.draw()
        if self.selected_item:
            for w in self.widgets:
                if w not in self.sidepanel:
                    w.draw(self.cursor_coords)
        for w in self.sidepanel:
            w.draw(self.cursor_coords)
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

    # Layout operations & snapping code {{{
    def center_layout(self, immediate=False):
        all_rects = [screen.target_rect for screen in self.gui_screens]
        avg_x, avg_y = Rect(*compute_bounding_box(all_rects)).center
        win_res = self.get_size()
        offX = (win_res[0] // 2) - avg_x
        offY = (win_res[1] // 2) - avg_y
        self.gui_screens = list(self.gui_screens)
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
                ]
                active_screen_coords: list[tuple[int, int]] = [
                    active_screen.rect.topleft,
                    active_screen.rect.topright,
                    active_screen.rect.bottomright,
                    active_screen.rect.bottomleft,
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

    # Button actions {{{
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
        screens = self.gui_screens
        min_x = UI_RATIO * min([screen.rect.x for screen in screens])
        min_y = UI_RATIO * min([-screen.rect.y for screen in screens])
        print("# Screens layout:")
        command = ["xrandr" if LEGACY else "wlr-randr"]
        for gs in screens:
            if not gs.screen.active:
                command.append(f"--output {gs.screen.uid} --off")
                continue
            x: int = int((gs.rect.x * UI_RATIO) - min_x)
            y: int = int(-gs.rect.y * UI_RATIO - min_y)
            assert gs.screen.mode
            sep = "x" if LEGACY else ","
            uid = gs.screen.uid
            mode = f"{int(gs.screen.mode.width)}x{int(gs.screen.mode.height)}"
            command.append(f"--output {uid} --pos {x}{sep}{y} --mode {mode}")
        cmd = " ".join(command)
        if os.system(cmd):
            self.set_error("Failed saving the layout")

    def action_toggle_screen_power(self):
        if self.selected_item:
            self.selected_item.screen.active = not self.selected_item.screen.active

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
        i = -1
        for i, r in enumerate(res):
            if r[0] == cur_mode.width and r[1] == cur_mode.height:
                break
        self.resolutions.selected_index = i
        self.action_update_frequencies(screen)

    # }}}
    # Gui getters & properties  {{{
    def get_status_text(self):
        if self.selected_item:
            words = []
            for word in self.selected_item.screen.name.split():
                if not hex_re.match(word):
                    words.append(word)
            return " ".join(words)
        else:
            return "Select a monitor"


# }}}
