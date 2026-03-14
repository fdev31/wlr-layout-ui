from pathlib import Path

import tomli
import tomli_w

cfg_file = Path("~/.config/wlrlui.toml").expanduser()


def load_profiles():
    try:
        with cfg_file.open("rb") as f:
            return tomli.load(f)
    except FileNotFoundError:
        return {}


def save_profile(name: str, profile_data):
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        profiles = {}

    profiles[name] = profile_data

    with cfg_file.open("wb") as f:
        tomli_w.dump(profiles, f)


def delete_profile(name: str):
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        return

    profiles.pop(name, None)

    with cfg_file.open("wb") as f:
        tomli_w.dump(profiles, f)
