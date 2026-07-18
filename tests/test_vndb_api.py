"""Tests for vndb_api.py — data models and API client (mocked HTTP)."""
from __future__ import annotations

import json

import pytest
import responses

from core.vndb_api import (
    API_BASE,
    VNDBAPIClient,
    VNDBError,
    VNDBNotFoundError,
    VNDBMultipleResultsError,
    VNCandidate,
    VNInfo,
    VNRelease,
    Producer,
    PLACEHOLDER,
)


# ── Producer ───────────────────────────────────────────────────────────

class TestProducer:
    def test_from_dict_complete(self) -> None:
        d = {"id": "p1", "name": "ALcot", "original": "ALcot",
             "developer": True, "publisher": False}
        p = Producer.from_dict(d)
        assert p.id == "p1"
        assert p.name == "ALcot"
        assert p.original == "ALcot"
        assert p.developer is True
        assert p.publisher is False

    def test_from_dict_minimal(self) -> None:
        d: dict = {}
        p = Producer.from_dict(d)
        assert p.id == ""
        assert p.name == PLACEHOLDER
        assert p.original == ""
        assert p.developer is False
        assert p.publisher is False

    def test_get_display_name_prefers_original(self) -> None:
        p = Producer(id="p1", name="AliceSoft", original="アリスソフト")
        assert p.get_display_name() == "アリスソフト"

    def test_get_display_name_falls_back_to_name(self) -> None:
        p = Producer(id="p1", name="AliceSoft", original="")
        assert p.get_display_name() == "AliceSoft"


# ── VNCandidate ────────────────────────────────────────────────────────

class TestVNCandidate:
    def test_from_dict(self) -> None:
        d = {"id": "v2622", "title": "My Girlfriend is the President.",
             "alttitle": "幼なじみは大統領",
             "titles": [{"lang": "ja", "title": "幼なじみは大統領"}]}
        c = VNCandidate.from_dict(d)
        assert c.id == "v2622"
        assert c.title == "My Girlfriend is the President."
        assert c.alttitle == "幼なじみは大統領"
        assert len(c.titles) == 1

    def test_from_dict_empty(self) -> None:
        d: dict = {}
        c = VNCandidate.from_dict(d)
        assert c.id == ""
        assert c.title == ""
        assert c.alttitle is None
        assert c.titles == []

    def test_get_display_title_japanese(self) -> None:
        c = VNCandidate(id="v1", title="English", alttitle="Alt",
                        titles=[{"lang": "ja", "title": "日本語"}])
        assert c.get_display_title() == "日本語"

    def test_get_display_title_fallback_alttitle(self) -> None:
        c = VNCandidate(id="v1", title="English", alttitle="Alt",
                        titles=[{"lang": "en", "title": "English"}])
        assert c.get_display_title() == "Alt"

    def test_get_display_title_fallback_title(self) -> None:
        c = VNCandidate(id="v1", title="English", alttitle=None)
        assert c.get_display_title() == "English"


# ── VNRelease ──────────────────────────────────────────────────────────

