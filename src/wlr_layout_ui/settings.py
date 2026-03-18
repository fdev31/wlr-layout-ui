import os

PROG_NAME = "WLR Layout"
WINDOW_MARGIN = 10
UI_RATIO = 8
LEGACY = not os.environ.get("WAYLAND_DISPLAY")
ALLOW_DESELECT = True


def reload_pre_commands():
    os.system("hyprctl reload")
    os.system("pypr relayout")
