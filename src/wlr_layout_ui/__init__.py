#!/bin/env python
import os
import math
import random
from itertools import chain

import pygame

UI_RATIO = 8
STATUS_HEIGHT = 20
MARGIN = 5

from .base import Screen, displayInfo, load as loadDisplayInfo, LEGACY

shared = {}


class GuiButton:
    def __init__(
        self,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        caption: str,
        clicked,
        description=None,
    ):
        self.rect = rect
        self.color = color
        self.caption = caption
        self.clicked = clicked
        self.hovering = False
        self.statusInfo = description or caption
        self._clicked = False

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=10)
        if self.hovering:
            pygame.draw.rect(
                surface,
                [x / 2 for x in self.color],
                self.rect,
                width=5,
                border_radius=10,
            )

        # Render the screen uid as text
        text = shared["bigfont"].render(self.caption, True, (0, 0, 0))

        # Calculate the position to blit the text onto the rectangle
        text_rect = text.get_rect()
        text_rect.center = self.rect.center
        # Blit the text onto the rectangle
        surface.blit(text, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._clicked = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if not self._clicked and self.hovering:
                self._clicked = True
                self.clicked()


class GuiScreen:
    def __init__(
        self,
        screen: Screen,
        rect: pygame.Rect,
        color: tuple[int, int, int] = (100, 100, 100),
    ):
        self.screen = screen
        self.rect = rect
        self.color = color
        self.hovering = False

    def genColor(self):
        self.color = (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200),
        )

    @property
    def statusInfo(self):
        return "Screen identifier: " + self.screen.name

    def draw(self, surface: pygame.Surface):
        # draw the background
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (50, 50, 50), self.rect, width=3)

        # Render the screen uid as text
        text = shared["font"].render(self.screen.uid, True, (0, 0, 0))

        # Calculate the position to blit the text onto the rectangle
        text_rect = text.get_rect()
        text_rect.center = self.rect.center
        # Blit the text onto the rectangle
        surface.blit(text, text_rect)

        # Second caption line
        if not self.screen.mode:
            label = "N/A"
        else:
            label = "%dx%d" % (self.screen.mode.width, self.screen.mode.height)
        text2 = shared["font"].render(label, True, (0, 0, 0))
        label_rect = text2.get_rect()
        label_rect.center = self.rect.center
        label_rect.y += text_rect.height + 10
        surface.blit(text2, label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.rect.collidepoint(event.pos)


def save_layout(screens: list[GuiScreen]):
    min_x = UI_RATIO * min([screen.rect.x for screen in screens])
    min_y = UI_RATIO * min([screen.rect.y for screen in screens])
    for screen in screens:
        x: int = screen.rect.x * UI_RATIO - min_x
        y: int = screen.rect.y * UI_RATIO - min_y
        if LEGACY:
            os.system(f"xrandr --output {screen.screen.uid} --pos {x}x{y}")
        else:
            os.system(f"wlr-randr --output {screen.screen.uid} --pos {x},{y}")


def gui():
    # Define a scale factor for the display surface

    # Get the maximum mode width and height for each available screen
    max_width = int(
        sum(
            max(screen.available, key=lambda mode: mode.width).width
            for screen in displayInfo
        )
        / UI_RATIO
    )
    max_height = int(
        sum(
            max(screen.available, key=lambda mode: mode.height).height
            for screen in displayInfo
        )
        / UI_RATIO
    )

    # Create a Pygame display surface with the maximum size
    display = pygame.display.set_mode((max_width * 2, max_height * 2))
    screen_rect = display.get_rect()
    gui_screens: list[GuiScreen] = []

    but_w = 200
    but_h = 80
    gui_buttons = [
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
    # Loop over each screen in the displayInfo list
    for screen in displayInfo:
        # Get the position and mode width and height for this screen
        x, y = screen.position
        max_width = max(screen.available, key=lambda mode: mode.width).width
        max_height = max(screen.available, key=lambda mode: mode.height).height

        if screen.mode:
            rect = pygame.Rect(
                int(x / UI_RATIO),
                int(y / UI_RATIO),
                int(screen.mode.width / UI_RATIO),
                int(screen.mode.height / UI_RATIO),
            )
        else:
            rect = pygame.Rect(
                int(x / UI_RATIO),
                int(y / UI_RATIO),
                int(max_width / UI_RATIO),
                int(max_height / UI_RATIO),
            )
        gs = GuiScreen(screen, rect)
        gs.genColor()
        gui_screens.append(gs)

    # Main loop for the Pygame application
    running = True
    status_bar = ""
    moving = False
    while running:
        # Handle Pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if the click was inside any of the rectangles
                for wid in gui_screens:
                    if wid.rect.collidepoint(event.pos):
                        # Remove the clicked gui_screenangle from the list of rectangles
                        gui_screens.remove(wid)
                        # Append it to the end of the list to ensure it is drawn on top of the others
                        gui_screens.append(wid)
                        break
            elif event.type == pygame.MOUSEBUTTONUP:
                moving = False
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
                                (point1[0] - point2[0]) ** 2
                                + (point1[1] - point2[1]) ** 2
                            )

                        # find which coordinates from active_screen & gui_screen are closest
                        min_distance = None
                        closest_gui_screen_coord = None
                        for coord in active_screen_coords:
                            for other_screen_coord in other_screen_coords:
                                if (
                                    min_distance is None
                                    or distance(coord, other_screen_coord)
                                    < min_distance
                                ):
                                    min_distance = distance(coord, other_screen_coord)
                                    closest_gui_screen_coord = other_screen_coord, coord
                        assert closest_gui_screen_coord is not None
                        active_screen.rect.x -= (
                            closest_gui_screen_coord[1][0]
                            - closest_gui_screen_coord[0][0]
                        )
                        active_screen.rect.y -= (
                            closest_gui_screen_coord[1][1]
                            - closest_gui_screen_coord[0][1]
                        )

            # Handle dragging events
            elif event.type == pygame.MOUSEMOTION and event.buttons[0] == 1:
                if moving:
                    moving.rect.x += event.rel[0]
                    moving.rect.y += event.rel[1]
                else:
                    # Get the mouse position
                    x, y = event.pos

                    # Find the rectangle being dragged
                    for wid in gui_screens:
                        if wid.rect.collidepoint(x, y):
                            moving = wid
                            # Move the gui_screenangle
                            wid.rect.x += event.rel[0]
                            wid.rect.y += event.rel[1]
                            break

            # propagate to widgets
            status_bar = ""
            for wid in chain(gui_screens, gui_buttons):
                wid.handle_event(event)
                if wid.hovering:
                    status_bar = wid.statusInfo

        # Draw the rectangles on the Pygame display surface with a neutral grey
        display.fill((150, 150, 150))

        # Grey status bar with white text showing the screen name when mouse is hovering over it
        status_bar_rect = pygame.Rect(display.get_rect())
        status_bar_rect.height = STATUS_HEIGHT
        status_bar_rect.y = display.get_rect().height - STATUS_HEIGHT

        pygame.draw.rect(display, (100, 100, 100), status_bar_rect)
        status_text = shared["font"].render(status_bar, True, (255, 255, 255))
        status_text_rect = status_text.get_rect()
        status_text_rect.center = status_bar_rect.center
        status_text_rect.x = MARGIN
        display.blit(status_text, status_text_rect)

        for wid in gui_screens:
            wid.draw(display)

        for but in gui_buttons:
            but.draw(display)

        # Update the Pygame display surface
        pygame.display.flip()


def main():
    loadDisplayInfo()
    # Initialize Pygame
    pygame.init()
    shared["font"] = pygame.font.Font(None, 24)  # Change the font and size as desired
    shared["bigfont"] = pygame.font.Font(
        None, 36
    )  # Change the font and size as desired
    gui()
    pygame.quit()


if __name__ == "__main__":
    main()
