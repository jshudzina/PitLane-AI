"""Tests for stats_db utility module using Parquet files."""

from pathlib import Path

import duckdb
from pitlane_agent.utils.stats_db import (
    get_season_stats,
    init_data_dir,
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


class TestInitDataDir:
    """Tests for init_data_dir."""

    def test_creates_directory(self, tmp_path):
        data_dir = tmp_path / "data"
        init_data_dir(data_dir)
        assert data_dir.exists()

    def test_creates_nested_directories(self, tmp_path):
        data_dir = tmp_path / "nested" / "dir" / "data"
        init_data_dir(data_dir)
        assert data_dir.exists()

    def test_idempotent_on_second_call(self, tmp_path):
        data_dir = tmp_path / "data"
        init_data_dir(data_dir)
        init_data_dir(data_dir)  # should not raise
        assert data_dir.exists()


class TestUpsertSessionStats:
    """Tests for upsert_session_stats."""

    def test_inserts_single_record(self, tmp_path):
        upsert_session_stats(tmp_path, [_SAMPLE_RECORD])

        parquet_path = tmp_path / "session_stats.parquet"
        assert parquet_path.exists()
        con = duckdb.connect()
        result = con.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path}')").fetchone()
        con.close()
        assert result[0] == 1

    def test_inserts_multiple_records(self, tmp_path):
        records = [
            {**_SAMPLE_RECORD, "round": 1, "session_type": "R"},
            {**_SAMPLE_RECORD, "round": 2, "session_type": "R"},
            {**_SAMPLE_RECORD, "round": 2, "session_type": "S"},
        ]
        upsert_session_stats(tmp_path, records)

        parquet_path = tmp_path / "session_stats.parquet"
        con = duckdb.connect()
        result = con.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path}')").fetchone()
        con.close()
        assert result[0] == 3

    def test_replaces_existing_record(self, tmp_path):
        upsert_session_stats(tmp_path, [_SAMPLE_RECORD])
        updated = {**_SAMPLE_RECORD, "total_overtakes": 99}
        upsert_session_stats(tmp_path, [updated])

        parquet_path = tmp_path / "session_stats.parquet"
        con = duckdb.connect()
        result = con.execute(
            f"SELECT total_overtakes FROM read_parquet('{parquet_path}')"
            " WHERE year = 2024 AND round = 1 AND session_type = 'R'"
        ).fetchone()
        con.close()
        assert result[0] == 99

    def test_empty_records_is_noop(self, tmp_path):
        upsert_session_stats(tmp_path, [])
        assert not (tmp_path / "session_stats.parquet").exists()

    def test_nullable_fields_accept_none(self, tmp_path):
        record = {**_SAMPLE_RECORD, "circuit_length_km": None, "podium": None, "date": None}
        upsert_session_stats(tmp_path, [record])

        parquet_path = tmp_path / "session_stats.parquet"
        con = duckdb.connect()
        result = con.execute(
            f"SELECT circuit_length_km, podium, date FROM read_parquet('{parquet_path}') WHERE round = 1"
        ).fetchone()
        con.close()
        assert result[0] is None
        assert result[1] is None
        assert result[2] is None


class TestGetSeasonStats:
    """Tests for get_season_stats."""

    def test_returns_none_when_parquet_does_not_exist(self, tmp_path):
        result = get_season_stats(tmp_path, 2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path):
        upsert_session_stats(tmp_path, [_SAMPLE_RECORD])
        result = get_season_stats(tmp_path, 2023)
        assert result is None

    def test_returns_rows_for_year(self, tmp_path):
        upsert_session_stats(tmp_path, [_SAMPLE_RECORD])
        result = get_season_stats(tmp_path, 2024)

        assert result is not None
        assert len(result) == 1
        assert result[0]["year"] == 2024
        assert result[0]["event_name"] == "Bahrain Grand Prix"

    def test_returns_dicts_with_correct_keys(self, tmp_path):
        upsert_session_stats(tmp_path, [_SAMPLE_RECORD])
        result = get_season_stats(tmp_path, 2024)

        assert result is not None
        row = result[0]
        expected_keys = {
            "year",
            "round",
            "event_name",
            "country",
            "date",
            "session_type",
            "circuit_length_km",
            "total_overtakes",
            "total_position_changes",
            "average_volatility",
            "mean_pit_stops",
            "total_laps",
            "num_safety_cars",
            "num_virtual_safety_cars",
            "num_red_flags",
            "podium",
        }
        assert set(row.keys()) == expected_keys

    def test_results_ordered_by_round(self, tmp_path):
        records = [
            {**_SAMPLE_RECORD, "round": 3, "event_name": "Australian GP"},
            {**_SAMPLE_RECORD, "round": 1, "event_name": "Bahrain GP"},
            {**_SAMPLE_RECORD, "round": 2, "event_name": "Saudi GP"},
        ]
        upsert_session_stats(tmp_path, records)
        result = get_season_stats(tmp_path, 2024)

        assert result is not None
        assert [r["round"] for r in result] == [1, 2, 3]

    def test_isolates_by_year(self, tmp_path):
        records = [
            {**_SAMPLE_RECORD, "year": 2023, "event_name": "Old GP"},
            {**_SAMPLE_RECORD, "year": 2024, "event_name": "New GP"},
        ]
        upsert_session_stats(tmp_path, records)

        result_2024 = get_season_stats(tmp_path, 2024)
        result_2023 = get_season_stats(tmp_path, 2023)

        assert result_2024 is not None
        assert len(result_2024) == 1
        assert result_2024[0]["event_name"] == "New GP"

        assert result_2023 is not None
        assert len(result_2023) == 1
        assert result_2023[0]["event_name"] == "Old GP"


class TestGetDataDir:
    """Tests for get_data_dir."""

    def test_returns_path_object(self):
        from pitlane_agent.utils.stats_db import get_data_dir

        result = get_data_dir()

        assert isinstance(result, Path)

    def test_path_is_directory_or_in_pitlane_agent_data(self):
        from pitlane_agent.utils.stats_db import get_data_dir

        result = get_data_dir()

        assert "pitlane_agent" in str(result)
        assert "data" in str(result)
