"""Tests for app_version.py."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import app_version


class TestGetAppVersion:
    def test_read_from_bundled_file(self, tmp_path) -> None:
        version_file = tmp_path / "version.txt"
        version_file.write_text("2.0.0", encoding="utf-8")

        with patch.object(app_version, "_base_dir", return_value=str(tmp_path)):
            result = app_version.get_app_version()
        assert result == "2.0.0"

    def test_fallback_to_env_var(self, monkeypatch) -> None:
        with patch.object(app_version, "_read_bundled_version", return_value=""):
            monkeypatch.setenv("VNDB_GUI_VERSION", "env-version")
            result = app_version.get_app_version()
        assert result == "env-version"

    def test_fallback_to_dev(self, monkeypatch) -> None:
        with patch.object(app_version, "_read_bundled_version", return_value=""):
            monkeypatch.delenv("VNDB_GUI_VERSION", raising=False)
            result = app_version.get_app_version()
        assert result == "dev"

    def test_env_var_stripped(self, monkeypatch) -> None:
        with patch.object(app_version, "_read_bundled_version", return_value=""):
            monkeypatch.setenv("VNDB_GUI_VERSION", "  1.2.3  ")
            result = app_version.get_app_version()
        assert result == "1.2.3"

    def test_empty_env_var_is_ignored(self, monkeypatch) -> None:
        with patch.object(app_version, "_read_bundled_version", return_value=""):
            monkeypatch.setenv("VNDB_GUI_VERSION", "")
            result = app_version.get_app_version()
        assert result == "dev"

    def test_bundled_has_priority_over_env(self, monkeypatch) -> None:
        with patch.object(app_version, "_read_bundled_version", return_value="bundled-ver"):
            monkeypatch.setenv("VNDB_GUI_VERSION", "env-ver")
            result = app_version.get_app_version()
        assert result == "bundled-ver"

    def test_read_bundled_version_file_not_found(self) -> None:
        with patch.object(app_version, "_base_dir", return_value="/nonexistent/path"):
            result = app_version._read_bundled_version()
        assert result == ""

    def test_version_file_whitespace_stripped(self, tmp_path) -> None:
        version_file = tmp_path / "version.txt"
        version_file.write_text("  3.0.0\n  ", encoding="utf-8")

        with patch.object(app_version, "_base_dir", return_value=str(tmp_path)):
            result = app_version.get_app_version()
        assert result == "3.0.0"
