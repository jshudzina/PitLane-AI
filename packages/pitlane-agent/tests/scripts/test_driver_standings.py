"""Tests for driver_standings script."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from click.testing import CliRunner
from pitlane_agent.cli_fetch import fetch
from pitlane_agent.scripts.driver_standings import get_driver_standings


class TestDriverStandingsBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.scripts.driver_standings.ergast")
    def test_get_driver_standings_success(self, mock_ergast):
        """Test getting driver standings successfully."""
        # Mock ErgastMultiResponse structure
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 24}])
        mock_response.content = [
            pd.DataFrame(
                [
                    {
                        "position": 1,
                        "positionText": "1",
                        "points": 437.0,
                        "wins": 9,
                        "driverId": "max_verstappen",
                        "driverNumber": 3,
                        "driverCode": "VER",
                        "driverUrl": "http://en.wikipedia.org/wiki/Max_Verstappen",
                        "givenName": "Max",
                        "familyName": "Verstappen",
                        "dateOfBirth": pd.Timestamp("1997-09-30"),
                        "driverNationality": "Dutch",
                        "constructorIds": ["red_bull"],
                        "constructorUrls": ["https://en.wikipedia.org/wiki/Red_Bull_Racing"],
                        "constructorNames": ["Red Bull"],
                        "constructorNationalities": ["Austrian"],
                    }
                ]
            )
        ]

        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_standings.return_value = mock_response

        result = get_driver_standings(2024)

        assert result["year"] == 2024
        assert result["round"] == 24
        assert result["total_standings"] == 1
        assert result["filters"]["round"] is None
        assert len(result["standings"]) == 1

        # Check driver data
        driver = result["standings"][0]
        assert driver["position"] == 1
        assert driver["points"] == 437.0
        assert driver["wins"] == 9
        assert driver["driver_id"] == "max_verstappen"
        assert driver["driver_code"] == "VER"
        assert driver["driver_number"] == 3
        assert driver["given_name"] == "Max"
        assert driver["family_name"] == "Verstappen"
        assert driver["full_name"] == "Max Verstappen"
        assert driver["nationality"] == "Dutch"
        assert driver["date_of_birth"] == "1997-09-30"
        assert driver["teams"] == ["Red Bull"]
        assert driver["team_ids"] == ["red_bull"]

        mock_ergast_instance.get_driver_standings.assert_called_once_with(season=2024, round="last")

    @patch("pitlane_agent.scripts.driver_standings.ergast")
    def test_get_driver_standings_with_round(self, mock_ergast):
        """Test filtering by specific round number."""
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 10}])
        mock_response.content = [
            pd.DataFrame(
                [
                    {
                        "position": 1,
                        "positionText": "1",
                        "points": 200.0,
                        "wins": 5,
                        "driverId": "max_verstappen",
                        "driverNumber": 3,
                        "driverCode": "VER",
                        "driverUrl": "http://example.com",
                        "givenName": "Max",
                        "familyName": "Verstappen",
                        "dateOfBirth": pd.Timestamp("1997-09-30"),
                        "driverNationality": "Dutch",
                        "constructorIds": ["red_bull"],
                        "constructorUrls": ["http://example.com"],
                        "constructorNames": ["Red Bull"],
                        "constructorNationalities": ["Austrian"],
                    }
                ]
            )
        ]

        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_standings.return_value = mock_response

        result = get_driver_standings(2024, round_number=10)

        assert result["year"] == 2024
        assert result["round"] == 10
        assert result["filters"]["round"] == 10
        mock_ergast_instance.get_driver_standings.assert_called_once_with(season=2024, round=10)

    @patch("pitlane_agent.scripts.driver_standings.ergast")
    def test_get_driver_standings_empty_results(self, mock_ergast):
        """Test handling empty results."""
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 24}])
        mock_response.content = []

        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_standings.return_value = mock_response

        result = get_driver_standings(2024)

        assert result["year"] == 2024
        assert result["total_standings"] == 0
        assert result["standings"] == []

    @patch("pitlane_agent.scripts.driver_standings.ergast")
    def test_get_driver_standings_handles_nan_driver_number(self, mock_ergast):
        """Test handling NaN driver numbers for historical drivers."""
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 1950, "round": 7}])
        mock_response.content = [
            pd.DataFrame(
                [
                    {
                        "position": 1,
                        "positionText": "1",
                        "points": 30.0,
                        "wins": 3,
                        "driverId": "farina",
                        "driverNumber": pd.NA,
                        "driverCode": "FAR",
                        "driverUrl": "http://example.com",
                        "givenName": "Giuseppe",
                        "familyName": "Farina",
                        "dateOfBirth": pd.Timestamp("1906-10-30"),
                        "driverNationality": "Italian",
                        "constructorIds": ["alfa"],
                        "constructorUrls": ["http://example.com"],
                        "constructorNames": ["Alfa Romeo"],
                        "constructorNationalities": ["Italian"],
                    }
                ]
            )
        ]

        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_standings.return_value = mock_response

        result = get_driver_standings(1950)

        assert result["standings"][0]["driver_number"] is None

    @patch("pitlane_agent.scripts.driver_standings.ergast")
    def test_get_driver_standings_error(self, mock_ergast):
        """Test error handling."""
        mock_ergast_instance = mock_ergast.Ergast.return_value
        mock_ergast_instance.get_driver_standings.side_effect = Exception("Ergast API error")

        with pytest.raises(Exception, match="Ergast API error"):
            get_driver_standings(2024)


class TestDriverStandingsCLI:
    """Integration tests for CLI interface."""

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_driver_standings")
    def test_cli_success(self, mock_get_standings, mock_get_path, mock_exists):
        """Test successful CLI execution."""
        # Mock workspace functions
        mock_exists.return_value = True
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: Mock(__truediv__=lambda s, y: "/tmp/test/data/driver_standings.json")
        mock_get_path.return_value = mock_path

        # Mock standings data
        mock_get_standings.return_value = {
            "year": 2024,
            "round": 24,
            "total_standings": 20,
            "filters": {"round": None},
            "standings": [],
        }

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(fetch, ["driver-standings", "--session-id", "test-session", "--year", "2024"])

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["year"] == 2024
            assert output["round"] == 24
            assert output["total_standings"] == 20

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_driver_standings")
    def test_cli_with_round_filter(self, mock_get_standings, mock_get_path, mock_exists):
        """Test CLI with round filter."""
        mock_exists.return_value = True
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: Mock(__truediv__=lambda s, y: "/tmp/test/data/driver_standings.json")
        mock_get_path.return_value = mock_path

        mock_get_standings.return_value = {
            "year": 2024,
            "round": 10,
            "total_standings": 20,
            "filters": {"round": 10},
            "standings": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(
                fetch,
                ["driver-standings", "--session-id", "test-session", "--year", "2024", "--round", "10"],
            )

            assert result.exit_code == 0
            mock_get_standings.assert_called_once_with(2024, 10)

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_workspace_not_exists(self, mock_exists):
        """Test CLI with non-existent workspace."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(fetch, ["driver-standings", "--session-id", "nonexistent", "--year", "2024"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Workspace does not exist" in error["error"]

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_invalid_year_too_old(self, mock_exists):
        """Test CLI rejects years before 1950."""
        mock_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(fetch, ["driver-standings", "--session-id", "test-session", "--year", "1949"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "1950" in error["error"]

    def test_cli_invalid_year_too_future(self):
        """Test CLI rejects years too far in future."""
        runner = CliRunner()
        current_year = datetime.now().year
        future_year = current_year + 3

        result = runner.invoke(fetch, ["driver-standings", "--session-id", "test-session", "--year", str(future_year)])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_driver_standings")
    def test_cli_error_handling(self, mock_get_standings, mock_get_path, mock_exists):
        """Test CLI error handling."""
        mock_exists.return_value = True
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: Mock(__truediv__=lambda s, y: "/tmp/test/data/driver_standings.json")
        mock_get_path.return_value = mock_path
        mock_get_standings.side_effect = Exception("Ergast error")

        runner = CliRunner()
        result = runner.invoke(fetch, ["driver-standings", "--session-id", "test-session", "--year", "2024"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Ergast error" in error["error"]
