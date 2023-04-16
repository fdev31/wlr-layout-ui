import pygame
import random
from typing import Tuple

# Base


class Mode:
    def __init__(self, width, height, freq):
        self.width = width
        self.height = height
        self.freq = freq


class Screen:
    def __init__(
        self,
        uid: str,
        name: str,
        active: bool = False,
        position: Tuple[int, int] = (0, 0),
        mode: None | Mode = None,
    ):
        self.uid = uid
        self.name = name
        self.active = active
        self.position = position
        self.mode: Mode | None = mode
        self.available: list[Mode] = []


displayInfo: list[Screen] = []


def load():
    import subprocess

    out = subprocess.getoutput("wlr-randr")
    current_screen: None | Screen = None
    mode_mode = False
    for line in out.splitlines():
        if line[0] != " ":
            uid, name = line.split(None, 1)
            current_screen = Screen(uid=uid, name=name)
            displayInfo.append(current_screen)
            mode_mode = False
        else:
            if line[2] != " ":
                mode_mode = False
            assert current_screen
            sline = line.strip()
            if mode_mode:
                res, freq = sline.split(",", 1)
                res = res.split(None, 1)[0]
                res = tuple(int(x) for x in res.split("x"))
                freq, comment = freq.strip().split(None, 1)
                current_screen.available.append(Mode(res[0], res[1], float(freq)))
                if "current" in comment:
                    current_screen.mode = current_screen.available[-1]

            elif sline.startswith("Modes:"):
                mode_mode = True
            elif sline.startswith("Enabled"):
                current_screen.active = "yes" in sline
            elif sline.startswith("Position"):
                current_screen.position = tuple(
                    int(x) for x in sline.split(":")[1].strip().split(",")
                )


# Gui


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
        self.font = pygame.font.Font(None, 24)  # Change the font and size as desired

    def genColor(self):
        self.color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)

        # Render the screen name as text
        text = self.font.render(self.screen.uid, True, (0, 0, 0))

        # Calculate the position to blit the text onto the rectangle
        text_rect = text.get_rect()
        text_rect.center = self.rect.center

        # Blit the text onto the rectangle
        surface.blit(text, text_rect)


def gui():
    # Define a scale factor for the display surface
    scale_factor = 10

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
        width = max(screen.available, key=lambda mode: mode.width).width
        height = max(screen.available, key=lambda mode: mode.height).height

        rect = pygame.Rect(
            int(x / scale_factor),
            y / scale_factor,
            width / scale_factor,
            height / scale_factor,
        )
        gs = GuiScreen(screen, rect)
        gs.genColor()
        gui_screens.append(gs)

    # Main loop for the Pygame application
    running = True
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

        # Draw the rectangles on the Pygame display surface
        display.fill((255, 255, 255))
        for gui_screen in gui_screens:
            gui_screen.draw(display)

        # Update the Pygame display surface
        pygame.display.flip()


if __name__ == "__main__":
    load()
    # Initialize Pygame
    pygame.init()
    gui()
    pygame.quit()
