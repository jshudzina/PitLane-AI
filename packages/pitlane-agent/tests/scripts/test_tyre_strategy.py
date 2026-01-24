"""Tests for tyre_strategy script."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from pitlane_agent.scripts.tyre_strategy import (
    cli,
    generate_tyre_strategy_chart,
    setup_plot_style,
)


class TestTyreStrategyBusinessLogic:
    """Unit tests for business logic functions."""

    def test_setup_plot_style(self):
        """Test plot style configuration."""
        # Test that setup_plot_style doesn't raise errors
        setup_plot_style()

    @patch("pitlane_agent.scripts.tyre_strategy.plt")
    @patch("pitlane_agent.scripts.tyre_strategy.fastf1")
    def test_generate_tyre_strategy_chart_success(
        self, mock_fastf1, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test successful chart generation."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session

        # Mock drivers and results
        import pandas as pd

        mock_results = pd.DataFrame(
            [{"Abbreviation": "VER", "Position": 1}, {"Abbreviation": "HAM", "Position": 2}]
        )
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
        output_path = str(tmp_output_dir / "tyre_strategy.png")
        result = generate_tyre_strategy_chart(
            year=2024, gp="Monaco", session_type="R", output_path=output_path
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert "strategies" in result
        assert result["output_path"] == output_path

        # Verify FastF1 was called correctly
        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "R")
        mock_fastf1_session.load.assert_called_once()

    @patch("pitlane_agent.scripts.tyre_strategy.fastf1")
    def test_generate_tyre_strategy_chart_error(self, mock_fastf1):
        """Test error handling in chart generation."""
        # Setup mock to raise error
        mock_fastf1.get_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            generate_tyre_strategy_chart(
                year=2024, gp="InvalidGP", session_type="R", output_path="/tmp/test.png"
            )


class TestTyreStrategyCLI:
    """Integration tests for CLI interface using CliRunner."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Generate tyre strategy" in result.output
        assert "--year" in result.output
        assert "--gp" in result.output
        assert "--session" in result.output
        assert "--output" in result.output

    @patch("pitlane_agent.scripts.tyre_strategy.generate_tyre_strategy_chart")
    def test_cli_success(self, mock_generate):
        """Test successful CLI execution."""
        # Setup mock return value
        mock_generate.return_value = {
            "output_path": "/tmp/test.png",
            "event_name": "Monaco Grand Prix",
            "session_name": "Race",
            "year": 2024,
            "total_laps": 78,
            "strategies": [],
        }

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--year", "2024", "--gp", "Monaco", "--session", "R", "--output", "/tmp/test.png"],
        )

        assert result.exit_code == 0

        # Verify JSON output
        output = json.loads(result.output)
        assert output["year"] == 2024
        assert output["event_name"] == "Monaco Grand Prix"

        # Verify function was called with correct args
        mock_generate.assert_called_once_with(
            year=2024, gp="Monaco", session_type="R", output_path="/tmp/test.png"
        )

    @patch("pitlane_agent.scripts.tyre_strategy.generate_tyre_strategy_chart")
    def test_cli_default_session(self, mock_generate):
        """Test CLI uses default session type R."""
        mock_generate.return_value = {"output_path": "/tmp/test.png"}

        runner = CliRunner()
        runner.invoke(cli, ["--year", "2024", "--gp", "Monaco"])

        # Verify default session was used
        call_args = mock_generate.call_args[1]
        assert call_args["session_type"] == "R"

    @patch("pitlane_agent.scripts.tyre_strategy.generate_tyre_strategy_chart")
    def test_cli_error_handling(self, mock_generate):
        """Test CLI error handling."""
        # Setup mock to raise error
        mock_generate.side_effect = Exception("Chart generation failed")

        runner = CliRunner()
        result = runner.invoke(cli, ["--year", "2024", "--gp", "Monaco"])

        assert result.exit_code == 1

        # Verify error output
        error = json.loads(result.output)
        assert "error" in error
        assert "Chart generation failed" in error["error"]

    def test_cli_missing_required_args(self):
        """Test CLI with missing required arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--year", "2024"])

        assert result.exit_code != 0
