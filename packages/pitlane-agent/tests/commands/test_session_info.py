"""Tests for session_info command."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastf1.core import DataNotLoadedError
from pitlane_agent.commands.fetch.session_info import (
    _extract_track_status,
    _extract_weather_data,
    get_session_info,
)


class TestExtractTrackStatus:
    """Unit tests for _extract_track_status function."""

    def test_extract_track_status_with_data(self):
        """Test extracting track status with valid data."""
        # Create mock session with track status data
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
        # Configure track_status property to raise DataNotLoadedError when accessed
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
        # Configure weather_data property to raise DataNotLoadedError when accessed
        type(mock_session).weather_data = property(
            lambda self: (_ for _ in ()).throw(DataNotLoadedError("Weather data not loaded"))
        )

        result = _extract_weather_data(mock_session)

        assert result is None


class TestSessionInfoBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_success(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_fastf1_session,
    ):
        """Test successful session info retrieval."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session
        mock_fastf1_session.results = MagicMock()

        # Create mock driver data
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

        # Mock race conditions and weather
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

        # Verify race conditions and weather are included
        assert result["race_conditions"] is not None
        assert result["race_conditions"]["num_safety_cars"] == 2
        assert result["weather"] is not None
        assert result["weather"]["air_temp"]["avg"] == 23.5

        # Verify FastF1 was called correctly
        mock_load_session.assert_called_once_with(2024, "Monaco", "Q", weather=True, messages=True)

    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_with_nan_values(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_fastf1_session,
    ):
        """Test session info retrieval with NaN values in driver data."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session
        mock_fastf1_session.results = MagicMock()
        mock_fastf1_session.total_laps = float("nan")

        # Create mock driver data with NaN values
        driver_data = pd.DataFrame(
            [
                {
                    "Abbreviation": "VER",
                    "FirstName": "Max",
                    "LastName": "Verstappen",
                    "TeamName": "Red Bull Racing",
                    "DriverNumber": 1,
                    "Position": 1,
                },
                {
                    "Abbreviation": "HAM",
                    "FirstName": "Lewis",
                    "LastName": "Hamilton",
                    "TeamName": "Mercedes",
                    "DriverNumber": float("nan"),  # NaN driver number
                    "Position": float("nan"),  # NaN position
                },
            ]
        )
        mock_fastf1_session.results.iterrows.return_value = driver_data.iterrows()

        # Mock race conditions and weather
        mock_extract_track_status.return_value = None
        mock_extract_weather_data.return_value = None

        # Call function
        result = get_session_info(2024, "Monaco", "Q")

        # Assertions
        assert len(result["drivers"]) == 2
        assert result["drivers"][0]["number"] == 1
        assert result["drivers"][0]["position"] == 1
        assert result["drivers"][1]["number"] is None  # NaN should be None
        assert result["drivers"][1]["position"] is None  # NaN should be None
        assert result["total_laps"] is None  # NaN total_laps should be None
        assert result["race_conditions"] is None
        assert result["weather"] is None

    @patch("pitlane_agent.commands.fetch.session_info._extract_weather_data")
    @patch("pitlane_agent.commands.fetch.session_info._extract_track_status")
    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_with_total_laps_error(
        self,
        mock_load_session,
        mock_extract_track_status,
        mock_extract_weather_data,
        mock_fastf1_session,
    ):
        """Test session info retrieval when total_laps raises DataNotLoadedError."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session
        mock_fastf1_session.results = MagicMock()

        # Create mock driver data
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

        # Mock total_laps to raise DataNotLoadedError
        type(mock_fastf1_session).total_laps = property(
            lambda self: MagicMock(side_effect=DataNotLoadedError("Total laps not loaded"))()
        )

        mock_extract_track_status.return_value = None
        mock_extract_weather_data.return_value = None

        # Call function
        result = get_session_info(2024, "Monaco", "Q")

        # Assertions
        assert result["total_laps"] is None

    @patch("pitlane_agent.commands.fetch.session_info.load_session")
    def test_get_session_info_error(self, mock_load_session):
        """Test error handling in session info retrieval."""
        # Setup mock to raise error
        mock_load_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            get_session_info(2024, "InvalidGP", "Q")
