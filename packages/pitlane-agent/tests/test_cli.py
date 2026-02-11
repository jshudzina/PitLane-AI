"""Tests for the main pitlane CLI group."""

from click.testing import CliRunner
from pitlane_agent.cli import pitlane


class TestCLIGroup:
    """Tests for the main CLI group."""

    def test_main_help(self):
        """Test main CLI help output shows all command groups."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["--help"])

        assert result.exit_code == 0
        assert "PitLane AI" in result.output
        assert "workspace" in result.output
        assert "fetch" in result.output
        assert "analyze" in result.output

    def test_subcommand_lap_times_help(self):
        """Test analyze lap-times subcommand help."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["analyze", "lap-times", "--help"])

        assert result.exit_code == 0
        assert "Generate lap times chart" in result.output
        assert "--workspace-id" in result.output
        assert "--year" in result.output
        assert "--gp" in result.output
        assert "--drivers" in result.output

    def test_subcommand_session_info_help(self):
        """Test fetch session-info subcommand help."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["fetch", "session-info", "--help"])

        assert result.exit_code == 0
        assert "Fetch session information" in result.output
        assert "--workspace-id" in result.output
        assert "--year" in result.output
        assert "--gp" in result.output
        assert "--session" in result.output

    def test_subcommand_tyre_strategy_help(self):
        """Test analyze tyre-strategy subcommand help."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["analyze", "tyre-strategy", "--help"])

        assert result.exit_code == 0
        assert "Generate tyre strategy" in result.output
        assert "--workspace-id" in result.output
        assert "--year" in result.output
        assert "--gp" in result.output

    def test_invalid_subcommand(self):
        """Test invalid subcommand returns error."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["invalid-command"])

        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output
