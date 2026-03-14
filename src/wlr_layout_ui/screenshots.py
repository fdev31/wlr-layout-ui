"""Per-monitor screenshot capture for display previews.

Provides a single public function :func:`capture_screenshots` that tries
two backends in order:

1. **grim** -- fast, per-output capture on wlroots compositors.
2. **XDG Desktop Portal** -- compositor-agnostic full-desktop capture,
   cropped per monitor using pyglet.

If both fail (tools missing, permission denied, etc.) the function
returns an empty dict and the caller falls back to solid-colour
backgrounds.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

if TYPE_CHECKING:
    from .types import Screen

log = logging.getLogger(__name__)

_SCREENSHOT_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "wlr-layout-ui"


def _cleanup():
    """Remove temporary screenshot files on exit."""
    if _SCREENSHOT_DIR.is_dir():
        shutil.rmtree(_SCREENSHOT_DIR, ignore_errors=True)


atexit.register(_cleanup)


def _screenshot_path(uid: str) -> str:
    """Return the temp file path for a monitor screenshot."""
    # Sanitise uid for use as a filename (replace slashes etc.)
    safe = uid.replace("/", "_").replace(" ", "_")
    return str(_SCREENSHOT_DIR / f"screenshot_{safe}.png")


def _ensure_dir() -> bool:
    """Create the screenshot temp directory.  Returns True on success."""
    try:
        _SCREENSHOT_DIR.mkdir(exist_ok=True, parents=True)
        return True
    except OSError:
        log.warning("Cannot create screenshot directory %s", _SCREENSHOT_DIR, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Backend 1: grim
# ---------------------------------------------------------------------------


def _capture_grim(screens: list[Screen]) -> dict[str, str]:
    """Capture per-output screenshots with grim."""
    grim = shutil.which("grim")
    if not grim:
        log.debug("grim not found, skipping grim backend")
        return {}

    results: dict[str, str] = {}
    for screen in screens:
        if not screen.active:
            continue
        path = _screenshot_path(screen.uid)
        try:
            subprocess.run(
                [grim, "-o", screen.uid, path],
                capture_output=True,
                timeout=10,
                check=True,
            )
            if Path(path).is_file():
                results[screen.uid] = path
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("grim failed for %s: %s", screen.uid, exc)
    return results


# ---------------------------------------------------------------------------
# Backend 2: XDG Desktop Portal
# ---------------------------------------------------------------------------


def _uri_to_path(uri: str) -> str:
    """Convert a file:// URI to a local filesystem path."""
    parsed = urlparse(uri)
    return unquote(parsed.path)


def _capture_portal_full() -> str | None:
    """Take a full-desktop screenshot via XDG Desktop Portal.

    Returns the local file path of the screenshot, or None on failure.
    """
    try:
        import random  # noqa: PLC0415

        from jeepney import DBusAddress, MatchRule, message_bus, new_method_call  # noqa: PLC0415
        from jeepney.io.blocking import open_dbus_connection  # noqa: PLC0415
    except ImportError:
        log.debug("jeepney not available, portal screenshot unavailable")
        return None

    portal_bus = "org.freedesktop.portal.Desktop"
    portal_path = "/org/freedesktop/portal/desktop"
    sc_iface = "org.freedesktop.portal.Screenshot"
    req_iface = "org.freedesktop.portal.Request"

    addr = DBusAddress(portal_path, bus_name=portal_bus, interface=sc_iface)

    try:
        conn = open_dbus_connection(bus="SESSION")
    except Exception:
        log.debug("Cannot open D-Bus session connection", exc_info=True)
        return None

    try:
        sender = conn.unique_name.lstrip(":").replace(".", "_")
        token = f"t{random.randint(0, 0xFFFFFF):x}"
        handle_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

        options = {
            "handle_token": ("s", token),
            "modal": ("b", False),
            "interactive": ("b", False),
        }

        match_rule = MatchRule(
            type="signal",
            interface=req_iface,
            member="Response",
            path=handle_path,
        )
        conn.send_and_get_reply(message_bus.AddMatch(match_rule))

        msg = new_method_call(addr, "Screenshot", "sa{sv}", ("", options))
        conn.send_and_get_reply(msg)

        with conn.filter(match_rule) as queue:
            response = conn.recv_until_filtered(queue, timeout=15)

        code = response.body[0]
        results = response.body[1]
        if code != 0:
            log.debug("Portal screenshot denied (code=%d)", code)
            return None

        uri = results.get("uri", (None, ""))[1]
        if not uri:
            log.debug("Portal screenshot returned no URI")
            return None

        return _uri_to_path(uri)
    except Exception:
        log.debug("Portal screenshot failed", exc_info=True)
        return None
    finally:
        conn.close()


def _crop_portal_screenshot(full_path: str, screens: list[Screen]) -> dict[str, str]:
    """Crop the full-desktop screenshot into per-monitor images using pyglet.

    The portal screenshot uses Y-down coordinates (standard screen coords).
    pyglet's get_region uses Y-up (origin at bottom-left), so we convert.
    """
    try:
        import pyglet  # noqa: PLC0415

        full_img = pyglet.image.load(full_path)
    except Exception:
        log.debug("Cannot load portal screenshot %s", full_path, exc_info=True)
        return {}

    img_h = full_img.height
    results: dict[str, str] = {}

    for screen in screens:
        if not screen.active or screen.mode is None:
            continue

        sx, sy = screen.position  # Y-down screen coordinates
        sw, sh = screen.mode.width, screen.mode.height

        # Convert Y-down (portal/screen coords) to Y-up (pyglet image coords)
        pyglet_y = img_h - sy - sh

        # Clamp to image bounds
        if sx < 0 or pyglet_y < 0 or sx + sw > full_img.width or pyglet_y + sh > img_h:
            log.debug(
                "Monitor %s region (%d,%d %dx%d) out of image bounds (%dx%d), skipping",
                screen.uid,
                sx,
                pyglet_y,
                sw,
                sh,
                full_img.width,
                img_h,
            )
            continue

        try:
            region = full_img.get_region(sx, pyglet_y, sw, sh)
            path = _screenshot_path(screen.uid)
            region.save(path)
            if Path(path).is_file():
                results[screen.uid] = path
        except Exception:
            log.debug("Failed to crop/save region for %s", screen.uid, exc_info=True)

    return results


def _capture_portal(screens: list[Screen]) -> dict[str, str]:
    """Capture per-monitor screenshots via XDG Desktop Portal."""
    full_path = _capture_portal_full()
    if not full_path:
        return {}
    try:
        return _crop_portal_screenshot(full_path, screens)
    finally:
        # Remove the full desktop screenshot, we only need the per-monitor crops
        with contextlib.suppress(OSError):
            Path(full_path).unlink()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def capture_screenshots(screens: list[Screen]) -> dict[str, str]:
    """Capture a screenshot for each active monitor.

    Tries grim first (per-output), then falls back to XDG Desktop Portal
    (full desktop + crop).  If both fail, returns an empty dict.

    Args:
        screens: List of Screen objects with uid, position, mode, active.

    Returns:
        Dict mapping screen uid to the local path of its screenshot PNG.
        Missing entries mean capture failed for that monitor.
    """
    if not _ensure_dir():
        return {}

    active_screens = [s for s in screens if s.active]
    if not active_screens:
        return {}

    # Try grim first
    results = _capture_grim(active_screens)
    if results or shutil.which("grim"):
        # grim is available; don't fall back to portal (avoids permission prompts)
        return results

    # No grim installed -- try portal as the sole backend
    return _capture_portal(active_screens)
