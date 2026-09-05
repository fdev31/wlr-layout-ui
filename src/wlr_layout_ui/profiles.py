from pathlib import Path

import tomli
import tomli_w

from . import settings
from .widgets import get_default_theme

cfg_file = Path("~/.config/wlrlui.toml").expanduser()


def load_profiles():
    try:
        with cfg_file.open("rb") as f:
            data = tomli.load(f)
    except FileNotFoundError:
        return {}
    return {k: v for k, v in data.items() if k != "settings"}


def save_profile(name: str, profile_data):
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        profiles = {}

    profiles[name] = profile_data

    _write_all(profiles)


def delete_profile(name: str):
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        return

    profiles.pop(name, None)

    _write_all(profiles)


def _write_all(profiles: dict):
    data = dict(profiles)
    data["settings"] = {
        "ui_scale": get_default_theme().scale,
        "screen_scale": settings.SCREEN_SCALE,
    }
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    with cfg_file.open("wb") as f:
        tomli_w.dump(data, f)


def load_settings():
    """Load persisted settings and apply them to the settings module and theme."""
    try:
        with cfg_file.open("rb") as f:
            data = tomli.load(f)
    except FileNotFoundError:
        return
    s = data.get("settings", {})
    if "ui_scale" in s:
        get_default_theme().scale = float(s["ui_scale"])
    if "screen_scale" in s:
        settings.SCREEN_SCALE = int(s["screen_scale"])


def save_settings():
    """Persist current settings to the config file."""
    try:
        profiles = load_profiles()
    except FileNotFoundError:
        profiles = {}
    _write_all(profiles)
