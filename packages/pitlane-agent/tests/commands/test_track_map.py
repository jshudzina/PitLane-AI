"""Tests for track_map command."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from pitlane_agent.commands.analyze.track_map import generate_track_map_chart


class TestTrackMapChart:
    """Unit tests for track map chart generation."""

    def _make_mock_circuit_info(self, corners_data=None, rotation=315.0):
        """Create a mock CircuitInfo object."""
        circuit_info = MagicMock()
        circuit_info.rotation = rotation

        if corners_data is None:
            corners_data = {
                "X": [1000.0, 2000.0, 3000.0],
                "Y": [500.0, 1500.0, 2500.0],
                "Number": [1, 2, 3],
                "Letter": ["", "", ""],
                "Angle": [90.0, 180.0, 270.0],
                "Distance": [100.0, 400.0, 800.0],
            }

        circuit_info.corners = pd.DataFrame(corners_data)
        return circuit_info

    def _make_mock_pos_data(self):
        """Create mock position data with sufficient points for validation."""
        # Generate 150 points to exceed MIN_TELEMETRY_POINTS_TRACK_MAP (100)
        num_points = 150
        # Create a simple oval track shape
        t = np.linspace(0, 2 * np.pi, num_points)
        return pd.DataFrame(
            {
                "X": 1000 * np.cos(t),  # Oval X coordinates
                "Y": 500 * np.sin(t),  # Oval Y coordinates
            }
        )

    @patch("pitlane_agent.commands.analyze.track_map.plt")
    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_success(self, mock_load_session, mock_plt, tmp_output_dir, mock_fastf1_session):
        """Test successful track map chart generation."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock position data
        mock_lap = MagicMock()
        mock_lap.get_pos_data.return_value = self._make_mock_pos_data()
        mock_fastf1_session.laps.pick_fastest.return_value = mock_lap

        # Mock circuit info
        mock_fastf1_session.get_circuit_info.return_value = self._make_mock_circuit_info()

        # Mock event Location
        mock_fastf1_session.event = {"EventName": "Monaco Grand Prix", "Location": "Monaco"}

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Call function
        result = generate_track_map_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert result["circuit_name"] == "Monaco"
        assert result["num_corners"] == 3
        assert len(result["corner_details"]) == 3
        assert result["corner_details"][0] == {"number": 1, "letter": ""}
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "track_map_2024_monaco_Q.png")
        assert result["workspace"] == str(tmp_output_dir)

        # Verify session loaded without telemetry
        mock_load_session.assert_called_once_with(2024, "Monaco", "Q", telemetry=True)

        # Verify position data and circuit info were accessed
        mock_lap.get_pos_data.assert_called_once()
        mock_fastf1_session.get_circuit_info.assert_called_once()

        # Verify plot was configured
        mock_ax.set_xticks.assert_called_once_with([])
        mock_ax.set_yticks.assert_called_once_with([])
        mock_ax.set_aspect.assert_called_once_with("equal")

    @patch("pitlane_agent.commands.analyze.track_map.plt")
    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_with_corner_letters(
        self, mock_load_session, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test track map with corners that have letter suffixes (e.g., 9a, 9b)."""
        mock_load_session.return_value = mock_fastf1_session

        mock_lap = MagicMock()
        mock_lap.get_pos_data.return_value = self._make_mock_pos_data()
        mock_fastf1_session.laps.pick_fastest.return_value = mock_lap

        corners_data = {
            "X": [1000.0, 1500.0],
            "Y": [500.0, 600.0],
            "Number": [9, 9],
            "Letter": ["a", "b"],
            "Angle": [90.0, 100.0],
            "Distance": [100.0, 150.0],
        }
        mock_fastf1_session.get_circuit_info.return_value = self._make_mock_circuit_info(corners_data=corners_data)
        mock_fastf1_session.event = {"EventName": "Silverstone Grand Prix", "Location": "Silverstone"}

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        result = generate_track_map_chart(year=2024, gp="Silverstone", session_type="R", workspace_dir=tmp_output_dir)

        assert result["num_corners"] == 2
        assert result["corner_details"][0] == {"number": 9, "letter": "a"}
        assert result["corner_details"][1] == {"number": 9, "letter": "b"}

    @patch("pitlane_agent.commands.analyze.track_map.plt")
    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_no_corners(
        self, mock_load_session, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test track map when circuit has no corner data."""
        mock_load_session.return_value = mock_fastf1_session

        mock_lap = MagicMock()
        mock_lap.get_pos_data.return_value = self._make_mock_pos_data()
        mock_fastf1_session.laps.pick_fastest.return_value = mock_lap

        # Empty corners
        empty_corners = {
            "X": [],
            "Y": [],
            "Number": [],
            "Letter": [],
            "Angle": [],
            "Distance": [],
        }
        mock_fastf1_session.get_circuit_info.return_value = self._make_mock_circuit_info(corners_data=empty_corners)
        mock_fastf1_session.event = {"EventName": "Test GP", "Location": "Test"}

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        result = generate_track_map_chart(year=2024, gp="Test", session_type="R", workspace_dir=tmp_output_dir)

        assert result["num_corners"] == 0
        assert result["corner_details"] == []

    @patch("pitlane_agent.commands.analyze.track_map.plt")
    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_no_pos_data(
        self, mock_load_session, mock_plt, tmp_output_dir, mock_fastf1_session
    ):
        """Test error when position data is unavailable."""
        mock_load_session.return_value = mock_fastf1_session

        mock_lap = MagicMock()
        mock_lap.get_pos_data.return_value = pd.DataFrame({"X": [], "Y": []})
        mock_fastf1_session.laps.pick_fastest.return_value = mock_lap

        with pytest.raises(ValueError, match="No position data available"):
            generate_track_map_chart(year=2024, gp="Monaco", session_type="Q", workspace_dir=tmp_output_dir)

    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_insufficient_pos_data(
        self, mock_load_session, tmp_output_dir, mock_fastf1_session
    ):
        """Test error when position data has insufficient points for visualization."""
        mock_load_session.return_value = mock_fastf1_session

        # Create position data with only 50 points (less than MIN_TELEMETRY_POINTS_TRACK_MAP of 100)
        mock_lap = MagicMock()
        mock_lap.get_pos_data.return_value = pd.DataFrame(
            {
                "X": np.linspace(0, 1000, 50),
                "Y": np.linspace(0, 500, 50),
            }
        )
        mock_fastf1_session.laps.pick_fastest.return_value = mock_lap

        with pytest.raises(ValueError, match="Insufficient position data for track map"):
            generate_track_map_chart(year=2024, gp="Monaco", session_type="Q", workspace_dir=tmp_output_dir)

    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_no_laps(self, mock_load_session, tmp_output_dir, mock_fastf1_session):
        """Test error when no laps are available (pick_fastest returns None)."""
        mock_load_session.return_value = mock_fastf1_session
        mock_fastf1_session.laps.pick_fastest.return_value = None

        with pytest.raises(ValueError, match="No laps available"):
            generate_track_map_chart(year=2024, gp="Monaco", session_type="Q", workspace_dir=tmp_output_dir)

    @patch("pitlane_agent.commands.analyze.track_map.load_session")
    def test_generate_track_map_chart_session_error(self, mock_load_session, tmp_output_dir):
        """Test error handling when session loading fails."""
        mock_load_session.side_effect = Exception("Session not found")

        with pytest.raises(Exception, match="Session not found"):
            generate_track_map_chart(year=2024, gp="InvalidGP", session_type="Q", workspace_dir=tmp_output_dir)

    def test_filename_generation(self, tmp_output_dir):
        """Test that chart path uses correct naming pattern (no drivers)."""
        from pitlane_agent.utils.fastf1_helpers import build_chart_path

        path = build_chart_path(tmp_output_dir, "track_map", 2024, "Monaco", "Q")
        assert path == tmp_output_dir / "charts" / "track_map_2024_monaco_Q.png"
