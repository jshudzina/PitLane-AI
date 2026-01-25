"""Tests for lap_times script."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from pitlane_agent.scripts.lap_times import cli, generate_lap_times_chart, setup_plot_style


class TestLapTimesBusinessLogic:
    """Unit tests for business logic functions."""

    def test_setup_plot_style(self):
        """Test plot style configuration."""
        # Test that setup_plot_style doesn't raise errors
        setup_plot_style()

    @patch("pitlane_agent.scripts.lap_times.plt")
    @patch("pitlane_agent.scripts.lap_times.fastf1")
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
        output_path = str(tmp_output_dir / "lap_times.png")
        result = generate_lap_times_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            output_path=output_path,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert "statistics" in result
        assert result["output_path"] == output_path
        assert len(result["drivers_plotted"]) <= 2

        # Verify FastF1 was called correctly
        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "Q")
        mock_fastf1_session.load.assert_called_once()

    @patch("pitlane_agent.scripts.lap_times.fastf1")
    def test_generate_lap_times_chart_error(self, mock_fastf1):
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
                output_path="/tmp/test.png",
            )


class TestLapTimesCLI:
    """Integration tests for CLI interface using CliRunner."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Generate lap times chart" in result.output
        assert "--year" in result.output
        assert "--gp" in result.output
        assert "--session" in result.output
        assert "--drivers" in result.output

    @patch("pitlane_agent.scripts.lap_times.generate_lap_times_chart")
    def test_cli_success(self, mock_generate):
        """Test successful CLI execution."""
        # Setup mock return value
        mock_generate.return_value = {
            "output_path": "/tmp/test.png",
            "event_name": "Monaco Grand Prix",
            "session_name": "Qualifying",
            "year": 2024,
            "drivers_plotted": ["VER", "HAM"],
            "statistics": [],
        }

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--year",
                "2024",
                "--gp",
                "Monaco",
                "--session",
                "Q",
                "--drivers",
                "VER",
                "--drivers",
                "HAM",
                "--output",
                "/tmp/test.png",
            ],
        )

        assert result.exit_code == 0

        # Verify JSON output
        output = json.loads(result.output)
        assert output["year"] == 2024
        assert output["event_name"] == "Monaco Grand Prix"

        # Verify function was called with correct args
        mock_generate.assert_called_once_with(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            output_path="/tmp/test.png",
        )

    @patch("pitlane_agent.scripts.lap_times.generate_lap_times_chart")
    def test_cli_single_driver(self, mock_generate):
        """Test CLI with single driver."""
        mock_generate.return_value = {"output_path": "/tmp/test.png"}

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "--year",
                "2024",
                "--gp",
                "Monaco",
                "--session",
                "Q",
                "--drivers",
                "VER",
            ],
        )

        # Verify single driver was passed correctly
        call_args = mock_generate.call_args[1]
        assert call_args["drivers"] == ["VER"]

    @patch("pitlane_agent.scripts.lap_times.generate_lap_times_chart")
    def test_cli_multiple_drivers(self, mock_generate):
        """Test CLI with multiple drivers using repeated options."""
        mock_generate.return_value = {"output_path": "/tmp/test.png"}

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "--year",
                "2024",
                "--gp",
                "Monaco",
                "--session",
                "Q",
                "--drivers",
                "VER",
                "--drivers",
                "HAM",
                "--drivers",
                "LEC",
            ],
        )

        # Verify multiple drivers were passed correctly
        call_args = mock_generate.call_args[1]
        assert call_args["drivers"] == ["VER", "HAM", "LEC"]

    @patch("pitlane_agent.scripts.lap_times.generate_lap_times_chart")
    def test_cli_default_output_path(self, mock_generate):
        """Test CLI uses default output path."""
        mock_generate.return_value = {"output_path": "/tmp/charts/lap_times.png"}

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "--year",
                "2024",
                "--gp",
                "Monaco",
                "--session",
                "Q",
                "--drivers",
                "VER",
            ],
        )

        # Verify default path was used
        call_args = mock_generate.call_args[1]
        assert call_args["output_path"] == "/tmp/charts/lap_times.png"

    @patch("pitlane_agent.scripts.lap_times.generate_lap_times_chart")
    def test_cli_error_handling(self, mock_generate):
        """Test CLI error handling."""
        # Setup mock to raise error
        mock_generate.side_effect = Exception("FastF1 error")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--year",
                "2024",
                "--gp",
                "Monaco",
                "--session",
                "Q",
                "--drivers",
                "VER",
            ],
        )

        assert result.exit_code == 1

        # Verify error output
        error = json.loads(result.output)
        assert "error" in error
        assert "FastF1 error" in error["error"]

    def test_cli_missing_required_args(self):
        """Test CLI with missing required arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--year", "2024"])

        assert result.exit_code != 0
