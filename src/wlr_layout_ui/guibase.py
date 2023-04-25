import pygame
from .base import displayInfo
from .layoutmode import draw_layout_mode
from .layoutmode import init as init_layout_mode
from .layoutmode import run_layout_mode
from .settingsmode import run_settings_mode, draw_settings_mode
from .settingsmode import init as init_settings_mode
from .settings import UI_RATIO
from .widgets import GuiScreen


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

    max_x = max(s.rect.right for s in gui_screens)
    min_x = min(s.rect.left for s in gui_screens)
    min_y = min(s.rect.top for s in gui_screens)
    max_y = min(s.rect.bottom for s in gui_screens)

    offsetX = (display.get_width() - (max_x - min_x)) //2 
    offsetY = (display.get_height() - (max_y  - min_y))//2

    for screen in gui_screens:
        screen.rect.x += offsetX
        screen.rect.y += offsetY


    init_layout_mode(screen_rect, gui_screens)
    init_settings_mode(screen_rect, gui_screens)
    # Main loop for the Pygame application
    running = True
    settings_mode = None
    clock = pygame.time.Clock()
    while running:
        old_mode = settings_mode
        # Handle Pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if settings_mode:
                settings_mode = run_settings_mode(settings_mode, event)
            else:
                settings_mode = run_layout_mode(gui_screens, event)

        # Draw the rectangles on the Pygame display surface with a neutral grey

        if old_mode == settings_mode:  # do not refresh during transitions
            display.fill((30, 30, 30))
            if settings_mode:
                draw_settings_mode(settings_mode, display)
            else:
                draw_layout_mode(gui_screens, display)

        # Update the Pygame display surface
        pygame.display.flip()
        clock.tick(15)
