"""Tests for driver_info script."""

import json
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest
from click.testing import CliRunner
from pitlane_agent.scripts.driver_info import cli, get_driver_info


class TestDriverInfoBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.scripts.driver_info.ergast")
    def test_get_driver_info_all_drivers(self, mock_ergast):
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
        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info()

        assert result["total_drivers"] == 1
        assert result["drivers"][0]["driver_code"] == "VER"
        assert result["drivers"][0]["full_name"] == "Max Verstappen"
        mock_ergast_instance.get_driver_info.assert_called_once_with()

    @patch("pitlane_agent.scripts.driver_info.ergast")
    def test_get_driver_info_by_code(self, mock_ergast):
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
        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info(driver_code="HAM")

        assert result["filters"]["driver_code"] == "HAM"
        assert result["drivers"][0]["driver_code"] == "HAM"
        # Verify lowercase conversion (Ergast expects lowercase driver IDs)
        mock_ergast_instance.get_driver_info.assert_called_once_with(driver="ham")

    @patch("pitlane_agent.scripts.driver_info.ergast")
    def test_get_driver_info_by_season(self, mock_ergast):
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
        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info(season=2024)

        assert result["filters"]["season"] == 2024
        mock_ergast_instance.get_driver_info.assert_called_once_with(season=2024)

    @patch("pitlane_agent.scripts.driver_info.ergast")
    def test_get_driver_info_with_pagination(self, mock_ergast):
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
        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_info.return_value = mock_df

        result = get_driver_info(limit=5, offset=10)

        assert result["total_drivers"] == 5
        assert result["pagination"]["limit"] == 5
        assert result["pagination"]["offset"] == 10
        # Should skip first 10 and return next 5
        assert result["drivers"][0]["driver_code"] == "D10"

    @patch("pitlane_agent.scripts.driver_info.ergast")
    def test_get_driver_info_error(self, mock_ergast):
        """Test error handling."""
        mock_ergast_instance = mock_ergast.Ergast.return_value
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
        assert "Get F1 driver information" in result.output
        assert "--driver-code" in result.output
        assert "--season" in result.output
        assert "--limit" in result.output
        assert "--offset" in result.output

    @patch("pitlane_agent.scripts.driver_info.get_driver_info")
    def test_cli_success(self, mock_get_info):
        """Test successful CLI execution."""
        mock_get_info.return_value = {
            "total_drivers": 1,
            "filters": {"driver_code": None, "season": None},
            "pagination": {"limit": 100, "offset": 0},
            "drivers": [{"driver_code": "VER", "full_name": "Max Verstappen"}],
        }

        runner = CliRunner()
        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["total_drivers"] == 1

    @patch("pitlane_agent.scripts.driver_info.get_driver_info")
    def test_cli_with_driver_code(self, mock_get_info):
        """Test CLI with driver code filter."""
        mock_get_info.return_value = {
            "total_drivers": 1,
            "filters": {"driver_code": "VER", "season": None},
            "pagination": {"limit": 100, "offset": 0},
            "drivers": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--driver-code", "VER"])

        assert result.exit_code == 0
        mock_get_info.assert_called_once_with(driver_code="VER", season=None, limit=100, offset=0)

    @patch("pitlane_agent.scripts.driver_info.get_driver_info")
    def test_cli_with_season(self, mock_get_info):
        """Test CLI with season filter."""
        mock_get_info.return_value = {
            "total_drivers": 20,
            "filters": {"driver_code": None, "season": 2024},
            "pagination": {"limit": 100, "offset": 0},
            "drivers": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--season", "2024"])

        assert result.exit_code == 0
        mock_get_info.assert_called_once_with(driver_code=None, season=2024, limit=100, offset=0)

    @patch("pitlane_agent.scripts.driver_info.get_driver_info")
    def test_cli_with_pagination(self, mock_get_info):
        """Test CLI with limit and offset."""
        mock_get_info.return_value = {
            "total_drivers": 10,
            "filters": {"driver_code": None, "season": None},
            "pagination": {"limit": 10, "offset": 50},
            "drivers": [],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--limit", "10", "--offset", "50"])

        assert result.exit_code == 0
        mock_get_info.assert_called_once_with(driver_code=None, season=None, limit=10, offset=50)

    def test_cli_invalid_season_too_old(self):
        """Test CLI rejects seasons before 1950."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--season", "1949"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "1950" in error["error"]

    def test_cli_invalid_season_too_future(self):
        """Test CLI rejects seasons too far in future."""
        runner = CliRunner()
        current_year = datetime.now().year
        future_year = current_year + 3

        result = runner.invoke(cli, ["--season", str(future_year)])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error

    @patch("pitlane_agent.scripts.driver_info.get_driver_info")
    def test_cli_error_handling(self, mock_get_info):
        """Test CLI error handling."""
        mock_get_info.side_effect = Exception("Ergast error")

        runner = CliRunner()
        result = runner.invoke(cli, [])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Ergast error" in error["error"]
