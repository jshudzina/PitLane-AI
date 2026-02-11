"""Tests for event_schedule command."""

import json
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest
from click.testing import CliRunner
from pitlane_agent.cli_fetch import event_schedule as cli
from pitlane_agent.commands.fetch.event_schedule import get_event_schedule


class TestEventScheduleBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.fetch.event_schedule.fastf1")
    def test_get_event_schedule_success(self, mock_fastf1):
        """Test successful event schedule retrieval."""
        # Setup mock schedule data
        mock_schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "Country": "Bahrain",
                    "Location": "Sakhir",
                    "OfficialEventName": "Bahrain Grand Prix 2024",
                    "EventName": "Bahrain Grand Prix",
                    "EventDate": pd.Timestamp("2024-03-02"),
                    "EventFormat": "conventional",
                    "F1ApiSupport": True,
                    "Session1": "Practice 1",
                    "Session1Date": pd.Timestamp("2024-03-01 11:30:00"),
                    "Session1DateUtc": pd.Timestamp("2024-03-01 08:30:00"),
                    "Session2": "Practice 2",
                    "Session2Date": pd.Timestamp("2024-03-01 15:00:00"),
                    "Session2DateUtc": pd.Timestamp("2024-03-01 12:00:00"),
                    "Session3": "Practice 3",
                    "Session3Date": pd.Timestamp("2024-03-02 12:30:00"),
                    "Session3DateUtc": pd.Timestamp("2024-03-02 09:30:00"),
                    "Session4": "Qualifying",
                    "Session4Date": pd.Timestamp("2024-03-02 16:00:00"),
                    "Session4DateUtc": pd.Timestamp("2024-03-02 13:00:00"),
                    "Session5": "Race",
                    "Session5Date": pd.Timestamp("2024-03-03 18:00:00"),
                    "Session5DateUtc": pd.Timestamp("2024-03-03 15:00:00"),
                }
            ]
        )
        mock_fastf1.get_event_schedule.return_value = mock_schedule

        # Call function
        result = get_event_schedule(2024)

        # Assertions
        assert result["year"] == 2024
        assert result["total_events"] == 1
        assert result["include_testing"] is True
        assert len(result["events"]) == 1
        assert result["events"][0]["country"] == "Bahrain"
        assert result["events"][0]["round"] == 1
        assert len(result["events"][0]["sessions"]) == 5

        # Verify FastF1 was called correctly
        mock_fastf1.get_event_schedule.assert_called_once_with(2024, include_testing=True)

    @patch("pitlane_agent.commands.fetch.event_schedule.fastf1")
    def test_get_event_schedule_filter_by_round(self, mock_fastf1):
        """Test event schedule filtering by round number."""
        mock_schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "Country": "Bahrain",
                    "Location": "Sakhir",
                    "OfficialEventName": "Bahrain GP",
                    "EventName": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
                    "EventFormat": "conventional",
                    "F1ApiSupport": True,
                    "Session1": None,
                    "Session1Date": None,
                    "Session1DateUtc": None,
                    "Session2": None,
                    "Session2Date": None,
                    "Session2DateUtc": None,
                    "Session3": None,
                    "Session3Date": None,
                    "Session3DateUtc": None,
                    "Session4": None,
                    "Session4Date": None,
                    "Session4DateUtc": None,
                    "Session5": None,
                    "Session5Date": None,
                    "Session5DateUtc": None,
                },
                {
                    "RoundNumber": 2,
                    "Country": "Saudi Arabia",
                    "Location": "Jeddah",
                    "OfficialEventName": "Saudi GP",
                    "EventName": "Saudi Arabia",
                    "EventDate": pd.Timestamp("2024-03-09"),
                    "EventFormat": "conventional",
                    "F1ApiSupport": True,
                    "Session1": None,
                    "Session1Date": None,
                    "Session1DateUtc": None,
                    "Session2": None,
                    "Session2Date": None,
                    "Session2DateUtc": None,
                    "Session3": None,
                    "Session3Date": None,
                    "Session3DateUtc": None,
                    "Session4": None,
                    "Session4Date": None,
                    "Session4DateUtc": None,
                    "Session5": None,
                    "Session5Date": None,
                    "Session5DateUtc": None,
                },
            ]
        )
        mock_fastf1.get_event_schedule.return_value = mock_schedule

        result = get_event_schedule(2024, round_number=2)

        assert result["total_events"] == 1
        assert result["events"][0]["country"] == "Saudi Arabia"
        assert result["filters"]["round"] == 2

    @patch("pitlane_agent.commands.fetch.event_schedule.fastf1")
    def test_get_event_schedule_filter_by_country(self, mock_fastf1):
        """Test event schedule filtering by country name (case-insensitive)."""
        mock_schedule = pd.DataFrame(
            [
                {
                    "RoundNumber": 1,
                    "Country": "Bahrain",
                    "Location": "Sakhir",
                    "OfficialEventName": "Bahrain GP",
                    "EventName": "Bahrain",
                    "EventDate": pd.Timestamp("2024-03-02"),
                    "EventFormat": "conventional",
                    "F1ApiSupport": True,
                    "Session1": None,
                    "Session1Date": None,
                    "Session1DateUtc": None,
                    "Session2": None,
                    "Session2Date": None,
                    "Session2DateUtc": None,
                    "Session3": None,
                    "Session3Date": None,
                    "Session3DateUtc": None,
                    "Session4": None,
                    "Session4Date": None,
                    "Session4DateUtc": None,
                    "Session5": None,
                    "Session5Date": None,
                    "Session5DateUtc": None,
                },
                {
                    "RoundNumber": 6,
                    "Country": "Monaco",
                    "Location": "Monte Carlo",
                    "OfficialEventName": "Monaco GP",
                    "EventName": "Monaco",
                    "EventDate": pd.Timestamp("2024-05-26"),
                    "EventFormat": "conventional",
                    "F1ApiSupport": True,
                    "Session1": None,
                    "Session1Date": None,
                    "Session1DateUtc": None,
                    "Session2": None,
                    "Session2Date": None,
                    "Session2DateUtc": None,
                    "Session3": None,
                    "Session3Date": None,
                    "Session3DateUtc": None,
                    "Session4": None,
                    "Session4Date": None,
                    "Session4DateUtc": None,
                    "Session5": None,
                    "Session5Date": None,
                    "Session5DateUtc": None,
                },
            ]
        )
        mock_fastf1.get_event_schedule.return_value = mock_schedule

        # Test case-insensitive matching
        result = get_event_schedule(2024, country="monaco")

        assert result["total_events"] == 1
        assert result["events"][0]["country"] == "Monaco"
        assert result["filters"]["country"] == "monaco"

    @patch("pitlane_agent.commands.fetch.event_schedule.fastf1")
    def test_get_event_schedule_no_testing(self, mock_fastf1):
        """Test event schedule excluding testing sessions."""
        mock_schedule = pd.DataFrame([])
        mock_fastf1.get_event_schedule.return_value = mock_schedule

        result = get_event_schedule(2024, include_testing=False)

        assert result["include_testing"] is False
        mock_fastf1.get_event_schedule.assert_called_once_with(2024, include_testing=False)

    @patch("pitlane_agent.commands.fetch.event_schedule.fastf1")
    def test_get_event_schedule_error(self, mock_fastf1):
        """Test error handling in event schedule retrieval."""
        mock_fastf1.get_event_schedule.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            get_event_schedule(2024)


