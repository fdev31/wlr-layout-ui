"""Application entry points for wlr-layout-ui."""

import os
import pathlib
import sys
import time
from typing import cast

import pyglet

from pyggets import Theme, set_default_theme

from . import settings
from .gui import UI
from .profiles import load_profiles, load_settings
from .screens import displayInfo, load
from .settings import LEGACY, PROG_NAME, reload_pre_commands
from .types import Mode
from .utils import Rect, get_size, make_command


def _patch_x11_drag_drop():
    """Wrap X11 drag-drop to ignore exceptions (pyglet bug workaround)."""
    try:
        original = pyglet.window.xlib.XlibWindow._event_drag_drop
    except AttributeError:
        return

    def safe_drag_drop(self, ev):
        try:
            return original(self, ev)
        except Exception:
            pass

    pyglet.window.xlib.XlibWindow._event_drag_drop = safe_drag_drop  # type: ignore[method-assign]


_patch_x11_drag_drop()

# Configure the default pyggets theme for this application
_theme = Theme.dark()
_theme.default_style.highlight = (100, 200, 150)
_theme.widget_radius = 3

set_default_theme(_theme)

# Load persisted settings (applies scale to the active theme)
load_settings()

try:
    import setproctitle

    setproctitle.setproctitle(PROG_NAME)
except ImportError:
    pass


def apply_profile(profile: list[dict[str, float | bool | str]]):
    load()
    screen_info = {p["uid"]: p for p in profile}
    rects = []
    for di in displayInfo:
        si = screen_info[di.uid]
        di.scale = cast("float | int", si.get("scale", 1))
        di.transform = cast("int", si.get("transform", 0))
        di.active = cast("bool", si.get("active", False))
        if di.active:
            w, h = get_size(
                cast("int", si["width"]), cast("int", si["height"]), cast("float", si.get("scale", 1)), cast("int", si.get("transform", 0))
            )
            di.mode = Mode(w, h, cast("float", si["freq"]))
            rects.append(Rect(int(si["x"]), -int(si["y"]) - h, w, h))
        else:
            rects.append(Rect(0, 0, 0, 0))  # width & height not used

    cmd = make_command(displayInfo, rects, not LEGACY)
    time.sleep(0.5)
    if os.system(cmd):
        print("Failed applying the layout")
    print(cmd)


def main():
    if len(sys.argv) > 1:
        profiles = load_profiles()
        if sys.argv[1] == "-l":
            print("")
            for p in profiles:
                print(f" - {p}")
        elif sys.argv[1] == "export":
            load()
            hyprlayout_dir = pathlib.Path("~/.config/hyprlayout/").expanduser()
            hyprlayout_profiles_dir = pathlib.Path(os.path.join(hyprlayout_dir, "profiles")).expanduser()
            pathlib.Path(hyprlayout_profiles_dir).mkdir(parents=True, exist_ok=True)
            with pathlib.Path(os.path.join(hyprlayout_dir, "settings.lua")).open(encoding="utf-8", mode="w") as f:
                f.write(
                    f"""return {{
      canvas_scale = {settings.SCREEN_SCALE},
      ui_scale = {settings.UI_SCALE},
      shot_interval = 5,
    }}
"""
                )
            for p in profiles:
                with pathlib.Path(os.path.join(hyprlayout_profiles_dir, f"{p}.lua")).open(encoding="utf-8", mode="w") as f:
                    f.write(
                        f"""return {{
    name = "{p}",
    screens = {{
                    """
                    )
                    screens = profiles[p]
                    for screen in screens:
                        f.write(
                            """
    {
        mode = {
            height = %d,
            freq = %f,
            width = %d,
        },
        transform = %d,
        position = {
            x = %d,
            y = %d,
        },
        uid = "%s",
        active = %s,
        scale = %d,
        hdr_enabled = false,
        cm = "auto",
        sdrbrightness = 1,
        sdrsaturation = 1
    },
"""
                            % (
                                screen["height"],
                                screen["freq"],
                                screen["width"],
                                screen["transform"],
                                screen["x"],
                                screen["y"],
                                screen["uid"],
                                str(screen["active"]).lower(),
                                screen["scale"],
                            )
                        )
                    f.write("\n    }\n}\n")
        elif sys.argv[1] == "-m":
            load()
            current_uids = set(di.uid for di in displayInfo)
            for key in sorted(profiles):
                prof_uids = {p["uid"] for p in profiles[key]}
                # check that the two sets have the same elements
                if prof_uids == current_uids:
                    print(f"Matched profile {key}. Applying it...")
                    apply_profile(profiles[key])
                    sys.exit(0)
            print(f"No profile found: {sys.argv[1]}")
            sys.exit(1)

        elif sys.argv[1][0] == "-":
            load()
            print(
                """With no options, launches the GUI
Options:
             -l : list profiles
             -m : find a profile that matches the currently plugged display set, and apply it.
                  No-op if not found; will apply first in alphabetical order if multiple found.
 <profile name> : loads a profile
            """
            )
        else:
            reload_pre_commands()
            try:
                profile = profiles[sys.argv[1]]
            except KeyError as e:
                print(f"No such profile: {sys.argv[1]}")
                raise SystemExit(1) from e
            apply_profile(profile)
        return
    load()
    max_width = int(sum(max(screen.available, key=lambda mode: mode.width).width for screen in displayInfo) // settings.SCREEN_SCALE)
    max_height = int(sum(max(screen.available, key=lambda mode: mode.height).height for screen in displayInfo) // settings.SCREEN_SCALE)
    average_width = int(
        sum(max(screen.available, key=lambda mode: mode.width).width for screen in displayInfo) / len(displayInfo) // settings.SCREEN_SCALE
    )
    average_height = int(
        sum(max(screen.available, key=lambda mode: mode.height).height for screen in displayInfo)
        / len(displayInfo)
        // settings.SCREEN_SCALE
    )

    width = max_width + average_width * 2
    height = max_height + average_height * 2
    window = UI(width, height)  # type: ignore[abstract]
    if hasattr(window, "set_wm_class"):
        window.set_wm_class(PROG_NAME)
    pyglet.app.run()
