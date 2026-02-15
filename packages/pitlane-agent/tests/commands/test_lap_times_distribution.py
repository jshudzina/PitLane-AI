"""Tests for lap_times_distribution command."""

from unittest.mock import MagicMock, patch

import pytest
from pitlane_agent.commands.analyze.lap_times_distribution import (
    generate_lap_times_distribution_chart,
)
from pitlane_agent.utils import sanitize_filename


class TestLapTimesDistributionBusinessLogic:
    """Unit tests for business logic functions."""

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_compound_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_driver_color_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.sns")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.plt")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_success_with_drivers(
        self,
        mock_load_session,
        mock_plt,
        mock_sns,
        mock_driver_colors,
        mock_compound_colors,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test successful chart generation with specific drivers."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock driver laps
        import pandas as pd

        mock_laps = pd.DataFrame(
            [
                {"Driver": "VER", "LapNumber": 1, "LapTime": pd.Timedelta(seconds=85.5), "Compound": "SOFT"},
                {"Driver": "VER", "LapNumber": 2, "LapTime": pd.Timedelta(seconds=85.2), "Compound": "SOFT"},
                {"Driver": "HAM", "LapNumber": 1, "LapTime": pd.Timedelta(seconds=85.8), "Compound": "MEDIUM"},
                {"Driver": "HAM", "LapNumber": 2, "LapTime": pd.Timedelta(seconds=85.3), "Compound": "MEDIUM"},
            ]
        )
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock driver color mapping
        mock_driver_colors.return_value = {"VER": "#0600EF", "HAM": "#00D2BE"}
        mock_compound_colors.return_value = {
            "SOFT": "#FF0000",
            "MEDIUM": "#FFFF00",
            "HARD": "#FFFFFF",
        }

        # Call function with specific drivers
        result = generate_lap_times_distribution_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        # Assertions
        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert "statistics" in result
        assert result["chart_path"] == str(
            tmp_output_dir / "charts" / "lap_times_distribution_2024_monaco_Q_HAM_VER.png"
        )
        assert result["workspace"] == str(tmp_output_dir)
        assert len(result["drivers_plotted"]) == 2
        assert "VER" in result["drivers_plotted"]
        assert "HAM" in result["drivers_plotted"]

        # Verify statistics structure
        assert len(result["statistics"]) == 2
        for stat in result["statistics"]:
            assert "driver" in stat
            assert "best_time" in stat
            assert "best_time_formatted" in stat
            assert "median_time" in stat
            assert "std_dev" in stat
            assert "lap_count" in stat
            assert "compounds_used" in stat

        # Verify FastF1 was called correctly
        mock_load_session.assert_called_once_with(2024, "Monaco", "Q")

        # Verify seaborn plots were called
        mock_sns.violinplot.assert_called_once()
        mock_sns.swarmplot.assert_called_once()

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_compound_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_driver_color_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.sns")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.plt")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_default_top10(
        self,
        mock_load_session,
        mock_plt,
        mock_sns,
        mock_driver_colors,
        mock_compound_colors,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test chart generation defaults to top 10 finishers when drivers is None."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock session.drivers to return top 10
        mock_fastf1_session.drivers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

        # Mock driver abbreviations for top 10
        mock_fastf1_session.get_driver.side_effect = lambda i: {"Abbreviation": f"DR{i}"}

        # Mock driver laps
        import pandas as pd

        mock_laps_data = []
        for i in range(1, 11):
            mock_laps_data.extend(
                [
                    {
                        "Driver": f"DR{i}",
                        "LapNumber": 1,
                        "LapTime": pd.Timedelta(seconds=85 + i * 0.1),
                        "Compound": "SOFT",
                    },
                    {
                        "Driver": f"DR{i}",
                        "LapNumber": 2,
                        "LapTime": pd.Timedelta(seconds=85 + i * 0.1 + 0.2),
                        "Compound": "MEDIUM",
                    },
                ]
            )

        mock_laps = pd.DataFrame(mock_laps_data)
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock color mappings
        mock_driver_colors.return_value = {f"DR{i}": "#000000" for i in range(1, 11)}
        mock_compound_colors.return_value = {
            "SOFT": "#FF0000",
            "MEDIUM": "#FFFF00",
            "HARD": "#FFFFFF",
        }

        # Call function with drivers=None (should default to top 10)
        result = generate_lap_times_distribution_chart(
            year=2024, gp="Monaco", session_type="R", drivers=None, workspace_dir=tmp_output_dir
        )

        # Assertions
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "lap_times_distribution_2024_monaco_R_top10.png")
        assert len(result["drivers_plotted"]) == 10

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_compound_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_driver_color_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.sns")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.plt")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_many_drivers(
        self,
        mock_load_session,
        mock_plt,
        mock_sns,
        mock_driver_colors,
        mock_compound_colors,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test chart generation with many drivers uses shortened filename."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock driver laps for 6 drivers
        import pandas as pd

        drivers = ["VER", "HAM", "LEC", "NOR", "PIA", "SAI"]
        mock_laps_data = []
        for driver in drivers:
            mock_laps_data.extend(
                [
                    {"Driver": driver, "LapNumber": 1, "LapTime": pd.Timedelta(seconds=85.5), "Compound": "SOFT"},
                    {"Driver": driver, "LapNumber": 2, "LapTime": pd.Timedelta(seconds=85.2), "Compound": "MEDIUM"},
                ]
            )

        mock_laps = pd.DataFrame(mock_laps_data)
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock color mappings
        mock_driver_colors.return_value = dict.fromkeys(drivers, "#000000")
        mock_compound_colors.return_value = {
            "SOFT": "#FF0000",
            "MEDIUM": "#FFFF00",
            "HARD": "#FFFFFF",
        }

        # Call function with 6 drivers (more than 5)
        result = generate_lap_times_distribution_chart(
            year=2024, gp="Monaco", session_type="Q", drivers=drivers, workspace_dir=tmp_output_dir
        )

        # Assertions - filename should use count instead of listing all drivers
        assert result["chart_path"] == str(
            tmp_output_dir / "charts" / "lap_times_distribution_2024_monaco_Q_6drivers.png"
        )

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_error(self, mock_load_session, tmp_output_dir):
        """Test error handling in chart generation."""
        # Setup mock to raise error
        mock_load_session.side_effect = Exception("Session not found")

        # Expect exception to be raised
        with pytest.raises(Exception, match="Session not found"):
            generate_lap_times_distribution_chart(
                year=2024, gp="InvalidGP", session_type="Q", drivers=["VER"], workspace_dir=tmp_output_dir
            )

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_no_quick_laps(self, mock_load_session, tmp_output_dir, mock_fastf1_session):
        """Test error handling when no quick laps are found."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock empty laps dataframe
        import pandas as pd

        mock_laps = pd.DataFrame()
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        # Expect ValueError to be raised
        with pytest.raises(ValueError, match="No quick laps found"):
            generate_lap_times_distribution_chart(
                year=2024, gp="Monaco", session_type="Q", drivers=["VER"], workspace_dir=tmp_output_dir
            )

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_compound_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_driver_color_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.sns")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.plt")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_verifies_plot_calls(
        self,
        mock_load_session,
        mock_plt,
        mock_sns,
        mock_driver_colors,
        mock_compound_colors,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test that seaborn plotting functions are called with correct parameters."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock driver laps
        import pandas as pd

        mock_laps = pd.DataFrame(
            [
                {"Driver": "VER", "LapNumber": 1, "LapTime": pd.Timedelta(seconds=85.5), "Compound": "SOFT"},
                {"Driver": "VER", "LapNumber": 2, "LapTime": pd.Timedelta(seconds=85.2), "Compound": "MEDIUM"},
            ]
        )
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock color mappings
        driver_colors = {"VER": "#0600EF"}
        compound_colors = {"SOFT": "#FF0000", "MEDIUM": "#FFFF00", "HARD": "#FFFFFF"}
        mock_driver_colors.return_value = driver_colors
        mock_compound_colors.return_value = compound_colors

        # Call function
        generate_lap_times_distribution_chart(
            year=2024, gp="Monaco", session_type="Q", drivers=["VER"], workspace_dir=tmp_output_dir
        )

        # Verify seaborn violinplot was called with correct parameters
        violin_call = mock_sns.violinplot.call_args
        assert violin_call is not None
        assert violin_call.kwargs["x"] == "Driver"
        assert violin_call.kwargs["y"] == "LapTime(s)"
        assert violin_call.kwargs["hue"] == "Driver"
        assert violin_call.kwargs["inner"] is None
        assert violin_call.kwargs["density_norm"] == "area"
        assert violin_call.kwargs["palette"] == driver_colors
        assert violin_call.kwargs["legend"] is False

        # Verify seaborn swarmplot was called with correct parameters
        swarm_call = mock_sns.swarmplot.call_args
        assert swarm_call is not None
        assert swarm_call.kwargs["x"] == "Driver"
        assert swarm_call.kwargs["y"] == "LapTime(s)"
        assert swarm_call.kwargs["hue"] == "Compound"
        assert swarm_call.kwargs["palette"] == compound_colors
        assert swarm_call.kwargs["hue_order"] == ["SOFT", "MEDIUM", "HARD"]
        assert swarm_call.kwargs["size"] == 4

        # Verify despine was called
        mock_sns.despine.assert_called_once()

    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_compound_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.fastf1.plotting.get_driver_color_mapping")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.sns")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.plt")
    @patch("pitlane_agent.commands.analyze.lap_times_distribution.load_session")
    def test_generate_distribution_chart_with_excluded_drivers(
        self,
        mock_load_session,
        mock_plt,
        mock_sns,
        mock_driver_colors,
        mock_compound_colors,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test that drivers with no quick laps are excluded with warning."""
        # Setup mocks
        mock_load_session.return_value = mock_fastf1_session

        # Mock driver laps - only VER has laps, HAM has none
        import pandas as pd

        mock_laps = pd.DataFrame(
            [
                {"Driver": "VER", "LapNumber": 1, "LapTime": pd.Timedelta(seconds=85.5), "Compound": "SOFT"},
                {"Driver": "VER", "LapNumber": 2, "LapTime": pd.Timedelta(seconds=85.2), "Compound": "MEDIUM"},
            ]
        )
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        # Mock pyplot
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock color mappings
        mock_driver_colors.return_value = {"VER": "#0600EF"}
        mock_compound_colors.return_value = {
            "SOFT": "#FF0000",
            "MEDIUM": "#FFFF00",
            "HARD": "#FFFFFF",
        }

        # Call function with two drivers, but only VER has laps
        result = generate_lap_times_distribution_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        # Assertions - HAM should be excluded
        assert len(result["drivers_plotted"]) == 1
        assert "VER" in result["drivers_plotted"]
        assert "HAM" not in result["drivers_plotted"]

        # Verify warning metadata
        assert "excluded_drivers" in result
        assert "HAM" in result["excluded_drivers"]
        assert "warning" in result
        assert "HAM" in result["warning"]
        assert "no quick laps" in result["warning"]

        # Verify only VER has statistics
        assert len(result["statistics"]) == 1
        assert result["statistics"][0]["driver"] == "VER"


class TestSanitizeFilename:
    """Unit tests for filename sanitization."""

    def test_sanitize_simple_name(self):
        """Test sanitization of simple name."""
        assert sanitize_filename("Monaco") == "monaco"

    def test_sanitize_name_with_spaces(self):
        """Test sanitization of name with spaces."""
        assert sanitize_filename("Abu Dhabi") == "abu_dhabi"

    def test_sanitize_name_with_hyphens(self):
        """Test sanitization of name with hyphens."""
        assert sanitize_filename("Emilia-Romagna") == "emilia_romagna"

    def test_sanitize_name_with_special_chars(self):
        """Test sanitization of name with special characters (diacritics stripped)."""
        assert sanitize_filename("São Paulo") == "sao_paulo"

    def test_sanitize_multiple_spaces(self):
        """Test sanitization of name with multiple consecutive spaces."""
        assert sanitize_filename("Great  Britain") == "great_britain"

    def test_sanitize_leading_trailing_spaces(self):
        """Test sanitization removes leading/trailing underscores."""
        assert sanitize_filename(" Monaco ") == "monaco"
