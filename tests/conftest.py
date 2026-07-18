"""Shared test fixtures for VNDB-GUI."""
from __future__ import annotations

import pytest
from core.vndb_api import (
    VNInfo,
    VNRelease,
    VNCandidate,
    Producer,
    PLACEHOLDER,
)


@pytest.fixture
def sample_producer() -> Producer:
    return Producer(
        id="p1",
        name="ALcot",
        original="ALcot",
        developer=True,
        publisher=True,
    )


@pytest.fixture
def sample_producer_patch_group() -> Producer:
    return Producer(
        id="p99",
        name="Makura Castle",
        original="枕城",
        developer=False,
        publisher=False,
    )


@pytest.fixture
def sample_release(sample_producer: Producer) -> VNRelease:
    return VNRelease(
        id="r123",
        title="My Girlfriend is the President.",
        alttitle="幼なじみは大統領",
        released="2009-09-18",
        platforms=["win"],
        languages=["ja"],
        producers=[sample_producer],
    )


@pytest.fixture
def sample_release_zh(sample_producer: Producer, sample_producer_patch_group: Producer) -> VNRelease:
    return VNRelease(
        id="r456",
        title="My Girlfriend is the President. - Chinese",
        alttitle="幼なじみは大統領",
        released="2013-03-14",
        platforms=["win"],
        languages=["ja", "zh-Hans"],
        producers=[sample_producer, sample_producer_patch_group],
    )


@pytest.fixture
def sample_release_tba() -> VNRelease:
    return VNRelease(
        id="r789",
        title="Future Game",
        alttitle=None,
        released="",
        platforms=["win"],
        languages=["ja", "en"],
        producers=[],
    )


@pytest.fixture
def sample_vn(sample_release: VNRelease, sample_release_zh: VNRelease, sample_release_tba: VNRelease) -> VNInfo:
    return VNInfo(
        id="v2622",
        title="My Girlfriend is the President.",
        alttitle="幼なじみは大統領",
        titles=[
            {"lang": "ja", "title": "幼なじみは大統領"},
            {"lang": "en", "title": "My Girlfriend is the President."},
        ],
        releases=[sample_release, sample_release_zh, sample_release_tba],
    )
