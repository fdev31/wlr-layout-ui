import pyglet
from .gui import UI
from .settings import UI_RATIO, PROG_NAME
from .screens import displayInfo, load

try:
    import setproctitle

    setproctitle.setproctitle(PROG_NAME)
except ImportError:
    pass


def main():
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
    window = UI(width, height, displayInfo)
    window.set_wm_class(PROG_NAME)
    pyglet.app.run()
