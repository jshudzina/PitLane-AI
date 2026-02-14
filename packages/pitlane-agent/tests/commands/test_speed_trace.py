"""Tests for speed_trace command."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.analyze.speed_trace import (
    generate_speed_trace_chart,
    setup_plot_style,
)
from pitlane_agent.utils import sanitize_filename
from pitlane_agent.utils.plotting import ensure_color_contrast, get_driver_team


class TestSpeedTraceBusinessLogic:
    """Unit tests for business logic functions."""

    def test_setup_plot_style(self):
        """Test plot style configuration."""
        # Test that setup_plot_style doesn't raise errors
        setup_plot_style()

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_success(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test successful speed trace chart generation with 2 drivers."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock telemetry data with Distance and Speed
        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0, 300.0, 400.0],
                "Speed": [250.0, 280.0, 310.0, 290.0, 270.0],
            }
        )

        # Mock fastest lap and telemetry chain
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        # Setup driver laps mock
        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function
        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert "statistics" in result
        assert "speed_delta" in result
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "speed_trace_2024_monaco_Q_HAM_VER.png")
        assert result["workspace"] == str(tmp_output_dir)
        assert len(result["drivers_compared"]) <= 2

        # Verify FastF1 was called correctly with telemetry=True
        mock_load_session.assert_called_once_with(2024, "Monaco", "Q", telemetry=True)

        # Verify telemetry methods were called
        assert mock_fastest_lap.get_car_data.called
        assert mock_car_data.add_distance.called

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_three_drivers(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test speed trace chart generation with 3 drivers."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock telemetry data
        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0, 300.0, 400.0],
                "Speed": [250.0, 280.0, 310.0, 290.0, 270.0],
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function with 3 drivers
        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM", "LEC"],
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert len(result["drivers_compared"]) <= 3
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "speed_trace_2024_monaco_Q_HAM_LEC_VER.png")

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_five_drivers(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test speed trace chart generation with 5 drivers (maximum allowed)."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock telemetry data
        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0, 300.0],
                "Speed": [250.0, 280.0, 310.0, 290.0],
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function with 5 drivers
        drivers = ["VER", "HAM", "LEC", "NOR", "PIA"]
        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=drivers,
            workspace_dir=tmp_output_dir,
        )

        # Should succeed with 5 drivers
        assert len(result["drivers_compared"]) <= 5

    def test_generate_speed_trace_chart_too_few_drivers(self, tmp_output_dir):
        """Test validation error when less than 2 drivers specified."""
        # Expect ValueError for < 2 drivers
        with pytest.raises(ValueError, match="at least 2 drivers"):
            generate_speed_trace_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER"],  # Only 1 driver
                workspace_dir=tmp_output_dir,
            )

    def test_generate_speed_trace_chart_too_many_drivers(self, tmp_output_dir):
        """Test validation error when more than 5 drivers specified."""
        # Expect ValueError for > 5 drivers
        with pytest.raises(ValueError, match="maximum 5 drivers"):
            generate_speed_trace_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER", "HAM", "LEC", "NOR", "PIA", "SAI"],  # 6 drivers
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_statistics_calculation(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test that speed statistics are calculated correctly."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock telemetry with known values
        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0, 300.0, 400.0],
                "Speed": [250.0, 280.0, 320.0, 290.0, 270.0],  # Max: 320, Avg: 282
            }
        )

        # Mock fastest lap
        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Call function
        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        # Check statistics
        assert "statistics" in result
        stats = result["statistics"]

        # Should have stats for drivers with data
        assert len(stats) > 0

        # Check first driver's stats
        driver_stats = stats[0]
        assert "driver" in driver_stats
        assert "max_speed" in driver_stats
        assert "average_speed" in driver_stats
        assert "fastest_lap_time" in driver_stats
        assert "fastest_lap_number" in driver_stats

        # Verify calculated values
        assert driver_stats["max_speed"] == 320.0
        assert driver_stats["average_speed"] == 282.0
        assert driver_stats["fastest_lap_number"] == 12

    def test_filename_generation(self, tmp_output_dir):
        """Test that filename is properly generated and sanitized."""
        gp_name = "Spanish Grand Prix"
        expected_sanitized = sanitize_filename(gp_name)

        # Verify sanitize_filename works as expected
        assert expected_sanitized == "spanish_grand_prix"

    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_error(self, mock_load_session, tmp_output_dir):
        """Test error handling in chart generation."""
        # Setup mock to raise error
        mock_load_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            generate_speed_trace_chart(
                year=2024,
                gp="InvalidGP",
                session_type="Q",
                drivers=["VER", "HAM"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_empty_laps(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test handling when driver has no laps."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock empty driver laps for first driver
        mock_empty_laps = MagicMock()
        mock_empty_laps.empty = True

        # Mock valid laps for second driver
        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0],
                "Speed": [250.0, 280.0, 310.0],
            }
        )

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_valid_laps = MagicMock()
        mock_valid_laps.empty = False
        mock_valid_laps.pick_fastest.return_value = mock_fastest_lap

        # Return different mock based on driver
        def pick_drivers_side_effect(driver):
            return mock_empty_laps if driver == "VER" else mock_valid_laps

        mock_fastf1_session.laps.pick_drivers.side_effect = pick_drivers_side_effect

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        # Mock driver color
        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Should succeed, just skip the driver with no laps
        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        # Should only have stats for HAM
        assert len(result["drivers_compared"]) == 1

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_with_corners(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test speed trace chart generation with corner annotations enabled."""
        mock_load_session.return_value = mock_fastf1_session

        # Mock telemetry data
        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0, 300.0, 400.0],
                "Speed": [250.0, 280.0, 310.0, 290.0, 270.0],
            }
        )

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Mock circuit info with corners
        mock_corners = pd.DataFrame(
            {
                "Number": [1, 2, 3],
                "Letter": ["", "", ""],
                "Distance": [100.0, 250.0, 350.0],
            }
        )
        mock_circuit_info = MagicMock()
        mock_circuit_info.corners = mock_corners
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
            annotate_corners=True,
        )

        assert result["corners_annotated"] is True
        # Verify corner annotations were drawn (3 corners = 3 axvline + 3 text calls)
        assert mock_ax.axvline.call_count == 3
        # text is called for corners (3) plus any other text calls
        corner_text_calls = [call for call in mock_ax.text.call_args_list if call[0][2] in ("1", "2", "3")]
        assert len(corner_text_calls) == 3

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_corners_fallback(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test graceful degradation when corner data is unavailable."""
        mock_load_session.return_value = mock_fastf1_session

        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0],
                "Speed": [250.0, 280.0, 310.0],
            }
        )

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        # Mock circuit info to raise an exception
        mock_fastf1_session.get_circuit_info.side_effect = Exception("No circuit data")

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Should not raise — graceful degradation
        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
            annotate_corners=True,
        )

        assert result["corners_annotated"] is True
        # No corner lines should be drawn
        mock_ax.axvline.assert_not_called()

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_generate_speed_trace_chart_without_corners_default(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test that corners are not annotated by default."""
        mock_load_session.return_value = mock_fastf1_session

        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0],
                "Speed": [250.0, 280.0, 310.0],
            }
        )

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        result = generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        assert result["corners_annotated"] is False
        # get_circuit_info should never be called when annotate_corners is False
        mock_fastf1_session.get_circuit_info.assert_not_called()

    @patch("pitlane_agent.commands.analyze.speed_trace.fastf1")
    @patch("pitlane_agent.commands.analyze.speed_trace.plt")
    @patch("pitlane_agent.commands.analyze.speed_trace.load_session")
    def test_teammates_get_different_line_styles(
        self, mock_load_session, mock_plt, mock_fastf1, tmp_output_dir, mock_fastf1_session
    ):
        """Test that drivers on the same team get different line styles."""
        mock_load_session.return_value = mock_fastf1_session

        mock_telemetry = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0],
                "Speed": [250.0, 280.0, 310.0],
            }
        )

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__.side_effect = lambda key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap

        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.get_ylim.return_value = (240, 320)

        mock_fastf1.plotting.get_driver_color.return_value = "#0600EF"

        # Use two teammates (VER and PER, both Red Bull)
        generate_speed_trace_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "PER"],
            workspace_dir=tmp_output_dir,
        )

        # Verify plot was called with different line styles for teammates
        plot_calls = mock_ax.plot.call_args_list
        assert len(plot_calls) == 2

        first_linestyle = plot_calls[0][1].get("linestyle", "-")
        second_linestyle = plot_calls[1][1].get("linestyle", "-")
        assert first_linestyle == "-"  # solid for first teammate
        assert second_linestyle == "--"  # dashed for second teammate


