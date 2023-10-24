import os
import tomli
import tomli_w

cfg_file = os.path.expanduser("~/.config/wlrlui.toml")


def load_profiles():
    try:
        return tomli.load(open(cfg_file, "rb"))
    except FileNotFoundError:
        return {}


def save_profile(name: str, screens: list):
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        profiles = {}

    pscreens = []
    for screen in screens:
        obj = screen.screen.mode.__dict__.copy()
        obj["rect"] = screen.rect.asTuple()
        obj["uid"] = screen.screen.uid
        obj["active"] = screen.screen.active
        pscreens.append(obj)

    profiles[name] = pscreens
    with open(cfg_file, "wb") as f:
        tomli_w.dump(profiles, f)
