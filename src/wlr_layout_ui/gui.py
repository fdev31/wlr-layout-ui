"""GUI for managing monitor layouts."""

import math
import os
import threading
import time

import pyglet

from pyggets import Rect as PRect
from pyggets import makeLabel, makeRectangle

from .displaywidget import GuiScreen
from .icons import icon_path
from .profiles import delete_profile, load_profiles, save_profile
from .screens import displayInfo, load
from .screenshots import capture_screenshots
from .settings import ALLOW_DESELECT, LEGACY, PROG_NAME, UI_RATIO, WINDOW_MARGIN, reload_pre_commands
from .utils import (
    Rect,
    compute_bounding_box,
    config,
    find_matching_mode,
    get_screen_size,
    make_command,
    simplify_model_name,
    sorted_frequencies,
    sorted_resolutions,
    trim_rects_flip_y,
)
from .widgets import (
    Button,
    Dropdown,
    HBox,
    Modal,
    Spacer,
    Style,
    TextInput,
    Toggle,
    VBox,
    Widget,
    get_default_theme,
)

CONFIRM_DELAY = 20

KEY_RETURN = 65293
KEY_ESCAPE = 65307
KEY_TAB = 65289


def get_closest_match(float_list, value):
    """Return the closest value in float_list to value."""
    return min(float_list, key=lambda x: abs(x - value))


