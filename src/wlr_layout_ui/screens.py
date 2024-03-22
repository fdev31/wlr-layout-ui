import os
import re
import json
from typing import Tuple
import subprocess
import difflib

from dataclasses import dataclass, field

__all__ = ["Mode", "Screen", "load", "LEGACY"]

LEGACY = not os.environ.get("WAYLAND_DISPLAY", False)
MODE_RE = re.compile(r"^(?P<width>\d+)x(?P<height>\d+)(?P<x>[+-]\d+)(?P<y>[+-]\d+)$")


@dataclass
class Mode:
    width: int
    height: int
    freq: float

    def __repr__(self):
        return "%dx%d@%.2fHz" % (self.width, self.height, self.freq)


@dataclass
class Screen:
    uid: str
    name: str
    active: bool = False
    position: Tuple[int, int] = (0, 0)
    mode: None | Mode = None
    scale: float = 1
    available: list[Mode] = field(default_factory=list)

    def __repr__(self):
        return "<Screen%s %s [%s]>" % ("*" if self.active else "", self.name, self.mode)


displayInfo: list[Screen] = []


def _parseMode(txt):
    res, freq = txt.split("@")
    x, y = res.split("x")
    return (int(x), int(y), float(freq[:-2]))


def load_from_hyprctl():
    monitors = json.loads(subprocess.getoutput("hyprctl -j monitors all"))
    for monitor in monitors:
        modes = [Mode(*_parseMode(m)) for m in monitor["availableModes"]]
        cur_mode = "%dx%d@%.2fHz" % (
            monitor["width"],
            monitor["height"],
            monitor["refreshRate"],
        )
        modes_str = [repr(m) for m in modes]
        try:
            idx = modes_str.index(cur_mode)
        except IndexError:
            idx = modes_str.index(difflib.get_close_matches(cur_mode, modes_str)[0])
        current_screen = Screen(
            uid=monitor["name"],
            name=monitor["description"],
            active=monitor["activeWorkspace"]["id"] >= 0,
            scale=monitor["scale"],
            position=(monitor["x"], monitor["y"]),
            available=modes,
            mode=modes[idx],
        )
        displayInfo.append(current_screen)


def load():

    if displayInfo:
        displayInfo.clear()

    try:
        v = json.loads(subprocess.getoutput("hyprctl -j version"))["tag"]
        good_v = (37, 38, 39)
        new_hyprland = any(v.startswith("v0.%d" % x) for x in good_v) or (
            not v.startswith("v0.2") and not v.startswith("v0.1")
        )
    except (KeyError, json.JSONDecodeError):
        new_hyprland = False

    if new_hyprland:
        load_from_hyprctl()
        return

    out = subprocess.getoutput("xrandr" if LEGACY else "wlr-randr")
    current_screen: None | Screen = None
    mode_mode = False
    for line in out.splitlines():
        if LEGACY and ("disconnected" in line or line.startswith("Screen")):
            continue
        if line[0] != " ":
            uid, name = line.split(None, 1)
            current_screen = Screen(uid=uid, name=name.strip('"'))
            try:
                chim = name.split("(", 1)[0].strip().rsplit(None, 1)[1]
            except IndexError:
                current_screen.active = False
            else:
                mode_re = MODE_RE.match(chim)
                if mode_re:
                    current_screen.position = (
                        int(mode_re.group("x")),
                        int(mode_re.group("y")),
                    )

            displayInfo.append(current_screen)
            mode_mode = False
        else:
            if line[2] != " ":
                mode_mode = False
            assert current_screen
            sline = line.strip()
            if LEGACY:
                res, freq = sline.split(None, 1)
                if not res.endswith("i"):
                    res = tuple(int(x) for x in res.split("x"))
                    current = "*" in freq
                    freq = freq.split(None, 1)[0].rstrip("*+")
                    current_screen.available.append(Mode(res[0], res[1], float(freq)))
                    if current:
                        current_screen.mode = current_screen.available[-1]
            else:
                if mode_mode:
                    try:
                        res, freq = sline.split(",", 1)
                    except ValueError:
                        print("Unable to parse: %s" % sline)
                    else:
                        res = res.split(None, 1)[0]
                        res = tuple(int(x) for x in res.split("x"))
                        freq, comment = freq.strip().split(None, 1)
                        current_screen.available.append(
                            Mode(res[0], res[1], float(freq))
                        )
                        if "current" in comment:
                            current_screen.mode = current_screen.available[-1]

                elif sline.startswith("Modes:"):
                    mode_mode = True
                elif sline.startswith("Enabled"):
                    current_screen.active = "yes" in sline
                elif sline.startswith("Position"):
                    current_screen.position = tuple(
                        int(x) for x in sline.split(":")[1].strip().split(",")
                    )
    try:
        monitors = json.loads(subprocess.getoutput("hyprctl -j monitors all"))
    except json.decoder.JSONDecodeError:
        pass
    else:
        monitors = {o["name"]: o for o in monitors}
        for info in displayInfo:
            info.active = monitors[info.uid]["activeWorkspace"]["id"] >= 0
            info.scale = monitors[info.uid]["scale"]
