"""Filename generation logic for VNDB releases."""

from __future__ import annotations

import re
from .vndb_api import VNInfo, VNRelease, PLACEHOLDER

# Mapping of Windows-illegal filename characters to fullwidth replacements
ILLEGAL_CHAR_MAP = {
    ":": "：",
    "?": "？",
    "/": "／",
    "\\": "＼",
    "*": "＊",
    '"': "”",
    "<": "《",
    ">": "》",
    "|": "｜",
}

_ILLEGAL_PATTERN = re.compile("[" + re.escape("".join(ILLEGAL_CHAR_MAP.keys())) + "]")


def sanitize_filename(text: str) -> str:
    """Replace Windows-illegal filename characters with safe fullwidth equivalents."""
    if not text:
        return text
    return _ILLEGAL_PATTERN.sub(lambda m: ILLEGAL_CHAR_MAP[m.group(0)], text)


def generate_filename(
    vn_info: VNInfo,
    release: VNRelease,
    group_name: str = "",
    patch_date: str = "",
    language: str = "CHS",
) -> str:
    """
    Generate a formatted filename for a VN release.

    Format:
    [developer][release_date]original_title[v+VNDB_ID][platform][group][patch_date][language]

    Example:
    [ALcot][20090918]幼なじみは大統領 My girlfriend is the PRESIDENT.[v2622][Windows][Makura Castle][20130314][CHS]
    """
    # --- Developer ---
    developer = release.get_developer_name()
    if not developer or developer == PLACEHOLDER:
        developer = vn_info.title  # fallback

    # --- Release date (YYYYMMDD) ---
    date_str = release.format_released()

    # --- Original title ---
    original_title = vn_info.get_original_title()

    # --- Platform (use full names from display) ---
    plat_display = release.get_platforms_display()
    if plat_display and plat_display != PLACEHOLDER:
        platform_str = plat_display.replace(", ", "_")
    else:
        platform_str = PLACEHOLDER

    # --- Group name ---
    group_name_clean = group_name.strip() if group_name else ""

    # --- Patch date ---
    patch_date_clean = patch_date.strip() if patch_date else ""

    # --- Language ---
    language_clean = language.strip().upper() if language else "CHS"

    # Build parts
    parts: list[str] = []

    # [Developer]
    parts.append(f"[{sanitize_filename(developer)}]")

    # [Date]
    parts.append(f"[{sanitize_filename(date_str)}]")

    # Original title
    parts.append(sanitize_filename(original_title))

    # [v+VNDB_ID] — strip any existing "v" prefix from VNInfo.id
    vid = vn_info.id
    if vid.startswith("v"):
        vid = vid[1:]
    parts.append(f"[v{vid}]")

    # [Platform]
    parts.append(f"[{sanitize_filename(platform_str)}]")

    # [Group name]
    if group_name_clean:
        parts.append(f"[{sanitize_filename(group_name_clean)}]")
    else:
        parts.append(f"[{PLACEHOLDER}]")

    # [Patch date] (optional)
    if patch_date_clean:
        parts.append(f"[{sanitize_filename(patch_date_clean)}]")

    # [Language]
    parts.append(f"[{sanitize_filename(language_clean)}]")

    return "".join(parts)


def get_release_preview(release: VNRelease) -> str:
    """Generate a human-readable preview string for a release (native title)."""
    platforms = ", ".join(release.platforms) if release.platforms else PLACEHOLDER
    languages = ", ".join(release.languages) if release.languages else PLACEHOLDER
    display_title = release.get_display_title()
    return f"{display_title} | {release.released or PLACEHOLDER} | {platforms} | {languages}"
