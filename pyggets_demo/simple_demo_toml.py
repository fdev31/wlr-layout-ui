#!/usr/bin/env python3
"""Minimal pyggets demo using the TOML loader with window and theme support."""

import sys
from pathlib import Path

sys.path.insert(0, "src")

import pyglet

from pyggets import load_ui, run_ui


class Controller:
    @staticmethod
    def on_close() -> None:
        pyglet.app.exit()


if __name__ == "__main__":
    result = load_ui(Path(__file__).parent / "simple_demo.toml", Controller())
    run_ui(result)