class TestVNRelease:
    def test_from_dict_complete(self) -> None:
        d = {
            "id": "r1",
            "title": "English Title",
            "alttitle": "日本語タイトル",
            "released": "2023-01-15",
            "platforms": ["win", "lin"],
            "languages": [{"lang": "ja"}, {"lang": "en"}],
            "producers": [{"id": "p1", "name": "ALcot", "original": "ALcot",
                           "developer": True, "publisher": True}],
            "media": [],
        }
        r = VNRelease.from_dict(d)
        assert r.id == "r1"
        assert r.title == "English Title"
        assert r.alttitle == "日本語タイトル"
        assert r.released == "2023-01-15"
        assert r.platforms == ["win", "lin"]
        assert r.languages == ["ja", "en"]
        assert len(r.producers) == 1
        assert r.producers[0].developer is True

    def test_from_dict_empty(self) -> None:
        d: dict = {}
        r = VNRelease.from_dict(d)
        assert r.id == ""
        assert r.title == ""
        assert r.alttitle is None
        assert r.released == ""
        assert r.platforms == []
        assert r.languages == []
        assert r.producers == []

    def test_format_released_full(self) -> None:
        r = VNRelease.from_dict({"released": "2023-01-15"})
        assert r.format_released() == "20230115"

    def test_format_released_year_only(self) -> None:
        r = VNRelease.from_dict({"released": "2023"})
        assert r.format_released() == "20230000"

    def test_format_released_empty(self) -> None:
        r = VNRelease.from_dict({"released": ""})
        assert r.format_released() == PLACEHOLDER

    def test_format_released_tba(self) -> None:
        r = VNRelease.from_dict({"released": "TBA"})
        assert r.format_released() == "TBA0000"

    def test_get_display_title_prefers_alttitle(self) -> None:
        r = VNRelease.from_dict(
            {"title": "English", "alttitle": "日本語"})
        assert r.get_display_title() == "日本語"

    def test_get_display_title_falls_back(self) -> None:
        r = VNRelease.from_dict({"title": "English"})
        assert r.get_display_title() == "English"

    def test_get_platforms_display_known(self) -> None:
        r = VNRelease.from_dict({"platforms": ["win", "swi", "ps4"]})
        assert r.get_platforms_display() == "Windows, Switch, PlayStation 4"

    def test_get_platforms_display_unknown(self) -> None:
        r = VNRelease.from_dict({"platforms": ["foo"]})
        assert r.get_platforms_display() == "foo"

    def test_get_platforms_display_empty(self) -> None:
        r = VNRelease.from_dict({})
        assert r.get_platforms_display() == PLACEHOLDER

    def test_get_developer_name_finds_developer(self, sample_release: VNRelease) -> None:
        assert sample_release.get_developer_name() == "ALcot"

    def test_get_developer_name_no_developer(self, sample_release_tba: VNRelease) -> None:
        assert sample_release_tba.get_developer_name() == PLACEHOLDER

    def test_get_non_developer_group(self, sample_release_zh: VNRelease) -> None:
        assert "枕城" in sample_release_zh.get_non_developer_group_name()

    def test_get_languages_display_sorts_ja_first(self) -> None:
        r = VNRelease.from_dict({
            "languages": [{"lang": "en"}, {"lang": "ja"}, {"lang": "zh-Hans"}],
        })
        assert r.get_languages_display().startswith("ja")

    def test_is_chinese_release_true(self) -> None:
        r = VNRelease.from_dict({"languages": [{"lang": "zh-Hans"}]})
        assert r.is_chinese_release() is True

    def test_is_chinese_release_zh_hant(self) -> None:
        r = VNRelease.from_dict({"languages": [{"lang": "zh-Hant"}]})
        assert r.is_chinese_release() is True

    def test_is_chinese_release_false(self) -> None:
        r = VNRelease.from_dict({"languages": [{"lang": "ja"}]})
        assert r.is_chinese_release() is False

    def test_is_chinese_release_empty(self) -> None:
        r = VNRelease.from_dict({})
        assert r.is_chinese_release() is False


# ── VNInfo ─────────────────────────────────────────────────────────────

class TestVNInfo:
    def test_from_dict(self) -> None:
        d = {
            "id": "v2622",
            "title": "English",
            "alttitle": "日本語",
            "titles": [{"lang": "ja", "title": "日本語"}],
            "image": None,
            "releases": [
                {"id": "r1", "title": "R1", "released": "2023-01-01",
                 "platforms": ["win"], "languages": [{"lang": "ja"}]},
            ],
        }
        vn = VNInfo.from_dict(d)
        assert vn.id == "v2622"
        assert vn.title == "English"
        assert len(vn.releases) == 1
        assert vn.releases[0].id == "r1"

    def test_get_original_title_japanese(self) -> None:
        vn = VNInfo.from_dict({
            "id": "v1", "title": "English", "alttitle": "Alt",
            "titles": [
                {"lang": "ja", "title": "日本語"},
                {"lang": "en", "title": "English"},
            ],
        })
        assert vn.get_original_title() == "日本語"

    def test_get_original_title_fallback_alttitle(self) -> None:
        vn = VNInfo.from_dict({
            "id": "v1", "title": "English", "alttitle": "Alt",
            "titles": [{"lang": "en", "title": "English"}],
        })
        assert vn.get_original_title() == "Alt"

    def test_get_original_title_fallback_title(self) -> None:
        vn = VNInfo.from_dict({
            "id": "v1", "title": "English", "alttitle": None, "titles": [],
        })
        assert vn.get_original_title() == "English"


