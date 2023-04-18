import random
import pygame
from .base import Screen

__all__ = ["GuiButton", "GuiScreen", "shared"]

shared = {}


class GuiButton:
    def __init__(
        self,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        caption: str,
        clicked,
        description=None,
        icon=None,
        icon_size=0,
        icon_align="l",
        padding=5,
    ):
        self.rect = rect
        self.color = color
        self.caption = caption
        self.clicked = clicked
        self.hovering = False
        self.statusInfo = description or caption
        self._clicked = False
        self.icon = icon
        self.icon_shape = None
        self.icon_align = icon_align
        self.icon_size = icon_size
        self.padding = padding

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=10)
        if self.hovering:
            pygame.draw.rect(
                surface,
                [x / 2 for x in self.color],
                self.rect,
                width=5,
                border_radius=10,
            )

        if self.icon_align == "c":  # icon only
            assert self.icon
            pygame.draw.polygon(
                surface,
                (0, 0, 0),
                self.icon(
                    position=(
                        self.rect.center[0],
                        self.rect.center[1],
                    ),
                    size=self.icon_size,
                ),
            )
            return

        text = shared["bigfont"].render(self.caption, True, (0, 0, 0))

        # Calculate the position to blit the text onto the rectangle
        text_rect: pygame.Rect = text.get_rect()
        text_rect.center = self.rect.center

        if self.icon:
            if not self.icon_align or self.icon_align[0] == "l":
                pygame.draw.polygon(
                    surface,
                    (255, 0, 0),
                    self.icon(
                        position=(
                            text_rect.left - self.padding,
                            text_rect.center[1],
                        ),
                        size=self.icon_size,
                    ),
                )
                text_rect.left += self.icon_size // 2
            else:
                pygame.draw.polygon(
                    surface,
                    (0, 0, 255),
                    self.icon(
                        position=(
                            text_rect.right + self.padding,
                            text_rect.center[1],
                        ),
                        size=self.icon_size,
                    ),
                )
                text_rect.left -= self.icon_size // 2
        #                 pygame.draw.polygon(surface, (0,0,0), self.icon(position=(self.rect.x + text_rect.x, self.rect.y), size=self.icon_size))
        # Blit the text onto the rectangle
        surface.blit(text, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._clicked = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if not self._clicked and self.hovering:
                self._clicked = True
                self.clicked()


class GuiScreen:
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
        rect: pygame.Rect,
        color: tuple[int, int, int] = (100, 100, 100),
    ):
        self.screen = screen
        self.rect = rect
        self.color = color
        self.hovering = False

    def genColor(self):
        if self.cur_color >= len(self.all_colors):
            self.color = (
                random.randint(100, 200),
                random.randint(100, 200),
                random.randint(100, 200),
            )
        else:
            self.color = self.all_colors[self.cur_color]
            GuiScreen.cur_color += 1

    @property
    def statusInfo(self):
        return "Screen identifier: " + self.screen.name

    def draw(self, surface: pygame.Surface):
        # draw the background
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (50, 50, 50), self.rect, width=3)

        # Render the screen uid as text
        text = shared["font"].render(self.screen.uid, True, (0, 0, 0))

        # Calculate the position to blit the text onto the rectangle
        text_rect = text.get_rect()
        text_rect.center = self.rect.center
        # Blit the text onto the rectangle
        surface.blit(text, text_rect)

        # Second caption line
        if not self.screen.mode:
            label = "N/A"
        else:
            label = "%dx%d @%.2d" % (
                self.screen.mode.width,
                self.screen.mode.height,
                self.screen.mode.freq,
            )
        text2 = shared["font"].render(label, True, (0, 0, 0))
        label_rect = text2.get_rect()
        label_rect.center = self.rect.center
        label_rect.y += text_rect.height + 10
        surface.blit(text2, label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovering = self.rect.collidepoint(event.pos)
