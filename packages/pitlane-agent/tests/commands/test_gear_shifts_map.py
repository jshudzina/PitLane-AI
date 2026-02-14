"""Tests for gear_shifts_map command."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from pitlane_agent.commands.analyze.gear_shifts_map import (
    _calculate_gear_statistics,
    generate_gear_shifts_map_chart,
)


class TestGearShiftsMapBusinessLogic:
    """Unit tests for business logic functions."""

    def test_calculate_gear_statistics(self):
        """Test gear statistics calculation."""
        # Create test telemetry with known gear distribution
        telemetry = pd.DataFrame(
            {
                "nGear": [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 6, 6, 7, 8, 8],  # 18 total points
            }
        )

        stats = _calculate_gear_statistics(telemetry)

        # Verify structure
        assert "gear_distribution" in stats
        assert "most_used_gear" in stats
        assert "highest_gear" in stats
        assert "total_gear_changes" in stats

        # Verify values
        assert stats["highest_gear"] == 8
        assert stats["most_used_gear"] == 4  # 4 appears 4 times, most frequent
        # 8 gear shifts in the sequence (1->2, 2->3, 3->4, 4->5, 5->6, 6->7, 7->8, 8->8)
        assert stats["total_gear_changes"] == 8

        # Verify percentages sum to 100
        total_percentage = sum(g["percentage"] for g in stats["gear_distribution"].values())
        assert 99.0 <= total_percentage <= 101.0  # Allow for rounding

    @patch("pitlane_agent.commands.analyze.gear_shifts_map.save_figure")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.setup_plot_style")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.load_session")
    def test_generate_gear_shifts_map_single_driver(
        self, mock_load_session, mock_setup_plot_style, mock_save_figure, tmp_output_dir, mock_fastf1_session
    ):
        """Test successful gear shifts map chart generation with 1 driver."""
        # Setup session mock
        mock_load_session.return_value = mock_fastf1_session

        # Mock circuit info with corners
        mock_circuit_info = MagicMock()
        mock_circuit_info.rotation = 45.0
        mock_circuit_info.corners = pd.DataFrame(
            {
                "Number": [1, 2, 3],
                "Letter": [None, "A", None],
                "Angle": [45.0, 90.0, 135.0],
                "X": [100.0, 200.0, 300.0],
                "Y": [50.0, 100.0, 150.0],
            }
        )
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock merged telemetry data (from get_telemetry())
        num_points = 100
        mock_telemetry = pd.DataFrame(
            {
                "X": np.linspace(0, 1000, num_points),
                "Y": np.linspace(0, 500, num_points),
                "nGear": np.random.randint(1, 9, num_points),  # Gears 1-8
                "Speed": np.random.uniform(100, 320, num_points),
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]
        mock_fastest_lap.get_telemetry.return_value = mock_telemetry

        # Mock driver laps
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Call function
        result = generate_gear_shifts_map_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER"],
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert "gear_statistics" in result
        assert len(result["drivers_analyzed"]) == 1
        assert result["drivers_analyzed"][0] == "VER"
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "gear_shifts_map_2024_monaco_Q_VER.png")
        assert result["workspace"] == str(tmp_output_dir)

        # Verify session loaded with telemetry
        mock_load_session.assert_called_once_with(2024, "Monaco", "Q", telemetry=True)

        # Verify save_figure was called
        assert mock_save_figure.called

        # Verify statistics structure
        assert len(result["gear_statistics"]) == 1
        driver_stats = result["gear_statistics"][0]
        assert driver_stats["driver"] == "VER"
        assert "gear_distribution" in driver_stats
        assert "most_used_gear" in driver_stats
        assert "highest_gear" in driver_stats
        assert "total_gear_changes" in driver_stats

    def test_generate_gear_shifts_map_too_many_drivers(self, tmp_output_dir):
        """Test validation error when more than 1 driver specified."""
        with pytest.raises(ValueError, match="exactly 1 driver"):
            generate_gear_shifts_map_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER", "HAM"],  # 2 drivers - exceeds max of 1
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.gear_shifts_map.setup_plot_style")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.load_session")
    def test_generate_gear_shifts_map_missing_gear_data(
        self, mock_load_session, mock_setup_plot_style, tmp_output_dir, mock_fastf1_session
    ):
        """Test error when gear telemetry is unavailable."""
        # Setup session mock
        mock_load_session.return_value = mock_fastf1_session

        # Mock circuit info with corners
        mock_circuit_info = MagicMock()
        mock_circuit_info.rotation = 45.0
        mock_circuit_info.corners = pd.DataFrame(
            {
                "Number": [1],
                "Letter": [None],
                "Angle": [45.0],
                "X": [100.0],
                "Y": [50.0],
            }
        )
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock telemetry WITHOUT nGear column
        mock_telemetry = pd.DataFrame(
            {
                "X": np.linspace(0, 1000, 100),
                "Y": np.linspace(0, 500, 100),
                "Speed": np.random.uniform(100, 320, 100),
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.get_telemetry.return_value = mock_telemetry

        # Mock driver laps
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Should raise ValueError for missing nGear
        with pytest.raises(ValueError, match="Missing required telemetry channels"):
            generate_gear_shifts_map_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.gear_shifts_map.setup_plot_style")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.load_session")
    def test_generate_gear_shifts_map_empty_telemetry(
        self, mock_load_session, mock_setup_plot_style, tmp_output_dir, mock_fastf1_session
    ):
        """Test error when telemetry data is empty."""
        # Setup session mock
        mock_load_session.return_value = mock_fastf1_session

        # Mock circuit info with corners
        mock_circuit_info = MagicMock()
        mock_circuit_info.rotation = 45.0
        mock_circuit_info.corners = pd.DataFrame(
            {
                "Number": [1],
                "Letter": [None],
                "Angle": [45.0],
                "X": [100.0],
                "Y": [50.0],
            }
        )
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock empty telemetry
        mock_telemetry = pd.DataFrame({"X": [], "Y": [], "nGear": [], "Speed": []})

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.get_telemetry.return_value = mock_telemetry

        # Mock driver laps
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Should raise ValueError for empty telemetry
        with pytest.raises(ValueError, match="No telemetry data"):
            generate_gear_shifts_map_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.gear_shifts_map.setup_plot_style")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.load_session")
    def test_generate_gear_shifts_map_empty_driver_laps(
        self, mock_load_session, mock_setup_plot_style, tmp_output_dir, mock_fastf1_session
    ):
        """Test error when driver has no laps."""
        # Setup session mock
        mock_load_session.return_value = mock_fastf1_session

        # Mock circuit info with corners
        mock_circuit_info = MagicMock()
        mock_circuit_info.rotation = 45.0
        mock_circuit_info.corners = pd.DataFrame(
            {
                "Number": [1],
                "Letter": [None],
                "Angle": [45.0],
                "X": [100.0],
                "Y": [50.0],
            }
        )
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock driver laps - empty
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = True

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Should raise ValueError for no laps
        with pytest.raises(ValueError, match="No laps found"):
            generate_gear_shifts_map_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.gear_shifts_map.save_figure")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.setup_plot_style")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.load_session")
    def test_chart_path_format(
        self, mock_load_session, mock_setup_plot_style, mock_save_figure, tmp_output_dir, mock_fastf1_session
    ):
        """Test that chart path follows expected naming pattern."""
        # Setup session mock
        mock_load_session.return_value = mock_fastf1_session

        # Mock circuit info with corners
        mock_circuit_info = MagicMock()
        mock_circuit_info.rotation = 0.0
        mock_circuit_info.corners = pd.DataFrame(
            {
                "Number": [1, 2],
                "Letter": [None, None],
                "Angle": [45.0, 90.0],
                "X": [100.0, 200.0],
                "Y": [50.0, 100.0],
            }
        )
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock merged telemetry data
        num_points = 100
        mock_telemetry = pd.DataFrame(
            {
                "X": np.linspace(0, 1000, num_points),
                "Y": np.linspace(0, 500, num_points),
                "nGear": [3] * num_points,  # Constant gear for simplicity
                "Speed": [200.0] * num_points,
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]
        mock_fastest_lap.get_telemetry.return_value = mock_telemetry

        # Mock driver laps
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Call function
        result = generate_gear_shifts_map_chart(
            year=2024,
            gp="Abu Dhabi",  # Test GP with space
            session_type="R",
            drivers=["VER"],
            workspace_dir=tmp_output_dir,
        )

        # Verify chart path format (should sanitize "Abu Dhabi" to "abu_dhabi")
        expected_path = str(tmp_output_dir / "charts" / "gear_shifts_map_2024_abu_dhabi_R_VER.png")
        assert result["chart_path"] == expected_path

    @patch("pitlane_agent.commands.analyze.gear_shifts_map.save_figure")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.setup_plot_style")
    @patch("pitlane_agent.commands.analyze.gear_shifts_map.load_session")
    def test_return_dict_structure(
        self, mock_load_session, mock_setup_plot_style, mock_save_figure, tmp_output_dir, mock_fastf1_session
    ):
        """Test that return dict has all required fields."""
        # Setup session mock
        mock_load_session.return_value = mock_fastf1_session

        # Mock circuit info with corners
        mock_circuit_info = MagicMock()
        mock_circuit_info.rotation = 0.0
        mock_circuit_info.corners = pd.DataFrame(
            {
                "Number": [1, 2, 3],
                "Letter": [None, "A", None],
                "Angle": [45.0, 90.0, 135.0],
                "X": [100.0, 200.0, 300.0],
                "Y": [50.0, 100.0, 150.0],
            }
        )
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock merged telemetry data
        num_points = 100
        mock_telemetry = pd.DataFrame(
            {
                "X": np.linspace(0, 1000, num_points),
                "Y": np.linspace(0, 500, num_points),
                "nGear": np.random.randint(1, 9, num_points),
                "Speed": np.random.uniform(100, 320, num_points),
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]
        mock_fastest_lap.get_telemetry.return_value = mock_telemetry

        # Mock driver laps
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Call function
        result = generate_gear_shifts_map_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER"],
            workspace_dir=tmp_output_dir,
        )

        # Verify all required fields
        required_fields = [
            "chart_path",
            "workspace",
            "event_name",
            "session_name",
            "year",
            "circuit_name",
            "drivers_analyzed",
            "gear_statistics",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
