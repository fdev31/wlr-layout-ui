import os
import sys
import time

import pyglet

from .gui import UI
from .settings import UI_RATIO, PROG_NAME, LEGACY, reload_pre_commands
from .screens import displayInfo, load
from .utils import make_command, Rect

try:
    import setproctitle

    setproctitle.setproctitle(PROG_NAME)
except ImportError:
    pass


def main():
    if len(sys.argv) > 1:
        from .profiles import load_profiles

        profiles = load_profiles()
        if sys.argv[1] == "-l":
            print("")
            for p in profiles.keys():
                print(f" - {p}")
        elif sys.argv[1][0] == "-":
            load()
            print(
                """With no options, launches the GUI
Options:
             -l : list profiles
 <profile name> : loads a profile
            """
            )

        else:
            reload_pre_commands()
            try:
                profile = profiles[sys.argv[1]]
            except KeyError:
                print("No such profile: %s" % sys.argv[1])
                raise SystemExit(1)
            load()
            p_by_id = {p["uid"]: p for p in profile}
            rects = [Rect(i["x"], i["y"], i["width"], i["height"]) for i in profile]
            for di in displayInfo:
                di.active = p_by_id[di.uid]["active"]
            cmd = make_command(displayInfo, rects, not LEGACY)
            time.sleep(0.5)
            if os.system(cmd):
                print("Failed applying the layout")
        sys.exit(0)
    load()
    max_width = int(
        sum(
            max(screen.available, key=lambda mode: mode.width).width
            for screen in displayInfo
        )
        // UI_RATIO
    )
    max_height = int(
        sum(
            max(screen.available, key=lambda mode: mode.height).height
            for screen in displayInfo
        )
        // UI_RATIO
    )
    average_width = int(
        sum(
            max(screen.available, key=lambda mode: mode.width).width
            for screen in displayInfo
        )
        / len(displayInfo)
        // UI_RATIO
    )
    average_height = int(
        sum(
            max(screen.available, key=lambda mode: mode.height).height
            for screen in displayInfo
        )
        / len(displayInfo)
        // UI_RATIO
    )

    width = max_width + average_width * 2
    height = max_height + average_height * 2
    window = UI(width, height)
    window.set_wm_class(PROG_NAME)
    pyglet.app.run()