# ── Exceptions ─────────────────────────────────────────────────────────

class TestExceptions:
    def test_vndb_not_found_is_vndb_error(self) -> None:
        e = VNDBNotFoundError("test")
        assert isinstance(e, VNDBError)

    def test_multiple_results_carries_candidates(self) -> None:
        candidates = [VNCandidate(id="v1", title="One")]
        e = VNDBMultipleResultsError("multiple", candidates)
        assert len(e.candidates) == 1
        assert e.candidates[0].id == "v1"


# ── API Client (mocked) ────────────────────────────────────────────────

class TestVNDBAPIClient:
    @pytest.fixture
    def client(self) -> VNDBAPIClient:
        return VNDBAPIClient(timeout=5)

    # ── _post ────────────────────────────────────────────────────────

    @responses.activate
    def test_post_http_404(self, client: VNDBAPIClient) -> None:
        responses.add(responses.POST, f"{API_BASE}/vn", status=404)
        with pytest.raises(VNDBNotFoundError):
            client._post("vn", {})

    @responses.activate
    def test_post_http_429(self, client: VNDBAPIClient) -> None:
        responses.add(responses.POST, f"{API_BASE}/vn", status=429)
        with pytest.raises(VNDBError, match="请求过于频繁"):
            client._post("vn", {})

    @responses.activate
    def test_post_http_500(self, client: VNDBAPIClient) -> None:
        responses.add(responses.POST, f"{API_BASE}/vn", status=500,
                      body="Internal Error")
        with pytest.raises(VNDBError, match="500"):
            client._post("vn", {})

    @responses.activate
    def test_post_http_200(self, client: VNDBAPIClient) -> None:
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json={"results": [{"id": "v1"}]}, status=200)
        data = client._post("vn", {})
        assert data["results"][0]["id"] == "v1"

    # ── search_vn_by_id ──────────────────────────────────────────────

    @responses.activate
    def test_search_vn_by_id(self, client: VNDBAPIClient) -> None:
        vn_resp = {
            "results": [{"id": "v2622", "title": "Test",
                         "titles": [], "image": None}],
        }
        release_resp = {"results": [], "more": False}
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=release_resp, status=200)

        vn = client.search_vn_by_id("v2622")
        assert isinstance(vn, VNInfo)
        assert vn.id == "v2622"

    @responses.activate
    def test_search_vn_by_id_not_found(self, client: VNDBAPIClient) -> None:
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json={"results": []}, status=200)
        with pytest.raises(VNDBNotFoundError):
            client.search_vn_by_id("v99999")

    @responses.activate
    def test_search_vn_by_id_adds_v_prefix(self, client: VNDBAPIClient) -> None:
        calls: list[dict] = []

        def on_vn(request):
            body = json.loads(request.body)
            calls.append(body)
            return (200, {}, json.dumps(
                {"results": [{"id": "v2622", "title": "T", "titles": [], "image": None}]}))

        responses.add_callback(responses.POST, f"{API_BASE}/vn", callback=on_vn)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json={"results": [], "more": False}, status=200)

        client.search_vn_by_id("2622")
        assert calls[0]["filters"] == ["id", "=", "v2622"]

    # ── search_vn_candidates ─────────────────────────────────────────

    @responses.activate
    def test_search_vn_candidates(self, client: VNDBAPIClient) -> None:
        resp = {
            "results": [
                {"id": "v1", "title": "One"},
                {"id": "v2", "title": "Two"},
            ],
        }
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=resp, status=200)
        candidates = client.search_vn_candidates("test")
        assert len(candidates) == 2
        assert candidates[0].id == "v1"

    @responses.activate
    def test_search_vn_candidates_not_found(self, client: VNDBAPIClient) -> None:
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json={"results": []}, status=200)
        with pytest.raises(VNDBNotFoundError):
            client.search_vn_candidates("nonexistent")

    # ── search_vn_by_title ───────────────────────────────────────────

    @responses.activate
    def test_search_vn_by_title_unique(self, client: VNDBAPIClient) -> None:
        vn_search_resp = {"results": [{"id": "v2622", "title": "Test",
                                       "titles": [], "image": None}]}
        release_resp = {"results": [], "more": False}

        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_search_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_search_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=release_resp, status=200)

        vn = client.search_vn_by_title("Test")
        assert isinstance(vn, VNInfo)

    @responses.activate
    def test_search_vn_by_title_multiple(self, client: VNDBAPIClient) -> None:
        resp = {
            "results": [
                {"id": "v1", "title": "One"},
                {"id": "v2", "title": "Two"},
            ],
        }
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=resp, status=200)
        with pytest.raises(VNDBMultipleResultsError) as exc:
            client.search_vn_by_title("common")
        assert len(exc.value.candidates) == 2

    # ── search_vn (auto-detect) ──────────────────────────────────────

    @responses.activate
    def test_search_vn_by_vid(self, client: VNDBAPIClient) -> None:
        vn_resp = {"results": [{"id": "v42", "title": "T",
                                "titles": [], "image": None}]}
        release_resp = {"results": [], "more": False}
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=release_resp, status=200)

        vn = client.search_vn("v42")
        assert vn.id == "v42"

    @responses.activate
    def test_search_vn_by_numeric_id(self, client: VNDBAPIClient) -> None:
        vn_resp = {"results": [{"id": "v42", "title": "T",
                                "titles": [], "image": None}]}
        release_resp = {"results": [], "more": False}
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=release_resp, status=200)

        vn = client.search_vn("42")
        assert vn.id == "v42"

    @responses.activate
    def test_search_vn_by_title_fallback(self, client: VNDBAPIClient) -> None:
        vn_search_resp = {"results": [{"id": "v2622", "title": "Specific Game",
                                       "titles": [], "image": None}]}
        release_resp = {"results": [], "more": False}

        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_search_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/vn",
                      json=vn_search_resp, status=200)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=release_resp, status=200)

        vn = client.search_vn("Specific Game")
        assert isinstance(vn, VNInfo)

    # ── _fetch_releases ──────────────────────────────────────────────

    @responses.activate
    def test_fetch_releases_paginated(self, client: VNDBAPIClient) -> None:
        page1 = {
            "results": [{"id": "r1", "title": "R1", "languages": []}],
            "more": True,
        }
        page2 = {
            "results": [{"id": "r2", "title": "R2", "languages": []}],
            "more": False,
        }
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=page1, status=200)
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=page2, status=200)

        releases = client._fetch_releases("v42")
        assert len(releases) == 2
        assert releases[0]["id"] == "r1"
        assert releases[1]["id"] == "r2"

    # ── get_chinese_patch_releases ───────────────────────────────────

    @responses.activate
    def test_get_chinese_patch_releases(self, client: VNDBAPIClient) -> None:
        resp = {
            "results": [
                {"id": "r1", "title": "JA", "languages": [{"lang": "ja"}]},
                {"id": "r2", "title": "ZH", "languages": [{"lang": "zh-Hans"}]},
            ],
            "more": False,
        }
        responses.add(responses.POST, f"{API_BASE}/release",
                      json=resp, status=200)

        zh_releases = client.get_chinese_patch_releases("v1")
        assert len(zh_releases) == 1
        assert zh_releases[0].id == "r2"
