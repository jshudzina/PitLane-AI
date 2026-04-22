"""Tests for pitlane_elo.data — read-only Parquet access."""

from __future__ import annotations

from pathlib import Path

import pytest
from pitlane_elo.data import (
    get_data_dir,
    get_qualifying_entries,
    get_race_entries,
)


class TestGetDataDir:
    def test_returns_path(self) -> None:
        path = get_data_dir()
        assert isinstance(path, Path)

    def test_env_override_data_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("PITLANE_DATA_DIR", str(tmp_path))
        assert get_data_dir() == tmp_path

    def test_env_override_db_path_uses_parent(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        fake_db = tmp_path / "override.duckdb"
        monkeypatch.setenv("PITLANE_DB_PATH", str(fake_db))
        monkeypatch.delenv("PITLANE_DATA_DIR", raising=False)
        assert get_data_dir() == tmp_path


class TestGetRaceEntries:
    def test_returns_none_for_missing_parquet(self, tmp_path: Path) -> None:
        result = get_race_entries(2024, data_dir=tmp_path)
        assert result is None

    def test_returns_none_for_empty_year(self, tmp_db: Path) -> None:
        result = get_race_entries(1950, data_dir=tmp_db)
        assert result is None

    def test_returns_entries(self, populated_db: Path) -> None:
        entries = get_race_entries(2024, data_dir=populated_db)
        assert entries is not None
        assert len(entries) == 5
        assert entries[0]["driver_id"] == "carlos_sainz"  # alphabetical order

    def test_filter_by_session_type(self, populated_db: Path) -> None:
        entries = get_race_entries(2024, data_dir=populated_db, session_type="R")
        assert entries is not None
        assert all(e["session_type"] == "R" for e in entries)

        sprint = get_race_entries(2024, data_dir=populated_db, session_type="S")
        assert sprint is None


class TestGetQualifyingEntries:
    def test_returns_none_for_missing_parquet(self, tmp_path: Path) -> None:
        result = get_qualifying_entries(2024, data_dir=tmp_path)
        assert result is None

    def test_returns_entries(self, populated_db: Path) -> None:
        entries = get_qualifying_entries(2024, data_dir=populated_db)
        assert entries is not None
        assert len(entries) == 5

    def test_filter_by_session_type(self, populated_db: Path) -> None:
        entries = get_qualifying_entries(2024, data_dir=populated_db, session_type="Q")
        assert entries is not None
        assert all(e["session_type"] == "Q" for e in entries)
