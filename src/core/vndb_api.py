"""VNDB API v2 (kana) client — fetch visual novel info & releases."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests

API_BASE = "https://api.vndb.org/kana"

# ── VN fields we always request ──────────────────────────────────────
VN_FIELDS = (
    "id, title, alttitle, titles{lang, title, latin}, "
    "image{url,dims,sexual,violence,votecount}"
)

VN_CANDIDATE_FIELDS = (
    "id, title, alttitle, titles{lang, title, latin}"
)

RELEASE_FIELDS = (
    "id, title, alttitle, released, platforms, "
    "languages{lang}, producers{id, name, original, developer, publisher}, "
    "media{medium, qty}, extlinks{url, label}"
)

PLACEHOLDER = "NO DATA"

# VNDB platform code → full name mapping
PLATFORM_MAP: dict[str, str] = {
    "win": "Windows",
    "lin": "Linux",
    "mac": "MacOS",
    "and": "Android",
    "ios": "iOS",
    "dvd": "DVD",
    "bdp": "Blu-ray Player",
    "dos": "DOS",
    "win3x": "Windows 3.x",
    "win9x": "Windows 9x",
    "winnt": "Windows NT",
    "web": "Web",
    "oth": "Other",
    "swi": "Switch",
    "xb3": "Xbox 360",
    "mob": "Mobile",
    "ps2": "PlayStation 2",
    "ps3": "PlayStation 3",
    "ps4": "PlayStation 4",
    "psv": "PlayStation Vita",
    "psp": "PlayStation Portable",
}

# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class Producer:
    id: str
    name: str
    original: str = ""
    developer: bool = False
    publisher: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Producer":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", PLACEHOLDER),
            original=d.get("original", ""),
            developer=d.get("developer", False),
            publisher=d.get("publisher", False),
        )

    def get_display_name(self) -> str:
        """Return original (Japanese) name if available, else romanized name."""
        if self.original:
            return self.original
        return self.name


@dataclass
class VNCandidate:
    """Lightweight VN info for search result listing."""
    id: str
    title: str
    alttitle: str | None = None
    titles: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "VNCandidate":
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            alttitle=d.get("alttitle"),
            titles=d.get("titles", []) or [],
        )

    def get_display_title(self) -> str:
        """Try to get original (Japanese) title, fallback to alttitle, then title."""
        for t in self.titles:
            if isinstance(t, dict) and t.get("lang") == "ja":
                return t.get("title", "")
        return self.alttitle or self.title


@dataclass
class VNRelease:
    id: str
    title: str
    alttitle: str | None = None
    released: str = ""
    platforms: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    producers: list[Producer] = field(default_factory=list)
    media: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "VNRelease":
        producers_raw = d.get("producers", []) or []
        languages_raw = d.get("languages", []) or []
        languages = [l.get("lang", "") for l in languages_raw if isinstance(l, dict)]
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            alttitle=d.get("alttitle"),
            released=d.get("released", ""),
            platforms=d.get("platforms", []) or [],
            languages=languages,
            producers=[Producer.from_dict(p) for p in producers_raw if isinstance(p, dict)],
            media=d.get("media", []) or [],
        )

    def format_released(self) -> str:
        """Return YYYYMMDD, padding with zeros or 'NO DATA'."""
        raw = (self.released or "").strip()
        if not raw:
            return PLACEHOLDER
        parts = raw.split("-")
        parts = [p for p in parts if p]
        while len(parts) < 3:
            parts.append("00")
        return "".join(parts)

    def get_display_title(self) -> str:
        """Return the best display title: native (alttitle) if available, else title."""
        if self.alttitle:
            return self.alttitle
        return self.title

    def get_platforms_display(self) -> str:
        """Return platform names with full names (e.g. win→Windows)."""
        if not self.platforms:
            return PLACEHOLDER
        names = [PLATFORM_MAP.get(p, p) for p in self.platforms]
        return ", ".join(names)

    def get_developer_name(self) -> str:
        """Return developer name (original Japanese if available), or PLACEHOLDER."""
        for p in self.producers:
            if p.developer:
                return p.get_display_name() or PLACEHOLDER
        # Don't fall back to first producer — if none is marked as developer,
        # there is no developer info. This prevents patch groups on Chinese
        # releases from being misidentified as the developer.
        return PLACEHOLDER

    def get_publisher_name(self) -> str:
        """Return publisher name (original Japanese if available), or PLACEHOLDER."""
        for p in self.producers:
            if p.publisher:
                return p.get_display_name() or PLACEHOLDER
        return PLACEHOLDER

    def get_non_developer_group_name(self) -> str:
        """Return the first producer that is NOT the developer (for Chinese patch groups)."""
        dev_name = self.get_developer_name()
        for p in self.producers:
            pn = p.get_display_name()
            if pn != dev_name and pn != PLACEHOLDER:
                return pn
        return PLACEHOLDER

    def get_languages_display(self) -> str:
        """Return languages string with Japanese (ja) first if present."""
        if not self.languages:
            return PLACEHOLDER
        sorted_langs = sorted(self.languages, key=lambda x: (x != "ja", x))
        return ", ".join(sorted_langs)

    def is_chinese_release(self) -> bool:
        """Check if this release has Chinese language."""
        return any(lang in ("zh-Hans", "zh-Hant", "zh") for lang in self.languages)


@dataclass
class VNInfo:
    id: str
    title: str
    alttitle: str | None = None
    titles: list[dict] = field(default_factory=list)
    image: dict | None = None
    releases: list[VNRelease] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "VNInfo":
        releases_raw = d.get("releases", []) or []
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            alttitle=d.get("alttitle"),
            titles=d.get("titles", []) or [],
            image=d.get("image"),
            releases=[VNRelease.from_dict(r) for r in releases_raw if isinstance(r, dict)],
        )

    def get_original_title(self) -> str:
        """Try to get the original (Japanese) title from the titles list."""
        for t in self.titles:
            if isinstance(t, dict) and t.get("lang") == "ja":
                return t.get("title", "")
        return self.alttitle or self.title


# ── Exceptions ────────────────────────────────────────────────────────


class VNDBError(Exception):
    """Base exception for VNDB API errors."""
    pass


class VNDBNotFoundError(VNDBError):
    """VN not found."""
    pass


class VNDBMultipleResultsError(VNDBError):
    """Multiple VNs found for a title search; candidates are stored."""
    def __init__(self, message: str, candidates: list[VNCandidate]):
        super().__init__(message)
        self.candidates = candidates


# ── Client ──────────────────────────────────────────────────────────────


class VNDBAPIClient:
    """Client for VNDB API v2 (kana)."""

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.timeout = timeout

    # ── low-level helpers ────────────────────────────────────────────────

    def _post(self, endpoint: str, payload: dict) -> dict:
        """发送 POST 请求到 VNDB API，统一处理超时、连接和 HTTP 错误。"""
        url = f"{API_BASE}/{endpoint}"
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise VNDBError("请求超时，请检查网络连接。")
        except requests.exceptions.ConnectionError:
            raise VNDBError("无法连接到 VNDB API，请检查网络连接。")
        except requests.exceptions.RequestException as e:
            raise VNDBError(f"网络请求失败：{e}")

        if resp.status_code == 404:
            raise VNDBNotFoundError("未找到该视觉小说。")
        if resp.status_code == 429:
            raise VNDBError("请求过于频繁，请稍后再试。")
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("errors", [{}])[0].get("msg", resp.text)
            except Exception:
                detail = resp.text
            raise VNDBError(f"API 错误 ({resp.status_code}): {detail}")

        return resp.json()

    def _fetch_all_results(
        self, endpoint: str, payload: dict, max_pages: int = 3
    ) -> list[dict]:
        """Fetch all results using pagination (page param)."""
        results: list[dict] = []
        payload = dict(payload)  # shallow copy
        page = 1
        while page <= max_pages:
            payload["page"] = page
            data = self._post(endpoint, payload)
            batch = data.get("results", [])
            results.extend(batch)
            if not data.get("more", False):
                break
            page += 1
        return results

    # ── VN search ──────────────────────────────────────────────────────

    def search_vn_by_id(self, vn_id: str) -> VNInfo:
        """通过 VNDB ID 搜索视觉小说并获取完整信息（含发行版本）。"""
        normalized = vn_id.strip().lower()
        if not normalized.startswith("v"):
            normalized = f"v{normalized}"

        payload: dict[str, Any] = {
            "filters": ["id", "=", normalized],
            "fields": VN_FIELDS,
        }
        data = self._post("vn", payload)
        results = data.get("results", [])
        if not results:
            raise VNDBNotFoundError(f"未找到 ID 为 {normalized} 的视觉小说。")

        raw_vn = results[0]

        # Always fetch releases separately (VN endpoint doesn't support inline releases)
        releases = self._fetch_releases(normalized)
        raw_vn["releases"] = releases

        return VNInfo.from_dict(raw_vn)

    def search_vn_candidates(self, title: str) -> list[VNCandidate]:
        """Search VN by title and return all candidates, without fetching releases."""
        payload: dict[str, Any] = {
            "filters": ["search", "=", title],
            "fields": VN_CANDIDATE_FIELDS,
            "results": 10,
        }
        data = self._post("vn", payload)
        results = data.get("results", [])
        if not results:
            raise VNDBNotFoundError(f"未找到标题包含「{title}」的视觉小说。")
        return [VNCandidate.from_dict(r) for r in results]

    def search_vn_by_title(self, title: str) -> VNInfo:
        """通过标题搜索，若唯一匹配则返回完整 VN 信息；若多结果则抛出异常。"""
        candidates = self.search_vn_candidates(title)
        if len(candidates) > 1:
            raise VNDBMultipleResultsError(
                f"找到多个匹配结果，请选择一个。",
                candidates,
            )

        raw_vn = self._fetch_vn_by_id(candidates[0].id)
        return VNInfo.from_dict(raw_vn)

    def search_vn(self, query: str) -> VNInfo:
        """自动判断查询类型（ID 或标题）并调用对应的搜索方法。"""
        query = query.strip()
        if query.lower().startswith("v") and query[1:].isdigit():
            return self.search_vn_by_id(query)
        if query.isdigit():
            return self.search_vn_by_id(query)
        return self.search_vn_by_title(query)

    def fetch_vn_by_id(self, vn_id: str) -> VNInfo:
        """Fetch full VNInfo (with releases) for a given vn ID."""
        normalized = vn_id.strip().lower()
        if not normalized.startswith("v"):
            normalized = f"v{normalized}"

        payload: dict[str, Any] = {
            "filters": ["id", "=", normalized],
            "fields": VN_FIELDS,
        }
        data = self._post("vn", payload)
        results = data.get("results", [])
        if not results:
            raise VNDBNotFoundError(f"未找到 ID 为 {normalized} 的视觉小说。")

        raw_vn = results[0]
        releases = self._fetch_releases(normalized)
        raw_vn["releases"] = releases
        return VNInfo.from_dict(raw_vn)

    def _fetch_vn_by_id(self, vn_id: str) -> dict:
        """Internal helper: fetch raw VN data by ID (without exception wrapping)."""
        normalized = vn_id.strip().lower()
        if not normalized.startswith("v"):
            normalized = f"v{normalized}"

        payload: dict[str, Any] = {
            "filters": ["id", "=", normalized],
            "fields": VN_FIELDS,
        }
        data = self._post("vn", payload)
        results = data.get("results", [])
        if not results:
            raise VNDBNotFoundError(f"未找到 ID 为 {normalized} 的视觉小说。")

        raw_vn = results[0]
        releases = self._fetch_releases(normalized)
        raw_vn["releases"] = releases
        return raw_vn

    # ── Release fetching ───────────────────────────────────────────────

    def _fetch_releases(self, vn_id: str) -> list[dict]:
        """获取指定 VN 的所有发行版本（含分页）。"""
        payload: dict[str, Any] = {
            "filters": ["vn", "=", ["id", "=", vn_id]],
            "fields": RELEASE_FIELDS,
            "results": 100,
        }
        return self._fetch_all_results("release", payload, max_pages=5)

    # ── Chinese patch helper ──────────────────────────────────────────

    def get_chinese_patch_releases(self, vn_id: str) -> list[VNRelease]:
        """Find releases that have Chinese language support."""
        payload: dict[str, Any] = {
            "filters": ["vn", "=", ["id", "=", vn_id]],
            "fields": RELEASE_FIELDS,
            "results": 100,
        }
        raw_releases = self._fetch_all_results("release", payload, max_pages=5)
        all_releases = [VNRelease.from_dict(r) for r in raw_releases]
        return [r for r in all_releases if r.is_chinese_release()]