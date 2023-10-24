from dataclasses import dataclass


def brighten(color):
    return [min(255, c + 20) for c in color]


def collidepoint(x, y, x2, y2, xp, yp):
    assert x < x2
    assert y < y2
    return x < xp < x2 and y < yp < y2


def sorted_resolutions(modes):
    res = set((m.width, m.height) for m in modes)
    lres = list(res)
    lres.sort(reverse=True)
    return lres


def sorted_frequencies(modes, filter_w=None, filter_h=None):
    filtered_modes = modes.copy()
    if filter_w:
        filtered_modes = filter(lambda m: m.width == filter_w, filtered_modes)
    if filter_h:
        filtered_modes = filter(lambda m: m.height == filter_h, filtered_modes)
    res = set(m.freq for m in filtered_modes)
    lres = list(res)
    lres.sort(reverse=True)
    return lres


def find_matching_mode(modes, res, freq):
    for mode in modes:
        if mode.width == res[0] and mode.height == res[1] and mode.freq == freq:
            return mode


def compute_bounding_box(rects):
    min_x = min(r.x for r in rects)
    min_y = min(r.y for r in rects)
    max_x = max(r.x + r.width for r in rects)
    max_y = max(r.y + r.height for r in rects)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def trim_rects_flip_y(rects):
    min_x = min([r.x for r in rects])
    min_y = min([-r.y for r in rects])
    for rect in rects:
        rect.x = int(rect.x - min_x)
        rect.y = int(-rect.y - min_y)


@dataclass
class Rect:  # {{{
    x: int
    y: int
    width: int
    height: int

    @property
    def topleft(self):
        return (self.left, self.top)

    @property
    def topright(self):
        return (self.right, self.top)

    @property
    def bottomleft(self):
        return (self.left, self.bottom)

    @property
    def bottomright(self):
        return (self.right, self.bottom)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y + self.height

    @property
    def bottom(self):
        return self.y

    @property
    def center(self):
        return self.x + self.width // 2, self.y + self.height // 2

    def contains(self, x, y):
        return collidepoint(
            self.x, self.y, self.x + self.width, self.y + self.height, x, y
        )

    def collide(self, rect):
        # return true if the two rectangles are overlapping in any way
        if rect.left >= self.right:
            return False
        if rect.right <= self.left:
            return False
        if rect.top <= self.bottom:
            return False
        if rect.bottom >= self.top:
            return False
        return True

    def copy(self):
        return Rect(self.x, self.y, self.width, self.height)

    def asTuple(self):
        return (self.x, self.y, self.width, self.height)

    def scaled(self, factor):
        return (
            self.x * factor,
            self.y * factor,
            self.width * factor,
            self.height * factor,
        )


# }}}
