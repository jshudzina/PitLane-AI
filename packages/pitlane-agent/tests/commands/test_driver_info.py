"""Tests for driver_info command."""

import json
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest
from click.testing import CliRunner
from pitlane_agent.cli_fetch import driver_info as cli
from pitlane_agent.commands.fetch.driver_info import get_driver_info


class TestDriverInfoBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.fetch.driver_info.get_ergast_client")
    def test_get_driver_info_all_drivers(self, mock_get_ergast):
        """Test getting all drivers without filters."""
        # Mock Ergast API response
        mock_df = pd.DataFrame(
            [
                {
                    "driverId": "verstappen",
                    "driverCode": "VER",
                    "driverNumber": 1,
                    "givenName": "Max",
                    "familyName": "Verstappen",
                    "dateOfBirth": "1997-09-30",
                    "driverNationality": "Dutch",
                    "driverUrl": "https://en.wikipedia.org/wiki/Max_Verstappen",
                }
            ]
        )
        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info()

        assert result["total_drivers"] == 1
        assert result["drivers"][0]["driver_code"] == "VER"
        assert result["drivers"][0]["full_name"] == "Max Verstappen"
        mock_ergast_instance.get_driver_info.assert_called_once_with()

    @patch("pitlane_agent.commands.fetch.driver_info.get_ergast_client")
    def test_get_driver_info_by_code(self, mock_get_ergast):
        """Test filtering by driver code."""
        mock_df = pd.DataFrame(
            [
                {
                    "driverId": "hamilton",
                    "driverCode": "HAM",
                    "driverNumber": 44,
                    "givenName": "Lewis",
                    "familyName": "Hamilton",
                    "dateOfBirth": "1985-01-07",
                    "driverNationality": "British",
                    "driverUrl": "https://en.wikipedia.org/wiki/Lewis_Hamilton",
                }
            ]
        )
        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info(driver_code="HAM")

        assert result["filters"]["driver_code"] == "HAM"
        assert result["drivers"][0]["driver_code"] == "HAM"
        # Verify lowercase conversion (Ergast expects lowercase driver IDs)
        mock_ergast_instance.get_driver_info.assert_called_once_with(driver="ham")

    @patch("pitlane_agent.commands.fetch.driver_info.get_ergast_client")
    def test_get_driver_info_by_season(self, mock_get_ergast):
        """Test filtering by season."""
        mock_df = pd.DataFrame(
            [
                {
                    "driverId": "verstappen",
                    "driverCode": "VER",
                    "driverNumber": 1,
                    "givenName": "Max",
                    "familyName": "Verstappen",
                    "dateOfBirth": "1997-09-30",
                    "driverNationality": "Dutch",
                    "driverUrl": "https://en.wikipedia.org/wiki/Max_Verstappen",
                }
            ]
        )
        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info(season=2024)

        assert result["filters"]["season"] == 2024
        mock_ergast_instance.get_driver_info.assert_called_once_with(season=2024)

    @patch("pitlane_agent.commands.fetch.driver_info.get_ergast_client")
    def test_get_driver_info_with_pagination(self, mock_get_ergast):
        """Test pagination with limit and offset."""
        mock_df = pd.DataFrame(
            [
                {
                    "driverId": f"driver{i}",
                    "driverCode": f"D{i:02d}",
                    "driverNumber": i,
                    "givenName": f"First{i}",
                    "familyName": f"Last{i}",
                    "dateOfBirth": "1990-01-01",
                    "driverNationality": "Unknown",
                    "driverUrl": f"http://example.com/{i}",
                }
                for i in range(20)
            ]
        )
        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info(limit=5, offset=10)

        assert result["total_drivers"] == 5
        assert result["pagination"]["limit"] == 5
        assert result["pagination"]["offset"] == 10
        # Should skip first 10 and return next 5
        assert result["drivers"][0]["driver_code"] == "D10"

    @patch("pitlane_agent.commands.fetch.driver_info.get_ergast_client")
    def test_get_driver_info_error(self, mock_get_ergast):
        """Test error handling."""
        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_driver_info.side_effect = Exception("Ergast API error")

        with pytest.raises(Exception, match="Ergast API error"):
            get_driver_info()


