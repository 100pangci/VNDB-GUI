"""VNDB GUI 核心模块 — API 通信、文件名生成与配色方案。"""

from .vndb_api import VNDBAPIClient, VNDBError, VNDBNotFoundError, VNDBMultipleResultsError, VNCandidate, VNInfo, VNRelease, PLACEHOLDER
from .filename_generator import generate_filename, sanitize_filename, get_release_preview
from . import colors_common
from . import colors_dark
from . import colors_light

__all__ = [
    "VNDBAPIClient", "VNDBError", "VNDBNotFoundError", "VNDBMultipleResultsError",
    "VNCandidate", "VNInfo", "VNRelease", "PLACEHOLDER",
    "generate_filename", "sanitize_filename", "get_release_preview",
    "colors_common", "colors_dark", "colors_light",
]