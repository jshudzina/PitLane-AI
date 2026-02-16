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


class TestTestingSessionCLI:
    """Tests for --test/--day CLI options."""

    def test_session_info_help_shows_test_options(self):
        """Test that session-info help shows --test and --day options."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["fetch", "session-info", "--help"])

        assert result.exit_code == 0
        assert "--test" in result.output
        assert "--day" in result.output

    def test_session_info_requires_gp_or_test(self):
        """Test that session-info fails when neither --gp/--session nor --test/--day is provided."""
        runner = CliRunner()
        result = runner.invoke(
            pitlane,
            [
                "fetch",
                "session-info",
                "--workspace-id",
                "test-ws",
                "--year",
                "2026",
            ],
        )

        assert result.exit_code != 0
        assert "Must provide either --gp and --session, or --test and --day" in result.output

    def test_session_info_rejects_both_gp_and_test(self):
        """Test that session-info fails when both --gp/--session and --test/--day are provided."""
        runner = CliRunner()
        result = runner.invoke(
            pitlane,
            [
                "fetch",
                "session-info",
                "--workspace-id",
                "test-ws",
                "--year",
                "2026",
                "--gp",
                "Monaco",
                "--session",
                "R",
                "--test",
                "1",
                "--day",
                "2",
            ],
        )

        assert result.exit_code != 0
        assert "Cannot use --gp/--session with --test/--day" in result.output

    def test_analyze_lap_times_help_shows_test_options(self):
        """Test that analyze lap-times help shows --test and --day options."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["analyze", "lap-times", "--help"])

        assert result.exit_code == 0
        assert "--test" in result.output
        assert "--day" in result.output

    def test_race_control_help_shows_test_options(self):
        """Test that race-control help shows --test and --day options."""
        runner = CliRunner()
        result = runner.invoke(pitlane, ["fetch", "race-control", "--help"])

        assert result.exit_code == 0
        assert "--test" in result.output
        assert "--day" in result.output
