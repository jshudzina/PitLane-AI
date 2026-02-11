"""Tests for constructor_standings command."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from click.testing import CliRunner
from pitlane_agent.cli_fetch import fetch
from pitlane_agent.commands.fetch.constructor_standings import get_constructor_standings


class TestConstructorStandingsBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.fetch.constructor_standings.get_ergast_client")
    def test_get_constructor_standings_success(self, mock_get_ergast):
        """Test getting constructor standings successfully."""
        # Mock ErgastMultiResponse structure
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 24}])
        mock_response.content = [
            pd.DataFrame(
                [
                    {
                        "position": 1,
                        "positionText": "1",
                        "points": 666.0,
                        "wins": 6,
                        "constructorId": "mclaren",
                        "constructorUrl": "http://en.wikipedia.org/wiki/McLaren",
                        "constructorName": "McLaren",
                        "constructorNationality": "British",
                    }
                ]
            )
        ]

        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_constructor_standings.return_value = mock_response

        result = get_constructor_standings(2024)

        assert result["year"] == 2024
        assert result["round"] == 24
        assert result["total_standings"] == 1
        assert result["filters"]["round"] is None
        assert len(result["standings"]) == 1

        # Check constructor data
        constructor = result["standings"][0]
        assert constructor["position"] == 1
        assert constructor["points"] == 666.0
        assert constructor["wins"] == 6
        assert constructor["constructor_id"] == "mclaren"
        assert constructor["constructor_name"] == "McLaren"
        assert constructor["nationality"] == "British"

        mock_ergast_instance.get_constructor_standings.assert_called_once_with(season=2024, round="last")

    @patch("pitlane_agent.commands.fetch.constructor_standings.get_ergast_client")
    def test_get_constructor_standings_with_round(self, mock_get_ergast):
        """Test filtering by specific round number."""
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 10}])
        mock_response.content = [
            pd.DataFrame(
                [
                    {
                        "position": 1,
                        "positionText": "1",
                        "points": 300.0,
                        "wins": 3,
                        "constructorId": "red_bull",
                        "constructorUrl": "http://example.com",
                        "constructorName": "Red Bull",
                        "constructorNationality": "Austrian",
                    }
                ]
            )
        ]

        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_constructor_standings.return_value = mock_response

        result = get_constructor_standings(2024, round_number=10)

        assert result["year"] == 2024
        assert result["round"] == 10
        assert result["filters"]["round"] == 10
        mock_ergast_instance.get_constructor_standings.assert_called_once_with(season=2024, round=10)

    @patch("pitlane_agent.commands.fetch.constructor_standings.get_ergast_client")
    def test_get_constructor_standings_empty_results(self, mock_get_ergast):
        """Test handling empty results."""
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 24}])
        mock_response.content = []

        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_constructor_standings.return_value = mock_response

        result = get_constructor_standings(2024)

        assert result["year"] == 2024
        assert result["total_standings"] == 0
        assert result["standings"] == []

    @patch("pitlane_agent.commands.fetch.constructor_standings.get_ergast_client")
    def test_get_constructor_standings_multiple_teams(self, mock_get_ergast):
        """Test getting standings for multiple constructors."""
        mock_response = Mock()
        mock_response.description = pd.DataFrame([{"season": 2024, "round": 24}])
        mock_response.content = [
            pd.DataFrame(
                [
                    {
                        "position": 1,
                        "positionText": "1",
                        "points": 666.0,
                        "wins": 6,
                        "constructorId": "mclaren",
                        "constructorUrl": "http://example.com",
                        "constructorName": "McLaren",
                        "constructorNationality": "British",
                    },
                    {
                        "position": 2,
                        "positionText": "2",
                        "points": 652.0,
                        "wins": 5,
                        "constructorId": "ferrari",
                        "constructorUrl": "http://example.com",
                        "constructorName": "Ferrari",
                        "constructorNationality": "Italian",
                    },
                ]
            )
        ]

        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_constructor_standings.return_value = mock_response

        result = get_constructor_standings(2024)

        assert result["total_standings"] == 2
        assert result["standings"][0]["constructor_id"] == "mclaren"
        assert result["standings"][1]["constructor_id"] == "ferrari"

    @patch("pitlane_agent.commands.fetch.constructor_standings.get_ergast_client")
    def test_get_constructor_standings_error(self, mock_get_ergast):
        """Test error handling."""
        mock_ergast_instance = mock_get_ergast.return_value
        mock_ergast_instance.get_constructor_standings.side_effect = Exception("Ergast API error")

        with pytest.raises(Exception, match="Ergast API error"):
            get_constructor_standings(2024)


class TestConstructorStandingsCLI:
    """Integration tests for CLI interface."""

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_constructor_standings")
    def test_cli_success(self, mock_get_standings, mock_get_path, mock_exists):
        """Test successful CLI execution."""
        # Mock workspace functions
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/constructor_standings.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        # Mock standings data
        mock_get_standings.return_value = {
            "year": 2024,
            "round": 24,
            "total_standings": 10,
            "filters": {"round": None},
            "standings": [],
        }

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(fetch, ["constructor-standings", "--workspace-id", "test-session", "--year", "2024"])

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["year"] == 2024
            assert output["round"] == 24
            assert output["total_standings"] == 10

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_constructor_standings")
    def test_cli_with_round_filter(self, mock_get_standings, mock_get_path, mock_exists):
        """Test CLI with round filter."""
        mock_exists.return_value = True

        # Create mock file that doesn't exist yet
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_file.__str__ = lambda self: "/tmp/test/data/constructor_standings.json"

        # Create mock data dir
        mock_data_dir = Mock()
        mock_data_dir.__truediv__ = lambda self, x: mock_file

        # Create mock workspace path
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: mock_data_dir
        mock_get_path.return_value = mock_path

        mock_get_standings.return_value = {
            "year": 2024,
            "round": 10,
            "total_standings": 10,
            "filters": {"round": 10},
            "standings": [],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock()
            mock_open.return_value.__exit__ = Mock(return_value=False)

            runner = CliRunner()
            result = runner.invoke(
                fetch,
                [
                    "constructor-standings",
                    "--workspace-id",
                    "test-session",
                    "--year",
                    "2024",
                    "--round",
                    "10",
                ],
            )

            assert result.exit_code == 0
            mock_get_standings.assert_called_once_with(2024, 10)

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_workspace_not_exists(self, mock_exists):
        """Test CLI with non-existent workspace."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(fetch, ["constructor-standings", "--workspace-id", "nonexistent", "--year", "2024"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Workspace does not exist" in error["error"]

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    def test_cli_invalid_year_too_old(self, mock_exists):
        """Test CLI rejects years before 1950."""
        mock_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(fetch, ["constructor-standings", "--workspace-id", "test-session", "--year", "1949"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "1950" in error["error"]

    def test_cli_invalid_year_too_future(self):
        """Test CLI rejects years too far in future."""
        runner = CliRunner()
        current_year = datetime.now().year
        future_year = current_year + 3

        result = runner.invoke(
            fetch,
            ["constructor-standings", "--workspace-id", "test-session", "--year", str(future_year)],
        )

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error

    @patch("pitlane_agent.cli_fetch.workspace_exists")
    @patch("pitlane_agent.cli_fetch.get_workspace_path")
    @patch("pitlane_agent.cli_fetch.get_constructor_standings")
    def test_cli_error_handling(self, mock_get_standings, mock_get_path, mock_exists):
        """Test CLI error handling."""
        mock_exists.return_value = True
        mock_path = Mock()
        mock_path.__truediv__ = lambda self, x: Mock(
            __truediv__=lambda s, y: "/tmp/test/data/constructor_standings.json"
        )
        mock_get_path.return_value = mock_path
        mock_get_standings.side_effect = Exception("Ergast error")

        runner = CliRunner()
        result = runner.invoke(fetch, ["constructor-standings", "--workspace-id", "test-session", "--year", "2024"])

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert "error" in error
        assert "Ergast error" in error["error"]
