#!/bin/env python

import pygame

from .base import load as loadDisplayInfo
from .guibase import gui
from .widgets import shared


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
