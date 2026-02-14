"""Unit tests for fastf1_helpers module."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from pitlane_agent.utils.fastf1_helpers import get_merged_telemetry


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
