"""Tests for session_info command."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastf1.exceptions import DataNotLoadedError
from pitlane_agent.commands.fetch.session_info import (
    _extract_track_status,
    _extract_weather_data,
    _format_classified_position,
    _format_finish_time,
    _nonempty_str,
    get_session_info,
)


class TestFormatClassifiedPosition:
    """Unit tests for _format_classified_position."""

    def test_integer_positions(self):
        assert _format_classified_position(1) == "1st"
        assert _format_classified_position(2) == "2nd"
        assert _format_classified_position(3) == "3rd"
        assert _format_classified_position(4) == "4th"
        assert _format_classified_position(11) == "11th"
        assert _format_classified_position(12) == "12th"
        assert _format_classified_position(21) == "21st"

    def test_numeric_string_positions(self):
        assert _format_classified_position("1") == "1st"
        assert _format_classified_position("20") == "20th"

    def test_code_mapping(self):
        assert _format_classified_position("R") == "Retired"
        assert _format_classified_position("D") == "Disqualified"
        assert _format_classified_position("E") == "Excluded"
        assert _format_classified_position("W") == "Withdrawn"
        assert _format_classified_position("F") == "Failed to Qualify"
        assert _format_classified_position("N") == "Not Classified"

    def test_nan_returns_none(self):
        assert _format_classified_position(float("nan")) is None
        assert _format_classified_position(None) is None


class TestNonemptyStr:
    """Unit tests for _nonempty_str."""

    def test_normal_string(self):
        assert _nonempty_str("Engine") == "Engine"

    def test_empty_string_returns_none(self):
        assert _nonempty_str("") is None
        assert _nonempty_str("   ") is None

    def test_nan_returns_none(self):
        assert _nonempty_str(float("nan")) is None
        assert _nonempty_str(None) is None

    def test_nat_returns_none(self):
        assert _nonempty_str(pd.NaT) is None


class TestFormatFinishTime:
    """Unit tests for _format_finish_time."""

    def test_timedelta_under_one_hour(self):
        result = _format_finish_time(timedelta(minutes=5, seconds=13, milliseconds=456))
        assert result == "5:13.456"

    def test_timedelta_over_one_hour(self):
        result = _format_finish_time(timedelta(hours=1, minutes=32, seconds=45, milliseconds=213))
        assert result == "1:32:45.213"

    def test_nat_returns_none(self):
        assert _format_finish_time(pd.NaT) is None

    def test_none_returns_none(self):
        assert _format_finish_time(None) is None


class TestExtractTrackStatus:
    """Unit tests for _extract_track_status function."""

    def test_extract_track_status_with_data(self):
        """Test extracting track status with valid data."""
        mock_session = MagicMock()
        track_status_data = pd.DataFrame({"Status": ["1", "1", "4", "4", "5", "6", "7", "1"]})
        mock_session.track_status = track_status_data

        result = _extract_track_status(mock_session)

        assert result is not None
        assert result["num_safety_cars"] == 2
        assert result["num_virtual_safety_cars"] == 1
        assert result["num_red_flags"] == 1

    def test_extract_track_status_no_incidents(self):
        """Test extracting track status with no incidents."""
        mock_session = MagicMock()
        track_status_data = pd.DataFrame({"Status": ["1", "1", "1", "2", "2"]})
        mock_session.track_status = track_status_data

        result = _extract_track_status(mock_session)

        assert result is not None
        assert result["num_safety_cars"] == 0
        assert result["num_virtual_safety_cars"] == 0
        assert result["num_red_flags"] == 0

    def test_extract_track_status_data_not_loaded(self):
        """Test handling when track status data is not loaded."""
        mock_session = MagicMock()
        type(mock_session).track_status = property(
            lambda self: (_ for _ in ()).throw(DataNotLoadedError("Track status not loaded"))
        )

        result = _extract_track_status(mock_session)

        assert result is None

    def test_extract_track_status_multiple_incidents(self):
        """Test extracting track status with multiple incidents of same type."""
        mock_session = MagicMock()
        track_status_data = pd.DataFrame({"Status": ["4", "1", "4", "4", "5", "5", "6", "6", "6", "7", "7", "7"]})
        mock_session.track_status = track_status_data

        result = _extract_track_status(mock_session)

        assert result is not None
        assert result["num_safety_cars"] == 3
        assert result["num_virtual_safety_cars"] == 3
        assert result["num_red_flags"] == 2


class TestExtractWeatherData:
    """Unit tests for _extract_weather_data function."""

    def test_extract_weather_data_with_complete_data(self):
        """Test extracting weather data with all metrics present."""
        mock_session = MagicMock()
        weather_data = pd.DataFrame(
            {
                "AirTemp": [22.5, 23.0, 24.5, 23.5],
                "TrackTemp": [35.0, 36.5, 38.0, 37.0],
                "Humidity": [45.0, 47.0, 46.0, 48.0],
                "Pressure": [1013.25, 1013.50, 1013.30, 1013.40],
                "WindSpeed": [2.5, 3.0, 2.8, 3.2],
            }
        )
        mock_session.weather_data = weather_data

        result = _extract_weather_data(mock_session)

        assert result is not None
        assert result["air_temp"]["min"] == 22.5
        assert result["air_temp"]["max"] == 24.5
        assert result["air_temp"]["avg"] == 23.38
        assert result["track_temp"]["min"] == 35.0
        assert result["track_temp"]["max"] == 38.0
        assert result["humidity"]["min"] == 45.0
        assert result["humidity"]["max"] == 48.0
        assert result["pressure"]["min"] == 1013.25
        assert result["pressure"]["max"] == 1013.50
        assert result["wind_speed"]["min"] == 2.5
        assert result["wind_speed"]["max"] == 3.2
        assert result["rain_percentage"] is None

    def test_extract_weather_data_with_rainfall(self):
        """Test extracting weather data with Rainfall column."""
        mock_session = MagicMock()
        weather_data = pd.DataFrame(
            {
                "AirTemp": [22.5, 23.0],
                "TrackTemp": [35.0, 36.5],
                "Humidity": [45.0, 47.0],
                "Pressure": [1013.25, 1013.50],
                "WindSpeed": [2.5, 3.0],
                "Rainfall": [True, False],
            }
        )
        mock_session.weather_data = weather_data

        result = _extract_weather_data(mock_session)

        assert result is not None
        assert result["rain_percentage"] == 50.0

    def test_extract_weather_data_with_nan_values(self):
        """Test extracting weather data with NaN values."""
        mock_session = MagicMock()
        weather_data = pd.DataFrame(
            {
                "AirTemp": [22.5, float("nan"), 24.5, 23.5],
                "TrackTemp": [35.0, 36.5, float("nan"), 37.0],
                "Humidity": [45.0, 47.0, 46.0, 48.0],
                "Pressure": [float("nan"), float("nan"), float("nan"), float("nan")],
                "WindSpeed": [2.5, 3.0, 2.8, 3.2],
            }
        )
        mock_session.weather_data = weather_data

        result = _extract_weather_data(mock_session)

        assert result is not None
        assert result["air_temp"]["min"] == 22.5
        assert result["air_temp"]["max"] == 24.5
        assert result["pressure"]["min"] is None
        assert result["pressure"]["max"] is None
        assert result["pressure"]["avg"] is None

    def test_extract_weather_data_missing_columns(self):
        """Test extracting weather data with missing columns."""
        mock_session = MagicMock()
        weather_data = pd.DataFrame(
            {
                "AirTemp": [22.5, 23.0, 24.5],
                "Humidity": [45.0, 47.0, 46.0],
                # Missing TrackTemp, Pressure, WindSpeed
            }
        )
        mock_session.weather_data = weather_data

        result = _extract_weather_data(mock_session)

        assert result is not None
        assert result["air_temp"]["min"] == 22.5
        assert result["track_temp"]["min"] is None
        assert result["track_temp"]["max"] is None
        assert result["track_temp"]["avg"] is None
        assert result["pressure"]["min"] is None
        assert result["wind_speed"]["min"] is None

    def test_extract_weather_data_empty_dataframe(self):
        """Test extracting weather data from empty DataFrame."""
        mock_session = MagicMock()
        mock_session.weather_data = pd.DataFrame()

        result = _extract_weather_data(mock_session)

        assert result is None

    def test_extract_weather_data_not_loaded(self):
        """Test handling when weather data is not loaded."""
        mock_session = MagicMock()
        type(mock_session).weather_data = property(
            lambda self: (_ for _ in ()).throw(DataNotLoadedError("Weather data not loaded"))
        )

        result = _extract_weather_data(mock_session)

        assert result is None


def _make_driver_df(rows: list[dict]) -> pd.DataFrame:
    """Build a driver results DataFrame with all required columns, filling defaults."""
    defaults = {
        "Abbreviation": "UNK",
        "FirstName": "Unknown",
        "LastName": "Driver",
        "TeamName": "Unknown Team",
        "DriverNumber": float("nan"),
        "Position": float("nan"),
        "GridPosition": float("nan"),
        "ClassifiedPosition": float("nan"),
        "Status": float("nan"),
        "Time": pd.NaT,
        "Points": float("nan"),
        "Q1": pd.NaT,
        "Q2": pd.NaT,
        "Q3": pd.NaT,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


class TestSessionInfoBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.fetch.session_info.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_success(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_get_circuit_length,
        mock_fastf1_session,
    ):
        """Test successful session info retrieval."""
        mock_load_session.return_value = mock_fastf1_session
        mock_get_circuit_length.return_value = 3.337

        mock_fastf1_session.results = _make_driver_df(
            [
                {
                    "Abbreviation": "VER",
                    "FirstName": "Max",
                    "LastName": "Verstappen",
                    "TeamName": "Red Bull Racing",
                    "DriverNumber": 1,
                    "Position": 1,
                    "GridPosition": 1,
                    "ClassifiedPosition": 1,
                    "Status": "Finished",
                    "Time": timedelta(hours=1, minutes=32, seconds=45, milliseconds=213),
                    "Points": 25.0,
                    "Q1": timedelta(minutes=1, seconds=10, milliseconds=500),
                    "Q2": timedelta(minutes=1, seconds=9, milliseconds=800),
                    "Q3": timedelta(minutes=1, seconds=9, milliseconds=100),
                }
            ]
        )

        mock_extract_track_status.return_value = {
            "num_safety_cars": 2,
            "num_virtual_safety_cars": 1,
            "num_red_flags": 0,
        }
        mock_extract_weather_data.return_value = {
            "air_temp": {"min": 22.5, "max": 24.5, "avg": 23.5},
            "track_temp": {"min": 35.0, "max": 38.0, "avg": 36.5},
            "humidity": {"min": 45.0, "max": 48.0, "avg": 46.5},
            "pressure": {"min": 1013.25, "max": 1013.50, "avg": 1013.38},
            "wind_speed": {"min": 2.5, "max": 3.2, "avg": 2.85},
        }

        result = get_session_info(2024, "Monaco", "Q")

        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["country"] == "Monaco"
        assert result["session_type"] == "Q"
        assert result["session_name"] == "Qualifying"
        assert len(result["drivers"]) == 1

        driver = result["drivers"][0]
        assert driver["abbreviation"] == "VER"
        assert driver["name"] == "Max Verstappen"
        assert driver["number"] == 1
        assert driver["position"] == 1
        assert driver["grid_position"] == 1
        assert driver["classified_position"] == "1st"
        assert driver["status"] == "Finished"
        assert driver["finish_time"] == "1:32:45.213"
        assert driver["points"] == 25.0
        assert driver["q1"] == "1:10.500"
        assert driver["q2"] == "1:09.800"
        assert driver["q3"] == "1:09.100"

        assert result["race_conditions"] is not None
        assert result["race_conditions"]["num_safety_cars"] == 2
        assert result["weather"] is not None
        assert result["weather"]["air_temp"]["avg"] == 23.5
        assert result["circuit_length_km"] == 3.337
        assert result["race_summary"] is None  # non-race session

        mock_load_session.assert_called_once_with(2024, "Monaco", "Q", weather=True, messages=True)

    @patch("pitlane_agent.commands.fetch.session_info.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.session_info.compute_race_summary_stats")
    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_race_includes_summary(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_compute_stats,
        mock_get_circuit_length,
        mock_fastf1_session,
    ):
        """Test that race sessions include race_summary stats."""
        mock_load_session.return_value = mock_fastf1_session
        mock_get_circuit_length.return_value = 3.337

        mock_fastf1_session.results = _make_driver_df(
            [
                {
                    "Abbreviation": "VER",
                    "FirstName": "Max",
                    "LastName": "Verstappen",
                    "TeamName": "Red Bull Racing",
                    "DriverNumber": 1,
                    "Position": 1,
                    "ClassifiedPosition": 1,
                    "Status": "Finished",
                    "Points": 25.0,
                }
            ]
        )
        mock_extract_track_status.return_value = None
        mock_extract_weather_data.return_value = None
        mock_compute_stats.return_value = {
            "total_overtakes": 42,
            "total_position_changes": 20,
            "average_volatility": 2.5,
            "mean_pit_stops": 1.8,
            "total_laps": 78,
        }

        result = get_session_info(2024, "Monaco", "R")

        assert result["race_summary"] is not None
        assert result["race_summary"]["total_overtakes"] == 42
        assert result["race_summary"]["mean_pit_stops"] == 1.8
        assert result["race_summary"]["total_laps"] == 78
        mock_compute_stats.assert_called_once()

    @patch("pitlane_agent.commands.fetch.session_info.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_with_nan_values(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_get_circuit_length,
        mock_fastf1_session,
    ):
        """Test session info retrieval with NaN values in driver data."""
        mock_load_session.return_value = mock_fastf1_session
        mock_get_circuit_length.return_value = None
        mock_fastf1_session.total_laps = float("nan")

        mock_fastf1_session.results = _make_driver_df(
            [
                {
                    "Abbreviation": "VER",
                    "FirstName": "Max",
                    "LastName": "Verstappen",
                    "TeamName": "Red Bull Racing",
                    "DriverNumber": 1,
                    "Position": 1,
                    "ClassifiedPosition": 1,
                    "Status": "Finished",
                    "Points": 25.0,
                },
                {
                    "Abbreviation": "HAM",
                    "FirstName": "Lewis",
                    "LastName": "Hamilton",
                    "TeamName": "Mercedes",
                    # NaN fields use defaults from _make_driver_df
                    "ClassifiedPosition": "R",
                    "Status": "Engine",
                },
                {
                    "Abbreviation": "ALO",
                    "FirstName": "Fernando",
                    "LastName": "Alonso",
                    "TeamName": "Aston Martin",
                    "ClassifiedPosition": "N",
                    "Status": "",  # empty string should become None
                },
            ]
        )
        mock_extract_track_status.return_value = None
        mock_extract_weather_data.return_value = None

        result = get_session_info(2024, "Monaco", "Q")

        assert len(result["drivers"]) == 3
        assert result["drivers"][0]["number"] == 1
        assert result["drivers"][0]["position"] == 1
        assert result["drivers"][0]["classified_position"] == "1st"
        assert result["drivers"][1]["number"] is None
        assert result["drivers"][1]["position"] is None
        assert result["drivers"][1]["classified_position"] == "Retired"
        assert result["drivers"][1]["status"] == "Engine"
        assert result["drivers"][1]["finish_time"] is None
        assert result["drivers"][1]["points"] is None
        assert result["drivers"][2]["classified_position"] == "Not Classified"
        assert result["drivers"][2]["status"] is None  # empty string → None
        assert result["total_laps"] is None
        assert result["race_conditions"] is None
        assert result["weather"] is None

    @patch("pitlane_agent.commands.fetch.session_info.get_circuit_length_km")
    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_with_total_laps_error(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_get_circuit_length,
        mock_fastf1_session,
    ):
        """Test session info retrieval when total_laps raises DataNotLoadedError."""
        mock_load_session.return_value = mock_fastf1_session
        mock_fastf1_session.results = _make_driver_df(
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

        type(mock_fastf1_session).total_laps = property(
            lambda self: MagicMock(side_effect=DataNotLoadedError("Total laps not loaded"))()
        )

        mock_extract_track_status.return_value = None
        mock_extract_weather_data.return_value = None

        result = get_session_info(2024, "Monaco", "Q")

        assert result["total_laps"] is None

    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_error(self, mock_load_session):
        """Test error handling in session info retrieval."""
        mock_load_session.side_effect = Exception("Session not found")

        with pytest.raises(Exception, match="Session not found"):
            get_session_info(2024, "InvalidGP", "Q")
