"""Tests for season_summary command."""

from unittest.mock import MagicMock, patch

import pandas as pd
from pitlane_agent.commands.fetch.season_summary import (
    _compute_wildness_score,
    _count_track_interruptions,
    get_season_summary,
)


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

        score = _compute_wildness_score(
            stats, num_safety_cars=3, num_red_flags=1, max_overtakes=100, max_volatility=5.0
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
            stats, num_safety_cars=0, num_red_flags=0, max_overtakes=100, max_volatility=5.0
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

        score = _compute_wildness_score(stats, num_safety_cars=0, num_red_flags=0, max_overtakes=0, max_volatility=0.0)

        assert score == 0.0


class TestGetSeasonSummary:
    """Tests for get_season_summary."""

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
    ):
        """Test basic season summary with two races."""
        # Setup schedule with 2 races
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "EventName": "Bahrain Grand Prix",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
                },
                {
                    "RoundNumber": 2,
                    "EventName": "Saudi Arabian Grand Prix",
                    "Country": "Saudi Arabia",
                    "EventDate": pd.Timestamp("2024-03-09"),
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
            },
            {
                "total_overtakes": 50,
                "total_position_changes": 30,
                "average_volatility": 3.0,
                "mean_pit_stops": 2.0,
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
        # Season averages should be computed
        assert result["season_averages"]["total_overtakes"] == 35
        assert result["season_averages"]["mean_pit_stops"] == 1.75
        # Podium should be extracted
        assert result["races"][0]["podium"] == ["VER", "NOR", "LEC"]

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
                },
            ]
        )
        mock_get_schedule.return_value = schedule
        mock_load_session.side_effect = Exception("Session not found")

        result = get_season_summary(2024)

        assert result["total_races"] == 0

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
    ):
        """Test that testing events (round 0) are skipped."""
        schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 0,
                    "EventName": "Pre-Season Testing",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-02-20"),
                },
                {
                    "RoundNumber": 1,
                    "EventName": "Bahrain Grand Prix",
                    "Country": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
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
        }

        result = get_season_summary(2024)

        assert result["total_races"] == 1
        assert result["races"][0]["event_name"] == "Bahrain Grand Prix"
        # load_session should only be called once (for round 1, not round 0)
        mock_load_session.assert_called_once()
