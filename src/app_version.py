"""Application version helpers."""

from __future__ import annotations

import os
import sys

DEFAULT_VERSION = "dev"
VERSION_FILE = "version.txt"


def _base_dir() -> str:
    """返回应用基础路径（PyInstaller 打包后返回 _MEIPASS，否则为脚本所在目录）。"""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _read_bundled_version() -> str:
    """从 version.txt 文件中读取版本号。"""
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