import os

PROG_NAME = "WLR Layout"
WINDOW_MARGIN = 10
FONT = "Free Sans"
UI_RATIO = 8
LEGACY = not os.environ.get("WAYLAND_DISPLAY", False)
WIDGETS_RADIUS = 3
ALLOW_DESELECT = True
