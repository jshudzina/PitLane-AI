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
# Shared helpers for analyze tests
# ---------------------------------------------------------------------------


def _make_ff1_results(rows: list[dict]) -> pd.DataFrame:
    """Make a minimal FastF1 results DataFrame."""
    defaults = {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0}
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _make_ff1_schedule(events: list[dict]) -> pd.DataFrame:
    """Make a minimal FastF1 schedule DataFrame."""
    defaults = {"RoundNumber": 1, "EventName": "Bahrain Grand Prix", "EventFormat": "conventional"}
    return pd.DataFrame([{**defaults, **e} for e in events])


def _make_session_mock(results: pd.DataFrame) -> MagicMock:
    session = MagicMock()
    session.results = results
    return session


# ---------------------------------------------------------------------------
# _fetch_per_round_points tests
# ---------------------------------------------------------------------------


class TestFetchPerRoundPoints:
    """Unit tests for _fetch_per_round_points."""

    def test_basic_driver_aggregation(self, monkeypatch):
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = _make_ff1_schedule(
            [
                {"RoundNumber": 1, "EventName": "Bahrain Grand Prix"},
                {"RoundNumber": 2, "EventName": "Saudi Arabian Grand Prix"},
            ]
        )
        results_r1 = _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0},
                {"Abbreviation": "LEC", "TeamName": "Ferrari", "Points": 18.0},
            ]
        )
        results_r2 = _make_ff1_results(
            [
                {"Abbreviation": "LEC", "TeamName": "Ferrari", "Points": 25.0},
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 18.0},
            ]
        )

        call_count = {"n": 0}

        def fake_get_session(year, event_name, session_type):
            call_count["n"] += 1
            if "Bahrain" in event_name:
                return _make_session_mock(results_r1)
            return _make_session_mock(results_r2)

        monkeypatch.setattr("pitlane_agent.commands.analyze.season_summary.fastf1.get_session", fake_get_session)

        points_df, total_points, short_names = _fetch_per_round_points(2024, schedule, "drivers")

        assert set(points_df.index) == {"VER", "LEC"}
        assert list(points_df.columns) == [1, 2]
        assert points_df.at["VER", 1] == 25.0
        assert points_df.at["VER", 2] == 18.0
        assert points_df.at["LEC", 1] == 18.0
        assert points_df.at["LEC", 2] == 25.0
        assert total_points["VER"] == 43.0
        assert total_points["LEC"] == 43.0
        assert short_names == ["Bahrain", "Saudi Arabian"]

    def test_sorted_ascending_by_total(self, monkeypatch):
        """Champion (most points) should be last in the ascending-sorted index."""
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = _make_ff1_schedule([{"RoundNumber": 1, "EventName": "Bahrain Grand Prix"}])
        results = _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0},
                {"Abbreviation": "HAM", "TeamName": "Mercedes", "Points": 12.0},
            ]
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.fastf1.get_session",
            lambda *a: _make_session_mock(results),
        )

        points_df, total_points, _ = _fetch_per_round_points(2024, schedule, "drivers")

        # Ascending sort: lowest points first, highest (champion) last
        assert list(total_points.index)[-1] == "VER"
        assert list(total_points.index)[0] == "HAM"

    def test_sprint_points_added(self, monkeypatch):
        """Sprint qualifying points are added to race points for the same round."""
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = _make_ff1_schedule(
            [
                {"RoundNumber": 1, "EventName": "Chinese Grand Prix", "EventFormat": "sprint_qualifying"},
            ]
        )
        race_results = _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0},
            ]
        )
        sprint_results = _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 8.0},
            ]
        )

        def fake_get_session(year, event_name, session_type):
            if session_type == "R":
                return _make_session_mock(race_results)
            return _make_session_mock(sprint_results)

        monkeypatch.setattr("pitlane_agent.commands.analyze.season_summary.fastf1.get_session", fake_get_session)

        points_df, total_points, _ = _fetch_per_round_points(2024, schedule, "drivers")

        assert points_df.at["VER", 1] == 33.0
        assert total_points["VER"] == 33.0

    def test_constructors_sums_driver_points(self, monkeypatch):
        """Constructor mode sums both drivers' points per team per round."""
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = _make_ff1_schedule([{"RoundNumber": 1, "EventName": "Bahrain Grand Prix"}])
        results = _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0},
                {"Abbreviation": "PER", "TeamName": "Red Bull Racing", "Points": 18.0},
                {"Abbreviation": "LEC", "TeamName": "Ferrari", "Points": 15.0},
            ]
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.fastf1.get_session",
            lambda *a: _make_session_mock(results),
        )

        points_df, total_points, _ = _fetch_per_round_points(2024, schedule, "constructors")

        assert points_df.at["Red Bull Racing", 1] == 43.0
        assert points_df.at["Ferrari", 1] == 15.0

    def test_round_zero_is_skipped(self, monkeypatch):
        """Events with RoundNumber == 0 (testing) must not produce rows."""
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = _make_ff1_schedule(
            [
                {"RoundNumber": 0, "EventName": "Pre-Season Testing"},
                {"RoundNumber": 1, "EventName": "Bahrain Grand Prix"},
            ]
        )
        results = _make_ff1_results([{"Abbreviation": "VER", "Points": 25.0}])
        call_log: list[str] = []

        def fake_get_session(year, event_name, session_type):
            call_log.append(event_name)
            return _make_session_mock(results)

        monkeypatch.setattr("pitlane_agent.commands.analyze.season_summary.fastf1.get_session", fake_get_session)

        _fetch_per_round_points(2024, schedule, "drivers")

        assert all("Testing" not in name for name in call_log)

    def test_failed_session_load_is_skipped(self, monkeypatch):
        """If FastF1 raises for a round, that round is skipped gracefully."""
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = _make_ff1_schedule(
            [
                {"RoundNumber": 1, "EventName": "Bahrain Grand Prix"},
                {"RoundNumber": 2, "EventName": "Saudi Arabian Grand Prix"},
            ]
        )
        results_r2 = _make_ff1_results([{"Abbreviation": "VER", "Points": 25.0}])

        def fake_get_session(year, event_name, session_type):
            if "Bahrain" in event_name:
                raise RuntimeError("Session not found")
            return _make_session_mock(results_r2)

        monkeypatch.setattr("pitlane_agent.commands.analyze.season_summary.fastf1.get_session", fake_get_session)

        points_df, total_points, _ = _fetch_per_round_points(2024, schedule, "drivers")

        assert list(points_df.columns) == [2]
        assert points_df.at["VER", 2] == 25.0

    def test_empty_schedule_returns_empty(self, monkeypatch):
        """An empty schedule yields empty DataFrames."""
        from pitlane_agent.commands.analyze.season_summary import _fetch_per_round_points

        schedule = pd.DataFrame(columns=["RoundNumber", "EventName", "EventFormat"])
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.fastf1.get_session",
            lambda *a: (_ for _ in ()).throw(AssertionError("should not be called")),
        )

        points_df, total_points, short_names = _fetch_per_round_points(2024, schedule, "drivers")

        assert points_df.empty
        assert total_points.empty
        assert short_names == []