class TestPlottingUtilities:
    """Unit tests for plotting utility functions."""

    def test_ensure_color_contrast_dark_color_is_lightened(self):
        """Test that very dark colors are lightened."""
        result = ensure_color_contrast("#0a0a0a")
        assert result != "#0a0a0a"

    def test_ensure_color_contrast_bright_color_unchanged(self):
        """Test that bright colors are not modified."""
        result = ensure_color_contrast("#ff0000")
        assert result == "#ff0000"

    def test_ensure_color_contrast_preserves_hue(self):
        """Test that color adjustment preserves hue."""
        import colorsys

        dark_blue = "#000033"
        result = ensure_color_contrast(dark_blue)
        # Result should still be blue-ish
        r, g, b = (int(result.lstrip("#")[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        h, _, _ = colorsys.rgb_to_hls(r, g, b)
        # Blue hue is around 0.66
        assert 0.55 < h < 0.75

    def test_ensure_color_contrast_handles_hash_prefix(self):
        """Test that # prefix is handled correctly."""
        with_hash = ensure_color_contrast("#ff0000")
        without_hash = ensure_color_contrast("ff0000")
        assert with_hash == without_hash

    def test_get_driver_team_found(self, mock_fastf1_session):
        """Test team lookup for a known driver."""
        assert get_driver_team("VER", mock_fastf1_session) == "Red Bull Racing"
        assert get_driver_team("HAM", mock_fastf1_session) == "Mercedes"

    def test_get_driver_team_not_found(self, mock_fastf1_session):
        """Test team lookup for an unknown driver."""
        assert get_driver_team("UNKNOWN", mock_fastf1_session) is None

    def test_get_driver_team_exception_handling(self):
        """Test graceful degradation when session.results is unavailable."""
        session = MagicMock()
        session.results.__getitem__.side_effect = Exception("No results")
        assert get_driver_team("VER", session) is None
