"""Tests for telemetry chart generation."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from pitlane_agent.commands.analyze.telemetry import (
    CHANNELS,
    _build_customdata,
    _build_hover_template,
    _build_merged_telemetry,
    generate_telemetry_chart,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_telemetry_df(speed_vals, rpm_vals=None, distance_vals=None):
    """Build a minimal telemetry DataFrame matching CHANNELS keys."""
    n = len(speed_vals)
    return pd.DataFrame(
        {
            "Distance": distance_vals if distance_vals is not None else [float(i * 100) for i in range(n)],
            "Speed": speed_vals,
            "RPM": rpm_vals if rpm_vals is not None else [10000.0] * n,
            "nGear": [7.0] * n,
            "Throttle": [100.0] * n,
            "Brake": [0] * n,
        }
    )


def _make_all_telemetry(drivers_speeds: dict[str, list[float]]):
    """Build the ``all_telemetry`` list expected by helpers."""
    entries = []
    for drv, speeds in drivers_speeds.items():
        entries.append({"driver": drv, "telemetry": _make_telemetry_df(speeds)})
    return entries


CHANNEL_KEYS = [ch["key"] for ch in CHANNELS]


# ---------------------------------------------------------------------------
# _build_merged_telemetry
# ---------------------------------------------------------------------------


class TestBuildMergedTelemetry:
    def test_returns_none_for_single_driver(self):
        entries = _make_all_telemetry({"VER": [300, 310, 320]})
        assert _build_merged_telemetry(entries, CHANNEL_KEYS) is None

    def test_returns_none_for_empty_list(self):
        assert _build_merged_telemetry([], CHANNEL_KEYS) is None

    def test_two_drivers_produces_correct_columns(self):
        entries = _make_all_telemetry({"VER": [300, 310, 320], "HAM": [295, 305, 315]})
        merged = _build_merged_telemetry(entries, CHANNEL_KEYS)

        assert merged is not None
        assert "Distance" in merged.columns
        for ch in CHANNEL_KEYS:
            assert f"{ch}_VER" in merged.columns
            assert f"{ch}_HAM" in merged.columns

    def test_three_drivers_merges_all(self):
        entries = _make_all_telemetry({"VER": [300, 310], "HAM": [295, 305], "LEC": [290, 300]})
        merged = _build_merged_telemetry(entries, CHANNEL_KEYS)

        assert merged is not None
        for drv in ("VER", "HAM", "LEC"):
            assert f"Speed_{drv}" in merged.columns

    def test_merged_values_are_aligned(self):
        entries = _make_all_telemetry({"VER": [300, 310, 320], "HAM": [295, 305, 315]})
        merged = _build_merged_telemetry(entries, CHANNEL_KEYS)

        # Both drivers share the same distance grid so values should be present
        assert not merged["Speed_VER"].isna().any()
        assert not merged["Speed_HAM"].isna().any()


# ---------------------------------------------------------------------------
# _build_customdata
# ---------------------------------------------------------------------------


class TestBuildCustomdata:
    def test_returns_zeros_when_merged_is_none(self):
        tel = _make_telemetry_df([300, 310, 320])
        result = _build_customdata("VER", "Speed", tel, None, ["HAM"])
        assert result.shape == (3, 1)
        np.testing.assert_array_equal(result, np.zeros((3, 1)))

    def test_returns_zeros_when_no_other_drivers(self):
        tel = _make_telemetry_df([300, 310, 320])
        merged = pd.DataFrame({"Distance": [0, 100, 200], "Speed_VER": [300, 310, 320]})
        result = _build_customdata("VER", "Speed", tel, merged, [])
        assert result.shape == (3, 1)
        np.testing.assert_array_equal(result, np.zeros((3, 1)))

    def test_delta_values_are_correct(self):
        entries = _make_all_telemetry({"VER": [300, 310, 320], "HAM": [290, 310, 310]})
        merged = _build_merged_telemetry(entries, CHANNEL_KEYS)
        tel_ver = entries[0]["telemetry"]

        result = _build_customdata("VER", "Speed", tel_ver, merged, ["HAM"])

        # Deltas: 300-290=10, 310-310=0, 320-310=10
        expected = np.array([[10.0], [0.0], [10.0]])
        np.testing.assert_array_almost_equal(result, expected, decimal=1)

    def test_multiple_other_drivers(self):
        entries = _make_all_telemetry({"VER": [300, 310], "HAM": [290, 300], "LEC": [280, 290]})
        merged = _build_merged_telemetry(entries, CHANNEL_KEYS)
        tel_ver = entries[0]["telemetry"]

        result = _build_customdata("VER", "Speed", tel_ver, merged, ["HAM", "LEC"])

        assert result.shape == (2, 2)
        # vs HAM: 10, 10; vs LEC: 20, 20
        np.testing.assert_array_almost_equal(result[:, 0], [10.0, 10.0], decimal=1)
        np.testing.assert_array_almost_equal(result[:, 1], [20.0, 20.0], decimal=1)


# ---------------------------------------------------------------------------
# _build_hover_template
# ---------------------------------------------------------------------------


class TestBuildHoverTemplate:
    def test_basic_structure(self):
        channel = {"key": "Speed", "label": "Speed (km/h)", "fmt": ".0f", "unit": "km/h"}
        tpl = _build_hover_template("VER", channel, [])

        assert "<b>VER</b>" in tpl
        assert "Distance:" in tpl
        assert "Speed (km/h):" in tpl
        assert "km/h" in tpl
        assert "<extra></extra>" in tpl

    def test_includes_delta_lines(self):
        channel = {"key": "Speed", "label": "Speed (km/h)", "fmt": ".0f", "unit": "km/h"}
        tpl = _build_hover_template("VER", channel, ["HAM", "LEC"])

        assert "\u0394 vs HAM" in tpl
        assert "\u0394 vs LEC" in tpl
        assert "customdata[0]" in tpl
        assert "customdata[1]" in tpl

    def test_no_deltas_without_others(self):
        channel = {"key": "RPM", "label": "RPM", "fmt": ".0f", "unit": ""}
        tpl = _build_hover_template("VER", channel, [])
        assert "\u0394" not in tpl

    def test_unit_appears_in_delta_line(self):
        channel = {"key": "Throttle", "label": "Throttle (%)", "fmt": ".0f", "unit": "%"}
        tpl = _build_hover_template("VER", channel, ["HAM"])
        # The delta line should end with the unit
        assert "+.1f}%" in tpl


# ---------------------------------------------------------------------------
# generate_telemetry_chart  (integration-style with mocks)
# ---------------------------------------------------------------------------


class TestGenerateTelemetryChart:
    def test_too_few_drivers(self, tmp_output_dir):
        with pytest.raises(ValueError, match="at least"):
            generate_telemetry_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER"],
                workspace_dir=tmp_output_dir,
            )

    def test_too_many_drivers(self, tmp_output_dir):
        with pytest.raises(ValueError, match="maximum"):
            generate_telemetry_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER", "HAM", "LEC", "NOR", "PIA", "SAI"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.telemetry.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_team")
    @patch("pitlane_agent.commands.analyze.telemetry.build_chart_path")
    def test_success_two_drivers(
        self,
        mock_build_path,
        mock_get_team,
        mock_get_color,
        mock_load_session,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        output_file = tmp_output_dir / "charts" / "telemetry.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        mock_build_path.return_value = output_file

        mock_load_session.return_value = mock_fastf1_session
        mock_get_color.return_value = "#0600EF"
        mock_get_team.return_value = "Red Bull Racing"

        mock_telemetry = _make_telemetry_df(
            [250, 280, 310, 290, 270],
            rpm_vals=[10000, 11000, 12000, 11500, 10500],
        )

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__ = lambda self, key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
            "Sector1Time": pd.Timedelta(seconds=28.123),
            "Sector2Time": pd.Timedelta(seconds=30.456),
            "Sector3Time": pd.Timedelta(seconds=30.921),
            "SpeedST": 315.0,
            "SpeedFL": 298.0,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap
        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        result = generate_telemetry_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert result["output_format"] == "html"
        assert len(result["drivers_compared"]) == 2
        assert len(result["statistics"]) == 2
        assert result["statistics"][0]["max_speed"] == 310.0
        assert result["statistics"][0]["sector_1_time"] == "28.123"
        assert result["statistics"][0]["sector_2_time"] == "30.456"
        assert result["statistics"][0]["sector_3_time"] == "30.921"
        assert result["statistics"][0]["speed_trap"] == 315.0
        assert result["statistics"][0]["speed_fl"] == 298.0
        assert result["corners_annotated"] is False
        assert output_file.exists()

    @patch("pitlane_agent.commands.analyze.telemetry.load_session_or_testing")
    def test_session_error_propagates(self, mock_load_session, tmp_output_dir):
        mock_load_session.side_effect = Exception("Session not found")
        with pytest.raises(Exception, match="Session not found"):
            generate_telemetry_chart(
                year=2024,
                gp="InvalidGP",
                session_type="Q",
                drivers=["VER", "HAM"],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.telemetry.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_team")
    @patch("pitlane_agent.commands.analyze.telemetry.build_chart_path")
    def test_empty_laps_skips_driver(
        self,
        mock_build_path,
        mock_get_team,
        mock_get_color,
        mock_load_session,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        output_file = tmp_output_dir / "charts" / "telemetry.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        mock_build_path.return_value = output_file

        mock_load_session.return_value = mock_fastf1_session
        mock_get_color.return_value = "#0600EF"
        mock_get_team.return_value = "Red Bull Racing"

        mock_telemetry = _make_telemetry_df([250, 280, 310])

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__ = lambda self, key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
            "Sector1Time": pd.Timedelta(seconds=28.123),
            "Sector2Time": pd.Timedelta(seconds=30.456),
            "Sector3Time": pd.Timedelta(seconds=30.921),
            "SpeedST": 315.0,
            "SpeedFL": 298.0,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_empty_laps = MagicMock()
        mock_empty_laps.empty = True

        mock_valid_laps = MagicMock()
        mock_valid_laps.empty = False
        mock_valid_laps.pick_fastest.return_value = mock_fastest_lap

        def pick_drivers_side_effect(driver):
            return mock_empty_laps if driver == "VER" else mock_valid_laps

        mock_fastf1_session.laps.pick_drivers.side_effect = pick_drivers_side_effect

        result = generate_telemetry_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
        )

        assert result["drivers_compared"] == ["HAM"]
        assert len(result["statistics"]) == 1

    @patch("pitlane_agent.commands.analyze.telemetry.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_team")
    @patch("pitlane_agent.commands.analyze.telemetry.build_chart_path")
    def test_corner_annotations(
        self,
        mock_build_path,
        mock_get_team,
        mock_get_color,
        mock_load_session,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        output_file = tmp_output_dir / "charts" / "telemetry.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        mock_build_path.return_value = output_file

        mock_load_session.return_value = mock_fastf1_session
        mock_get_color.return_value = "#0600EF"
        mock_get_team.return_value = "Red Bull Racing"

        mock_telemetry = _make_telemetry_df([250, 280, 310, 290, 270])

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__ = lambda self, key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
            "Sector1Time": pd.Timedelta(seconds=28.123),
            "Sector2Time": pd.Timedelta(seconds=30.456),
            "Sector3Time": pd.Timedelta(seconds=30.921),
            "SpeedST": 315.0,
            "SpeedFL": 298.0,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap
        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        mock_corners = pd.DataFrame({"Number": [1, 2], "Letter": ["", "A"], "Distance": [100.0, 250.0]})
        mock_circuit_info = MagicMock()
        mock_circuit_info.corners = mock_corners
        mock_fastf1_session.get_circuit_info.return_value = mock_circuit_info

        result = generate_telemetry_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
            annotate_corners=True,
        )

        assert result["corners_annotated"] is True

    @patch("pitlane_agent.commands.analyze.telemetry.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_team")
    @patch("pitlane_agent.commands.analyze.telemetry.build_chart_path")
    def test_corner_annotation_failure_is_graceful(
        self,
        mock_build_path,
        mock_get_team,
        mock_get_color,
        mock_load_session,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        output_file = tmp_output_dir / "charts" / "telemetry.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        mock_build_path.return_value = output_file

        mock_load_session.return_value = mock_fastf1_session
        mock_get_color.return_value = "#0600EF"
        mock_get_team.return_value = "Red Bull Racing"

        mock_telemetry = _make_telemetry_df([250, 280, 310])

        mock_fastest_lap = MagicMock()
        mock_fastest_lap.__getitem__ = lambda self, key: {
            "LapTime": pd.Timedelta(seconds=89.5),
            "LapNumber": 12,
            "Sector1Time": pd.Timedelta(seconds=28.123),
            "Sector2Time": pd.Timedelta(seconds=30.456),
            "Sector3Time": pd.Timedelta(seconds=30.921),
            "SpeedST": 315.0,
            "SpeedFL": 298.0,
        }[key]

        mock_car_data = MagicMock()
        mock_car_data.add_distance.return_value = mock_telemetry
        mock_fastest_lap.get_car_data.return_value = mock_car_data

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_driver_laps.pick_fastest.return_value = mock_fastest_lap
        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        mock_fastf1_session.get_circuit_info.side_effect = Exception("No circuit data")

        result = generate_telemetry_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            drivers=["VER", "HAM"],
            workspace_dir=tmp_output_dir,
            annotate_corners=True,
        )

        assert result["corners_annotated"] is False
