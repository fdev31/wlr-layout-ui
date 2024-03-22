from functools import cache
from .factories import makeCircle, makeRectangle


@cache
def makeRoundedRectangle(rect, radius, color):
    return RoundedRectangle(rect, radius, color)


class RoundedRectangle:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.radius = radius
        self.color = tuple(color)

    def draw(self):
        if not self.radius:
            makeRectangle(
                self.rect.x,
                self.rect.y,
                self.rect.width,
                self.rect.height,
                color=self.color,
            ).draw()
            return
        # Draw rounded corners using circles
        rect = self.rect
        color = self.color
        diameter = 2 * self.radius
        corners_pos = [
            (rect.x, rect.y),
            (rect.x + rect.width - diameter, rect.y),
            (rect.x, rect.y + rect.height - diameter),
            (
                rect.x + rect.width - diameter,
                rect.y + rect.height - diameter,
            ),
        ]
        for corner_x, corner_y in corners_pos:
            makeCircle(
                corner_x + self.radius,
                corner_y + self.radius,
                self.radius,
                color=color,
            ).draw()

        # Draw rectangles to fill the gaps inside the rounded borders
        makeRectangle(
            rect.x + self.radius,
            rect.y,
            rect.width - diameter,
            rect.height,
            color=color,
        ).draw()
        makeRectangle(
            rect.x,
            rect.y + self.radius,
            rect.width,
            rect.height - diameter,
            color=color,
        ).draw()
