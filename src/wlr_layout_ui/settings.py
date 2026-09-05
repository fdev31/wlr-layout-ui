import os

PROG_NAME = "WLR Layout"
WINDOW_MARGIN = 10
SCREEN_SCALE = 8
UI_SCALE = 1.0
LEGACY = not os.environ.get("WAYLAND_DISPLAY")
ALLOW_DESELECT = True


def reload_pre_commands():
    os.system("hyprctl reload")
    os.system("pypr relayout")
