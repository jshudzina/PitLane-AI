"""Unit tests for fastf1_helpers module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pandas as pd
import pytest
from pitlane_agent.utils.fastf1_helpers import (
    build_chart_path,
    build_data_path,
    format_lap_time,
    format_sector_time,
    get_merged_telemetry,
    load_session_or_testing,
    load_testing_session,
    pick_lap_by_spec,
    validate_session_or_test,
)


class TestFormatLapTime:
    def test_valid_timedelta_formats_correctly(self):
        td = pd.Timedelta(seconds=89.456)
        assert format_lap_time(td) == "1:29.456"

    def test_sub_minute_lap_time(self):
        td = pd.Timedelta(seconds=59.123)
        assert format_lap_time(td) == "0:59.123"

    def test_nat_returns_none(self):
        assert format_lap_time(pd.NaT) is None

    def test_none_returns_none(self):
        assert format_lap_time(None) is None

    def test_three_decimal_places(self):
        td = pd.Timedelta(seconds=90.001)
        result = format_lap_time(td)
        assert result.endswith(".001")


class TestFormatSectorTime:
    def test_sub_minute_sector_no_minutes_prefix(self):
        td = pd.Timedelta(seconds=28.341)
        assert format_sector_time(td) == "28.341"

    def test_over_minute_sector_includes_minutes(self):
        td = pd.Timedelta(seconds=75.5)
        assert format_sector_time(td) == "1:15.500"

    def test_nat_returns_none(self):
        assert format_sector_time(pd.NaT) is None

    def test_none_returns_none(self):
        assert format_sector_time(None) is None

    def test_three_decimal_places(self):
        td = pd.Timedelta(seconds=30.007)
        assert format_sector_time(td) == "30.007"


class TestGetMergedTelemetry:
    """Unit tests for get_merged_telemetry function."""

    def test_get_merged_telemetry_success(self):
        """Test successful telemetry retrieval with all required channels."""
        # Mock lap object
        mock_lap = MagicMock()
        mock_telemetry = pd.DataFrame(
            {
                "X": [0.0, 100.0, 200.0],
                "Y": [0.0, 50.0, 100.0],
                "nGear": [3, 4, 5],
                "Speed": [150.0, 180.0, 200.0],
            }
        )
        mock_lap.get_telemetry.return_value = mock_telemetry

        # Call function with required channels
        result = get_merged_telemetry(mock_lap, required_channels=["X", "Y", "nGear"])

        # Verify
        assert not result.empty
        assert "X" in result.columns
        assert "Y" in result.columns
        assert "nGear" in result.columns
        assert len(result) == 3
        mock_lap.get_telemetry.assert_called_once()

    def test_get_merged_telemetry_no_required_channels(self):
        """Test telemetry retrieval without channel validation."""
        # Mock lap object
        mock_lap = MagicMock()
        mock_telemetry = pd.DataFrame(
            {
                "X": [0.0, 100.0],
                "Speed": [150.0, 180.0],
            }
        )
        mock_lap.get_telemetry.return_value = mock_telemetry

        # Call function without required channels
        result = get_merged_telemetry(mock_lap, required_channels=None)

        # Verify - should return telemetry without validation
        assert not result.empty
        assert len(result) == 2
        mock_lap.get_telemetry.assert_called_once()

    def test_get_merged_telemetry_empty_telemetry(self):
        """Test error when telemetry data is empty."""
        # Mock lap object with empty telemetry
        mock_lap = MagicMock()
        mock_lap.get_telemetry.return_value = pd.DataFrame()

        # Should raise ValueError
        with pytest.raises(ValueError, match="No telemetry data available for lap"):
            get_merged_telemetry(mock_lap)

    def test_get_merged_telemetry_missing_required_channels(self):
        """Test error when required channels are missing."""
        # Mock lap object with telemetry missing nGear
        mock_lap = MagicMock()
        mock_telemetry = pd.DataFrame(
            {
                "X": [0.0, 100.0, 200.0],
                "Y": [0.0, 50.0, 100.0],
                "Speed": [150.0, 180.0, 200.0],
                # Missing: nGear
            }
        )
        mock_lap.get_telemetry.return_value = mock_telemetry

        # Should raise ValueError with missing channels listed
        with pytest.raises(ValueError, match="Missing required telemetry channels: \\['nGear'\\]"):
            get_merged_telemetry(mock_lap, required_channels=["X", "Y", "nGear"])

    def test_get_merged_telemetry_multiple_missing_channels(self):
        """Test error when multiple required channels are missing."""
        # Mock lap object with telemetry missing multiple channels
        mock_lap = MagicMock()
        mock_telemetry = pd.DataFrame(
            {
                "Speed": [150.0, 180.0, 200.0],
                # Missing: X, Y, nGear
            }
        )
        mock_lap.get_telemetry.return_value = mock_telemetry

        # Should raise ValueError listing all missing channels
        with pytest.raises(ValueError, match="Missing required telemetry channels"):
            get_merged_telemetry(mock_lap, required_channels=["X", "Y", "nGear"])

        # Verify the error contains the missing channels
        try:
            get_merged_telemetry(mock_lap, required_channels=["X", "Y", "nGear"])
        except ValueError as e:
            assert "X" in str(e)
            assert "Y" in str(e)
            assert "nGear" in str(e)

    def test_get_merged_telemetry_extra_channels_ok(self):
        """Test that having extra channels beyond required is acceptable."""
        # Mock lap object with extra channels
        mock_lap = MagicMock()
        mock_telemetry = pd.DataFrame(
            {
                "X": [0.0, 100.0],
                "Y": [0.0, 50.0],
                "nGear": [3, 4],
                "Speed": [150.0, 180.0],
                "RPM": [8000, 9000],
                "Throttle": [80, 100],
            }
        )
        mock_lap.get_telemetry.return_value = mock_telemetry

        # Call function requesting only X, Y, nGear
        result = get_merged_telemetry(mock_lap, required_channels=["X", "Y", "nGear"])

        # Should succeed - extra channels are fine
        assert not result.empty
        assert len(result) == 2
        assert all(col in result.columns for col in ["X", "Y", "nGear", "Speed", "RPM", "Throttle"])

    def test_get_merged_telemetry_empty_required_channels_list(self):
        """Test with empty required channels list (different from None)."""
        # Mock lap object
        mock_lap = MagicMock()
        mock_telemetry = pd.DataFrame(
            {
                "X": [0.0, 100.0],
                "Speed": [150.0, 180.0],
            }
        )
        mock_lap.get_telemetry.return_value = mock_telemetry

        # Call with empty list (should not validate)
        result = get_merged_telemetry(mock_lap, required_channels=[])

        # Should succeed without validation
        assert not result.empty
        assert len(result) == 2


class TestBuildDataPath:
    """Unit tests for build_data_path function."""

    def test_session_scoped(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "session_info", year=2024, gp="Monaco", session_type="R")
        assert result == workspace / "data" / "session_info_2024_monaco_R.json"

    def test_session_scoped_with_diacritics(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "race_control", year=2024, gp="São Paulo", session_type="Q")
        assert result == workspace / "data" / "race_control_2024_sao_paulo_Q.json"

    def test_year_round_scoped(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "driver_standings", year=2024, round_number=10)
        assert result == workspace / "data" / "driver_standings_2024_round10.json"

    def test_year_scoped(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "driver_standings", year=2024)
        assert result == workspace / "data" / "driver_standings_2024.json"

    def test_year_only(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "season_summary", year=2024)
        assert result == workspace / "data" / "season_summary_2024.json"

    def test_driver_with_season(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "driver_info", driver_code="VER", season=2024)
        assert result == workspace / "data" / "driver_info_ver_2024.json"

    def test_driver_without_season(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "driver_info", driver_code="HAM")
        assert result == workspace / "data" / "driver_info_ham.json"

    def test_no_params_fallback(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "driver_info")
        assert result == workspace / "data" / "driver_info.json"

    def test_schedule_with_round(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "schedule", year=2024, round_number=5)
        assert result == workspace / "data" / "schedule_2024_round5.json"

    def test_schedule_without_round(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(workspace, "schedule", year=2024)
        assert result == workspace / "data" / "schedule_2024.json"

    def test_testing_session_scoped(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(
            workspace,
            "session_info",
            year=2026,
            test_number=1,
            session_number=2,
        )
        assert result == workspace / "data" / "session_info_2026_test1_day2.json"

    def test_testing_session_race_control(self):
        workspace = Path("/tmp/workspace")
        result = build_data_path(
            workspace,
            "race_control",
            year=2026,
            test_number=2,
            session_number=3,
        )
        assert result == workspace / "data" / "race_control_2026_test2_day3.json"

    def test_testing_takes_priority_over_gp(self):
        """When both test_number and gp are provided, testing takes priority."""
        workspace = Path("/tmp/workspace")
        result = build_data_path(
            workspace,
            "session_info",
            year=2026,
            gp="Monaco",
            session_type="R",
            test_number=1,
            session_number=1,
        )
        assert "test1" in str(result)
        assert "monaco" not in str(result)


class TestBuildChartPath:
    """Unit tests for build_chart_path with testing sessions."""

    def test_regular_session(self):
        workspace = Path("/tmp/workspace")
        result = build_chart_path(workspace, "lap_times", 2024, "Monaco", "Q", ["VER", "HAM"])
        assert result == workspace / "charts" / "lap_times_2024_monaco_Q_HAM_VER.png"

    def test_testing_session(self):
        workspace = Path("/tmp/workspace")
        result = build_chart_path(
            workspace,
            "lap_times",
            2026,
            "",
            "",
            ["VER", "HAM"],
            test_number=1,
            session_number=2,
        )
        assert result == workspace / "charts" / "lap_times_2026_test1_day2_HAM_VER.png"

    def test_testing_session_no_drivers(self):
        workspace = Path("/tmp/workspace")
        result = build_chart_path(
            workspace,
            "track_map",
            2026,
            "",
            "",
            test_number=2,
            session_number=1,
        )
        assert result == workspace / "charts" / "track_map_2026_test2_day1.png"


class TestLoadTestingSession:
    """Unit tests for load_testing_session function."""

    @patch("pitlane_agent.utils.fastf1_helpers.setup_fastf1_cache")
    @patch("pitlane_agent.utils.fastf1_helpers.fastf1")
    def test_load_testing_session_calls_correct_api(self, mock_fastf1, mock_cache):
        """Verify load_testing_session uses get_testing_session, not get_session."""
        mock_session = MagicMock()
        mock_fastf1.get_testing_session.return_value = mock_session

        result = load_testing_session(2026, 1, 2, telemetry=True)

        mock_fastf1.get_testing_session.assert_called_once_with(2026, 1, 2)
        mock_session.load.assert_called_once_with(telemetry=True, weather=False, messages=False)
        assert result == mock_session
        mock_cache.assert_called_once()

    @patch("pitlane_agent.utils.fastf1_helpers.setup_fastf1_cache")
    @patch("pitlane_agent.utils.fastf1_helpers.fastf1")
    def test_load_testing_session_with_messages(self, mock_fastf1, mock_cache):
        """Verify messages flag is passed through."""
        mock_session = MagicMock()
        mock_fastf1.get_testing_session.return_value = mock_session

        load_testing_session(2026, 2, 3, messages=True)

        mock_session.load.assert_called_once_with(telemetry=False, weather=False, messages=True)


class TestLoadSessionOrTesting:
    """Unit tests for load_session_or_testing dispatch helper."""

    @patch("pitlane_agent.utils.fastf1_helpers.setup_fastf1_cache")
    @patch("pitlane_agent.utils.fastf1_helpers.fastf1")
    def test_dispatches_to_testing_when_test_params_provided(self, mock_fastf1, mock_cache):
        mock_session = MagicMock()
        mock_fastf1.get_testing_session.return_value = mock_session

        result = load_session_or_testing(2026, None, None, test_number=1, session_number=2, telemetry=True)

        mock_fastf1.get_testing_session.assert_called_once_with(2026, 1, 2)
        mock_fastf1.get_session.assert_not_called()
        assert result == mock_session

    @patch("pitlane_agent.utils.fastf1_helpers.setup_fastf1_cache")
    @patch("pitlane_agent.utils.fastf1_helpers.fastf1")
    def test_dispatches_to_regular_when_gp_params_provided(self, mock_fastf1, mock_cache):
        mock_session = MagicMock()
        mock_fastf1.get_session.return_value = mock_session

        result = load_session_or_testing(2024, "Monaco", "Q", telemetry=True)

        mock_fastf1.get_session.assert_called_once_with(2024, "Monaco", "Q")
        mock_fastf1.get_testing_session.assert_not_called()
        assert result == mock_session


class TestValidateSessionOrTest:
    """Unit tests for validate_session_or_test."""

    def test_valid_gp_session(self):
        has_gp, has_test = validate_session_or_test("Monaco", "R", None, None)
        assert has_gp is True
        assert has_test is False

    def test_valid_testing_session(self):
        has_gp, has_test = validate_session_or_test(None, None, 1, 2)
        assert has_gp is False
        assert has_test is True

    def test_rejects_neither(self):
        with pytest.raises(click.UsageError, match="Must provide either"):
            validate_session_or_test(None, None, None, None)

    def test_rejects_both(self):
        with pytest.raises(click.UsageError, match="Cannot use"):
            validate_session_or_test("Monaco", "R", 1, 2)


class TestPickLapBySpec:
    """Unit tests for pick_lap_by_spec."""

    def _make_laps_df(self, lap_numbers: list[int]) -> pd.DataFrame:
        return pd.DataFrame({"LapNumber": [float(n) for n in lap_numbers]})

    def test_best_delegates_to_pick_fastest(self):
        mock_laps = MagicMock()
        mock_laps.pick_fastest.return_value = "fastest_lap"
        result = pick_lap_by_spec(mock_laps, "best")
        mock_laps.pick_fastest.assert_called_once()
        assert result == "fastest_lap"

    def test_invalid_lap_number_raises_with_available_laps(self):
        df = self._make_laps_df([1, 2, 3])
        with pytest.raises(ValueError, match="Lap 99 not found") as exc_info:
            pick_lap_by_spec(df, 99)
        assert "Available lap numbers: [1, 2, 3]" in str(exc_info.value)

    def test_invalid_lap_lists_all_available(self):
        df = self._make_laps_df([5, 10, 15, 20])
        with pytest.raises(ValueError) as exc_info:
            pick_lap_by_spec(df, 7)
        msg = str(exc_info.value)
        assert "5" in msg
        assert "10" in msg
        assert "15" in msg
        assert "20" in msg