class UI(pyglet.window.Window):
    """Main class for the GUI. Handles the layout of the screens and the widgets."""

    def __init__(self, width, height):
        super().__init__(width, height, PROG_NAME, resizable=True, vsync=True)
        self.selected_item = None
        self.scale_factor = 1
        self.cursor_coords = (0, 0)
        self.confirmation_needed = 0.0
        self.error_message = ""
        self.error_message_duration = 0
        self.require_selected_item: set[Widget] = set()  # Items that can't be displayed without a selection

        # Text input modal for profile naming
        self._text_input_action = None
        self._text_input_widget = TextInput(
            PRect(0, 0, 300, 28),
            placeholder="Profile name",
            onsubmit=self._on_text_input_submit,
        )
        self._text_input_modal = Modal(
            PRect(0, 0, width, height),
            title="Profile name",
            content=self._text_input_widget,
            on_close=self._on_text_input_cancel,
        )

        but_w = 120
        but_h = 28

        # make profiles widgets {{{
        ref_rect = Rect(0, 0, but_w, but_h)
        s_but_style = Style(color=(213, 139, 139))
        act_but_style = Style(color=(139, 233, 202))
        main_but_style = Style(color=(255, 185, 50))
        icon_rect = Rect(0, 0, 25, but_h)
        new_but_style = Style(color=(255, 185, 50))
        del_but_style = Style(color=(200, 100, 100))
        profile_buttons = HBox(
            widgets=[
                Button(
                    icon_rect.copy(),
                    icon=icon_path("new.png"),
                    style=new_but_style,
                    action=lambda: self.set_text_input(self.action_save_new_profile),
                ),
                Button(
                    icon_rect.copy(),
                    icon=icon_path("save.png"),
                    style=s_but_style,
                    action=self.action_save_profile,
                ),
                Button(
                    icon_rect.copy(),
                    icon=icon_path("load.png"),
                    style=act_but_style,
                    action=self.action_load_selected_profile,
                ),
                Button(
                    icon_rect.copy(),
                    icon=icon_path("delete.png"),
                    style=del_but_style,
                    action=self.action_delete_profile,
                ),
            ]
        )
        self.profile_list = Dropdown(ref_rect.copy(), label="Profiles", options=[])

        self.placement_mode = Toggle(
            ref_rect.copy(),
            label="Attraction",
            toggled=True,
            style=Style(
                text_color=(200, 200, 200, 255),
                color=(100, 100, 100),
                highlight=(80, 180, 80),
            ),
        )

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
                self.placement_mode,
                Spacer(
                    ref_rect.copy(),
                    label="Profiles:",
                    style=Style(text_color=(255, 255, 255, 200)),
                ),
                profile_buttons,
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

        ref_rect.width = but_w
        self.rotation = Dropdown(
            ref_rect.copy(),
            label="Transform",
            options=[
                {"name": "original", "value": 0},
                {"name": "rot 90°", "value": 1},
                {"name": "rot 180°", "value": 2},
                {"name": "rot 270°", "value": 3},
                {"name": "flip", "value": 4},
                {"name": "rot 90° flip", "value": 5},
                {"name": "rot 180° flip", "value": 6},
                {"name": "rot 270° flip", "value": 7},
            ],
            onchange=self.action_update_rotation,
            # invert=True,
        )
        ref_rect.width = int(but_w // 1.5)
        self.scale_ratio = Dropdown(
            ref_rect.copy(),
            label="Scale",
            options=[
                {"name": "100%", "value": 1},
                {"name": "90%", "value": 0.833333},
                {"name": "80%", "value": 0.666667},
                {"name": "125%", "value": 1.25000},
                {"name": "160%", "value": 1.6},
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
            self.sidepanel,
            self.settings_box,
        ]
        for w in self._widgets:
            w.margin = WINDOW_MARGIN

        # alignment
        self.settings_box.set_alignment("top", "right")
        self.sidepanel.set_alignment("top", "left")

        self.gui_screens: list[GuiScreen] = []
        self.load_screens()
        # NOTE: disabled
        # Refresh screenshots every 10 seconds in the background
        # pyglet.clock.schedule_interval(self._refresh_screenshots, 10.0)
        # Ensure correct positioning
        self.on_resize(width, height)
        self.set_current_modes_as_ref()

    def set_current_modes_as_ref(self):
        """Set original cmd to allow reverting the selected mode."""
        self.original_cmd = make_command(
            [s.screen for s in self.gui_screens],
            [s.rect.scaled(UI_RATIO) for s in self.gui_screens],
            not LEGACY,
        )

    @property
    def widgets(self):
        """Return all widgets and gui_screens."""
        return self.gui_screens + self._widgets

    def set_error(self, message, duration=200):
        """Set an error message to be displayed for a certain duration."""
        self.error_message = message
        self.error_message_duration = duration

    def sync_profiles(self):
        """Load profiles and update the profile list."""
        self.profiles = load_profiles()
        self.profile_list.options = [{"name": k, "value": v} for k, v in self.profiles.items()]

    def set_text_input(self, action):
        """Show the text input modal to be validated by the given action."""
        self._text_input_action = action
        self._text_input_widget.set_text("")
        self._text_input_widget.focus()
        self._text_input_modal.show()

    def _on_text_input_submit(self, text):
        """Handle text input submission."""
        if self._text_input_action and text:
            self._text_input_action(text)
        self._text_input_modal.hide()
        self._text_input_action = None

    def _on_text_input_cancel(self):
        """Handle text input cancellation."""
        self._text_input_action = None

    def load_screens(self):
        """Load the screens from the displayInfo and create the GuiScreen widgets."""
        gui_screens = self.gui_screens
        gui_screens.clear()

        # make screen widgets {{{
        for screen in sorted(displayInfo, key=lambda s: s.uid):
            # Get the position and mode width and height for this screen
            x, y = screen.position

            max_width = max(m.width for m in screen.available)
            max_height = max(m.height for m in screen.available)

            if screen.mode:
                w, h = get_screen_size(screen, scale=UI_RATIO)
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

        self._start_screenshot_worker()
        self.center_layout(immediate=True)
        # }}}

    def _start_screenshot_worker(self):
        """Launch a background thread to capture screenshots without blocking the UI."""

        def _worker():
            previews = capture_screenshots(displayInfo)
            if previews:
                pyglet.clock.schedule_once(lambda _dt: self._on_screenshots_ready(previews), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_screenshots_ready(self, previews: dict[str, str]):
        """Apply captured screenshots to GuiScreen widgets (called on main thread)."""
        for gs in self.gui_screens:
            path = previews.get(gs.screen.uid)
            if path:
                gs.set_preview(path)

    def _refresh_screenshots(self, _dt=None):
        """Periodic callback to refresh screenshots."""
        self._start_screenshot_worker()

    # Layout operations & snapping code {{{

    # Attraction weight multipliers for snap distance sorting.
    # Lower weight = stronger attraction (weight is multiplied with distance).
    #
    # Opposite edges (right↔left, top↔bottom) are "adjacency" snaps —
    # placing screens edge-to-edge.  Same edges (left↔left) are "alignment"
    # snaps — lining up shared edges across monitors.
    #
    # Priority (strongest → weakest):
    #  - Both axes match (adjacency or alignment on both axes): strongest
    #  - One axis matches: moderate
    #  - No axis match, but at least one midpoint involved: neutral
    #  - Corner↔corner with no shared axis (point-touch): weak but possible
    SNAP_WEIGHT_BOTH = 0.25
    SNAP_WEIGHT_SINGLE = 0.5
    SNAP_PENALTY_CORNER = 1.5

    # Per-axis priority tiers used in _collect_snap_axes.
    # Lower tier = higher priority.  When combining the best X and Y
    # translations, candidates are sorted by (tier, abs_delta) — tier wins
    # over distance, so centre alignment always beats edge alignment within
    # reasonable reach.
    #  - TIER_CENTER (0): center_x↔center_x, center_y↔center_y — "middle"
    #    alignment.  Highest priority so centering screens is easy to reach.
    #  - TIER_OPPOSITE (1): opposite edges (right↔left, top↔bottom) —
    #    adjacency (placing screens edge-to-edge).
    #  - TIER_SAME (2): same edges (left↔left, top↔top) — alignment.
    TIER_CENTER = 0
    TIER_OPPOSITE = 1
    TIER_SAME = 2
    TIER_NONE = 3  # no axis match — fallback only

    # Opposite-edge pairs that represent adjacency on each axis.
    _OPPOSITE_EDGES = frozenset({
        ("left", "right"),
        ("right", "left"),
        ("top", "bottom"),
        ("bottom", "top"),
    })

    # Maximum raw distance (in UI pixels) for attraction snapping.
    # Pairs beyond this distance are ignored during attract_screens() so that
    # distant monitors don't pull the active screen unexpectedly.
    # Set to 0 or None to disable the radius check.
    SNAP_RADIUS = 300

    def center_layout(self, immediate=False):
        """Center the layout in the window."""
        all_rects = [screen.target_rect for screen in self.gui_screens]
        avg_x, avg_y = Rect(*compute_bounding_box(all_rects)).center
        win_res = self.get_size()
        off_x = (win_res[0] // 2) - avg_x
        off_y = (win_res[1] // 2) - avg_y
        for screen in self.gui_screens:
            if immediate:
                screen.set_position(screen.target_rect.x + off_x, screen.target_rect.y + off_y)
            else:
                screen.target_rect.x = screen.target_rect.x + off_x
                screen.target_rect.y = screen.target_rect.y + off_y

    def snap_active_screen(self):
        """Snap the active screen to the closest screen if it collides."""
        active_screen = self.gui_screens[-1]

        colliding = [wid for wid in self.gui_screens[:-1] if wid.rect.collide(active_screen.rect)]
        if colliding:
            self._snap_to_best_non_overlapping(active_screen, colliding)

    @staticmethod
    def _ref_points(rect) -> list[tuple]:
        """Return 8 reference points with semantic labels for magnet snapping.

        Each entry is ``((x, y), (x_type, y_type))`` where ``x_type`` /
        ``y_type`` identify which edge or centre the point represents on each
        axis.  Same-type pairs (e.g. left/left) are given higher attraction
        priority than cross-type pairs (e.g. left/centre_x).
        """
        cx = rect.x + rect.width / 2
        cy = rect.y + rect.height / 2
        return [
            (rect.topleft, ("left", "top")),
            (rect.topright, ("right", "top")),
            (rect.bottomright, ("right", "bottom")),
            (rect.bottomleft, ("left", "bottom")),
            ((cx, rect.y), ("center_x", "bottom")),
            ((cx, rect.y + rect.height), ("center_x", "top")),
            ((rect.x, cy), ("left", "center_y")),
            ((rect.x + rect.width, cy), ("right", "center_y")),
        ]

    def _axes_match(self, a, b):
        """Return True if two axis labels are a valid snap pair.

        Valid pairs are same-label (e.g. left/left for alignment) *or*
        opposite-label (e.g. right/left for adjacency).
        """
        return a == b or (a, b) in self._OPPOSITE_EDGES

    def _axis_tier(self, label_a, label_b):
        """Return the priority tier for a single-axis snap pair.

        Lower tier = higher priority.  Used in _collect_snap_axes to produce
        ``(tier, abs_delta)`` scores that sort lexicographically so that
        center alignment always beats edge alignment within reach.
        """
        if label_a == label_b:
            if label_a in ("center_x", "center_y"):
                return self.TIER_CENTER
            return self.TIER_SAME
        if (label_a, label_b) in self._OPPOSITE_EDGES:
            return self.TIER_OPPOSITE
        return self.TIER_NONE

    def _snap_weight(self, ac_types, oc_types):
        """Return the attraction weight for a pair of reference-point types.

        Lower weight = stronger attraction.  The weight is multiplied with the
        raw distance to produce a *weighted* distance used for sorting.
        """
        matches = self._axes_match(ac_types[0], oc_types[0]) + self._axes_match(ac_types[1], oc_types[1])
        if matches == 2:
            return self.SNAP_WEIGHT_BOTH
        if matches == 1:
            return self.SNAP_WEIGHT_SINGLE
        # Both points are corners (no centre component) with 0 shared axes →
        # point-touch only, possible but weak.
        if ac_types[0] != "center_x" and ac_types[1] != "center_y" and oc_types[0] != "center_x" and oc_types[1] != "center_y":
            return self.SNAP_PENALTY_CORNER
        return 1.0

    def _collect_snap_axes(self, active_coords, other_coords, max_dist=0, active_rect=None, other_rect=None):
        """Collect per-axis snap candidates between two sets of reference points.

        Returns ``(x_snaps, y_snaps)`` where each list contains
        ``((tier, abs_delta), raw_delta)`` entries.  Sorting these tuples
        lexicographically gives priority to the best tier first, then to
        the smallest distance within that tier.

        Pairs are collected when the axis labels are compatible — either
        the same (alignment, e.g. left/left) or opposite (adjacency, e.g.
        right/left).

        Center-to-center pairs (tier 0) are subject to a reach limit:
        they are only included when ``abs(delta) <= max(active_dim, other_dim)``
        on that axis, so that center snaps don't pull screens unreasonably far.

        Args:
            active_coords: reference points of the active screen.
            other_coords: reference points of a candidate screen.
            max_dist: if >0, ignore pairs whose raw single-axis distance
                exceeds this value.
            active_rect: Rect of the active screen (for center reach limit).
            other_rect: Rect of the candidate screen (for center reach limit).
        """
        # Center reach limits (100% of the larger screen's dimension).
        center_reach_x = 0.0
        center_reach_y = 0.0
        if active_rect is not None and other_rect is not None:
            center_reach_x = max(active_rect.width, other_rect.width)
            center_reach_y = max(active_rect.height, other_rect.height)

        x_snaps: list[tuple[tuple[int, float], float]] = []
        y_snaps: list[tuple[tuple[int, float], float]] = []
        for ac_coord, ac_types in active_coords:
            for oc_coord, oc_types in other_coords:
                dx = ac_coord[0] - oc_coord[0]
                dy = ac_coord[1] - oc_coord[1]

                # X-axis: consider pairs whose X-labels are compatible
                # (same edge for alignment, opposite edges for adjacency).
                if self._axes_match(ac_types[0], oc_types[0]):
                    abs_dx = abs(dx)
                    if max_dist and abs_dx > max_dist:
                        pass  # beyond attraction radius
                    else:
                        tier = self._axis_tier(ac_types[0], oc_types[0])
                        # Center reach limit: skip center pairs that are too far.
                        if tier == self.TIER_CENTER and center_reach_x and abs_dx > center_reach_x:
                            pass
                        else:
                            x_snaps.append(((tier, abs_dx), dx))
                # Y-axis: same logic for Y.
                if self._axes_match(ac_types[1], oc_types[1]):
                    abs_dy = abs(dy)
                    if max_dist and abs_dy > max_dist:
                        pass  # beyond attraction radius
                    else:
                        tier = self._axis_tier(ac_types[1], oc_types[1])
                        if tier == self.TIER_CENTER and center_reach_y and abs_dy > center_reach_y:
                            pass
                        else:
                            y_snaps.append(((tier, abs_dy), dy))
        return x_snaps, y_snaps

    def _test_no_overlap(self, ar, dx, dy):
        """Return True if moving *ar* by (-dx, -dy) causes no overlap."""
        test = PRect(ar.x - dx, ar.y - dy, ar.width, ar.height)
        return all(not test.collide(other.target_rect) for other in self.gui_screens[:-1])

    def _snap_to_best_non_overlapping(self, active, candidates, max_dist=0):
        """Find the best non-overlapping snap and apply it.

        The algorithm has two stages:

        1. **Per-axis independent snap** -- the best X-translation and the
           best Y-translation are chosen independently across *all*
           candidates, then combined.  This allows the active screen to
           align its left edge with monitor A while aligning its top edge
           with monitor B.
        2. **Point-pair fallback** -- if no valid per-axis combination is
           found, fall back to the original approach: pick the single
           reference-point pair with the smallest weighted distance.

        Per-axis candidates are scored as ``(tier, abs_delta)`` tuples that
        sort lexicographically — tier wins over distance.  This ensures that
        center alignment (tier 0) always beats edge alignment (tier 1/2)
        within reach, regardless of the distance involved.

        Args:
            active: the GuiScreen being moved.
            candidates: list of GuiScreens to match reference points against.
            max_dist: if >0, ignore pairs whose raw distance exceeds this
                value (used by attract_screens to limit snap radius).
        """
        ar = active.target_rect
        active_coords = self._ref_points(ar)

        # ------------------------------------------------------------------
        # Collect per-axis snap candidates and point-pair candidates
        # ------------------------------------------------------------------
        # Each entry in all_x / all_y is ((tier, abs_delta), raw_delta).
        all_x: list[tuple[tuple[int, float], float]] = []
        all_y: list[tuple[tuple[int, float], float]] = []
        pairs: list[tuple[float, float, float]] = []

        for other in candidates:
            otr = other.target_rect
            other_coords = self._ref_points(otr)

            xs, ys = self._collect_snap_axes(
                active_coords,
                other_coords,
                max_dist,
                active_rect=ar,
                other_rect=otr,
            )
            all_x.extend(xs)
            all_y.extend(ys)

            # Also build the classic point-pair list as fallback
            for ac_coord, ac_types in active_coords:
                for oc_coord, oc_types in other_coords:
                    dx = ac_coord[0] - oc_coord[0]
                    dy = ac_coord[1] - oc_coord[1]
                    dist = math.sqrt(dx**2 + dy**2)
                    if max_dist and dist > max_dist:
                        continue
                    weight = self._snap_weight(ac_types, oc_types)
                    pairs.append((dist * weight, dx, dy))

        # ------------------------------------------------------------------
        # Stage 1: per-axis independent snap
        # ------------------------------------------------------------------
        all_x.sort()
        all_y.sort()

        # Try combinations of the best X and Y snaps.  We also include
        # "no snap on this axis" (delta=0) so that a single-axis alignment
        # can still win when the other axis has no good match.
        best_x = [dx for _, dx in all_x[:6]]  # top-6 X candidates
        best_y = [dy for _, dy in all_y[:6]]  # top-6 Y candidates
        if 0 not in best_x:
            best_x.append(0)
        if 0 not in best_y:
            best_y.append(0)

        # Score each combination by the sum of per-axis (tier, abs_delta)
        # scores.  Build a lookup from delta → best score (keep minimum).
        x_scores: dict[float, tuple[int, float]] = {}
        for score, dx in all_x:
            if dx not in x_scores or score < x_scores[dx]:
                x_scores[dx] = score
        y_scores: dict[float, tuple[int, float]] = {}
        for score, dy in all_y:
            if dy not in y_scores or score < y_scores[dy]:
                y_scores[dy] = score

        # "No movement" on an axis should not beat actual snap targets.
        # Give it a score worse than any real candidate (tier=999).
        zero_score: tuple[int, float] = (999, 0.0)

        # Build axis combo scores.  Each combo score is the element-wise sum
        # of the two per-axis scores: (tier_x + tier_y, dist_x + dist_y).
        axis_combos: list[tuple[tuple[int, float], float, float]] = []
        for dx in best_x:
            for dy in best_y:
                sx = x_scores.get(dx, zero_score if dx == 0 else (self.TIER_NONE, abs(dx)))
                sy = y_scores.get(dy, zero_score if dy == 0 else (self.TIER_NONE, abs(dy)))
                combined = (sx[0] + sy[0], sx[1] + sy[1])
                axis_combos.append((combined, dx, dy))
        axis_combos.sort()

        for _, dx, dy in axis_combos:
            if dx == 0 and dy == 0:
                continue  # no movement
            if self._test_no_overlap(ar, dx, dy):
                ar.x -= dx
                ar.y -= dy
                return

        # ------------------------------------------------------------------
        # Stage 2: point-pair fallback (original algorithm)
        # ------------------------------------------------------------------
        pairs.sort(key=lambda p: p[0])

        for _, dx, dy in pairs:
            if self._test_no_overlap(ar, dx, dy):
                ar.x -= dx
                ar.y -= dy
                return

    def attract_screens(self):
        """Magnet-snap the active screen to the nearest reference point on any neighbor.

        Uses 8-point matching (4 corners + 4 edge midpoints) and picks the
        closest anchor-point pair that does not cause overlap with any screen.
        A maximum snap radius limits attraction to nearby monitors only.
        """
        active = self.gui_screens[-1]
        ar = active.target_rect

        # If screens already overlap, don't interfere with snap_active_screen
        for other in self.gui_screens[:-1]:
            if ar.collide(other.target_rect):
                return

        self._snap_to_best_non_overlapping(active, self.gui_screens[:-1], max_dist=self.SNAP_RADIUS)

    # }}}
    # Gui getters & properties  {{{
    def get_status_text(self):
        """Return the status text to be displayed."""
        if self.selected_item:
            return simplify_model_name(self.selected_item.screen.name)
        else:
            return "Select a monitor to edit its settings"

    # }}}
    # Event handler methods {{{
    def on_text(self, text):
        """Handle text input."""
        if self._text_input_modal.is_visible():
            self._text_input_modal.on_text(text)

    def on_key_press(self, symbol, modifiers):
        """Handle key presses."""
        if self._text_input_modal.is_visible():
            self._text_input_modal.on_key_press(symbol, modifiers)
            return
        if symbol == KEY_RETURN:
            if self.confirmation_needed:
                self.confirmation_needed = 0.0
                self.set_current_modes_as_ref()
            else:
                self.action_save_layout()
        elif symbol == KEY_ESCAPE and self.confirmation_needed:
            os.system(self.original_cmd)
            self.confirmation_needed = 0.0
            self.reset_sel()
        elif symbol == KEY_TAB:
            # cycle through profiles
            if not self.profile_list.options:
                return
            index = self.profile_list.selected_index
            index += 1
            if index >= len(self.profile_list.options):
                index = 0
            self.profile_list.selected_index = index
            # load the profile
            self.action_load_selected_profile()
        else:
            super().on_key_press(symbol, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        """Update the cursor coordinates."""
        self.cursor_coords = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse presses."""
        if self._text_input_modal.is_visible():
            self._text_input_modal.on_mouse_press(x, y, button, modifiers)
            return

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
        """Handle mouse dragging."""
        self.cursor_coords = (x, y)

        if self.selected_item and self.selected_item.dragging:
            self.selected_item.set_position(self.selected_item.rect.x + dx, self.selected_item.rect.y + dy)

    def on_resize(self, width, height):
        """Handle window resizing."""
        pyglet.window.Window.on_resize(self, width, height)

        for w in self._widgets:
            w.update_alignment(0, 0, width, height)

        self.center_layout(immediate=True)

        # Update modal backdrop size
        self._text_input_modal.rect = PRect(0, 0, width, height)

    def on_mouse_release(self, x, y, button, modifiers):
        """Handle mouse releases."""
        if self.selected_item and self.selected_item.dragging:
            self.snap_active_screen()
            if self.placement_mode.toggled:
                self.attract_screens()
            self.selected_item.dragging = False
            self.center_layout()
        if self.selected_item:
            self.on_off_but.toggled = not self.selected_item.screen.active

    def draw_countdown(self):
        """Draw the countdown for the confirmation."""
        delay = time.time() - self.confirmation_needed
        if delay >= CONFIRM_DELAY:
            os.system(self.original_cmd)
            self.confirmation_needed = 0.0
        else:
            w, h = self.get_size()
            remaining = CONFIRM_DELAY - delay
            ratio = remaining / CONFIRM_DELAY
            font_name = get_default_theme().font_name

            # Progress bar (color transitions green -> red)
            bar_color = (50 + int(200 * (1.0 - ratio)), int(200 * ratio), 100, 255)
            makeRectangle(0, h // 2 - 40, int(w * ratio), 10, color=bar_color).draw()

            # Instruction labels
            text_color = (200, 200, 200, 255)
            makeLabel(
                "Press ENTER",
                x=WINDOW_MARGIN,
                y=h // 2 + 40,
                font_size=40,
                color=text_color,
                font_name=font_name,
                weight="bold",
            ).draw()
            makeLabel(
                "to confirm (or ESCAPE to abort)",
                x=WINDOW_MARGIN,
                y=h // 2,
                font_size=20,
                color=text_color,
                font_name=font_name,
            ).draw()

    def _can_draw(self, widget):
        """Return whether the widget can be drawn."""
        return self.selected_item or widget not in self.require_selected_item

    def draw_screens_and_widgets(self):
        """Draw the screens and widgets."""
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
        """Draw the GUI."""
        self.clear()
        # Draw a grey background
        pyglet.shapes.Rectangle(0, 0, self.width, self.height, color=(50, 50, 50, 255)).draw()

        # Higher priority modes
        if self.confirmation_needed:
            self.draw_countdown()
        else:
            self.draw_screens_and_widgets()
            self.draw_status_label()

        # Draw modal overlay (only visible when shown)
        self._text_input_modal.draw(self.cursor_coords)

    def draw_status_label(self):
        """Draw the status label."""
        text = None
        color = (200, 200, 200, 255)

        if self.error_message:
            self.error_message_duration -= 1
            if self.error_message_duration == 0:
                self.error_message = ""
            else:
                text = self.error_message
                color = (250, 100, 100, 255)

        makeLabel(
            text if text else self.get_status_text(),
            x=WINDOW_MARGIN,
            y=WINDOW_MARGIN,
            font_name=get_default_theme().font_name,
            color=color,
        ).draw()

    # }}}
    # Button actions {{{

    def reset_sel(self):
        """Reset the selected item."""
        self.selected_item = None
        load()
        GuiScreen.cur_color = 0
        self.load_screens()

    def action_reload(self):
        """Reload the screens."""
        reload_pre_commands()
        time.sleep(0.5)
        self.reset_sel()
        self.center_layout(immediate=True)

    def get_profile_data(self):
        """Return the data for the current profile."""
        screens_rect = [screen.target_rect.scaled(UI_RATIO) for screen in self.gui_screens]
        trim_rects_flip_y(screens_rect)
        ret = []
        for rect, gs in zip(screens_rect, self.gui_screens):
            assert gs.screen.mode
            ret.append({
                "name": gs.screen.name,
                "active": gs.screen.active,
                "width": gs.screen.mode.width,
                "height": gs.screen.mode.height,
                "freq": gs.screen.mode.freq,
                "x": rect.x,
                "y": rect.y,
                "uid": gs.screen.uid,
                "scale": gs.screen.scale,
                "transform": gs.screen.transform,
            })
        return ret

    def action_save_new_profile(self, name):
        """Save a new profile."""
        save_profile(name, self.get_profile_data())
        self.sync_profiles()

    def action_save_profile(self):
        """Save the current profile."""
        if self.profile_list.options:
            save_profile(self.profile_list.get_selected_option()["name"], self.get_profile_data())
            self.sync_profiles()
        else:
            self.set_error("No profile selected!")

    def action_delete_profile(self):
        """Delete the selected profile."""
        if self.profile_list.options:
            delete_profile(self.profile_list.get_selected_option()["name"])
            self.sync_profiles()
        else:
            self.set_error("No profile selected!")

    def action_load_selected_profile(self):
        """Load the selected profile."""
        if not self.profile_list.options:
            self.set_error("No profile selected!")
            return

        def findScreen(uid):
            """Find the screen with the given uid."""
            for screen in self.gui_screens:
                if screen.screen.uid == uid:
                    return screen

        for screen_info in self.profile_list.get_value():
            # try to match screen info with current screens & update accordingly
            found = findScreen(screen_info["uid"])
            if found:
                info = screen_info.copy()
                found.screen.transform = info.get("transform", 0)
                found.screen.scale = info.get("scale", 1)
                info.pop("uid")
                found.screen.active = info.pop("active")
                mode = find_matching_mode(
                    found.screen.available,
                    (info["width"], info["height"]),
                    info["freq"],
                )
                if mode:
                    found.screen.mode = mode
                else:
                    self.set_error(f"No matching mode for {found.screen.uid}")
                w, h = get_screen_size(found.screen, scale=1)
                rect = Rect(info["x"], -info["y"] - h, w, h)
                found.target_rect = rect.scaled(1 / UI_RATIO)
        self.center_layout()

    def action_update_scale(self):
        """Update the scale of the selected screen."""
        monitor = self.selected_item
        assert monitor
        monitor.screen.scale = self.scale_ratio.get_value()
        monitor.target_rect.width, monitor.target_rect.height = get_screen_size(monitor.screen, scale=UI_RATIO)

    def action_update_frequencies(self, screen, mode=None):
        """Update the frequencies of the selected screen."""
        cur_mode = (screen.screen.mode.width, screen.screen.mode.height) if mode is None else mode
        freqs = sorted_frequencies(screen.screen.available, cur_mode[0], cur_mode[1])
        self.freqs.options = [{"name": f"{r:.2f} Hz", "value": r} for r in freqs]
        if mode is None:
            self.freqs.selected_index = freqs.index(screen.screen.mode.freq)
        else:
            self.freqs.selected_index = 0

    def action_save_layout(self):
        """Save the current layout."""
        cmd = make_command(
            [s.screen for s in self.gui_screens],
            [s.target_rect.scaled(UI_RATIO) for s in self.gui_screens],
            not LEGACY,
        )
        if os.system(cmd):
            self.set_error("Failed applying the layout")
        print(cmd)

        self.confirmation_needed = time.time()

    def action_toggle_screen_power(self):
        """Toggle the power of the selected screen."""
        if self.selected_item:
            self.selected_item.screen.active = not self.selected_item.screen.active

    def action_update_rotation(self):
        """Update the rotation of the selected screen."""
        assert self.selected_item
        self.selected_item.screen.transform = self.rotation.get_value()
        self.selected_item.target_rect.width, self.selected_item.target_rect.height = get_screen_size(
            self.selected_item.screen, scale=UI_RATIO
        )

    def action_update_screen_spec(self):
        """Update the screen specifications."""
        self.action_update_frequencies(self.selected_item, self.resolutions.get_value())
        self.action_update_mode()
        self.center_layout()

    def action_update_mode(self):
        """Update the mode of the selected screen."""
        assert self.selected_item
        screen = self.selected_item.screen
        screen.mode = find_matching_mode(screen.available, self.resolutions.get_value(), self.freqs.get_value())
        self.selected_item.target_rect.width = screen.mode.width // UI_RATIO
        self.selected_item.target_rect.height = screen.mode.height // UI_RATIO

    def action_select_screen(self, screen):
        """Select a screen."""
        self.selected_item = screen
        self.selected_item.dragging = True
        # make it last displayed + easy to find
        self.gui_screens.remove(screen)
        self.gui_screens.append(screen)

        cur_mode = screen.screen.mode
        # update scale
        values = [o["value"] for o in self.scale_ratio.options]
        self.scale_ratio.selected_index = values.index(get_closest_match(values, screen.screen.scale))
        # update resolution dropdown
        res = sorted_resolutions(screen.screen.available)
        self.resolutions.options = [{"name": f"{r[0]} x {r[1]}", "value": r} for r in res]
        i = -1
        for i, r in enumerate(res):  # noqa: B007
            if r[0] == cur_mode.width and r[1] == cur_mode.height:
                break
        self.resolutions.selected_index = i
        # update rotation / transform
        self.rotation.selected_index = screen.screen.transform
        # update frequency
        self.action_update_frequencies(screen)

    # }}}
