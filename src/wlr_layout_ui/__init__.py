#!/bin/env python

import os
import pygame

from .base import load as loadDisplayInfo
from .guibase import gui
from .widgets import shared


def main():
    loadDisplayInfo()
    if (
        os.environ.get("SDL_VIDEODRIVER", "") == "wayland"
        and not "NOHACK" in os.environ
    ):
        os.environ["SDL_VIDEODRIVER"] = "x11"
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
