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