class TestEventScheduleCLI:
    """Integration tests for CLI interface using CliRunner."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Fetch event schedule and store in workspace" in result.output
        assert "--year" in result.output
        assert "--round" in result.output
        assert "--country" in result.output
        assert "--include-testing" in result.output

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_event_schedule")
    def test_cli_success(self, mock_get_schedule, mock_get_path, mock_exists):
        """Test successful CLI execution."""
        # Mock workspace functions
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/schedule.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_schedule.return_value = {
            "year": 2024,
            "total_events": 24,
            "include_testing": True,
            "filters": {"round": None, "country": None},
            "events": [],
        }

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", "2024"])

            assert result.exit_code == 0

            output = json.loads(result.output)
            assert output["year"] == 2024
            assert output["total_events"] == 24

            mock_get_schedule.assert_called_once_with(
                2024,
                round_number=None,
                country=None,
                include_testing=True,
            )

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_event_schedule")
    def test_cli_with_round_filter(self, mock_get_schedule, mock_get_path, mock_exists):
        """Test CLI with round number filter."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/schedule.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_schedule.return_value = {
            "year": 2024,
            "total_events": 1,
            "include_testing": True,
            "filters": {"round": 6, "country": None},
            "events": [{"round": 6, "country": "Monaco"}],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", "2024", "--round", "6"])

            assert result.exit_code == 0
            mock_get_schedule.assert_called_once_with(
                2024,
                round_number=6,
                country=None,
                include_testing=True,
            )

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_event_schedule")
    def test_cli_with_country_filter(self, mock_get_schedule, mock_get_path, mock_exists):
        """Test CLI with country filter."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/schedule.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_schedule.return_value = {
            "year": 2024,
            "total_events": 1,
            "include_testing": True,
            "filters": {"round": None, "country": "Italy"},
            "events": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", "2024", "--country", "Italy"])

            assert result.exit_code == 0
            mock_get_schedule.assert_called_once_with(
                2024,
                round_number=None,
                country="Italy",
                include_testing=True,
            )

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_event_schedule")
    def test_cli_no_testing(self, mock_get_schedule, mock_get_path, mock_exists):
        """Test CLI with --no-testing flag."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/schedule.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_schedule.return_value = {
            "year": 2024,
            "total_events": 24,
            "include_testing": False,
            "filters": {"round": None, "country": None},
            "events": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", "2024", "--no-testing"])

            assert result.exit_code == 0
            mock_get_schedule.assert_called_once_with(
                2024,
                round_number=None,
                country=None,
                include_testing=False,
            )

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_workspace_not_exists(self, mock_exists):
        """Test CLI with non-existent workspace."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["--workspace-id", "nonexistent", "--year", "2024"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Workspace does not exist" in error["error"]

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_invalid_year_too_old(self, mock_exists):
        """Test CLI rejects years before 1950."""
        mock_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", "1949"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "1950" in error["error"]

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_invalid_year_too_future(self, mock_exists):
        """Test CLI rejects years too far in the future."""
        mock_exists.return_value = True

        runner = CliRunner()
        current_year = datetime.now().year
        future_year = current_year + 3

        result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", str(future_year)])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_event_schedule")
    def test_cli_error_handling(self, mock_get_schedule, mock_get_path, mock_exists):
        """Test CLI error handling."""
        mock_exists.return_value = True

        from unittest.mock import Mock

        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: Mock(__truediv__=lambda s, y: "/tmp/test/data/schedule.json")
        mock_get_path.return_value = mock_path

        mock_get_schedule.side_effect = Exception("FastF1 error")

        runner = CliRunner()
        result = runner.invoke(cli, ["--workspace-id", "test-session", "--year", "2024"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "FastF1 error" in error["error"]

    def test_cli_missing_required_args(self):
        """Test CLI with missing required arguments."""
        runner = CliRunner()
        # Test missing --workspace-id
        result = runner.invoke(cli, ["--year", "2024"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_missing_year(self, mock_exists):
        """Test CLI with missing year argument."""
        mock_exists.return_value = True

        runner = CliRunner()
        # Test missing --year
        result = runner.invoke(cli, ["--workspace-id", "test-session"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output
