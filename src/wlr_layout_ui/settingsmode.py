from functools import partial
import pygame
from wlr_layout_ui.settings import UI_RATIO
from .widgets import GuiButton, GuiScreen, shared
from .gui_utils import get_arrow_shape
from .settings import UI_RATIO


class Ctx:
    screen: GuiScreen
    screen_rect: pygame.Rect | None = None
    exit_requested = False

    cur_res = 0
    cur_freq = 0
    available = []

    @classmethod
    def getMode(cls):
        return (cls.resolutions[cls.cur_res], cls.frequencies[cls.cur_freq])

    @classmethod
    @property
    def currentResolutionName(cls):
        return "%dx%d" % tuple(cls.resolutions[cls.cur_res])

    @classmethod
    @property
    def resolutions(cls):
        res = set((r.width, r.height) for r in cls.available)
        return list(sorted(res))

    @classmethod
    @property
    def frequencies(cls):
        ref = tuple(cls.resolutions[cls.cur_res])
        res = set(r.freq for r in cls.available if (r.width, r.height) == ref)
        return list(sorted(res))

    @classmethod
    def changeResolution(cls, direction):
        cls.cur_res = (cls.cur_res + direction) % len(cls.resolutions)

    @classmethod
    def changeFreq(cls, direction):
        cls.cur_freq = (cls.cur_freq + direction) % len(cls.frequencies)

    @classmethod
    def exit(cls):
        cls.exit_requested = True


MARGIN = 5
NICE_BLUE = (12, 140, 255)

gui_buttons = []


def init(screen_rect, *a):
    Ctx.screen_rect = screen_rect

    but_w = 30
    but_h = 30

    icon_w = 40

    gui_buttons[:] = [
        GuiButton(
            pygame.Rect(
                screen_rect.width - 200 - MARGIN,
                screen_rect.height - but_h - MARGIN,
                200,
                but_h,
            ),
            (100, 200, 100),
            "Apply",
            lambda: Ctx.exit(),
            description="Save settings for this screen",
        ),
        GuiButton(
            pygame.Rect(
                10,
                40,
                icon_w + 10,
                icon_w + 10,
            ),
            NICE_BLUE,
            "",
            lambda: Ctx.changeResolution(-1),
            description="Save settings for this screen",
            icon=partial(get_arrow_shape, orientation="l"),
            icon_size=icon_w,
            icon_align="c",
        ),
        GuiButton(
            pygame.Rect(
                screen_rect.width - 10 - (icon_w + 10),
                40,
                icon_w + 10,
                icon_w + 10,
            ),
            NICE_BLUE,
            "",
            lambda: Ctx.changeResolution(+1),
            description="Save settings for this screen",
            icon=partial(get_arrow_shape, orientation="r"),
            icon_size=icon_w,
            icon_align="c",
        ),
        GuiButton(
            pygame.Rect(
                10,
                140,
                icon_w + 10,
                icon_w + 10,
            ),
            NICE_BLUE,
            "",
            lambda: Ctx.changeFreq(-1),
            description="Save settings for this screen",
            icon=partial(get_arrow_shape, orientation="l"),
            icon_size=icon_w,
            icon_align="c",
        ),
        GuiButton(
            pygame.Rect(
                screen_rect.width - 10 - (icon_w + 10),
                140,
                icon_w + 10,
                icon_w + 10,
            ),
            NICE_BLUE,
            "",
            lambda: Ctx.changeFreq(+1),
            description="Save settings for this screen",
            icon=partial(get_arrow_shape, orientation="r"),
            icon_size=icon_w,
            icon_align="c",
        ),
    ]


def draw_settings_mode(gui_screen: GuiScreen, surface: pygame.Surface):
    if not Ctx.resolutions:
        return

    for wid in gui_buttons:
        wid.draw(surface)

    screen_name = shared["font"].render(gui_screen.statusInfo, True, (255, 255, 255))
    screen_name_rect = screen_name.get_rect()
    screen_name_rect.center = (Ctx.screen_rect.center[0], screen_name_rect.size[1] // 2)
    surface.blit(screen_name, screen_name_rect)

    res_name = shared["bigfont"].render(
        Ctx.currentResolutionName, True, (255, 255, 255)
    )
    res_name_rect = res_name.get_rect()
    res_name_rect.center = (Ctx.screen_rect.center[0], 60)
    surface.blit(res_name, res_name_rect)

    freq_name = shared["bigfont"].render(
        "%.2dHz" % Ctx.frequencies[Ctx.cur_freq], True, (255, 255, 255)
    )
    freq_name_rect = freq_name.get_rect()
    freq_name_rect.center = (Ctx.screen_rect.center[0], 160)
    surface.blit(freq_name, freq_name_rect)


def run_settings_mode(gui_screen: GuiScreen, event):
    Ctx.available = gui_screen.screen.available
    Ctx.screen = gui_screen

    ref = (gui_screen.screen.mode.width, gui_screen.screen.mode.height)
    Ctx.cur_res = Ctx.resolutions.index(ref)
    Ctx.cur_freq = Ctx.frequencies.index(gui_screen.screen.mode.freq)

    for wid in gui_buttons:
        wid.handle_event(event)

    ref_mode, ref_freq = Ctx.getMode()
    for mode in gui_screen.screen.available:
        if (
            mode.width == ref_mode[0]
            and mode.height == ref_mode[1]
            and mode.freq == ref_freq
        ):
            if gui_screen.screen.mode != mode:
                gui_screen.screen.mode = mode
                gui_screen.rect.width = mode.width / UI_RATIO
                gui_screen.rect.height = mode.height / UI_RATIO
            break

    if Ctx.exit_requested:
        Ctx.exit_requested = False
        return
    return gui_screen
