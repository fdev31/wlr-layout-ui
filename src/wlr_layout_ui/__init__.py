#!/bin/env python
import math
import random

import pygame

from .base import Screen, displayInfo, load as loadDisplayInfo

shared = {}

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

    def draw(self, surface: pygame.Surface):
        # draw the background
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (50, 50, 50), self.rect, width=3)

        # Render the screen uid as text
        text = shared['font'].render(self.screen.uid, True, (0, 0, 0))

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
        text2 = shared['font'].render(label, True, (0, 0, 0))
        label_rect = text2.get_rect()
        label_rect.center = self.rect.center
        label_rect.y += text_rect.height + 10
        surface.blit(text2, label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.rect.collidepoint(event.pos)


def gui():
    # Define a scale factor for the display surface
    scale_factor = 8

    # Get the maximum mode width and height for each available screen
    max_width = int(
        sum(
            max(screen.available, key=lambda mode: mode.width).width
            for screen in displayInfo
        )
        / scale_factor
    )
    max_height = int(
        sum(
            max(screen.available, key=lambda mode: mode.height).height
            for screen in displayInfo
        )
        / scale_factor
    )

    # Create a Pygame display surface with the maximum size
    display = pygame.display.set_mode((max_width * 2, max_height * 2))

    # Loop over each screen in the displayInfo list
    gui_screens: list[GuiScreen] = []
    for screen in displayInfo:
        # Get the position and mode width and height for this screen
        x, y = screen.position
        max_width = max(screen.available, key=lambda mode: mode.width).width
        max_height = max(screen.available, key=lambda mode: mode.height).height

        if screen.mode:
            rect = pygame.Rect(
                int(x / scale_factor),
                int(y / scale_factor),
                int(screen.mode.width / scale_factor),
                int(screen.mode.height / scale_factor),
            )
        else:
            rect = pygame.Rect(
                int(x / scale_factor),
                int(y / scale_factor),
                int(max_width / scale_factor),
                int(max_height / scale_factor),
            )
        gs = GuiScreen(screen, rect)
        gs.genColor()
        gui_screens.append(gs)

    # Main loop for the Pygame application
    running = True
    status_bar = ''
    while running:
        # Handle Pygame events
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            # Handle mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if the click was inside any of the rectangles
                for gui_screen in gui_screens:
                    if gui_screen.rect.collidepoint(event.pos):
                        # Remove the clicked gui_screenangle from the list of rectangles
                        gui_screens.remove(gui_screen)
                        # Append it to the end of the list to ensure it is drawn on top of the others
                        gui_screens.append(gui_screen)
                        break
            elif event.type == pygame.MOUSEBUTTONUP:
                for gui_screen in gui_screens:
                    gui_screen.rect.x = round(gui_screen.rect.x/4) * 4
                    gui_screen.rect.y = round(gui_screen.rect.y/4) * 4
                # Check screen overlaps and correct the rectangles accordingly
                active_screen = gui_screens[-1]
                for gui_screen in gui_screens[:-1]:
                    if gui_screen.rect.colliderect(active_screen.rect):
                        # find the pair of corners (one from gui_screen & one from active_screen) which are closest
                        gui_screen_coords = [
                            (gui_screen.rect.x, gui_screen.rect.y),
                            (gui_screen.rect.x, gui_screen.rect.y + gui_screen.rect.width),
                            (gui_screen.rect.x + gui_screen.rect.width, gui_screen.rect.y),
                            (gui_screen.rect.x + gui_screen.rect.width, gui_screen.rect.y + gui_screen.rect.height),
                        ]
                        active_screen_coords = [
                            (active_screen.rect.x, active_screen.rect.y),
                            (active_screen.rect.x, active_screen.rect.y + active_screen.rect.width),
                            (active_screen.rect.x + active_screen.rect.width, active_screen.rect.y),
                            (active_screen.rect.x + active_screen.rect.width, active_screen.rect.y + active_screen.rect.height),
                        ]
                        def distance(point1: tuple[int, int], point2: tuple[int,int]):
                            return math.sqrt(
                                (point1[0] - point2[0])**2 + (point1[1] - point2[1])**2
                            )
                        # find which coordinates from active_screen & gui_screen are closest
                        min_distance = None
                        closest_gui_screen_coord = None
                        for coord in active_screen_coords:
                            for gui_screen_coord in gui_screen_coords:
                                if  min_distance is None or distance(coord, gui_screen_coord) < min_distance:
                                    min_distance = distance(coord, gui_screen_coord)
                                    closest_gui_screen_coord = gui_screen_coord, coord
                        active_screen.rect.x -= (closest_gui_screen_coord[1][0] - closest_gui_screen_coord[0][0])
                        active_screen.rect.y -= (closest_gui_screen_coord[1][1] - closest_gui_screen_coord[0][1])



            # Handle dragging events
            elif event.type == pygame.MOUSEMOTION and event.buttons[0] == 1:
                # Get the mouse position
                x, y = event.pos

                # Find the rectangle being dragged
                for gui_screen in gui_screens:
                    if gui_screen.rect.collidepoint(x, y):
                        # Move the gui_screenangle
                        gui_screen.rect.x += event.rel[0]
                        gui_screen.rect.y += event.rel[1]
                        break

            # propagate to screens
            for gui_screen in gui_screens:
                gui_screen.handle_event(event)
                if gui_screen.hovering:
                    status_bar = gui_screen.screen.name


        # Draw the rectangles on the Pygame display surface
        display.fill((255, 255, 255))

       # Grey status bar with white text showing the screen name when mouse is hovering over it
        status_bar_rect = pygame.Rect(display.get_rect())
        status_bar_rect.height = 20
        status_bar_rect.y = display.get_rect().height - 20

        pygame.draw.rect(display, (150, 150, 150), status_bar_rect)
        status_text = shared['font'].render(status_bar, True, (255, 255, 255))
        status_text_rect = status_text.get_rect()
        status_text_rect.center = status_bar_rect.center
        display.blit(status_text, status_text_rect)


        for gui_screen in gui_screens:
            gui_screen.draw(display)

        # Update the Pygame display surface
        pygame.display.flip()


def main():
    loadDisplayInfo()
    # Initialize Pygame
    pygame.init()
    shared['font'] = pygame.font.Font(None, 24)  # Change the font and size as desired
    gui()
    pygame.quit()


if __name__ == "__main__":
    main()
