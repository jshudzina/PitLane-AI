"""Tests for session_info script."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from pitlane_agent.scripts.session_info import cli, get_session_info


class TestSessionInfoBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.scripts.session_info.fastf1")
    def test_get_session_info_success(self, mock_fastf1, mock_fastf1_session):
        """Test successful session info retrieval."""
        # Setup mocks
        mock_fastf1.get_session.return_value = mock_fastf1_session
        mock_fastf1_session.results = MagicMock()

        # Create mock driver data
        import pandas as pd

        driver_data = pd.DataFrame(
            [
                {
                    "Abbreviation": "VER",
                    "FirstName": "Max",
                    "LastName": "Verstappen",
                    "TeamName": "Red Bull Racing",
                    "DriverNumber": 1,
                    "Position": 1,
                }
            ]
        )
        mock_fastf1_session.results.iterrows.return_value = driver_data.iterrows()

        # Call function
        result = get_session_info(2024, "Monaco", "Q")

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["country"] == "Monaco"
        assert result["session_type"] == "Q"
        assert result["session_name"] == "Qualifying"
        assert len(result["drivers"]) == 1
        assert result["drivers"][0]["abbreviation"] == "VER"
        assert result["drivers"][0]["name"] == "Max Verstappen"

        # Verify FastF1 was called correctly
        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "Q")
        mock_fastf1_session.load.assert_called_once()

    @patch("pitlane_agent.scripts.session_info.fastf1")
    def test_get_session_info_error(self, mock_fastf1):
        """Test error handling in session info retrieval."""
        # Setup mock to raise error
        mock_fastf1.get_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            get_session_info(2024, "InvalidGP", "Q")


class TestSessionInfoCLI:
    """Integration tests for CLI interface using CliRunner."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Get F1 session information" in result.output
        assert "--year" in result.output
        assert "--gp" in result.output
        assert "--session" in result.output

    @patch("pitlane_agent.scripts.session_info.get_session_info")
    def test_cli_success(self, mock_get_session_info):
        """Test successful CLI execution."""
        # Setup mock return value
        mock_get_session_info.return_value = {
            "year": 2024,
            "event_name": "Monaco Grand Prix",
            "country": "Monaco",
            "session_type": "R",
            "session_name": "Race",
            "date": "2024-05-26",
            "total_laps": 78,
            "drivers": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--year", "2024", "--gp", "Monaco", "--session", "R"])

        assert result.exit_code == 0

        # Verify JSON output
        output = json.loads(result.output)
        assert output["year"] == 2024
        assert output["event_name"] == "Monaco Grand Prix"

        # Verify function was called with correct args
        mock_get_session_info.assert_called_once_with(2024, "Monaco", "R")

    @patch("pitlane_agent.scripts.session_info.get_session_info")
    def test_cli_error_handling(self, mock_get_session_info):
        """Test CLI error handling."""
        # Setup mock to raise error
        mock_get_session_info.side_effect = Exception("FastF1 error")

        runner = CliRunner()
        result = runner.invoke(cli, ["--year", "2024", "--gp", "Monaco", "--session", "R"])

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
        assert "Missing option" in result.output or "Error" in result.output
