"""Tests for pitlane_elo.data — read-only DB access."""

from __future__ import annotations

from pathlib import Path

from pitlane_elo.data import (
    get_db_path,
    get_qualifying_entries,
    get_race_entries,
)


class TestGetDbPath:
    def test_returns_path(self) -> None:
        path = get_db_path()
        assert isinstance(path, Path)

    def test_env_override(self, monkeypatch: object, tmp_path: Path) -> None:
        import pytest

        mp = pytest.MonkeyPatch()
        fake = tmp_path / "override.duckdb"
        mp.setenv("PITLANE_DB_PATH", str(fake))
        try:
            assert get_db_path() == fake
        finally:
            mp.undo()


class TestGetRaceEntries:
    def test_returns_none_for_missing_db(self, tmp_path: Path) -> None:
        result = get_race_entries(2024, db_path=tmp_path / "nonexistent.duckdb")
        assert result is None

    def test_returns_none_for_empty_year(self, tmp_db: Path) -> None:
        result = get_race_entries(1950, db_path=tmp_db)
        assert result is None

    def test_returns_entries(self, populated_db: Path) -> None:
        entries = get_race_entries(2024, db_path=populated_db)
        assert entries is not None
        assert len(entries) == 5
        assert entries[0]["driver_id"] == "carlos_sainz"  # alphabetical order

    def test_filter_by_session_type(self, populated_db: Path) -> None:
        entries = get_race_entries(2024, db_path=populated_db, session_type="R")
        assert entries is not None
        assert all(e["session_type"] == "R" for e in entries)

        sprint = get_race_entries(2024, db_path=populated_db, session_type="S")
        assert sprint is None


class TestGetQualifyingEntries:
    def test_returns_none_for_missing_db(self, tmp_path: Path) -> None:
        result = get_qualifying_entries(2024, db_path=tmp_path / "nonexistent.duckdb")
        assert result is None

    def test_returns_entries(self, populated_db: Path) -> None:
        entries = get_qualifying_entries(2024, db_path=populated_db)
        assert entries is not None
        assert len(entries) == 5

    def test_filter_by_session_type(self, populated_db: Path) -> None:
        entries = get_qualifying_entries(2024, db_path=populated_db, session_type="Q")
        assert entries is not None
        assert all(e["session_type"] == "Q" for e in entries)
