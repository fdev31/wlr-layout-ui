import os

PROG_NAME = "Baconizer"
WINDOW_MARGIN = 10
FONT = "Free Sans"
UI_RATIO = 8
LEGACY = not os.environ.get("WAYLAND_DISPLAY", False)
