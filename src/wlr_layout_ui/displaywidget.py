import pyglet
from pyglet import shapes
from .utils import collidepoint
from .screens import Screen
from .widgets import Rect
import random


class GuiScreen:
    def __str__(self):
        return "<Screen %s (%s) - %s>" % (self.rect, self.color, self.screen.name)

    all_colors: tuple[tuple[int, int, int], ...] = (
        (172, 65, 66),
        (126, 141, 80),
        (229, 181, 102),
        (108, 153, 186),
        (158, 78, 133),
        (125, 213, 207),
        (208, 208, 208),
    )
    cur_color = 0

    def __init__(
        self,
        screen: Screen,
        rect: Rect,
        color: tuple[int, int, int] = (100, 100, 100),
    ):
        self.screen = screen
        self.rect = rect
        self.target_rect = rect.copy()
        self.color = color
        self.dragging = False
        self.highlighted = False

    def genColor(self):
        if self.cur_color >= len(self.all_colors):
            self.color = (
                random.randint(100, 200),
                random.randint(100, 200),
                random.randint(100, 200),
                255,
            )
        else:
            self.color = list(self.all_colors[self.cur_color]) + [255]
            GuiScreen.cur_color += 1
        self.drag_color = list(self.color)
        self.drag_color[-1] = 200

    @property
    def current_color(self):
        """The current_color property."""
        color = self.drag_color if self.dragging else self.color
        if self.screen.active:
            return color
        return [color[0] // 3, color[1] // 3, color[2] // 3, color[3]]

    @property
    def statusInfo(self):
        return "Screen identifier: " + self.screen.name

    def _animation_step(self, speed=1):
        r = self.rect
        t = self.target_rect
        for var in ("x", "y", "width", "height"):
            cv = getattr(r, var)
            tv = getattr(t, var)
            if cv != tv:
                if abs(tv - cv) <= 1:
                    setattr(r, var, tv)
                else:
                    if cv < tv:
                        setattr(r, var, min(tv, (cv + tv) / 2))
                    elif cv > tv:
                        setattr(r, var, max(tv, (cv + tv) / 2))

    def set_position(self, x, y):
        self.rect.x = x
        self.target_rect.x = x
        self.rect.y = y
        self.target_rect.y = y

    def draw(self):
        if self.rect != self.target_rect:
            self._animation_step()

        txt_color = (0, 0, 0, 200) if self.screen.active else (255, 255, 255, 120)
        border_color = (100, 100, 155)
        if not self.screen.active:
            border_color = (70, 70, 70)
        if self.highlighted:
            border_color = (255, 201, 0)
        # draw the background
        shapes.BorderedRectangle(
            self.rect.x,
            self.rect.y,
            self.rect.width,
            self.rect.height,
            border=9 if self.highlighted else 2,
            color=self.current_color,
            border_color=border_color,
        ).draw()
        # Render the screen uid as text
        tx, ty = self.rect.center
        pyglet.text.Label(
            self.screen.uid,
            anchor_x="center",
            anchor_y="center",
            x=tx,
            y=ty,
            font_size=16,
            color=(200, 200, 200, 255),
        ).draw()

        # Second caption line
        if self.screen.active:
            assert self.screen.mode
            label = "%dx%d" % (
                self.screen.mode.width,
                self.screen.mode.height,
            )
            pyglet.text.Label(
                label,
                anchor_x="center",
                anchor_y="center",
                x=tx,
                y=ty + 20,
                color=txt_color,
                bold=self.screen.active,
            ).draw()
            pyglet.text.Label(
                "%dHz" % self.screen.mode.freq,
                anchor_x="center",
                anchor_y="center",
                x=tx,
                y=ty - 20,
                color=txt_color,
                bold=self.screen.active,
            ).draw()
