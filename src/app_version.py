"""Application version helpers."""

from __future__ import annotations

import os
import sys

DEFAULT_VERSION = "1.0.0"
VERSION_FILE = "version.txt"


def _base_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _read_bundled_version() -> str:
    version_path = os.path.join(_base_dir(), VERSION_FILE)
    try:
        with open(version_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def get_app_version() -> str:
    """Return app version from bundled data, env, or fallback."""
    bundled = _read_bundled_version()
    if bundled:
        return bundled

    raw = os.getenv("VNDB_GUI_VERSION", "").strip()
    if raw:
        return raw

    return DEFAULT_VERSION