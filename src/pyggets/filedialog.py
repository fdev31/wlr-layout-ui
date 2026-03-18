"""Native file dialog utilities using XDG Desktop Portal, zenity, or tkinter.

Provides three public functions for opening native file/directory dialogs:

- ``open_file()``  -- pick one or more files to open
- ``save_file()``  -- pick a location to save a file
- ``pick_directory()``  -- pick a directory

Backend priority: XDG Portal (via jeepney) > zenity/kdialog > tkinter.

All calls are **blocking** -- they return only after the user selects a
file or cancels the dialog.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from urllib.parse import unquote, urlparse

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

try:
    import random

    from jeepney import DBusAddress, MatchRule, message_bus, new_method_call
    from jeepney.io.blocking import open_dbus_connection

    _HAS_JEEPNEY = True
except ImportError:
    _HAS_JEEPNEY = False


# ---------------------------------------------------------------------------
# XDG Desktop Portal backend (jeepney)
# ---------------------------------------------------------------------------

_PORTAL_BUS = "org.freedesktop.portal.Desktop"
_PORTAL_PATH = "/org/freedesktop/portal/desktop"
_FC_IFACE = "org.freedesktop.portal.FileChooser"
_REQ_IFACE = "org.freedesktop.portal.Request"

_FC_ADDR = DBusAddress(_PORTAL_PATH, bus_name=_PORTAL_BUS, interface=_FC_IFACE) if _HAS_JEEPNEY else None


def _uri_to_path(uri: str) -> str:
    """Convert a file:// URI to a local filesystem path."""
    parsed = urlparse(uri)
    return unquote(parsed.path)


def _portal_request(method: str, title: str, options: dict, timeout: int = 120):
    """Call a FileChooser portal method and block until the user responds."""
    conn = open_dbus_connection(bus="SESSION")
    try:
        sender = conn.unique_name.lstrip(":").replace(".", "_")
        token = f"t{random.randint(0, 0xFFFFFF):x}"
        handle_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
        options["handle_token"] = ("s", token)

        # Subscribe to the Response signal before making the call
        match_rule = MatchRule(
            type="signal",
            interface=_REQ_IFACE,
            member="Response",
            path=handle_path,
        )
        conn.send_and_get_reply(message_bus.AddMatch(match_rule))

        msg = new_method_call(_FC_ADDR, method, "ssa{sv}", ("", title, options))
        conn.send_and_get_reply(msg)

        with conn.filter(match_rule) as queue:
            response = conn.recv_until_filtered(queue, timeout=timeout)

        return response.body[0], response.body[1]
    finally:
        conn.close()


def _portal_open_file(
    title: str,
    *,
    multiple: bool,
    directory: bool,
    filters: list | None,
    current_folder: str | None,
) -> list[str]:
    """Open file/directory via XDG Portal. Returns list of paths."""
    options: dict = {}
    if multiple:
        options["multiple"] = ("b", True)
    if directory:
        options["directory"] = ("b", True)
    if current_folder:
        options["current_folder"] = ("ay", list(current_folder.encode() + b"\x00"))
    if filters:
        options["filters"] = ("a(sa(us))", filters)

    code, results = _portal_request("OpenFile", title, options)
    if code != 0:
        return []
    uris = results.get("uris", (None, []))[1]
    return [_uri_to_path(u) for u in (uris or [])]


def _portal_save_file(
    title: str,
    current_name: str | None,
    current_folder: str | None,
    filters: list | None,
) -> str | None:
    """Save file via XDG Portal. Returns path or None."""
    options: dict = {}
    if current_name:
        options["current_name"] = ("s", current_name)
    if current_folder:
        options["current_folder"] = ("ay", list(current_folder.encode() + b"\x00"))
    if filters:
        options["filters"] = ("a(sa(us))", filters)

    code, results = _portal_request("SaveFile", title, options)
    if code != 0:
        return None
    uris = results.get("uris", (None, []))[1]
    return _uri_to_path(uris[0]) if uris else None


# ---------------------------------------------------------------------------
# Zenity / kdialog backend
# ---------------------------------------------------------------------------


def _find_cli_tool() -> str | None:
    """Return the name of an available CLI dialog tool, or None."""
    for tool in ("zenity", "kdialog"):
        if shutil.which(tool):
            return tool
    return None


