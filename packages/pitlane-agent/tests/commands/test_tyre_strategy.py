"""Tests for tyre_strategy command."""

from unittest.mock import MagicMock, patch

import pytest
from pitlane_agent.commands.analyze.tyre_strategy import (
    generate_tyre_strategy_chart,
    setup_plot_style,
)
from pitlane_agent.utils import sanitize_filename


class TestTyreStrategyBusinessLogic:
    """Unit tests for business logic functions."""

    def test_setup_plot_style(self):
        """Test plot style configuration."""
        # Test that setup_plot_style doesn't raise errors
        setup_plot_style()

    @patch("pitlane_agent.commands.analyze.tyre_strategy.plt")
    @patch("pitlane_agent.commands.analyze.tyre_strategy.fastf1")
    def test_generate_tyre_strategy_chart_success(self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session):
        """Test successful chart generation."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        # Mock drivers and results
        import pandas as pd

        mock_results = pd.DataFrame([{"Abbreviation": "VER", "Position": 1}, {"Abbreviation": "HAM", "Position": 2}])
        mock_fastf1_session.results.sort_values.return_value = mock_results

        # Mock laps data
        mock_laps = pd.DataFrame(
            [
                {"LapNumber": 1, "Compound": "SOFT"},
                {"LapNumber": 2, "Compound": "SOFT"},
                {"LapNumber": 3, "Compound": "MEDIUM"},
            ]
        )
        mock_fastf1_session.laps.pick_driver.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Call function
        result = generate_tyre_strategy_chart(year=2024, gp="Monaco", session_type="R", workspace_dir=tmp_output_dir)

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert "strategies" in result
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "tyre_strategy_2024_monaco_R.png")
        assert result["workspace"] == str(tmp_output_dir)

        # Verify FastF1 was called correctly
        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "R")
        mock_fastf1_session.load.assert_called_once()

    @patch("pitlane_agent.commands.analyze.tyre_strategy.fastf1")
    def test_generate_tyre_strategy_chart_error(self, mock_fastf1, tmp_output_dir):
        """Test error handling in chart generation."""
        # Setup mock to raise error
        mock_fastf1.get_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            generate_tyre_strategy_chart(year=2024, gp="InvalidGP", session_type="R", workspace_dir=tmp_output_dir)


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
