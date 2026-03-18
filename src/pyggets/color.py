"""Color utility functions for pyggets widgets."""


def brighten(color, amount=20):
    """Return a brightened version of the given color tuple."""
    return tuple(min(255, c + amount) for c in color)
