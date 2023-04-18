import math
import os
from itertools import chain

import pygame

from .base import LEGACY
from .settings import UI_RATIO
from .widgets import GuiButton, GuiScreen, shared

STATUS_HEIGHT = 20
MARGIN = 5
gui_buttons = []


class Ctx:
    moving: GuiScreen | None = None
    status_bar: str = ""


def init(screen_rect, gui_screens):
    but_w = 200
    but_h = 80

    gui_buttons[:] = [
        GuiButton(
            pygame.Rect(
                screen_rect.width / 2 - but_w / 2,
                screen_rect.height - but_h - STATUS_HEIGHT - MARGIN,
                200,
                but_h,
            ),
            (100, 200, 100),
            "Apply",
            lambda: save_layout(gui_screens),
            description="Save layout (run wlr-randr)",
        )
    ]


def save_layout(screens: list[GuiScreen]):
    min_x = UI_RATIO * min([screen.rect.x for screen in screens])
    min_y = UI_RATIO * min([screen.rect.y for screen in screens])
    print("# Screens layout:")
    for gs in screens:
        if not gs.screen.mode:
            continue
        x: int = gs.rect.x * UI_RATIO - min_x
        y: int = gs.rect.y * UI_RATIO - min_y
        if LEGACY:
            command = f"xrandr --output {gs.screen.uid} --pos {x}x{y} --mode {gs.screen.mode.width}x{gs.screen.mode.height}"
        else:
            command = f"wlr-randr --output {gs.screen.uid} --pos {x},{y} --mode {gs.screen.mode.width}x{gs.screen.mode.height}"
        print(command)
        os.system(command)


def draw_layout_mode(gui_screens: list[GuiScreen], display: pygame.Surface):
    for wid in chain(gui_screens, gui_buttons):
        wid.draw(display)

    # Grey status bar with white text showing the screen name when mouse is hovering over it
    status_bar_rect = pygame.Rect(display.get_rect())
    status_bar_rect.height = STATUS_HEIGHT
    status_bar_rect.y = display.get_rect().height - STATUS_HEIGHT

    pygame.draw.rect(display, (100, 100, 100), status_bar_rect)
    status_text = shared["font"].render(Ctx.status_bar, True, (255, 255, 255))
    status_text_rect = status_text.get_rect()
    status_text_rect.center = status_bar_rect.center
    status_text_rect.x = MARGIN
    display.blit(status_text, status_text_rect)


def run_layout_mode(gui_screens: list[GuiScreen], event):
    Ctx.status_bar = Ctx.moving.statusInfo if Ctx.moving else ""
    gui_mode = None

    for wid in chain(gui_screens, gui_buttons):
        wid.handle_event(event)
        if wid.hovering:
            Ctx.status_bar = wid.statusInfo

    # Handle mouse events
    if event.type == pygame.MOUSEBUTTONDOWN:
        # Check if the click was inside any of the rectangles
        for wid in gui_screens:
            if wid.rect.collidepoint(event.pos):
                # Remove the clicked gui_screenangle f]rom the list of rectangles
                gui_screens.remove(wid)
                # Append it to the end of the list to ensure it is drawn on top of the others
                gui_screens.append(wid)

                if event.button > 1:
                    gui_mode = wid
                break
    elif event.type == pygame.MOUSEBUTTONUP:
        Ctx.moving = None
        # Check screen overlaps and correct the rectangles accordingly
        active_screen = gui_screens[-1]
        for wid in gui_screens[:-1]:
            if wid.rect.colliderect(active_screen.rect):
                # find the pair of corners (one from gui_screen & one from active_screen) which are closest
                other_screen_coords: list[tuple[int, int]] = [
                    (wid.rect.x, wid.rect.y),
                    (wid.rect.x, wid.rect.y + wid.rect.width),
                    (wid.rect.x + wid.rect.width, wid.rect.y),
                    (wid.rect.x + wid.rect.width, wid.rect.y + wid.rect.height),
                ]
                active_screen_coords: list[tuple[int, int]] = [
                    (active_screen.rect.x, active_screen.rect.y),
                    (
                        active_screen.rect.x,
                        active_screen.rect.y + active_screen.rect.width,
                    ),
                    (
                        active_screen.rect.x + active_screen.rect.width,
                        active_screen.rect.y,
                    ),
                    (
                        active_screen.rect.x + active_screen.rect.width,
                        active_screen.rect.y + active_screen.rect.height,
                    ),
                ]

                def distance(point1: tuple[int, int], point2: tuple[int, int]):
                    return math.sqrt(
                        (point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2
                    )

                # find which coordinates from active_screen & gui_screen are closest
                min_distance = None
                closest_gui_screen_coord = None
                for coord in active_screen_coords:
                    for other_screen_coord in other_screen_coords:
                        if (
                            min_distance is None
                            or distance(coord, other_screen_coord) < min_distance
                        ):
                            min_distance = distance(coord, other_screen_coord)
                            closest_gui_screen_coord = other_screen_coord, coord
                assert closest_gui_screen_coord is not None
                active_screen.rect.x -= (
                    closest_gui_screen_coord[1][0] - closest_gui_screen_coord[0][0]
                )
                active_screen.rect.y -= (
                    closest_gui_screen_coord[1][1] - closest_gui_screen_coord[0][1]
                )

    # Handle dragging events
    elif event.type == pygame.MOUSEMOTION:
        if event.buttons[0] == 1:
            if Ctx.moving:
                Ctx.moving.rect.x += event.rel[0]
                Ctx.moving.rect.y += event.rel[1]
            else:
                # Get the mouse position
                x, y = event.pos

                # Find the rectangle being dragged
                for wid in gui_screens:
                    if wid.rect.collidepoint(x, y):
                        Ctx.moving = wid
                        # Move the gui_screenangle
                        wid.rect.x += event.rel[0]
                        wid.rect.y += event.rel[1]
                        break
    return gui_mode
