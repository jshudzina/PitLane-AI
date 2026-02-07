"""Tests for lap_times command."""

from unittest.mock import MagicMock, patch

import pytest
from pitlane_agent.commands.analyze.lap_times import (
    generate_lap_times_chart,
    setup_plot_style,
)
from pitlane_agent.utils import sanitize_filename


class TestLapTimesBusinessLogic:
    """Unit tests for business logic functions."""

    def test_setup_plot_style(self):
        """Test plot style configuration."""
        # Test that setup_plot_style doesn't raise errors
        setup_plot_style()

    @patch("pitlane_agent.commands.analyze.lap_times.plt")
    @patch("pitlane_agent.commands.analyze.lap_times.fastf1")
    def test_generate_lap_times_chart_success(self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session):
        """Test successful chart generation."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        # Mock driver laps
        import pandas as pd

        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "LapTime": pd.Timedelta(seconds=90)},
                {"LapNumber": 2, "LapTime": pd.Timedelta(seconds=89)},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (85, 95)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function
        result = generate_lap_times_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert "statistics" in result
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "lap_times_2024_monaco_Q_HAM_VER.png")
        assert result["workspace"] == str(tmp_output_dir)
        assert len(result["drivers_plotted"]) <= 2

        # Verify FastF1 was called correctly
        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "Q")
        mock_fastf1_session.load.assert_called_once()

    @patch("pitlane_agent.commands.analyze.lap_times.fastf1")
    def test_generate_lap_times_chart_error(self, mock_fastf1, tmp_output_dir):
        """Test error handling in chart generation."""
        # Setup mock to raise error
        mock_fastf1.get_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            generate_lap_times_chart(
                year=2024,
                gp="InvalidGP",
                session_type="Q",
                drivers=["VER"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.lap_times.plt")
    @patch("pitlane_agent.commands.analyze.lap_times.fastf1")
    def test_generate_lap_times_chart_many_drivers(self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session):
        """Test chart generation with many drivers uses shortened filename."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        # Mock driver laps
        import pandas as pd

        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "LapTime": pd.Timedelta(seconds=90)},
                {"LapNumber": 2, "LapTime": pd.Timedelta(seconds=89)},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (85, 95)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function with 6 drivers (more than 5)
        drivers = ["VER", "HAM", "LEC", "NOR", "PIA", "SAI"]
        result = generate_lap_times_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=drivers,
            workspace_dir=tmp_output_dir,
        )

        # Assertions - filename should use count instead of listing all drivers
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "lap_times_2024_monaco_Q_6drivers.png")


class TestSanitizeFilename:
    """Unit tests for filename sanitization."""

    def test_sanitize_simple_name(self):
        """Test sanitization of simple name."""
        assert sanitize_filename("Monaco") == "monaco"

    def test_sanitize_name_with_spaces(self):
        """Test sanitization of name with spaces."""
        assert sanitize_filename("Abu Dhabi") == "abu_dhabi"

    def test_sanitize_name_with_hyphens(self):
        """Test sanitization of name with hyphens."""
        assert sanitize_filename("Emilia-Romagna") == "emilia_romagna"

    def test_sanitize_name_with_special_chars(self):
        """Test sanitization of name with special characters."""
        assert sanitize_filename("São Paulo") == "são_paulo"

    def test_sanitize_multiple_spaces(self):
        """Test sanitization of name with multiple consecutive spaces."""
        assert sanitize_filename("Great  Britain") == "great_britain"

    def test_sanitize_leading_trailing_spaces(self):
        """Test sanitization removes leading/trailing underscores."""
        assert sanitize_filename(" Monaco ") == "monaco"
