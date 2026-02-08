"""Tests for championship_possibilities command."""

from unittest.mock import MagicMock, patch

import pytest
from pitlane_agent.commands.analyze.championship_possibilities import (
    _calculate_championship_scenarios,
    _calculate_max_points_available,
    _count_remaining_races,
    generate_championship_possibilities_chart,
)


class TestChampionshipPossibilitiesHelpers:
    """Unit tests for helper functions."""

    def test_calculate_max_points_available(self):
        """Test maximum points calculation."""
        # 2024 and earlier: 26 points per race (win + fastest lap), 8 per sprint
        assert _calculate_max_points_available(5, 0, 2024) == 130  # 5 races * 26
        assert _calculate_max_points_available(3, 2, 2024) == 94  # (3 * 26) + (2 * 8)
        assert _calculate_max_points_available(0, 0, 2024) == 0

        # 2025 onwards: 25 points per race (no fastest lap), 8 per sprint
        assert _calculate_max_points_available(5, 0, 2025) == 125  # 5 races * 25
        assert _calculate_max_points_available(5, 0, 2026) == 125  # 5 races * 25
        assert _calculate_max_points_available(3, 2, 2025) == 91  # (3 * 25) + (2 * 8)

    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    def test_count_remaining_races(self, mock_get_schedule):
        """Test counting remaining races and sprints."""
        # Mock schedule with mix of race and sprint weekends
        mock_get_schedule.return_value = {
            "events": [
                {
                    "round": 10,
                    "sessions": [
                        {"name": "Practice 1"},
                        {"name": "Qualifying"},
                        {"name": "Race"},
                    ],
                },
                {
                    "round": 11,
                    "sessions": [
                        {"name": "Practice 1"},
                        {"name": "Qualifying"},
                        {"name": "Sprint"},
                        {"name": "Race"},
                    ],
                },
                {
                    "round": 12,
                    "sessions": [
                        {"name": "Practice 1"},
                        {"name": "Qualifying"},
                        {"name": "Race"},
                    ],
                },
            ]
        }

        remaining_races, remaining_sprints = _count_remaining_races(2024, 9)

        assert remaining_races == 3
        assert remaining_sprints == 1
        mock_get_schedule.assert_called_once_with(2024, include_testing=False)

    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    def test_count_remaining_races_season_complete(self, mock_get_schedule):
        """Test counting when season is complete."""
        mock_get_schedule.return_value = {
            "events": [
                {
                    "round": 10,
                    "sessions": [{"name": "Race"}],
                }
            ]
        }

        remaining_races, remaining_sprints = _count_remaining_races(2024, 24)

        assert remaining_races == 0
        assert remaining_sprints == 0

    def test_calculate_championship_scenarios_early_season(self):
        """Test scenarios when many drivers can still win."""
        standings = [
            {"position": 1, "points": 100.0, "full_name": "Driver A"},
            {"position": 2, "points": 90.0, "full_name": "Driver B"},
            {"position": 3, "points": 85.0, "full_name": "Driver C"},
        ]
        max_points = 260  # 10 races remaining

        stats, leader = _calculate_championship_scenarios(standings, max_points, "drivers")

        assert leader["name"] == "Driver A"
        assert leader["points"] == 100.0
        assert len(stats) == 3

        # All should be able to win
        assert all(s["can_win"] for s in stats)
        assert stats[0]["required_scenario"] == "Leading the championship"
        assert "points more than leader" in stats[1]["required_scenario"]

    def test_calculate_championship_scenarios_late_season(self):
        """Test scenarios when leader has unassailable lead."""
        standings = [
            {"position": 1, "points": 400.0, "full_name": "Driver A"},
            {"position": 2, "points": 350.0, "full_name": "Driver B"},
            {"position": 3, "points": 300.0, "full_name": "Driver C"},
        ]
        max_points = 26  # 1 race remaining

        stats, leader = _calculate_championship_scenarios(standings, max_points, "drivers")

        # Leader and maybe second place can win
        assert stats[0]["can_win"] is True  # Leader
        assert stats[1]["can_win"] is False  # 350 + 26 = 376 < 400
        assert stats[2]["can_win"] is False  # 300 + 26 = 326 < 400

    def test_calculate_championship_scenarios_constructors(self):
        """Test scenarios for constructors championship."""
        standings = [
            {"position": 1, "points": 500.0, "constructor_name": "Team A"},
            {"position": 2, "points": 480.0, "constructor_name": "Team B"},
        ]
        max_points = 130  # 5 races

        stats, leader = _calculate_championship_scenarios(standings, max_points, "constructors")

        assert leader["name"] == "Team A"
        assert stats[0]["name"] == "Team A"
        assert stats[1]["name"] == "Team B"
        assert stats[1]["can_win"] is True  # 480 + 130 = 610 > 500


class TestChampionshipPossibilitiesBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.analyze.championship_possibilities.plt")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_driver_standings")
    def test_generate_chart_drivers_success(self, mock_get_standings, mock_get_schedule, mock_plt, tmp_output_dir):
        """Test successful chart generation for drivers championship."""
        # Mock driver standings
        mock_get_standings.return_value = {
            "year": 2024,
            "round": 18,
            "standings": [
                {
                    "position": 1,
                    "points": 350.0,
                    "full_name": "Max Verstappen",
                },
                {
                    "position": 2,
                    "points": 310.0,
                    "full_name": "Lando Norris",
                },
                {
                    "position": 3,
                    "points": 290.0,
                    "full_name": "Charles Leclerc",
                },
            ],
        }

        # Mock event schedule - 6 races remaining, 1 sprint
        mock_get_schedule.return_value = {
            "events": [
                {
                    "round": 19,
                    "sessions": [{"name": "Race"}],
                },
                {
                    "round": 20,
                    "sessions": [{"name": "Sprint"}, {"name": "Race"}],
                },
                {
                    "round": 21,
                    "sessions": [{"name": "Race"}],
                },
                {
                    "round": 22,
                    "sessions": [{"name": "Race"}],
                },
                {
                    "round": 23,
                    "sessions": [{"name": "Race"}],
                },
                {
                    "round": 24,
                    "sessions": [{"name": "Race"}],
                },
            ]
        }

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Generate chart
        result = generate_championship_possibilities_chart(
            year=2024,
            championship="drivers",
            workspace_dir=tmp_output_dir,
        )

        # Verify result structure
        assert result["year"] == 2024
        assert result["championship_type"] == "drivers"
        assert result["analysis_round"] == 18
        assert result["remaining_races"] == 6
        assert result["remaining_sprints"] == 1
        assert result["max_points_available"] == 164  # (6 * 26) + (1 * 8)

        # Verify leader info
        assert result["leader"]["name"] == "Max Verstappen"
        assert result["leader"]["points"] == 350.0

        # Verify statistics
        stats = result["statistics"]
        assert stats["total_competitors"] == 3
        assert stats["still_possible"] >= 1  # At least the leader
        assert len(stats["competitors"]) == 3

        # Verify chart path
        assert "championship_possibilities_2024_drivers.png" in result["chart_path"]

        # Verify mocks were called
        mock_get_standings.assert_called_once_with(2024, round_number=None)
        mock_get_schedule.assert_called_once_with(2024, include_testing=False)

    @patch("pitlane_agent.commands.analyze.championship_possibilities.plt")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_constructor_standings")
    def test_generate_chart_constructors_success(self, mock_get_standings, mock_get_schedule, mock_plt, tmp_output_dir):
        """Test successful chart generation for constructors championship."""
        # Mock constructor standings
        mock_get_standings.return_value = {
            "year": 2024,
            "round": 20,
            "standings": [
                {
                    "position": 1,
                    "points": 600.0,
                    "constructor_name": "McLaren",
                },
                {
                    "position": 2,
                    "points": 580.0,
                    "constructor_name": "Ferrari",
                },
            ],
        }

        # Mock event schedule
        mock_get_schedule.return_value = {
            "events": [
                {"round": 21, "sessions": [{"name": "Race"}]},
                {"round": 22, "sessions": [{"name": "Race"}]},
            ]
        }

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Generate chart
        result = generate_championship_possibilities_chart(
            year=2024,
            championship="constructors",
            workspace_dir=tmp_output_dir,
        )

        # Verify result
        assert result["championship_type"] == "constructors"
        assert result["leader"]["name"] == "McLaren"
        assert "championship_possibilities_2024_constructors.png" in result["chart_path"]

        # Verify correct fetch function was called
        mock_get_standings.assert_called_once_with(2024, round_number=None)

    @patch("pitlane_agent.commands.analyze.championship_possibilities.plt")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_driver_standings")
    def test_generate_chart_2026_no_fastest_lap_point(
        self, mock_get_standings, mock_get_schedule, mock_plt, tmp_output_dir
    ):
        """Test chart generation for 2026 (no fastest lap point)."""
        # Mock driver standings for 2026
        mock_get_standings.return_value = {
            "year": 2026,
            "round": 10,
            "standings": [
                {"position": 1, "points": 200.0, "full_name": "Driver A"},
                {"position": 2, "points": 180.0, "full_name": "Driver B"},
            ],
        }

        # Mock event schedule - 5 races remaining, 1 sprint
        mock_get_schedule.return_value = {
            "events": [
                {"round": 11, "sessions": [{"name": "Race"}]},
                {"round": 12, "sessions": [{"name": "Sprint"}, {"name": "Race"}]},
                {"round": 13, "sessions": [{"name": "Race"}]},
                {"round": 14, "sessions": [{"name": "Race"}]},
                {"round": 15, "sessions": [{"name": "Race"}]},
            ]
        }

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Generate chart
        result = generate_championship_possibilities_chart(
            year=2026,
            championship="drivers",
            workspace_dir=tmp_output_dir,
        )

        # Verify 2026 uses 25 points per race (no fastest lap)
        # 5 races * 25 + 1 sprint * 8 = 125 + 8 = 133
        assert result["year"] == 2026
        assert result["remaining_races"] == 5
        assert result["remaining_sprints"] == 1
        assert result["max_points_available"] == 133  # (5 * 25) + (1 * 8)

    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_driver_standings")
    def test_generate_chart_no_standings_data(self, mock_get_standings, tmp_output_dir):
        """Test error handling when no standings data available."""
        mock_get_standings.return_value = {"year": 2024, "round": 1, "standings": []}

        with pytest.raises(ValueError, match="No standings data available"):
            generate_championship_possibilities_chart(
                year=2024,
                championship="drivers",
                workspace_dir=tmp_output_dir,
            )

    def test_generate_chart_invalid_championship_type(self, tmp_output_dir):
        """Test error handling for invalid championship type."""
        with pytest.raises(ValueError, match="Invalid championship type"):
            generate_championship_possibilities_chart(
                year=2024,
                championship="invalid",
                workspace_dir=tmp_output_dir,
            )

    def test_generate_chart_invalid_after_round_negative(self, tmp_output_dir):
        """Test error handling for negative after_round parameter."""
        with pytest.raises(ValueError, match="after_round must be a positive integer"):
            generate_championship_possibilities_chart(
                year=2024,
                championship="drivers",
                workspace_dir=tmp_output_dir,
                after_round=-1,
            )

    def test_generate_chart_invalid_after_round_zero(self, tmp_output_dir):
        """Test error handling for zero after_round parameter."""
        with pytest.raises(ValueError, match="after_round must be a positive integer"):
            generate_championship_possibilities_chart(
                year=2024,
                championship="drivers",
                workspace_dir=tmp_output_dir,
                after_round=0,
            )

    @patch("pitlane_agent.commands.analyze.championship_possibilities.plt")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_driver_standings")
    def test_generate_chart_season_complete(self, mock_get_standings, mock_get_schedule, mock_plt, tmp_output_dir):
        """Test chart generation when season is complete."""
        # Mock driver standings (season over)
        mock_get_standings.return_value = {
            "year": 2024,
            "round": 24,  # Final round
            "standings": [
                {"position": 1, "points": 437.0, "full_name": "Max Verstappen"},
                {"position": 2, "points": 374.0, "full_name": "Lando Norris"},
            ],
        }

        # No remaining races
        mock_get_schedule.return_value = {"events": []}

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Generate chart
        result = generate_championship_possibilities_chart(
            year=2024,
            championship="drivers",
            workspace_dir=tmp_output_dir,
        )

        # Verify results
        assert result["remaining_races"] == 0
        assert result["remaining_sprints"] == 0
        assert result["max_points_available"] == 0

        # When season is complete, nobody can "still win" - championship is decided
        stats = result["statistics"]
        assert stats["still_possible"] == 0
        assert stats["eliminated"] == 2

    @patch("pitlane_agent.commands.analyze.championship_possibilities.plt")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_event_schedule")
    @patch("pitlane_agent.commands.analyze.championship_possibilities.get_driver_standings")
    def test_generate_chart_with_after_round(self, mock_get_standings, mock_get_schedule, mock_plt, tmp_output_dir):
        """Test chart generation with after_round parameter for historical analysis."""
        # Mock driver standings after round 10
        mock_get_standings.return_value = {
            "year": 2024,
            "round": 10,
            "standings": [
                {"position": 1, "points": 200.0, "full_name": "Max Verstappen"},
                {"position": 2, "points": 180.0, "full_name": "Lando Norris"},
                {"position": 3, "points": 170.0, "full_name": "Charles Leclerc"},
            ],
        }

        # Mock event schedule with 14 races remaining after round 10
        mock_get_schedule.return_value = {
            "events": [
                {"round": 11, "sessions": [{"name": "Race"}]},
                {"round": 12, "sessions": [{"name": "Sprint"}, {"name": "Race"}]},
                {"round": 13, "sessions": [{"name": "Race"}]},
                {"round": 14, "sessions": [{"name": "Race"}]},
                {"round": 15, "sessions": [{"name": "Race"}]},
                {"round": 16, "sessions": [{"name": "Race"}]},
                {"round": 17, "sessions": [{"name": "Race"}]},
                {"round": 18, "sessions": [{"name": "Race"}]},
                {"round": 19, "sessions": [{"name": "Race"}]},
                {"round": 20, "sessions": [{"name": "Race"}]},
                {"round": 21, "sessions": [{"name": "Race"}]},
                {"round": 22, "sessions": [{"name": "Race"}]},
                {"round": 23, "sessions": [{"name": "Race"}]},
                {"round": 24, "sessions": [{"name": "Race"}]},
            ]
        }

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Generate chart with after_round parameter
        result = generate_championship_possibilities_chart(
            year=2024,
            championship="drivers",
            workspace_dir=tmp_output_dir,
            after_round=10,
        )

        # Verify result structure
        assert result["year"] == 2024
        assert result["championship_type"] == "drivers"
        assert result["analysis_round"] == 10
        assert result["remaining_races"] == 14
        assert result["remaining_sprints"] == 1

        # Verify chart filename includes round number
        assert "championship_possibilities_2024_drivers_round_10.png" in result["chart_path"]

        # Verify mocks were called with correct parameters
        mock_get_standings.assert_called_once_with(2024, round_number=10)
        mock_get_schedule.assert_called_once_with(2024, include_testing=False)
