"""Filesystem locations.

Works both when running from source and from a frozen (PyInstaller) build.
Read-only resources live next to the code; saves and settings live in a
per-user folder so the game also works when installed in a protected place
(e.g. "Program Files" on Windows or /opt on Linux).
"""
import os
import sys
import tempfile
from pathlib import Path

USER_DIR_NAME = "VoidLoop"


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def package_dir():
    """Folder that contains the VoidLoop package resources (lang/, assets/)."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "VoidLoop"
    return Path(__file__).resolve().parent


def asset_path(*parts):
    return package_dir().joinpath("assets", *parts)


def lang_dir():
    return package_dir() / "lang"


def _pick_user_dir():
    override = os.environ.get("VOIDLOOP_HOME")
    if override:
        return Path(override)
    home = Path.home()
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        return Path(base) / USER_DIR_NAME if base else home / "AppData" / "Roaming" / USER_DIR_NAME
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / USER_DIR_NAME
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local" / "share") / "voidloop"


_user_dir = None


def user_data_dir():
    """Writable per-user folder for settings, saves, logs and caches."""
    global _user_dir
    if _user_dir is None:
        path = _pick_user_dir()
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_test"
            probe.write_text("ok")
            probe.unlink()
        except OSError:
            path = Path(tempfile.gettempdir()) / USER_DIR_NAME
            path.mkdir(parents=True, exist_ok=True)
        _user_dir = path
    return _user_dir


def cache_dir():
    path = user_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_save_path():
    """Where VoidLoop 3.x kept its save file (next to the game script)."""
    return Path(__file__).resolve().parent / "saves" / "savegame.json"


def reset_for_tests():
    """Forget the cached user folder (used by the test-suite)."""
    global _user_dir
    _user_dir = None