def _zenity_open_file(
    title: str,
    *,
    multiple: bool,
    directory: bool,
    filters: list | None,
) -> list[str]:
    """Open file via zenity subprocess."""
    cmd = ["zenity", "--file-selection", f"--title={title}"]
    if multiple:
        cmd.append("--multiple")
        cmd.append("--separator=|")
    if directory:
        cmd.append("--directory")
    if filters:
        for name, patterns in filters:
            pattern_strs = [p[1] for p in patterns]
            cmd.append(f"--file-filter={name} | {' '.join(pattern_strs)}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    raw = result.stdout.strip()
    return raw.split("|") if multiple else [raw]


def _zenity_save_file(
    title: str,
    current_name: str | None,
    filters: list | None,
) -> str | None:
    """Save file via zenity subprocess."""
    cmd = ["zenity", "--file-selection", "--save", f"--title={title}"]
    if current_name:
        cmd.append(f"--filename={current_name}")
    if filters:
        for name, patterns in filters:
            pattern_strs = [p[1] for p in patterns]
            cmd.append(f"--file-filter={name} | {' '.join(pattern_strs)}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _kdialog_open_file(
    title: str,
    *,
    multiple: bool,
    directory: bool,
) -> list[str]:
    """Open file via kdialog subprocess."""
    if directory:
        cmd = ["kdialog", "--getexistingdirectory", ".", "--title", title]
    else:
        method = "--getopenfilename"
        cmd = ["kdialog", method, ".", "--title", title]
        if multiple:
            cmd.append("--multiple")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    raw = result.stdout.strip()
    return raw.split("\n") if multiple else [raw]


def _kdialog_save_file(title: str, current_name: str | None) -> str | None:
    """Save file via kdialog subprocess."""
    start = current_name or "."
    cmd = ["kdialog", "--getsavefilename", start, "--title", title]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# tkinter backend
# ---------------------------------------------------------------------------


def _tk_open_file(
    title: str,
    *,
    multiple: bool,
    directory: bool,
    filters: list | None,
) -> list[str]:
    """Open file via tkinter (last resort)."""
    import tkinter as tk  # noqa: PLC0415
    from tkinter import filedialog  # noqa: PLC0415

    root = tk.Tk()
    root.withdraw()
    try:
        if directory:
            path = filedialog.askdirectory(title=title)
            return [path] if path else []

        tk_filters = []
        if filters:
            for name, patterns in filters:
                exts = " ".join(p[1] for p in patterns)
                tk_filters.append((name, exts))

        if multiple:
            paths = filedialog.askopenfilenames(title=title, filetypes=tk_filters or [("All files", "*.*")])
            return list(paths)
        path = filedialog.askopenfilename(title=title, filetypes=tk_filters or [("All files", "*.*")])
        return [path] if path else []
    finally:
        root.destroy()


def _tk_save_file(
    title: str,
    current_name: str | None,
    filters: list | None,
) -> str | None:
    """Save file via tkinter (last resort)."""
    import tkinter as tk  # noqa: PLC0415
    from tkinter import filedialog  # noqa: PLC0415

    root = tk.Tk()
    root.withdraw()
    try:
        tk_filters = []
        if filters:
            for name, patterns in filters:
                exts = " ".join(p[1] for p in patterns)
                tk_filters.append((name, exts))

        path = filedialog.asksaveasfilename(
            title=title,
            initialfile=current_name or "",
            filetypes=tk_filters or [("All files", "*.*")],
        )
        return path or None
    finally:
        root.destroy()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def open_file(
    title: str = "Open File",
    *,
    multiple: bool = False,
    filters: list | None = None,
    current_folder: str | None = None,
) -> list[str]:
    """Open a native file picker dialog.

    Args:
        title: Dialog title.
        multiple: Allow selecting multiple files.
        filters: File filters as ``[("Name", [(type, pattern), ...]), ...]``
            where *type* is ``0`` for glob or ``1`` for MIME type.
            Example: ``[("Images", [(0, "*.png"), (0, "*.jpg")])]``
        current_folder: Starting directory.

    Returns:
        List of selected file paths, or ``[]`` if cancelled.
    """
    # Try XDG Portal
    if _HAS_JEEPNEY:
        try:
            return _portal_open_file(title, multiple=multiple, directory=False, filters=filters, current_folder=current_folder)
        except Exception:
            log.debug("XDG Portal file dialog failed, trying fallback", exc_info=True)

    # Try CLI tools
    cli = _find_cli_tool()
    if cli == "zenity":
        return _zenity_open_file(title, multiple=multiple, directory=False, filters=filters)
    if cli == "kdialog":
        return _kdialog_open_file(title, multiple=multiple, directory=False)

    # tkinter fallback
    return _tk_open_file(title, multiple=multiple, directory=False, filters=filters)


def save_file(
    title: str = "Save File",
    *,
    current_name: str | None = None,
    current_folder: str | None = None,
    filters: list | None = None,
) -> str | None:
    """Open a native save-file dialog.

    Args:
        title: Dialog title.
        current_name: Suggested filename.
        current_folder: Starting directory.
        filters: File filters (same format as ``open_file``).

    Returns:
        Selected file path, or ``None`` if cancelled.
    """
    if _HAS_JEEPNEY:
        try:
            return _portal_save_file(title, current_name, current_folder, filters)
        except Exception:
            log.debug("XDG Portal save dialog failed, trying fallback", exc_info=True)

    cli = _find_cli_tool()
    if cli == "zenity":
        return _zenity_save_file(title, current_name, filters)
    if cli == "kdialog":
        return _kdialog_save_file(title, current_name)

    return _tk_save_file(title, current_name, filters)


def pick_directory(
    title: str = "Select Folder",
    *,
    current_folder: str | None = None,
) -> str | None:
    """Open a native directory picker dialog.

    Args:
        title: Dialog title.
        current_folder: Starting directory.

    Returns:
        Selected directory path, or ``None`` if cancelled.
    """
    if _HAS_JEEPNEY:
        try:
            paths = _portal_open_file(title, multiple=False, directory=True, filters=None, current_folder=current_folder)
            return paths[0] if paths else None
        except Exception:
            log.debug("XDG Portal directory dialog failed, trying fallback", exc_info=True)

    cli = _find_cli_tool()
    if cli == "zenity":
        paths = _zenity_open_file(title, multiple=False, directory=True, filters=None)
        return paths[0] if paths else None
    if cli == "kdialog":
        paths = _kdialog_open_file(title, multiple=False, directory=True)
        return paths[0] if paths else None

    paths = _tk_open_file(title, multiple=False, directory=True, filters=None)
    return paths[0] if paths else None
