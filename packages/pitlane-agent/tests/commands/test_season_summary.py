"""Tests for season_summary commands (fetch and analyze)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.fetch.season_summary import (
    _compute_wildness_score,
    _count_track_interruptions,
    get_season_summary,
)

# ---------------------------------------------------------------------------
# Helpers shared by analyze tests
# ---------------------------------------------------------------------------


def _make_race_result_row(**kwargs) -> dict:
    defaults = {
        "position": 1,
        "positionText": "1",
        "status": "Finished",
        "driverId": "ver",
        "constructorId": "red_bull",
        "fastestLapRank": 3,
    }
    return {**defaults, **kwargs}


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _ergast_resp(content: list[pd.DataFrame]) -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


def _standings(entries: list[dict], round_num: int = 3) -> dict:
    return {
        "year": 2024,
        "round": round_num,
        "total_standings": len(entries),
        "filters": {"round": None},
        "standings": entries,
    }


def _schedule(total_races: int = 3) -> dict:
    return {
        "year": 2024,
        "events": [{"round": i, "sessions": [{"name": "Race"}]} for i in range(1, total_races + 1)],
    }


def _driver_entry(position: int, driver_id: str, name: str, wins: int, points: float) -> dict:
    return {
        "position": position,
        "points": points,
        "wins": wins,
        "driver_id": driver_id,
        "driver_code": driver_id.upper()[:3],
        "full_name": name,
        "teams": ["Team A"],
        "team_ids": ["team_a"],
    }


# ---------------------------------------------------------------------------
# Analyze season_summary tests
# ---------------------------------------------------------------------------


class TestAnalyzeSeasonSummaryHelpers:
    """Unit tests for _count_per_driver and _count_per_constructor."""

    def test_count_per_driver_by_position(self):
        from pitlane_agent.commands.analyze.season_summary import _count_per_driver

        df = _make_df(
            [
                _make_race_result_row(driverId="ver", position=1),
                _make_race_result_row(driverId="lec", position=2),
                _make_race_result_row(driverId="ham", position=1),
            ]
        )
        result = _count_per_driver([df], position=1)
        assert result == {"ver": 1, "ham": 1}

    def test_count_per_driver_fastest_lap(self):
        from pitlane_agent.commands.analyze.season_summary import _count_per_driver

        df = _make_df(
            [
                _make_race_result_row(driverId="ver", fastestLapRank=1),
                _make_race_result_row(driverId="lec", fastestLapRank=2),
            ]
        )
        result = _count_per_driver([df], fastest_rank=True)
        assert result == {"ver": 1}

    def test_count_per_driver_accumulates_across_rounds(self):
        from pitlane_agent.commands.analyze.season_summary import _count_per_driver

        df1 = _make_df([_make_race_result_row(driverId="ver", position=1)])
        df2 = _make_df([_make_race_result_row(driverId="ver", position=1)])
        result = _count_per_driver([df1, df2], position=1)
        assert result == {"ver": 2}

    def test_count_per_driver_empty_content(self):
        from pitlane_agent.commands.analyze.season_summary import _count_per_driver

        assert _count_per_driver([], position=1) == {}

    def test_count_per_constructor(self):
        from pitlane_agent.commands.analyze.season_summary import _count_per_constructor

        df = _make_df(
            [
                _make_race_result_row(constructorId="red_bull", position=1),
                _make_race_result_row(constructorId="ferrari", position=2),
            ]
        )
        result = _count_per_constructor([df], position=1)
        assert result == {"red_bull": 1}


class TestGenerateSeasonSummaryChart:
    """Tests for generate_season_summary_chart using mocked dependencies."""

    def _setup_patches(self, monkeypatch, driver_standings_data, schedule_data, mock_api):
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.get_driver_standings",
            lambda year, **kw: driver_standings_data,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.get_constructor_standings",
            lambda year, **kw: driver_standings_data,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.get_event_schedule",
            lambda year, **kw: schedule_data,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.get_ergast_client",
            lambda: mock_api,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.setup_plot_style",
            lambda: None,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.save_figure",
            lambda fig, path, **kw: (path.parent.mkdir(parents=True, exist_ok=True), path.touch()),
        )

    def _minimal_api(self, round_dfs: dict[int, pd.DataFrame]) -> MagicMock:
        """Build a mock Ergast API returning empty for position-filtered queries."""
        api = MagicMock()
        api.get_race_results.side_effect = lambda **kw: (
            _ergast_resp([])
            if kw.get("results_position") in (2, 3)
            else _ergast_resp([])
            if kw.get("fastest_rank") == 1
            else _ergast_resp([round_dfs[kw["round"]]])
            if kw.get("round") in round_dfs
            else _ergast_resp([])
        )
        api.get_qualifying_results.return_value = _ergast_resp([])
        return api

    def test_returns_required_keys(self, monkeypatch, tmp_path):
        standings = _standings([_driver_entry(1, "ver", "Max Verstappen", 3, 75.0)])
        schedule = _schedule(3)
        round_df = _make_df(
            [_make_race_result_row(driverId="ver", constructorId="red_bull", position=1, positionText="1")]
        )
        api = self._minimal_api({1: round_df, 2: round_df, 3: round_df})

        self._setup_patches(monkeypatch, standings, schedule, api)

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        for key in (
            "chart_path",
            "workspace",
            "year",
            "summary_type",
            "analysis_round",
            "total_races",
            "season_complete",
            "leader",
            "statistics",
        ):
            assert key in result, f"Missing key: {key}"

        assert result["year"] == 2024
        assert result["summary_type"] == "drivers"
        assert result["season_complete"] is True

    def test_invalid_type_raises(self, tmp_path):
        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        with pytest.raises(ValueError, match="Invalid summary_type"):
            generate_season_summary_chart(year=2024, summary_type="teams", workspace_dir=tmp_path)

    def test_empty_standings_raises(self, monkeypatch, tmp_path):
        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.get_driver_standings",
            lambda year, **kw: _standings([]),
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.get_event_schedule",
            lambda year, **kw: _schedule(3),
        )

        with pytest.raises(ValueError, match="No standings data"):
            generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

    def test_partial_season_marked_incomplete(self, monkeypatch, tmp_path):
        standings = _standings([_driver_entry(1, "ver", "Max Verstappen", 1, 25.0)], round_num=1)
        schedule = _schedule(3)  # 3 total races
        round_df = _make_df([_make_race_result_row(driverId="ver", positionText="1")])
        api = self._minimal_api({1: round_df})

        self._setup_patches(monkeypatch, standings, schedule, api)

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        assert result["season_complete"] is False
        assert result["analysis_round"] == 1

    def test_dnf_counted_for_retired_driver(self, monkeypatch, tmp_path):
        standings = _standings(
            [
                _driver_entry(1, "ver", "Max Verstappen", 1, 25.0),
                _driver_entry(2, "lec", "Charles Leclerc", 0, 0.0),
            ],
            round_num=1,
        )
        schedule = _schedule(1)

        round_df = _make_df(
            [
                _make_race_result_row(
                    driverId="ver", constructorId="red_bull", position=1, positionText="1", status="Finished"
                ),
                _make_race_result_row(
                    driverId="lec", constructorId="ferrari", position=20, positionText="R", status="Retired"
                ),
            ]
        )
        api = self._minimal_api({1: round_df})

        self._setup_patches(monkeypatch, standings, schedule, api)

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)
        competitors = result["statistics"]["competitors"]
        lec = next(c for c in competitors if c["driver_id"] == "lec")
        ver = next(c for c in competitors if c["driver_id"] == "ver")

        assert lec["dnfs"] == 1
        assert ver["dnfs"] == 0
        assert lec["avg_finish_position"] is None
        assert ver["avg_finish_position"] == 1.0

    def test_podiums_include_p1_p2_p3(self, monkeypatch, tmp_path):
        """Podiums = wins + P2 + P3 counts."""
        standings = _standings(
            [
                _driver_entry(1, "ver", "Max Verstappen", 1, 25.0),
                _driver_entry(2, "lec", "Charles Leclerc", 0, 18.0),
            ],
            round_num=1,
        )
        schedule = _schedule(1)

        p2_df = _make_df([_make_race_result_row(driverId="lec", constructorId="ferrari", position=2)])

        api = MagicMock()
        api.get_race_results.side_effect = lambda **kw: (
            _ergast_resp([p2_df])
            if kw.get("results_position") == 2
            else _ergast_resp([])
            if kw.get("results_position") == 3
            else _ergast_resp([])
            if kw.get("fastest_rank") == 1
            else _ergast_resp(
                [
                    _make_df(
                        [
                            _make_race_result_row(
                                driverId="ver", constructorId="red_bull", position=1, positionText="1"
                            ),
                            _make_race_result_row(
                                driverId="lec", constructorId="ferrari", position=2, positionText="2"
                            ),
                        ]
                    )
                ]
            )
            if kw.get("round") == 1
            else _ergast_resp([])
        )
        api.get_qualifying_results.return_value = _ergast_resp([])

        self._setup_patches(monkeypatch, standings, schedule, api)

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)
        competitors = result["statistics"]["competitors"]
        lec = next(c for c in competitors if c["driver_id"] == "lec")
        ver = next(c for c in competitors if c["driver_id"] == "ver")

        assert ver["wins"] == 1
        assert ver["podiums"] == 1
        assert lec["wins"] == 0
        assert lec["podiums"] == 1  # 1 P2

    def test_chart_file_written_to_workspace(self, monkeypatch, tmp_path):
        standings = _standings([_driver_entry(1, "ver", "Max Verstappen", 0, 0.0)], round_num=1)
        schedule = _schedule(1)
        api = self._minimal_api({1: _make_df([_make_race_result_row()])})

        self._setup_patches(monkeypatch, standings, schedule, api)

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        chart_path = Path(result["chart_path"])
        assert chart_path.name == "season_summary_2024_drivers.png"
        assert chart_path.parent == tmp_path / "charts"
        assert chart_path.exists()


class TestCountTrackInterruptions:
    """Tests for _count_track_interruptions."""

    def test_with_interruptions(self):
        """Test counting various track interruptions."""
        session = MagicMock()
        session.track_status = pd.DataFrame(
            {
                "Status": ["1", "4", "4", "6", "7", "1"],
            }
        )

        sc, vsc, rf = _count_track_interruptions(session)

        assert sc == 2
        assert vsc == 1
        assert rf == 0

    def test_no_data(self):
        """Test with DataNotLoadedError."""
        from fastf1.exceptions import DataNotLoadedError

        session = MagicMock()
        type(session).track_status = property(lambda self: (_ for _ in ()).throw(DataNotLoadedError("Not loaded")))

        sc, vsc, rf = _count_track_interruptions(session)

        assert sc == 0
        assert vsc == 0
        assert rf == 0


class TestComputeWildnessScore:
    """Tests for _compute_wildness_score."""

    def test_maximum_wildness(self):
        """Test that a race with max everything scores 1.0."""
        stats = {
            "total_overtakes": 100,
            "total_position_changes": 50,
            "average_volatility": 5.0,
            "mean_pit_stops": 2.0,
        }
        # 100 overtakes / 300 km = 0.333 per km (the max)
        score = _compute_wildness_score(
            stats,
            num_safety_cars=3,
            num_red_flags=1,
            race_distance_km=300.0,
            max_overtakes_per_km=100 / 300.0,
            max_volatility=5.0,
        )

        assert score == 1.0

    def test_minimum_wildness(self):
        """Test that a boring race scores low."""
        stats = {
            "total_overtakes": 0,
            "total_position_changes": 0,
            "average_volatility": 0.0,
            "mean_pit_stops": 1.0,
        }

        score = _compute_wildness_score(
            stats,
            num_safety_cars=0,
            num_red_flags=0,
            race_distance_km=300.0,
            max_overtakes_per_km=0.5,
            max_volatility=5.0,
        )

        assert score == 0.0

    def test_zero_max_values(self):
        """Test handling of zero max values (no division by zero)."""
        stats = {
            "total_overtakes": 0,
            "total_position_changes": 0,
            "average_volatility": 0.0,
            "mean_pit_stops": 0.0,
        }

        score = _compute_wildness_score(
            stats,
            num_safety_cars=0,
            num_red_flags=0,
            race_distance_km=0.0,
            max_overtakes_per_km=0.0,
            max_volatility=0.0,
        )

        assert score == 0.0

    def test_short_race_scores_higher_than_full_race_with_same_overtakes(self):
        """Test that a shortened race with same raw overtakes scores higher."""
        stats = {
            "total_overtakes": 40,
            "total_position_changes": 20,
            "average_volatility": 2.0,
            "mean_pit_stops": 1.0,
        }
        # Short race: 40 overtakes in 150 km = 0.267/km
        short_score = _compute_wildness_score(
            stats,
            num_safety_cars=0,
            num_red_flags=0,
            race_distance_km=150.0,
            max_overtakes_per_km=40 / 150.0,
            max_volatility=2.0,
        )
        # Full race: 40 overtakes in 300 km = 0.133/km
        full_score = _compute_wildness_score(
            stats,
            num_safety_cars=0,
            num_red_flags=0,
            race_distance_km=300.0,
            max_overtakes_per_km=40 / 150.0,
            max_volatility=2.0,
        )

        assert short_score > full_score


class TestGetSeasonSummary:
    """Tests for get_season_summary."""

    @patch("pitlane_agent.commands.fetch.season_summary.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.season_summary.load_session")
    @patch("pitlane_agent.commands.fetch.season_summary.fastf1.get_event_schedule")
    @patch("pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache")
    @patch("pitlane_agent.commands.fetch.season_summary.compute_race_summary_stats")
    def test_basic_season_summary(
        self,
        mock_compute_stats,
        mock_setup_cache,
        mock_get_schedule,
        mock_load_session,
        mock_get_circuit_length,
    ):
        """Test basic season summary with two races."""
        mock_get_circuit_length.return_value = 5.412
        # Setup schedule with 2 conventional races
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "EventName": "Bahrain Grand Prix",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
                    "EventFormat": "conventional",
                },
                {
                    "RoundNumber": 2,
                    "EventName": "Saudi Arabian Grand Prix",
                    "Country": "Saudi Arabia",
                    "EventDate": pd.Timestamp("2024-03-09"),
                    "EventFormat": "conventional",
                },
            ]
        )
        mock_get_schedule.return_value = schedule

        # Mock session loading
        mock_session = MagicMock()
        mock_session.track_status = pd.DataFrame({"Status": ["1", "1"]})
        mock_session.results = pd.DataFrame(
            {
                "Position": [1.0, 2.0, 3.0],
                "Abbreviation": ["VER", "NOR", "LEC"],
            }
        )
        mock_load_session.return_value = mock_session

        # Mock race stats - make race 2 wilder
        mock_compute_stats.side_effect = [
            {
                "total_overtakes": 20,
                "total_position_changes": 10,
                "average_volatility": 1.5,
                "mean_pit_stops": 1.5,
                "total_laps": 57,
            },
            {
                "total_overtakes": 50,
                "total_position_changes": 30,
                "average_volatility": 3.0,
                "mean_pit_stops": 2.0,
                "total_laps": 50,
            },
        ]

        result = get_season_summary(2024)

        assert result["year"] == 2024
        assert result["total_races"] == 2
        assert len(result["races"]) == 2
        # Race 2 should be ranked first (wilder)
        assert result["races"][0]["event_name"] == "Saudi Arabian Grand Prix"
        assert result["races"][1]["event_name"] == "Bahrain Grand Prix"
        # Wildness scores should be in descending order
        assert result["races"][0]["wildness_score"] >= result["races"][1]["wildness_score"]
        # Season averages should be per-lap normalized
        # Race 1: 20/57=0.351, Race 2: 50/50=1.0 → avg = 0.675 → round = 0.68
        assert result["season_averages"]["overtakes_per_lap"] == round((20 / 57 + 50 / 50) / 2, 2)
        assert result["season_averages"]["mean_pit_stops"] == 1.75
        # Podium should be extracted
        assert result["races"][0]["podium"] == ["VER", "NOR", "LEC"]
        # Circuit length should be present
        assert result["races"][0]["circuit_length_km"] == 5.412
        # All entries should be race sessions
        assert all(r["session_type"] == "R" for r in result["races"])

    @patch("pitlane_agent.commands.fetch.season_summary.load_session")
    @patch("pitlane_agent.commands.fetch.season_summary.fastf1.get_event_schedule")
    @patch("pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache")
    def test_empty_season(self, mock_setup_cache, mock_get_schedule, mock_load_session):
        """Test season with no races."""
        mock_get_schedule.return_value = pd.DataFrame(
            columns=[
                "RoundNumber",
                "EventName",
                "Country",
                "EventDate",
            ]
        )

        result = get_season_summary(2024)

        assert result["total_races"] == 0
        assert result["races"] == []

    @patch("pitlane_agent.commands.fetch.season_summary.load_session")
    @patch("pitlane_agent.commands.fetch.season_summary.fastf1.get_event_schedule")
    @patch("pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache")
    def test_skips_failed_sessions(self, mock_setup_cache, mock_get_schedule, mock_load_session):
        """Test that races that fail to load are skipped."""
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "EventName": "Bahrain Grand Prix",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
                    "EventFormat": "conventional",
                },
            ]
        )
        mock_get_schedule.return_value = schedule
        mock_load_session.side_effect = Exception("Session not found")

        result = get_season_summary(2024)

        assert result["total_races"] == 0

    @patch("pitlane_agent.commands.fetch.season_summary.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.season_summary.load_session")
    @patch("pitlane_agent.commands.fetch.season_summary.fastf1.get_event_schedule")
    @patch("pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache")
    @patch("pitlane_agent.commands.fetch.season_summary.compute_race_summary_stats")
    def test_skips_round_zero(
        self,
        mock_compute_stats,
        mock_setup_cache,
        mock_get_schedule,
        mock_load_session,
        mock_get_circuit_length,
    ):
        """Test that testing events (round 0) are skipped."""
        mock_get_circuit_length.return_value = 5.412
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 0,
                    "EventName": "Pre-Season Testing",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-02-20"),
                    "EventFormat": "conventional",
                },
                {
                    "RoundNumber": 1,
                    "EventName": "Bahrain Grand Prix",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
                    "EventFormat": "conventional",
                },
            ]
        )
        mock_get_schedule.return_value = schedule

        mock_session = MagicMock()
        mock_session.track_status = pd.DataFrame({"Status": ["1"]})
        mock_session.results = pd.DataFrame(
            {
                "Position": [1.0, 2.0, 3.0],
                "Abbreviation": ["VER", "NOR", "LEC"],
            }
        )
        mock_load_session.return_value = mock_session

        mock_compute_stats.return_value = {
            "total_overtakes": 30,
            "total_position_changes": 15,
            "average_volatility": 2.0,
            "mean_pit_stops": 1.5,
            "total_laps": 57,
        }

        result = get_season_summary(2024)

        assert result["total_races"] == 1
        assert result["races"][0]["event_name"] == "Bahrain Grand Prix"
        assert result["races"][0]["session_type"] == "R"
        # load_session should only be called once (for round 1, not round 0)
        mock_load_session.assert_called_once()

    @patch("pitlane_agent.commands.fetch.season_summary.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.season_summary.load_session")
    @patch("pitlane_agent.commands.fetch.season_summary.fastf1.get_event_schedule")
    @patch("pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache")
    @patch("pitlane_agent.commands.fetch.season_summary.compute_race_summary_stats")
    def test_sprint_weekend_produces_two_entries(
        self,
        mock_compute_stats,
        mock_setup_cache,
        mock_get_schedule,
        mock_load_session,
        mock_get_circuit_length,
    ):
        """Test that a sprint weekend produces both R and S entries."""
        mock_get_circuit_length.return_value = 5.451
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "EventName": "Chinese Grand Prix",
                    "Country": "China",
                    "EventDate": pd.Timestamp("2024-04-21"),
                    "EventFormat": "sprint_qualifying",
                },
            ]
        )
        mock_get_schedule.return_value = schedule

        mock_session = MagicMock()
        mock_session.track_status = pd.DataFrame({"Status": ["1"]})
        mock_session.results = pd.DataFrame(
            {
                "Position": [1.0, 2.0, 3.0],
                "Abbreviation": ["VER", "NOR", "LEC"],
            }
        )
        mock_load_session.return_value = mock_session

        mock_compute_stats.return_value = {
            "total_overtakes": 25,
            "total_position_changes": 12,
            "average_volatility": 2.0,
            "mean_pit_stops": 1.0,
            "total_laps": 56,
        }

        result = get_season_summary(2024)

        assert result["total_races"] == 2
        session_types = {r["session_type"] for r in result["races"]}
        assert session_types == {"R", "S"}
        # Both entries should be for the same event
        assert all(r["event_name"] == "Chinese Grand Prix" for r in result["races"])
        # load_session should be called twice (R and S)
        assert mock_load_session.call_count == 2

    @patch("pitlane_agent.commands.fetch.season_summary.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.season_summary.load_session")
    @patch("pitlane_agent.commands.fetch.season_summary.fastf1.get_event_schedule")
    @patch("pitlane_agent.commands.fetch.season_summary.setup_fastf1_cache")
    @patch("pitlane_agent.commands.fetch.season_summary.compute_race_summary_stats")
    def test_sprint_density_compared_against_race(
        self,
        mock_compute_stats,
        mock_setup_cache,
        mock_get_schedule,
        mock_load_session,
        mock_get_circuit_length,
    ):
        """Test that sprint and race wildness are normalized by overtake density.

        With density-based normalization, sprints and races share a single
        max.  A sprint with the same overtakes-per-lap as the race should
        score equally on the overtakes component.
        """
        mock_get_circuit_length.return_value = 5.451
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "EventName": "Chinese Grand Prix",
                    "Country": "China",
                    "EventDate": pd.Timestamp("2024-04-21"),
                    "EventFormat": "sprint_qualifying",
                },
            ]
        )
        mock_get_schedule.return_value = schedule

        mock_session = MagicMock()
        mock_session.track_status = pd.DataFrame({"Status": ["1"]})
        mock_session.results = pd.DataFrame(
            {
                "Position": [1.0, 2.0, 3.0],
                "Abbreviation": ["VER", "NOR", "LEC"],
            }
        )
        mock_load_session.return_value = mock_session

        # Give the sprint the same overtakes-per-lap as the race so both
        # should receive the same overtake density component.
        # Race: 56 overtakes / 56 laps = 1.0/lap
        # Sprint: 20 overtakes / 20 laps = 1.0/lap
        race_stats = {
            "total_overtakes": 56,
            "total_position_changes": 30,
            "average_volatility": 3.0,
            "mean_pit_stops": 2.0,
            "total_laps": 56,
        }
        sprint_stats = {
            "total_overtakes": 20,
            "total_position_changes": 8,
            "average_volatility": 3.0,
            "mean_pit_stops": 0.0,
            "total_laps": 20,
        }
        # R is loaded first, then S
        mock_compute_stats.side_effect = [race_stats, sprint_stats]

        result = get_season_summary(2024)

        race_entry = next(r for r in result["races"] if r["session_type"] == "R")
        sprint_entry = next(r for r in result["races"] if r["session_type"] == "S")

        # Both have the same overtakes/lap and same volatility, so both
        # should score identically: 0.4*1 + 0.3*1 + 0.2*0 + 0.1*0 = 0.7
        assert race_entry["wildness_score"] == 0.7
        assert sprint_entry["wildness_score"] == 0.7
