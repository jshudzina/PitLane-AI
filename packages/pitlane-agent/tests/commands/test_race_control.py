"""Tests for race_control command."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.fetch.race_control import (
    _filter_by_category,
    _filter_by_detail_level,
    _filter_by_driver,
    _filter_by_flag_type,
    _filter_by_lap_range,
    _filter_by_sector,
    _is_high_impact_message,
    _is_medium_impact_message,
    get_race_control_messages,
)


class TestIsHighImpactMessage:
    """Unit tests for _is_high_impact_message function."""

    def test_red_flag_is_high_impact(self):
        """Test that RED flag is identified as high impact."""
        row = pd.Series({"Category": "Flag", "Flag": "RED", "Message": "RED FLAG", "Lap": 1})
        assert _is_high_impact_message(row) is True

    def test_safety_car_is_high_impact(self):
        """Test that SafetyCar messages are high impact."""
        row = pd.Series({"Category": "SafetyCar", "Flag": None, "Message": "SAFETY CAR DEPLOYED", "Lap": 5})
        assert _is_high_impact_message(row) is True

    def test_chequered_flag_is_high_impact(self):
        """Test that CHEQUERED flag is high impact."""
        row = pd.Series({"Category": "Flag", "Flag": "CHEQUERED", "Message": "CHEQUERED FLAG", "Lap": 78})
        assert _is_high_impact_message(row) is True

    def test_race_start_green_is_high_impact(self):
        """Test that race start GREEN light is high impact."""
        row = pd.Series(
            {
                "Category": "Flag",
                "Flag": "GREEN",
                "Message": "GREEN LIGHT - PIT EXIT OPEN",
                "Lap": 1,
            }
        )
        assert _is_high_impact_message(row) is True

    def test_collision_is_high_impact(self):
        """Test that collision messages are high impact."""
        row = pd.Series(
            {
                "Category": "Other",
                "Flag": None,
                "Message": "TURN 1 INCIDENT INVOLVING CARS 10 AND 31 - CAUSING A COLLISION",
                "Lap": 1,
            }
        )
        assert _is_high_impact_message(row) is True

    def test_blue_flag_is_not_high_impact(self):
        """Test that BLUE flag is not high impact."""
        row = pd.Series({"Category": "Flag", "Flag": "BLUE", "Message": "BLUE FLAG FOR CAR 18", "Lap": 10})
        assert _is_high_impact_message(row) is False

    def test_track_limits_is_not_high_impact(self):
        """Test that track limits violation is not high impact."""
        row = pd.Series(
            {
                "Category": "Other",
                "Flag": None,
                "Message": "CAR 55 (SAI) LAP DELETED - TRACK LIMITS AT TURN 7",
                "Lap": 5,
            }
        )
        assert _is_high_impact_message(row) is False


class TestIsMediumImpactMessage:
    """Unit tests for _is_medium_impact_message function."""

    def test_double_yellow_is_medium_impact(self):
        """Test that DOUBLE YELLOW is medium impact."""
        row = pd.Series(
            {
                "Category": "Flag",
                "Flag": "DOUBLE YELLOW",
                "Message": "DOUBLE YELLOW IN TRACK SECTOR 3",
                "Lap": 1,
            }
        )
        assert _is_medium_impact_message(row) is True

    def test_single_yellow_is_medium_impact(self):
        """Test that single YELLOW is medium impact."""
        row = pd.Series({"Category": "Flag", "Flag": "YELLOW", "Message": "YELLOW IN TRACK SECTOR 6", "Lap": 1})
        assert _is_medium_impact_message(row) is True

    def test_drs_is_medium_impact(self):
        """Test that DRS messages are medium impact."""
        row = pd.Series({"Category": "Drs", "Flag": None, "Message": "DRS ENABLED", "Lap": 2})
        assert _is_medium_impact_message(row) is True

    def test_penalty_is_medium_impact(self):
        """Test that penalties are medium impact."""
        row = pd.Series(
            {
                "Category": "Other",
                "Flag": None,
                "Message": "FIA STEWARDS: 10 SECOND TIME PENALTY FOR CAR 31 (OCO)",
                "Lap": 8,
            }
        )
        assert _is_medium_impact_message(row) is True

    def test_no_further_investigation_is_not_medium_impact(self):
        """Test that NO FURTHER INVESTIGATION is not medium impact."""
        row = pd.Series(
            {
                "Category": "Other",
                "Flag": None,
                "Message": "FIA STEWARDS: INCIDENT REVIEWED NO FURTHER INVESTIGATION",
                "Lap": 10,
            }
        )
        assert _is_medium_impact_message(row) is False

    def test_clear_flag_is_not_medium_impact(self):
        """Test that CLEAR flag is not medium impact."""
        row = pd.Series({"Category": "Flag", "Flag": "CLEAR", "Message": "CLEAR IN TRACK SECTOR 3", "Lap": 2})
        assert _is_medium_impact_message(row) is False


class TestFilterByDetailLevel:
    """Unit tests for _filter_by_detail_level function."""

    def test_full_detail_returns_all(self):
        """Test that full detail returns all messages."""
        df = pd.DataFrame(
            {
                "Category": ["Flag", "Flag", "Other", "Drs"],
                "Flag": ["RED", "BLUE", None, None],
                "Message": ["RED FLAG", "BLUE FLAG", "TRACK LIMITS", "DRS ENABLED"],
                "Lap": [1, 10, 15, 2],
            }
        )

        result = _filter_by_detail_level(df, "full")
        assert len(result) == 4

    def test_high_detail_filters_correctly(self):
        """Test that high detail only returns high-impact messages."""
        df = pd.DataFrame(
            {
                "Category": ["Flag", "Flag", "Flag", "Drs", "SafetyCar"],
                "Flag": ["RED", "BLUE", "YELLOW", None, None],
                "Message": [
                    "RED FLAG",
                    "BLUE FLAG",
                    "YELLOW IN SECTOR 1",
                    "DRS ENABLED",
                    "SAFETY CAR DEPLOYED",
                ],
                "Lap": [1, 10, 15, 2, 20],
            }
        )

        result = _filter_by_detail_level(df, "high")
        assert len(result) == 2  # RED flag and SAFETY CAR
        assert "RED" in result["Flag"].values
        assert result["Category"].tolist() == ["Flag", "SafetyCar"]

    def test_medium_detail_includes_high_and_medium(self):
        """Test that medium detail includes both high and medium impact messages."""
        df = pd.DataFrame(
            {
                "Category": ["Flag", "Flag", "Flag", "Drs"],
                "Flag": ["RED", "BLUE", "YELLOW", None],
                "Message": ["RED FLAG", "BLUE FLAG", "YELLOW IN SECTOR 1", "DRS ENABLED"],
                "Lap": [1, 10, 15, 2],
            }
        )

        result = _filter_by_detail_level(df, "medium")
        # Should include RED (high), YELLOW (medium), DRS (medium)
        # Should exclude BLUE (low)
        assert len(result) == 3
        assert "BLUE" not in result["Flag"].values

    def test_invalid_detail_level_raises_error(self):
        """Test that invalid detail level raises ValueError."""
        df = pd.DataFrame(
            {
                "Category": ["Flag"],
                "Flag": ["RED"],
                "Message": ["RED FLAG"],
                "Lap": [1],
            }
        )

        with pytest.raises(ValueError, match="Invalid detail level: 'invalid'"):
            _filter_by_detail_level(df, "invalid")

        with pytest.raises(ValueError, match="Invalid detail level: 'HIGH'"):
            _filter_by_detail_level(df, "HIGH")  # Case-sensitive check


class TestFilterByCategory:
    """Unit tests for _filter_by_category function."""

    def test_filter_by_flag_category(self):
        """Test filtering by Flag category."""
        df = pd.DataFrame(
            {
                "Category": ["Flag", "Other", "Flag", "Drs"],
                "Message": ["RED FLAG", "INCIDENT", "YELLOW FLAG", "DRS ENABLED"],
            }
        )

        result = _filter_by_category(df, "Flag")
        assert len(result) == 2
        assert all(result["Category"] == "Flag")

    def test_filter_by_safety_car_category(self):
        """Test filtering by SafetyCar category."""
        df = pd.DataFrame(
            {
                "Category": ["SafetyCar", "Other", "Flag", "SafetyCar"],
                "Message": ["SC DEPLOYED", "INCIDENT", "RED FLAG", "SC IN THIS LAP"],
            }
        )

        result = _filter_by_category(df, "SafetyCar")
        assert len(result) == 2
        assert all(result["Category"] == "SafetyCar")

    def test_no_filter_when_none(self):
        """Test that None category returns all messages."""
        df = pd.DataFrame({"Category": ["Flag", "Other", "Drs"], "Message": ["RED", "INCIDENT", "DRS ENABLED"]})

        result = _filter_by_category(df, None)
        assert len(result) == 3


class TestFilterByFlagType:
    """Unit tests for _filter_by_flag_type function."""

    def test_filter_by_red_flag(self):
        """Test filtering by RED flag type."""
        df = pd.DataFrame(
            {
                "Flag": ["RED", "YELLOW", "BLUE", None],
                "Message": ["RED FLAG", "YELLOW", "BLUE", "DRS"],
            }
        )

        result = _filter_by_flag_type(df, "RED")
        assert len(result) == 1
        assert result.iloc[0]["Flag"] == "RED"

    def test_filter_case_insensitive(self):
        """Test that flag type filtering is case-insensitive."""
        df = pd.DataFrame({"Flag": ["RED", "YELLOW"], "Message": ["RED FLAG", "YELLOW"]})

        result = _filter_by_flag_type(df, "red")
        assert len(result) == 1
        assert result.iloc[0]["Flag"] == "RED"

    def test_no_filter_when_none(self):
        """Test that None flag type returns all messages."""
        df = pd.DataFrame({"Flag": ["RED", "YELLOW", "BLUE"], "Message": ["R", "Y", "B"]})

        result = _filter_by_flag_type(df, None)
        assert len(result) == 3


class TestFilterByDriver:
    """Unit tests for _filter_by_driver function."""

    def test_filter_by_driver_number(self):
        """Test filtering by driver racing number."""
        df = pd.DataFrame(
            {
                "RacingNumber": ["1", "44", "16", None],
                "Message": ["VER", "HAM", "LEC", "GENERAL"],
            }
        )

        result = _filter_by_driver(df, "1")
        assert len(result) == 1
        assert result.iloc[0]["RacingNumber"] == "1"

    def test_no_filter_when_none(self):
        """Test that None driver returns all messages."""
        df = pd.DataFrame({"RacingNumber": ["1", "44", None], "Message": ["VER", "HAM", "GENERAL"]})

        result = _filter_by_driver(df, None)
        assert len(result) == 3


class TestFilterByLapRange:
    """Unit tests for _filter_by_lap_range function."""

    def test_filter_by_lap_start_only(self):
        """Test filtering with only lap_start specified."""
        df = pd.DataFrame({"Lap": [1, 5, 10, 15, 20], "Message": ["A", "B", "C", "D", "E"]})

        result = _filter_by_lap_range(df, 10, None)
        assert len(result) == 3
        assert result["Lap"].min() >= 10

    def test_filter_by_lap_end_only(self):
        """Test filtering with only lap_end specified."""
        df = pd.DataFrame({"Lap": [1, 5, 10, 15, 20], "Message": ["A", "B", "C", "D", "E"]})

        result = _filter_by_lap_range(df, None, 10)
        assert len(result) == 3
        assert result["Lap"].max() <= 10

    def test_filter_by_lap_range_both(self):
        """Test filtering with both lap_start and lap_end."""
        df = pd.DataFrame({"Lap": [1, 5, 10, 15, 20], "Message": ["A", "B", "C", "D", "E"]})

        result = _filter_by_lap_range(df, 5, 15)
        assert len(result) == 3
        assert result["Lap"].min() >= 5
        assert result["Lap"].max() <= 15

    def test_no_filter_when_both_none(self):
        """Test that None for both returns all messages."""
        df = pd.DataFrame({"Lap": [1, 5, 10], "Message": ["A", "B", "C"]})

        result = _filter_by_lap_range(df, None, None)
        assert len(result) == 3


class TestFilterBySector:
    """Unit tests for _filter_by_sector function."""

    def test_filter_by_sector(self):
        """Test filtering by sector number."""
        df = pd.DataFrame({"Sector": [3, 7, 12, None], "Message": ["A", "B", "C", "D"]})

        result = _filter_by_sector(df, 7)
        assert len(result) == 1
        assert result.iloc[0]["Sector"] == 7

    def test_no_filter_when_none(self):
        """Test that None sector returns all messages."""
        df = pd.DataFrame({"Sector": [3, 7, None], "Message": ["A", "B", "C"]})

        result = _filter_by_sector(df, None)
        assert len(result) == 3


class TestGetRaceControlMessages:
    """Integration tests for get_race_control_messages function."""

    @patch("pitlane_agent.commands.fetch.race_control.load_session")
    def test_get_race_control_messages_basic(self, mock_load_session):
        """Test basic fetching of race control messages without filters."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
        mock_session.name = "Race"

        # Create sample messages DataFrame
        messages_df = pd.DataFrame(
            {
                "Time": pd.to_datetime(["2024-05-26 13:00:00", "2024-05-26 13:01:00"]),
                "Category": ["Flag", "Other"],
                "Message": ["RED FLAG", "INCIDENT NOTED"],
                "Status": [None, None],
                "Flag": ["RED", None],
                "Scope": ["Track", None],
                "Sector": [None, None],
                "RacingNumber": [None, None],
                "Lap": [1, 1],
            }
        )
        mock_session.race_control_messages = messages_df
        mock_load_session.return_value = mock_session

        result = get_race_control_messages(2024, "Monaco", "R", detail="full")

        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["total_messages"] == 2
        assert result["filtered_messages"] == 2
        assert len(result["messages"]) == 2

    @patch("pitlane_agent.commands.fetch.race_control.load_session")
    def test_filter_by_detail_high(self, mock_load_session):
        """Test filtering with high detail level."""
        mock_session = MagicMock()
        mock_session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
        mock_session.name = "Race"

        messages_df = pd.DataFrame(
            {
                "Time": pd.to_datetime(["2024-05-26 13:00:00", "2024-05-26 13:01:00", "2024-05-26 13:02:00"]),
                "Category": ["Flag", "Flag", "SafetyCar"],
                "Message": ["RED FLAG", "BLUE FLAG FOR CAR 18", "SAFETY CAR DEPLOYED"],
                "Status": [None, None, None],
                "Flag": ["RED", "BLUE", None],
                "Scope": ["Track", "Driver", None],
                "Sector": [None, None, None],
                "RacingNumber": [None, "18", None],
                "Lap": [1, 10, 15],
            }
        )
        mock_session.race_control_messages = messages_df
        mock_load_session.return_value = mock_session

        result = get_race_control_messages(2024, "Monaco", "R", detail="high")

        # Should only get RED flag and SAFETY CAR (not BLUE flag)
        assert result["filtered_messages"] == 2
        assert result["filters_applied"]["detail"] == "high"

    @patch("pitlane_agent.commands.fetch.race_control.load_session")
    def test_filter_by_category(self, mock_load_session):
        """Test filtering by category."""
        mock_session = MagicMock()
        mock_session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
        mock_session.name = "Race"

        messages_df = pd.DataFrame(
            {
                "Time": pd.to_datetime(["2024-05-26 13:00:00", "2024-05-26 13:01:00", "2024-05-26 13:02:00"]),
                "Category": ["Flag", "Other", "Flag"],
                "Message": ["RED FLAG", "INCIDENT", "BLUE FLAG"],
                "Status": [None, None, None],
                "Flag": ["RED", None, "BLUE"],
                "Scope": ["Track", None, "Driver"],
                "Sector": [None, None, None],
                "RacingNumber": [None, None, "18"],
                "Lap": [1, 1, 10],
            }
        )
        mock_session.race_control_messages = messages_df
        mock_load_session.return_value = mock_session

        result = get_race_control_messages(2024, "Monaco", "R", category="Flag", detail="full")

        assert result["filtered_messages"] == 2
        assert result["filters_applied"]["category"] == "Flag"

    @patch("pitlane_agent.commands.fetch.race_control.load_session")
    def test_filter_combination(self, mock_load_session):
        """Test combining multiple filters."""
        mock_session = MagicMock()
        mock_session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
        mock_session.name = "Race"

        messages_df = pd.DataFrame(
            {
                "Time": pd.to_datetime(
                    [
                        "2024-05-26 13:00:00",
                        "2024-05-26 13:01:00",
                        "2024-05-26 13:02:00",
                        "2024-05-26 13:03:00",
                    ]
                ),
                "Category": ["Flag", "Flag", "Flag", "Other"],
                "Message": ["RED FLAG", "YELLOW SECTOR 3", "BLUE FLAG", "INCIDENT"],
                "Status": [None, None, None, None],
                "Flag": ["RED", "YELLOW", "BLUE", None],
                "Scope": ["Track", "Sector", "Driver", None],
                "Sector": [None, 3, None, None],
                "RacingNumber": [None, None, "18", None],
                "Lap": [1, 5, 10, 15],
            }
        )
        mock_session.race_control_messages = messages_df
        mock_load_session.return_value = mock_session

        result = get_race_control_messages(2024, "Monaco", "R", category="Flag", lap_start=1, lap_end=10, detail="full")

        # Should get RED, YELLOW, and BLUE (all Flag category, laps 1-10)
        assert result["filtered_messages"] == 3
        assert result["filters_applied"]["category"] == "Flag"
        assert result["filters_applied"]["lap_start"] == 1
        assert result["filters_applied"]["lap_end"] == 10

    @patch("pitlane_agent.commands.fetch.race_control.load_session")
    def test_session_without_messages(self, mock_load_session):
        """Test handling session without race control messages."""
        mock_session = MagicMock()
        mock_session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
        mock_session.name = "Race"
        mock_session.race_control_messages = None
        mock_load_session.return_value = mock_session

        result = get_race_control_messages(2024, "Monaco", "R")

        assert result["total_messages"] == 0
        assert result["filtered_messages"] == 0
        assert len(result["messages"]) == 0

    @patch("pitlane_agent.commands.fetch.race_control.load_session")
    def test_session_with_attribute_error(self, mock_load_session):
        """Test handling when race_control_messages attribute doesn't exist."""
        mock_session = MagicMock()
        mock_session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
        mock_session.name = "Race"
        # Simulate AttributeError when accessing race_control_messages
        type(mock_session).race_control_messages = property(
            lambda self: (_ for _ in ()).throw(AttributeError("No race control messages"))
        )
        mock_load_session.return_value = mock_session

        result = get_race_control_messages(2024, "Monaco", "R")

        assert result["total_messages"] == 0
        assert result["filtered_messages"] == 0
        assert len(result["messages"]) == 0
