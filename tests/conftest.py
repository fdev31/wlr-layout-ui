import sys
from dataclasses import replace

sys.path.insert(0, "src")

import pyglet

pyglet.options["headless"] = True

import pytest  # noqa: E402

from pyggets.theme import get_default_theme, set_default_theme  # noqa: E402


@pytest.fixture(autouse=True)
def reset_theme_scale():
    original = get_default_theme()
    set_default_theme(replace(original, scale=1.0))
    yield
    set_default_theme(original)
