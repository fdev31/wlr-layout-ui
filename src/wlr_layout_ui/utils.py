import json
import re
import subprocess
from functools import lru_cache

from .types import Rect, Screen

config = {"hyprland": False}

hex_re = re.compile(r"^[0-9x]+$")


@lru_cache(maxsize=1)
def _using_lua_syntax() -> bool:
    """Check if Hyprland version supports Lua monitor syntax (>= 0.55.0)."""
    try:
        data = json.loads(subprocess.getoutput("hyprctl -j version"))
        match = re.search(r"v?(\d+)\.(\d+)", data.get("version", ""))
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            return (major, minor) >= (0, 55)
    except Exception:
        pass
    return False


def get_size(width: int, height: int, scale: float, transform: int, glob_scale: float = 1):
    w, h = (
        int((width / glob_scale) / scale),
        int((height / glob_scale) / scale),
    )
    if transform in (1, 3, 5, 7):
        return (h, w)
    return (w, h)


def get_screen_size(screen: Screen, scale: float = 1):
    """Get the size of the window based on the screen size and UI_RATIO."""
    assert screen.mode
    return get_size(screen.mode.width, screen.mode.height, screen.scale, screen.transform, scale)


def simplify_model_name(name):
    # remove duplicate words keeping order (comparing lowercase)
    words = list(dict.fromkeys(word for word in name.split() if not hex_re.match(word)))
    return " ".join(words)


def make_command(screens: list[Screen], rects: list[Rect], wayland=True) -> list[str]:
    return make_command_hyprland(screens, rects) if wayland and config.get("hyprland") else make_command_legacy(screens, rects, wayland)


def _make_command_hyprland_lua(screens: list[Screen], rects: list[Rect]) -> list[str]:
    screens_rect = rects.copy()
    trim_rects_flip_y(screens_rect)
    commands = []

    on_off_commands = []

    for screen, rect in zip(screens, screens_rect):
        if not screen.active:
            on_off_commands.append(f'hl.monitor({{output="{screen.uid}", disabled=true}})')
            continue
        else:
            on_off_commands.append(f'hl.monitor({{output="{screen.uid}", disabled=false}})')
        parts = [f'output="{screen.uid}"']
        parts.append(f'mode="{screen.mode}"')
        pos = f"{int(rect.x)}x{int(rect.y)}"
        parts.append(f'position="{pos}"')
        parts.append(f"scale={screen.scale:g}")
        parts.append(f"transform={screen.transform}")
        commands.append("hl.monitor({" + ", ".join(parts) + "})")

    return ["hyprctl eval '" + " ; ".join(on_off_commands) + "'", "sleep 2", "hyprctl eval '" + " ; ".join(commands) + "'"]


def _make_command_hyprland_old(screens: list[Screen], rects: list[Rect]) -> list[str]:
    screens_rect = rects.copy()
    trim_rects_flip_y(screens_rect)
    keywords = []

    for screen, rect in zip(screens, screens_rect):
        if not screen.active:
            keywords.append(f"keyword monitor {screen.uid},disable")
            continue
        keywords.append(
            f"keyword monitor {screen.uid},{screen.mode},{int(rect.x)}x{int(rect.y)},{screen.scale:.6f},transform,{screen.transform}"
        )

    return ['hyprctl --batch "' + " ; ".join(keywords) + '"']


def make_command_hyprland(screens: list[Screen], rects: list[Rect]) -> list[str]:
    if _using_lua_syntax():
        return _make_command_hyprland_lua(screens, rects)
    return _make_command_hyprland_old(screens, rects)


def make_command_legacy(screens: list[Screen], rects: list[Rect], wayland=False) -> list[str]:
    screens_rect = rects.copy()
    trim_rects_flip_y(screens_rect)
    command = ["wlr-randr" if wayland else "xrandr"]

    for screen, rect in zip(screens, screens_rect):
        if not screen.active:
            command.append(f"--output {screen.uid} --off")
            continue
        assert screen.mode
        sep = "," if wayland else "x"
        mode = f"{int(screen.mode.width)}x{int(screen.mode.height)}"
        command.append(f"--output {screen.uid} --on --pos {int(rect.x)}{sep}{int(rect.y)} --mode {mode}")

    cmd = " ".join(command)
    return [cmd]


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
    # Fallback: same resolution, closest frequency
    candidates = [m for m in modes if m.width == res[0] and m.height == res[1]]
    if candidates:
        return min(candidates, key=lambda m: abs(m.freq - freq))


def compute_bounding_box(rects):
    min_x = min(r.x for r in rects)
    min_y = min(r.y for r in rects)
    max_x = max(r.x + r.width for r in rects)
    max_y = max(r.y + r.height for r in rects)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def trim_rects_flip_y(rects):
    min_x = min([r.x for r in rects if r])
    max_y = max([r.y + r.height for r in rects if r])
    for rect in rects:
        if rect is None:
            continue
        rect.x = rect.x - min_x
        rect.y = max_y - (rect.y + rect.height)