class TestDriverInfoCLI:
    """Integration tests for CLI interface using CliRunner."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Fetch driver information and store in workspace" in result.output
        assert "--driver-code" in result.output
        assert "--season" in result.output
        assert "--limit" in result.output
        assert "--offset" in result.output

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.commands.fetch.driver_info.get_driver_info")
    def test_cli_success(self, mock_get_info, mock_get_path, mock_exists):
        """Test successful CLI execution."""
        # Mock workspace functions
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/drivers.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_info.return_value = {
            "total_drivers": 1,
            "filters": {"driver_code": None, "season": None},
            "pagination": {"limit": 100, "offset": 0},
            "drivers": [{"driver_code": "VER", "full_name": "Max Verstappen"}],
        }

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--session-id", "test-session"])

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["total_drivers"] == 1

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.commands.fetch.driver_info.get_driver_info")
    def test_cli_with_driver_code(self, mock_get_info, mock_get_path, mock_exists):
        """Test CLI with driver code filter."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/drivers.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_info.return_value = {
            "total_drivers": 1,
            "filters": {"driver_code": "VER", "season": None},
            "pagination": {"limit": 100, "offset": 0},
            "drivers": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--session-id", "test-session", "--driver-code", "VER"])

            assert result.exit_code == 0
            mock_get_info.assert_called_once_with(driver_code="VER", season=None, limit=100, offset=0)

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.commands.fetch.driver_info.get_driver_info")
    def test_cli_with_season(self, mock_get_info, mock_get_path, mock_exists):
        """Test CLI with season filter."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/drivers.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_info.return_value = {
            "total_drivers": 20,
            "filters": {"driver_code": None, "season": 2024},
            "pagination": {"limit": 100, "offset": 0},
            "drivers": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--session-id", "test-session", "--season", "2024"])

            assert result.exit_code == 0
            mock_get_info.assert_called_once_with(driver_code=None, season=2024, limit=100, offset=0)

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.commands.fetch.driver_info.get_driver_info")
    def test_cli_with_pagination(self, mock_get_info, mock_get_path, mock_exists):
        """Test CLI with limit and offset."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        from unittest.mock import Mock

        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/drivers.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_info.return_value = {
            "total_drivers": 10,
            "filters": {"driver_code": None, "season": None},
            "pagination": {"limit": 10, "offset": 50},
            "drivers": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(cli, ["--session-id", "test-session", "--limit", "10", "--offset", "50"])

            assert result.exit_code == 0
            mock_get_info.assert_called_once_with(driver_code=None, season=None, limit=10, offset=50)

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_workspace_not_exists(self, mock_exists):
        """Test CLI with non-existent workspace."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["--session-id", "nonexistent"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Workspace does not exist" in error["error"]

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_invalid_season_too_old(self, mock_exists):
        """Test CLI rejects seasons before 1950."""
        mock_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["--session-id", "test-session", "--season", "1949"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "1950" in error["error"]

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_invalid_season_too_future(self, mock_exists):
        """Test CLI rejects seasons too far in future."""
        mock_exists.return_value = True

        runner = CliRunner()
        current_year = datetime.now().year
        future_year = current_year + 3

        result = runner.invoke(cli, ["--session-id", "test-session", "--season", str(future_year)])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.commands.fetch.driver_info.get_driver_info")
    def test_cli_error_handling(self, mock_get_info, mock_get_path, mock_exists):
        """Test CLI error handling."""
        mock_exists.return_value = True

        from unittest.mock import Mock

        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: Mock(__truediv__=lambda s, y: "/tmp/test/data/drivers.json")
        mock_get_path.return_value = mock_path

        mock_get_info.side_effect = Exception("Ergast error")

        runner = CliRunner()
        result = runner.invoke(cli, ["--session-id", "test-session"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Ergast error" in error["error"]
