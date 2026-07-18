"""Tests for filename_generator.py — sanitize, generate, get_release_preview."""
from __future__ import annotations

import pytest
from core.filename_generator import (
    sanitize_filename,
    generate_filename,
    get_release_preview,
    ILLEGAL_CHAR_MAP,
)
from core.vndb_api import PLACEHOLDER, VNInfo, VNRelease


class TestSanitizeFilename:
    def test_disabled_returns_unchanged(self) -> None:
        assert sanitize_filename("abc:def*test", enabled=False) == "abc:def*test"

    def test_no_illegal_chars_returns_unchanged(self) -> None:
        assert sanitize_filename("hello world 123", enabled=True) == "hello world 123"

    def test_replaces_colon(self) -> None:
        assert sanitize_filename("a:b", enabled=True) == "a：b"

    def test_replaces_all_illegal_chars(self) -> None:
        result = sanitize_filename(':/\\?*"<>|', enabled=True)
        expected = "：／＼？＊”《》｜"
        assert result == expected

    def test_empty_string(self) -> None:
        assert sanitize_filename("", enabled=True) == ""

    def test_mixed_content(self) -> None:
        result = sanitize_filename('Title "Subtitle" <with> tags?', enabled=True)
        assert result == 'Title ”Subtitle” 《with》 tags？'

    def test_none_input(self) -> None:
        assert sanitize_filename(None, enabled=True) is None  # type: ignore[arg-type]


class TestGenerateFilename:
    def test_basic_filename(self, sample_vn: VNInfo, sample_release: VNRelease) -> None:
        result = generate_filename(
            sample_vn, sample_release,
            group_name="Makura Castle", patch_date="20130314", language="CHS",
        )
        expected = (
            "[ALcot][20090918]"
            "幼なじみは大統領"
            "[v2622][Windows][Makura Castle][20130314][CHS]"
        )
        assert result == expected

    def test_missing_developer(self, sample_vn: VNInfo, sample_release_tba: VNRelease) -> None:
        result = generate_filename(
            sample_vn, sample_release_tba,
            group_name="", patch_date="", language="EN",
        )
        assert result.startswith(f"[{PLACEHOLDER}]")

    def test_use_release_title(self, sample_vn: VNInfo, sample_release: VNRelease) -> None:
        result = generate_filename(
            sample_vn, sample_release,
            use_release_title=True,
        )
        assert "幼なじみは大統領" in result

    def test_no_group_no_patch_date(self, sample_vn: VNInfo, sample_release: VNRelease) -> None:
        result = generate_filename(sample_vn, sample_release)
        assert f"[{PLACEHOLDER}]" in result
        assert "[CHS]" in result

    def test_sanitize_disabled(self, sample_vn: VNInfo) -> None:
        release_with_colon = VNRelease(
            id="r1", title="Test: Subtitle", alttitle=None,
            released="2023-01-01", platforms=["win"], languages=["ja"],
        )
        result = generate_filename(
            sample_vn, release_with_colon,
            use_release_title=True, sanitize=False,
        )
        assert "Test: Subtitle" in result

    def test_sanitize_enabled(self, sample_vn: VNInfo) -> None:
        release_with_colon = VNRelease(
            id="r1", title="Test: Subtitle", alttitle=None,
            released="2023-01-01", platforms=["win"], languages=["ja"],
        )
        result = generate_filename(
            sample_vn, release_with_colon,
            use_release_title=True, sanitize=True,
        )
        assert "Test： Subtitle" in result
        assert "Test: Subtitle" not in result

    def test_tba_date_shows_no_data(self, sample_vn: VNInfo, sample_release_tba: VNRelease) -> None:
        result = generate_filename(sample_vn, sample_release_tba)
        assert f"[{PLACEHOLDER}]" in result

    def test_custom_language(self, sample_vn: VNInfo, sample_release: VNRelease) -> None:
        result = generate_filename(sample_vn, sample_release, language="JPN")
        assert "[JPN]" in result

    def test_empty_language_defaults_to_chs(self, sample_vn: VNInfo, sample_release: VNRelease) -> None:
        result = generate_filename(sample_vn, sample_release, language="")
        assert "[CHS]" in result

    def test_platform_underscore_replacement(self, sample_vn: VNInfo) -> None:
        release = VNRelease(
            id="r1", title="Test", alttitle=None, released="2023-01-01",
            platforms=["win", "lin", "mac"], languages=["ja"],
        )
        result = generate_filename(sample_vn, release, group_name="", patch_date="")
        assert "[Windows_Linux_MacOS]" in result

    def test_strips_v_prefix_from_id(self, sample_vn: VNInfo, sample_release: VNRelease) -> None:
        result = generate_filename(sample_vn, sample_release)
        assert "[v2622]" in result

    def test_id_without_v_prefix(self) -> None:
        vn = VNInfo(id="123", title="Test", alttitle=None)
        release = VNRelease(id="r1", title="Test", released="2023-01-01",
                            platforms=["win"], languages=["ja"])
        result = generate_filename(vn, release, group_name="", patch_date="")
        assert "[v123]" in result


class TestGetReleasePreview:
    def test_normal_release(self, sample_release: VNRelease) -> None:
        preview = get_release_preview(sample_release)
        assert "幼なじみは大統領" in preview
        assert "2009-09-18" in preview
        assert "win" in preview
        assert "ja" in preview

    def test_missing_data(self, sample_release_tba: VNRelease) -> None:
        preview = get_release_preview(sample_release_tba)
        assert PLACEHOLDER in preview

    def test_no_alttitle_falls_back_to_title(self) -> None:
        release = VNRelease(
            id="r1", title="Fallback Title", alttitle=None,
            released="2023-01-01", platforms=["win"], languages=["en"],
        )
        preview = get_release_preview(release)
        assert "Fallback Title" in preview
