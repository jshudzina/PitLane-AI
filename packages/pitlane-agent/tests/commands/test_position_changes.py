"""Tests for position_changes command."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.analyze.position_changes import (
    generate_position_changes_chart,
    setup_plot_style,
)


class TestPositionChangesBusinessLogic:
    """Unit tests for business logic functions."""

    def test_setup_plot_style(self):
        """Test plot style configuration."""
        # Test that setup_plot_style doesn't raise errors
        setup_plot_style()

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_success(self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session):
        """Test successful chart generation with position data."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        # Mock drivers
        mock_fastf1_session.drivers = [33, 44]
        mock_fastf1_session.get_driver.side_effect = [
            {"Abbreviation": "VER"},
            {"Abbreviation": "HAM"},
        ]

        # Mock laps data with position changes
        mock_laps_ver = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 2, "PitOutTime": pd.NaT},
                {"LapNumber": 2, "Position": 1, "PitOutTime": pd.NaT},
                {"LapNumber": 3, "Position": 1, "PitOutTime": pd.NaT},
            ]
        )
        mock_laps_ham = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 1, "PitOutTime": pd.NaT},
                {"LapNumber": 2, "Position": 2, "PitOutTime": pd.NaT},
                {"LapNumber": 3, "Position": 2, "PitOutTime": pd.NaT},
            ]
        )

        def mock_pick_driver(driver):
            if driver == "VER":
                return mock_laps_ver
            return mock_laps_ham

        mock_fastf1_session.laps.pick_driver.side_effect = mock_pick_driver

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)  # Inverted axis

        # Mock driver colors
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function
        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=None,
            top_n=None,
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert "statistics" in result
        assert "total_overtakes" in result["statistics"]
        assert len(result["drivers_plotted"]) == 2
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "position_changes_2024_monaco_R_all.png")

        # Verify FastF1 was called correctly
        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "R")
        mock_fastf1_session.load.assert_called_once()

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_with_drivers_filter(
        self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test chart generation with specific drivers."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 1, "PitOutTime": pd.NaT},
                {"LapNumber": 2, "Position": 1, "PitOutTime": pd.NaT},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=["VER"],
            top_n=None,
            workspace_dir=tmp_output_dir,
        )

        # Verify filename includes driver abbreviation
        assert "VER" in result["chart_path"]

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_with_top_n(
        self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test chart generation with top N filter."""
        mock_fastf1.get_session.return_value = mock_fastf1_session

        # Mock top 3 finishers
        mock_fastf1_session.drivers = [33, 44, 16]
        mock_fastf1_session.get_driver.side_effect = [
            {"Abbreviation": "VER"},
            {"Abbreviation": "HAM"},
            {"Abbreviation": "LEC"},
        ]

        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 1, "PitOutTime": pd.NaT},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=None,
            top_n=3,
            workspace_dir=tmp_output_dir,
        )

        # Verify filename includes top3
        assert "top3" in result["chart_path"]

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_with_pit_stops(
        self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test chart marks pit stops correctly."""
        mock_fastf1.get_session.return_value = mock_fastf1_session
        mock_fastf1_session.drivers = [33]
        mock_fastf1_session.get_driver.return_value = {"Abbreviation": "VER"}

        # Mock laps with a pit stop
        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 1, "PitOutTime": pd.NaT},
                {"LapNumber": 2, "Position": 5, "PitOutTime": pd.Timestamp("2024-05-25 15:30:00")},
                {"LapNumber": 3, "Position": 4, "PitOutTime": pd.NaT},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=["VER"],
            top_n=None,
            workspace_dir=tmp_output_dir,
        )

        # Verify pit stop is tracked in statistics
        driver_stats = result["statistics"]["drivers"][0]
        assert driver_stats["pit_stops"] == 1

        # Verify ax.scatter was called for pit stop marker
        mock_ax.scatter.assert_called()

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_no_position_data(
        self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test handling of drivers with no position data (DNS)."""
        mock_fastf1.get_session.return_value = mock_fastf1_session
        mock_fastf1_session.drivers = [33]
        mock_fastf1_session.get_driver.return_value = {"Abbreviation": "VER"}

        # Mock empty laps (DNS scenario)
        mock_laps = pd.DataFrame()
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)

        # Should handle gracefully but may not generate meaningful output
        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=["VER"],
            top_n=None,
            workspace_dir=tmp_output_dir,
        )

        # Verify driver is excluded
        assert "VER" in result.get("excluded_drivers", [])

    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_error(self, mock_fastf1, tmp_output_dir):
        """Test error handling in chart generation."""
        # Setup mock to raise error
        mock_fastf1.get_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            generate_position_changes_chart(
                year=2024,
                gp="InvalidGP",
                session_type="R",
                drivers=None,
                top_n=None,
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_statistics_calculation(self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session):
        """Test correct calculation of position change statistics."""
        mock_fastf1.get_session.return_value = mock_fastf1_session
        mock_fastf1_session.drivers = [33]
        mock_fastf1_session.get_driver.return_value = {"Abbreviation": "VER"}

        # Mock laps with known position changes
        # Start P5, gain to P3, lose to P4, finish P2
        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 5, "PitOutTime": pd.NaT},
                {"LapNumber": 2, "Position": 3, "PitOutTime": pd.NaT},  # +2 positions
                {"LapNumber": 3, "Position": 4, "PitOutTime": pd.NaT},  # -1 position
                {"LapNumber": 4, "Position": 2, "PitOutTime": pd.NaT},  # +2 positions
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=["VER"],
            top_n=None,
            workspace_dir=tmp_output_dir,
        )

        driver_stats = result["statistics"]["drivers"][0]
        assert driver_stats["start_position"] == 5
        assert driver_stats["finish_position"] == 2
        assert driver_stats["net_change"] == 3  # Gained 3 positions overall
        assert driver_stats["overtakes"] == 2  # Two instances of position gain
        assert driver_stats["times_overtaken"] == 1  # One instance of position loss
        assert driver_stats["biggest_gain"] == 2  # Biggest single gain
        assert driver_stats["biggest_loss"] == 1  # Biggest single loss

    @patch("pitlane_agent.commands.analyze.position_changes.plt")
    @patch("pitlane_agent.commands.analyze.position_changes.fastf1")
    def test_generate_position_changes_chart_many_drivers(
        self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test chart generation with many drivers uses shortened filename."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "Position": 1, "PitOutTime": pd.NaT},
                {"LapNumber": 2, "Position": 1, "PitOutTime": pd.NaT},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (20, 1)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function with 6 drivers (more than 5)
        drivers = ["VER", "HAM", "LEC", "NOR", "PIA", "SAI"]
        result = generate_position_changes_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            drivers=drivers,
            workspace_dir=tmp_output_dir,
        )

        # Assertions - filename should use count instead of listing all drivers
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "position_changes_2024_monaco_R_6drivers.png")
