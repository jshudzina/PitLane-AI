"""Tests for season_summary DB-first path (_build_summary_from_db, get_season_summary)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pitlane_agent.commands.fetch.season_summary import _build_summary_from_db, get_season_summary
from pitlane_agent.utils.constants import AVG_CIRCUIT_LENGTH_KM
from pitlane_agent.utils.stats_db import init_db, upsert_session_stats

_SAMPLE_ROW = {
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
    "podium": json.dumps([
        {"driver": "VER", "team": "Red Bull Racing"},
        {"driver": "SAI", "team": "Ferrari"},
        {"driver": "LEC", "team": "Ferrari"},
    ]),
}


class TestBuildSummaryFromDb:
    """Tests for _build_summary_from_db."""

    def test_returns_none_when_db_missing(self, tmp_path: Path) -> None:
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=tmp_path / "missing.duckdb",
        ):
            result = _build_summary_from_db(2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [{**_SAMPLE_ROW, "year": 2023}])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is None

    def test_returns_summary_for_single_race(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_ROW])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        assert result["year"] == 2024
        assert result["total_races"] == 1
        assert len(result["races"]) == 1
        race = result["races"][0]
        assert race["round"] == 1
        assert race["event_name"] == "Bahrain Grand Prix"
        assert race["circuit_length_km"] == 5.412

    def test_podium_deserialized_from_json(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_ROW])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        podium = result["races"][0]["podium"]
        assert isinstance(podium, list)
        assert len(podium) == 3
        assert podium[0]["driver"] == "VER"
        assert podium[0]["team"] == "Red Bull Racing"

    def test_null_podium_becomes_empty_list(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [{**_SAMPLE_ROW, "podium": None}])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        assert result["races"][0]["podium"] == []

    def test_race_distance_uses_circuit_length(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_ROW])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        expected = _SAMPLE_ROW["total_laps"] * _SAMPLE_ROW["circuit_length_km"]
        assert abs(result["races"][0]["race_distance_km"] - expected) < 0.01

    def test_race_distance_uses_avg_fallback_when_no_circuit_length(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [{**_SAMPLE_ROW, "circuit_length_km": None}])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        expected = _SAMPLE_ROW["total_laps"] * AVG_CIRCUIT_LENGTH_KM
        assert abs(result["races"][0]["race_distance_km"] - expected) < 0.01

    def test_wildness_score_in_range(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_ROW])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        score = result["races"][0]["wildness_score"]
        assert 0.0 <= score <= 1.0

    def test_races_sorted_by_wildness_descending(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        rows = [
            {**_SAMPLE_ROW, "round": 1, "total_overtakes": 5, "num_safety_cars": 0},
            {**_SAMPLE_ROW, "round": 2, "total_overtakes": 50, "num_safety_cars": 3},
        ]
        upsert_session_stats(db_path, rows)
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        scores = [r["wildness_score"] for r in result["races"]]
        assert scores == sorted(scores, reverse=True)

    def test_season_averages_computed(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_ROW])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            result = _build_summary_from_db(2024)
        assert result is not None
        avgs = result["season_averages"]
        assert "overtakes_per_lap" in avgs
        assert "position_changes_per_lap" in avgs
        assert "average_volatility" in avgs
        assert "mean_pit_stops" in avgs
        assert avgs["average_volatility"] == round(_SAMPLE_ROW["average_volatility"], 2)


class TestGetSeasonSummaryDbFirst:
    """Tests for the DB-first fast path in get_season_summary."""

    def test_db_path_used_when_data_exists(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)
        upsert_session_stats(db_path, [_SAMPLE_ROW])
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            with patch(
                "pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache"
            ) as mock_cache:
                result = get_season_summary(2024)
        # FastF1 should not be touched when DB has data
        mock_cache.assert_not_called()
        assert result["year"] == 2024
        assert result["total_races"] == 1

    def test_falls_back_to_live_when_db_empty(self, tmp_path: Path) -> None:
        db_path = tmp_path / "missing.duckdb"
        with patch(
            "pitlane_agent.commands.fetch.season_summary.get_db_path",
            return_value=db_path,
        ):
            with patch(
                "pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache"
            ) as mock_cache:
                with patch("pitlane_agent.commands.fetch.season_summary.fastf1") as mock_ff1:
                    import pandas as pd
                    mock_ff1.get_event_schedule.return_value = pd.DataFrame(columns=["RoundNumber"])
                    result = get_season_summary(2024)
        # Live path was reached
        mock_cache.assert_called_once()
        mock_ff1.get_event_schedule.assert_called_once_with(2024, include_testing=False)
        assert result["year"] == 2024
        assert result["total_races"] == 0
