from typing import Tuple

__all__ = ['Mode', 'Screen', 'load']

class Mode:
    def __init__(self, width, height, freq):
        self.width = width
        self.height = height
        self.freq = freq


class Screen:
    def __init__(
        self,
        uid: str,
        name: str,
        active: bool = False,
        position: Tuple[int, int] = (0, 0),
        mode: None | Mode = None,
    ):
        self.uid = uid
        self.name = name
        self.active = active
        self.position = position
        self.mode: Mode | None = mode
        self.available: list[Mode] = []


displayInfo: list[Screen] = []


def load():
    import subprocess

    out = subprocess.getoutput("wlr-randr")
    current_screen: None | Screen = None
    mode_mode = False
    for line in out.splitlines():
        if line[0] != " ":
            uid, name = line.split(None, 1)
            current_screen = Screen(uid=uid, name=name)
            displayInfo.append(current_screen)
            mode_mode = False
        else:
            if line[2] != " ":
                mode_mode = False
            assert current_screen
            sline = line.strip()
            if mode_mode:
                res, freq = sline.split(",", 1)
                res = res.split(None, 1)[0]
                res = tuple(int(x) for x in res.split("x"))
                freq, comment = freq.strip().split(None, 1)
                current_screen.available.append(Mode(res[0], res[1], float(freq)))
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