# ---------------------------------------------------------------------------
# generate_season_summary_chart tests
# ---------------------------------------------------------------------------


class TestGenerateSeasonSummaryChart:
    """Tests for generate_season_summary_chart using mocked FastF1."""

    def _setup_patches(self, monkeypatch, schedule: pd.DataFrame, session_factory):
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.fastf1.get_event_schedule",
            lambda year, **kw: schedule,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.fastf1.get_session",
            session_factory,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.setup_fastf1_cache",
            lambda: None,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.setup_plot_style",
            lambda: None,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.save_figure",
            lambda fig, path, **kw: (path.parent.mkdir(parents=True, exist_ok=True), path.touch()),
        )

    def _single_round_schedule(self) -> pd.DataFrame:
        return _make_ff1_schedule([{"RoundNumber": 1, "EventName": "Bahrain Grand Prix"}])

    def _single_round_results(self) -> pd.DataFrame:
        return _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0},
                {"Abbreviation": "LEC", "TeamName": "Ferrari", "Points": 18.0},
            ]
        )

    def test_returns_required_keys(self, monkeypatch, tmp_path):
        schedule = self._single_round_schedule()
        self._setup_patches(
            monkeypatch,
            schedule,
            lambda *a: _make_session_mock(self._single_round_results()),
        )

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

    def test_invalid_type_raises(self, tmp_path):
        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        with pytest.raises(ValueError, match="Invalid summary_type"):
            generate_season_summary_chart(year=2024, summary_type="teams", workspace_dir=tmp_path)

    def test_no_data_raises(self, monkeypatch, tmp_path):
        """Empty schedule → no FastF1 data → ValueError."""
        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.fastf1.get_event_schedule",
            lambda year, **kw: pd.DataFrame(columns=["RoundNumber", "EventName", "EventFormat"]),
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.analyze.season_summary.setup_fastf1_cache",
            lambda: None,
        )

        with pytest.raises(ValueError, match="No standings data"):
            generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

    def test_partial_season_marked_incomplete(self, monkeypatch, tmp_path):
        schedule = _make_ff1_schedule(
            [
                {"RoundNumber": 1, "EventName": "Bahrain Grand Prix"},
                {"RoundNumber": 2, "EventName": "Saudi Arabian Grand Prix"},
                {"RoundNumber": 3, "EventName": "Australian Grand Prix"},
            ]
        )
        # Only round 1 returns data; rounds 2 and 3 raise
        results_r1 = _make_ff1_results([{"Abbreviation": "VER", "Points": 25.0}])

        def fake_get_session(year, event_name, session_type):
            if "Bahrain" in event_name:
                return _make_session_mock(results_r1)
            raise RuntimeError("not available")

        self._setup_patches(monkeypatch, schedule, fake_get_session)

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        assert result["season_complete"] is False
        assert result["analysis_round"] == 1
        assert result["total_races"] == 3

    def test_complete_season_flagged(self, monkeypatch, tmp_path):
        schedule = self._single_round_schedule()
        self._setup_patches(
            monkeypatch,
            schedule,
            lambda *a: _make_session_mock(self._single_round_results()),
        )

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        assert result["season_complete"] is True
        assert result["total_races"] == 1

    def test_leader_is_points_leader(self, monkeypatch, tmp_path):
        schedule = self._single_round_schedule()
        self._setup_patches(
            monkeypatch,
            schedule,
            lambda *a: _make_session_mock(self._single_round_results()),
        )

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        leader = result["leader"]
        assert leader["name"] == "VER"
        assert leader["points"] == 25.0
        assert leader["position"] == 1

    def test_statistics_contains_all_competitors(self, monkeypatch, tmp_path):
        schedule = self._single_round_schedule()
        self._setup_patches(
            monkeypatch,
            schedule,
            lambda *a: _make_session_mock(self._single_round_results()),
        )

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        stats = result["statistics"]
        assert stats["total_competitors"] == 2
        names = {c["name"] for c in stats["competitors"]}
        assert names == {"VER", "LEC"}
        positions = {c["championship_position"] for c in stats["competitors"]}
        assert positions == {1, 2}

    def test_chart_file_written_to_workspace(self, monkeypatch, tmp_path):
        schedule = self._single_round_schedule()
        self._setup_patches(
            monkeypatch,
            schedule,
            lambda *a: _make_session_mock(self._single_round_results()),
        )

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="drivers", workspace_dir=tmp_path)

        chart_path = Path(result["chart_path"])
        assert chart_path.name == "season_summary_2024_drivers.png"
        assert chart_path.parent == tmp_path / "charts"
        assert chart_path.exists()

    def test_constructors_type(self, monkeypatch, tmp_path):
        schedule = self._single_round_schedule()
        results = _make_ff1_results(
            [
                {"Abbreviation": "VER", "TeamName": "Red Bull Racing", "Points": 25.0},
                {"Abbreviation": "PER", "TeamName": "Red Bull Racing", "Points": 18.0},
                {"Abbreviation": "LEC", "TeamName": "Ferrari", "Points": 15.0},
            ]
        )
        self._setup_patches(monkeypatch, schedule, lambda *a: _make_session_mock(results))

        from pitlane_agent.commands.analyze.season_summary import generate_season_summary_chart

        result = generate_season_summary_chart(year=2024, summary_type="constructors", workspace_dir=tmp_path)

        assert result["summary_type"] == "constructors"
        assert result["leader"]["name"] == "Red Bull Racing"
        assert result["leader"]["points"] == 43.0
        chart_path = Path(result["chart_path"])
        assert chart_path.name == "season_summary_2024_constructors.png"


# ---------------------------------------------------------------------------
# fetch/season_summary.py tests (unchanged)
# ---------------------------------------------------------------------------


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
