import os
import sys
import time

import pyglet

from .gui import UI
from .profiles import load_profiles
from .screens import displayInfo, load
from .settings import LEGACY, PROG_NAME, UI_RATIO, reload_pre_commands
from .utils import Rect, make_command

try:
    import setproctitle

    setproctitle.setproctitle(PROG_NAME)
except ImportError:
    pass


def apply_profile(profile):
    load()
    p_by_id = {p["uid"]: p for p in profile}
    rects = [
        (
            Rect(-i["x"], i["y"], i["height"], i["width"])
            if i.get("transform", 0) in (1, 3, 5, 7)
            else Rect(-i["x"], i["y"], i["width"], i["height"])
        )
        for i in profile
    ]

    for i, di in enumerate(displayInfo):
        di.active = p_by_id[di.uid]["active"]
        di.transform = p_by_id[di.uid].get("transform", 0)
        di.scale = p_by_id[di.uid].get("scale", 1.0)
        if di.transform in (1, 3, 5, 7):
            rects[i].width, rects[i].height = rects[i].height, rects[i].width

    cmd = make_command(displayInfo, rects, not LEGACY)
    time.sleep(0.5)
    if os.system(cmd):
        print("Failed applying the layout")


def main():
    if len(sys.argv) > 1:
        profiles = load_profiles()
        if sys.argv[1] == "-l":
            print("")
            for p in profiles:
                print(f" - {p}")
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
    max_width = int(sum(max(screen.available, key=lambda mode: mode.width).width for screen in displayInfo) // UI_RATIO)
    max_height = int(sum(max(screen.available, key=lambda mode: mode.height).height for screen in displayInfo) // UI_RATIO)
    average_width = int(
        sum(max(screen.available, key=lambda mode: mode.width).width for screen in displayInfo) / len(displayInfo) // UI_RATIO
    )
    average_height = int(
        sum(max(screen.available, key=lambda mode: mode.height).height for screen in displayInfo) / len(displayInfo) // UI_RATIO
    )

    width = max_width + average_width * 2
    height = max_height + average_height * 2
    window = UI(width, height)
    window.set_wm_class(PROG_NAME)
    pyglet.app.run()
