import os
import sys
import time

import pyglet

from .gui import UI
from .settings import UI_RATIO, PROG_NAME, LEGACY
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
            print(
                """With no options, launches the GUI
Options:
             -l : list profiles
 <profile name> : loads a profile
            """
            )

        else:
            os.system("hyprctl reload")
            profile = profiles[sys.argv[1]]
            rects = [Rect(i["x"], i["y"], i["width"], i["height"]) for i in profile]
            names = [i["uid"] for i in profile]
            activity = [i["active"] for i in profile]
            cmd = make_command(rects, names, activity, not LEGACY)
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
