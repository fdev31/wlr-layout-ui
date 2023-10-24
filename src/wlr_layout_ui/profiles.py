import os
import tomli
import tomli_w

cfg_file = os.path.expanduser("~/.config/wlrlui.toml")


def load_profiles():
    try:
        return tomli.load(open(cfg_file, "rb"))
    except FileNotFoundError:
        return {}


def save_profile(name: str, profile_data):
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        profiles = {}

    profiles[name] = profile_data

    with open(cfg_file, "wb") as f:
        tomli_w.dump(profiles, f)
