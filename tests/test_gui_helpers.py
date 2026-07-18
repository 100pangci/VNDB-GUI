"""Tests for gui.py standalone helper functions."""
from __future__ import annotations

import pytest
from core.vndb_api import VNRelease

from gui import _parse_date_to_int, _nonzh_sort_key, _zh_sort_key


class TestParseDateToInt:
    def test_full_date(self) -> None:
        assert _parse_date_to_int("2009-09-18") == 20090918

    def test_year_month_only(self) -> None:
        assert _parse_date_to_int("2025-09") == 20250999

    def test_year_only(self) -> None:
        assert _parse_date_to_int("2026") == 20269999

    def test_tba(self) -> None:
        assert _parse_date_to_int("TBA") == 0

    def test_none(self) -> None:
        assert _parse_date_to_int(None) == 0

    def test_empty_string(self) -> None:
        assert _parse_date_to_int("") == 0

    def test_invalid_format(self) -> None:
        assert _parse_date_to_int("not-a-date") == 0

    def test_partial_pads_with_99(self) -> None:
        val = _parse_date_to_int("2025")
        assert val == 20259999

    def test_date_with_whitespace(self) -> None:
        assert _parse_date_to_int("  2023-06-15  ") == 20230615


class TestNonzhSortKey:
    def _make(self, langs: list[str], released: str) -> VNRelease:
        return VNRelease(
            id="r", title="", alttitle=None, released=released,
            platforms=[], languages=langs,
        )

    def test_ja_first(self) -> None:
        ja = self._make(["ja"], "2023-01-01")
        en = self._make(["en"], "2023-01-01")
        assert _nonzh_sort_key(ja) < _nonzh_sort_key(en)

    def test_en_before_other(self) -> None:
        en = self._make(["en"], "2023-01-01")
        fr = self._make(["fr"], "2023-01-01")
        assert _nonzh_sort_key(en) < _nonzh_sort_key(fr)

    def test_earlier_date_first(self) -> None:
        early = self._make(["ja"], "2020-01-01")
        late = self._make(["ja"], "2023-01-01")
        assert _nonzh_sort_key(early) < _nonzh_sort_key(late)

    def test_tba_last(self) -> None:
        normal = self._make(["ja"], "2023-01-01")
        tba = self._make(["ja"], "TBA")
        assert _nonzh_sort_key(normal) < _nonzh_sort_key(tba)


class TestZhSortKey:
    def _make(self, released: str) -> VNRelease:
        return VNRelease(
            id="r", title="", alttitle=None, released=released,
            platforms=[], languages=["zh-Hans"],
        )

    def test_newest_first(self) -> None:
        newer = self._make("2025-01-01")
        older = self._make("2020-01-01")
        assert _zh_sort_key(newer) < _zh_sort_key(older)

    def test_tba_last(self) -> None:
        normal = self._make("2023-01-01")
        tba = self._make("")
        assert _zh_sort_key(normal) < _zh_sort_key(tba)
