"""Tests for stats_db utility module using in-memory DuckDB."""

from pathlib import Path

import duckdb
from pitlane_agent.utils.stats_db import (
    get_season_stats,
    init_db,
    upsert_session_stats,
)

_SAMPLE_RECORD = {
    "year": 2024,
    "round": 1,
    "event_name": "Bahrain Grand Prix",
    "country": "Bahrain",
    "date": "2024-03-02",
    "session_type": "R",
    "circuit_length_km": 5.412,
    "total_overtakes": 32,
    "total_position_changes": 45,
    "average_volatility": 2.3,
    "mean_pit_stops": 1.8,
    "total_laps": 57,
    "num_safety_cars": 0,
    "num_virtual_safety_cars": 1,
    "num_red_flags": 0,
    "podium": '["VER", "SAI", "PER"]',
}


class TestInitDb:
    """Tests for init_db."""

    def test_creates_session_stats_table(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM session_stats").fetchone()
        con.close()

        assert result[0] == 0

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dir" / "test.duckdb"
        init_db(db_path)

        assert db_path.exists()

    def test_idempotent_on_second_call(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        init_db(db_path)  # should not raise

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM session_stats").fetchone()
        con.close()

        assert result[0] == 0


class TestUpsertSessionStats:
    """Tests for upsert_session_stats."""

    def test_inserts_single_record(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        upsert_session_stats(db_path, [_SAMPLE_RECORD])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM session_stats").fetchone()
        con.close()

        assert result[0] == 1

    def test_inserts_multiple_records(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        records = [
            {**_SAMPLE_RECORD, "round": 1, "session_type": "R"},
            {**_SAMPLE_RECORD, "round": 2, "session_type": "R"},
            {**_SAMPLE_RECORD, "round": 2, "session_type": "S"},
        ]
        upsert_session_stats(db_path, records)

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM session_stats").fetchone()
        con.close()

        assert result[0] == 3

    def test_replaces_existing_record(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        upsert_session_stats(db_path, [_SAMPLE_RECORD])
        updated = {**_SAMPLE_RECORD, "total_overtakes": 99}
        upsert_session_stats(db_path, [updated])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT total_overtakes FROM session_stats WHERE year = 2024 AND round = 1 AND session_type = 'R'"
        ).fetchone()
        con.close()

        assert result[0] == 99

    def test_empty_records_is_noop(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        upsert_session_stats(db_path, [])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM session_stats").fetchone()
        con.close()

        assert result[0] == 0

    def test_nullable_fields_accept_none(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        record = {**_SAMPLE_RECORD, "circuit_length_km": None, "podium": None, "date": None}
        upsert_session_stats(db_path, [record])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT circuit_length_km, podium, date FROM session_stats WHERE round = 1"
        ).fetchone()
        con.close()

        assert result[0] is None
        assert result[1] is None
        assert result[2] is None


class TestGetSeasonStats:
    """Tests for get_season_stats."""

    def test_returns_none_when_db_does_not_exist(self, tmp_path):
        db_path = tmp_path / "nonexistent.duckdb"
        result = get_season_stats(db_path, 2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_RECORD])

        result = get_season_stats(db_path, 2023)

        assert result is None

    def test_returns_rows_for_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_RECORD])

        result = get_season_stats(db_path, 2024)

        assert result is not None
        assert len(result) == 1
        assert result[0]["year"] == 2024
        assert result[0]["event_name"] == "Bahrain Grand Prix"

    def test_returns_dicts_with_correct_keys(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_RECORD])

        result = get_season_stats(db_path, 2024)

        assert result is not None
        row = result[0]
        expected_keys = {
            "year", "round", "event_name", "country", "date", "session_type",
            "circuit_length_km", "total_overtakes", "total_position_changes",
            "average_volatility", "mean_pit_stops", "total_laps",
            "num_safety_cars", "num_virtual_safety_cars", "num_red_flags", "podium",
        }
        assert set(row.keys()) == expected_keys

    def test_results_ordered_by_round(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        records = [
            {**_SAMPLE_RECORD, "round": 3, "event_name": "Australian GP"},
            {**_SAMPLE_RECORD, "round": 1, "event_name": "Bahrain GP"},
            {**_SAMPLE_RECORD, "round": 2, "event_name": "Saudi GP"},
        ]
        upsert_session_stats(db_path, records)

        result = get_season_stats(db_path, 2024)

        assert result is not None
        assert [r["round"] for r in result] == [1, 2, 3]

    def test_isolates_by_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)

        records = [
            {**_SAMPLE_RECORD, "year": 2023, "event_name": "Old GP"},
            {**_SAMPLE_RECORD, "year": 2024, "event_name": "New GP"},
        ]
        upsert_session_stats(db_path, records)

        result_2024 = get_season_stats(db_path, 2024)
        result_2023 = get_season_stats(db_path, 2023)

        assert result_2024 is not None
        assert len(result_2024) == 1
        assert result_2024[0]["event_name"] == "New GP"

        assert result_2023 is not None
        assert len(result_2023) == 1
        assert result_2023[0]["event_name"] == "Old GP"


class TestGetDbPath:
    """Tests for get_db_path."""

    def test_returns_path_object(self):
        from pitlane_agent.utils.stats_db import get_db_path

        result = get_db_path()

        assert isinstance(result, Path)

    def test_path_ends_with_duckdb(self):
        from pitlane_agent.utils.stats_db import get_db_path

        result = get_db_path()

        assert result.suffix == ".duckdb"

    def test_path_is_within_pitlane_agent_data(self):
        from pitlane_agent.utils.stats_db import get_db_path

        result = get_db_path()

        assert "pitlane_agent" in str(result)
        assert "data" in str(result)
