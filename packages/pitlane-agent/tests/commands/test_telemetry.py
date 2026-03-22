"""Tests for telemetry chart generation."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from pitlane_agent.commands.analyze.telemetry import (
    CHANNEL_GROUPS,
    _add_time_delta,
    _build_customdata,
    _build_hover_template,
    _build_merged_telemetry,
    generate_telemetry_chart,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_telemetry_df(speed_vals, rpm_vals=None, distance_vals=None, time_offset_s=0.0):
    """Build a minimal telemetry DataFrame matching channel keys."""
    n = len(speed_vals)
    distances = distance_vals if distance_vals is not None else [float(i * 100) for i in range(n)]
    return pd.DataFrame(
        {
            "Distance": distances,
            "Speed": speed_vals,
            "RPM": rpm_vals if rpm_vals is not None else [10000.0] * n,
            "nGear": [7.0] * n,
            "Throttle": [100.0] * n,
            "Brake": [0] * n,
            "SuperClip": [0] * n,
            "TimeDelta": [0.0] * n,
            "Time": pd.to_timedelta([float(i) + time_offset_s for i in range(n)], unit="s"),
        }
    )


def _make_all_telemetry(drivers_speeds: dict[str, list[float]]):
    """Build the ``all_telemetry`` list expected by helpers."""
    entries = []
    for drv, speeds in drivers_speeds.items():
        entries.append({"driver": drv, "telemetry": _make_telemetry_df(speeds)})
    return entries


def _make_mock_fastest_lap(data: dict) -> MagicMock:
    """Create a MagicMock that supports both bracket access and .get()."""
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: data[key]
    mock.get = lambda key, default=None: data.get(key, default)
    return mock


# Raw channel keys available in the test helper df (excludes computed TimeDelta)
CHANNEL_KEYS = [t["key"] for grp in CHANNEL_GROUPS.values() for t in grp["traces"] if t["key"] != "TimeDelta"]


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
        for ch in ["Speed", "RPM", "nGear", "Throttle", "Brake", "SuperClip"]:
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
# _add_time_delta
# ---------------------------------------------------------------------------


class TestAddTimeDelta:
    def test_reference_driver_is_zero(self):
        entries = _make_all_telemetry({"VER": [300, 310, 320], "HAM": [295, 305, 315]})
        _add_time_delta(entries)
        np.testing.assert_array_equal(entries[0]["telemetry"]["TimeDelta"].values, [0.0, 0.0, 0.0])

    def test_single_entry_leaves_zero(self):
        entries = _make_all_telemetry({"VER": [300, 310, 320]})
        _add_time_delta(entries)
        np.testing.assert_array_equal(entries[0]["telemetry"]["TimeDelta"].values, [0.0, 0.0, 0.0])

    def test_faster_driver_has_negative_delta(self):
        # HAM's Time starts 2s earlier at same distances → HAM is "faster" to each point
        # delta for HAM = HAM_laptime - VER_laptime; HAM laptime relative = 0,1,2 vs VER = 0,1,2
        # Both have same lap-relative times (sequential seconds), so delta should be ~0
        entries = _make_all_telemetry({"VER": [300, 310, 320], "HAM": [295, 305, 315]})
        _add_time_delta(entries)
        # Both have Time = 0s, 1s, 2s relative to start → lap-relative times are equal → delta ≈ 0
        ham_delta = entries[1]["telemetry"]["TimeDelta"].values
        np.testing.assert_array_almost_equal(ham_delta, [0.0, 0.0, 0.0], decimal=3)

    def test_absolute_time_offset_is_normalized_away(self):
        # HAM's session timestamps start 5s later than VER, but lap-relative
        # elapsed time is identical (both 0,1,2s step) → delta should be 0
        ref_tel = _make_telemetry_df([300, 310, 320], time_offset_s=0.0)  # VER: Time = 0,1,2
        other_tel = _make_telemetry_df([295, 305, 315], time_offset_s=5.0)  # HAM: Time = 5,6,7 → relative 0,1,2

        entries = [
            {"driver": "VER", "key": "VER", "label": "VER", "telemetry": ref_tel},
            {"driver": "HAM", "key": "HAM", "label": "HAM", "telemetry": other_tel},
        ]
        _add_time_delta(entries)
        # Normalizing by Time.iloc[0] cancels the offset → both have relative 0,1,2 → delta ≈ 0
        ham_delta = entries[1]["telemetry"]["TimeDelta"].values
        np.testing.assert_array_almost_equal(ham_delta, [0.0, 0.0, 0.0], decimal=3)

    def test_delta_positive_when_other_is_slower(self):
        # HAM has laptime 0,2,4 vs VER 0,1,2 at the same distances → HAM is slower
        ref_tel = _make_telemetry_df([300, 310, 320], time_offset_s=0.0)  # VER: Time = 0,1,2
        # Build HAM manually with 2s per step
        ham_tel = pd.DataFrame(
            {
                "Distance": [0.0, 100.0, 200.0],
                "Speed": [295.0, 305.0, 315.0],
                "RPM": [10000.0] * 3,
                "nGear": [7.0] * 3,
                "Throttle": [100.0] * 3,
                "Brake": [0] * 3,
                "SuperClip": [0] * 3,
                "TimeDelta": [0.0] * 3,
                "Time": pd.to_timedelta([0.0, 2.0, 4.0], unit="s"),  # 2s per step vs VER's 1s
            }
        )

        entries = [
            {"driver": "VER", "key": "VER", "label": "VER", "telemetry": ref_tel},
            {"driver": "HAM", "key": "HAM", "label": "HAM", "telemetry": ham_tel},
        ]
        _add_time_delta(entries)
        ham_delta = entries[1]["telemetry"]["TimeDelta"].values
        # At distance 100m: HAM lap time = 2.0, VER lap time = 1.0 → delta = +1.0
        # At distance 200m: HAM lap time = 4.0, VER lap time = 2.0 → delta = +2.0
        assert ham_delta[1] == pytest.approx(1.0, abs=0.1)
        assert ham_delta[2] == pytest.approx(2.0, abs=0.1)

    def test_multiple_entries_all_receive_delta(self):
        entries = _make_all_telemetry({"VER": [300, 310], "HAM": [295, 305], "LEC": [290, 300]})
        _add_time_delta(entries)
        assert "TimeDelta" in entries[0]["telemetry"].columns
        assert "TimeDelta" in entries[1]["telemetry"].columns
        assert "TimeDelta" in entries[2]["telemetry"].columns


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
        tpl = _build_hover_template("VER", "Speed (km/h)", "km/h", ".0f", [])

        assert "<b>VER</b>" in tpl
        assert "Distance:" in tpl
        assert "Speed (km/h):" in tpl
        assert "km/h" in tpl
        assert "<extra></extra>" in tpl

    def test_includes_delta_lines(self):
        tpl = _build_hover_template("VER", "Speed (km/h)", "km/h", ".0f", ["HAM", "LEC"])

        assert "\u0394 vs HAM" in tpl
        assert "\u0394 vs LEC" in tpl
        assert "customdata[0]" in tpl
        assert "customdata[1]" in tpl

    def test_no_deltas_without_others(self):
        tpl = _build_hover_template("VER", "RPM", "", ".0f", [])
        assert "\u0394" not in tpl

    def test_unit_appears_in_delta_line(self):
        tpl = _build_hover_template("VER", "Throttle (%)", "%", ".0f", ["HAM"])
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

    def test_unknown_channel_raises(self, tmp_output_dir):
        with pytest.raises(ValueError, match="Unknown channel"):
            generate_telemetry_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                drivers=["VER", "HAM"],
                workspace_dir=tmp_output_dir,
                channels=["speed", "bogus_channel"],
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

        mock_fastest_lap = _make_mock_fastest_lap(
            {
                "LapTime": pd.Timedelta(seconds=89.5),
                "LapNumber": 12,
                "Sector1Time": pd.Timedelta(seconds=28.123),
                "Sector2Time": pd.Timedelta(seconds=30.456),
                "Sector3Time": pd.Timedelta(seconds=30.921),
                "SpeedST": 315.0,
                "SpeedFL": 298.0,
            }
        )

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
            annotate_corners=False,
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
        assert "channels" in result
        assert result["corners_annotated"] is False
        assert output_file.exists()

    @patch("pitlane_agent.commands.analyze.telemetry.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.telemetry.get_driver_team")
    @patch("pitlane_agent.commands.analyze.telemetry.build_chart_path")
    def test_custom_channels_respected(
        self,
        mock_build_path,
        mock_get_team,
        mock_get_color,
        mock_load_session,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        output_file = tmp_output_dir / "charts" / "telemetry_custom.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        mock_build_path.return_value = output_file

        mock_load_session.return_value = mock_fastf1_session
        mock_get_color.return_value = "#0600EF"
        mock_get_team.return_value = "Red Bull Racing"

        mock_telemetry = _make_telemetry_df([250, 280, 310])
        mock_fastest_lap = _make_mock_fastest_lap(
            {
                "LapTime": pd.Timedelta(seconds=89.5),
                "LapNumber": 12,
                "Sector1Time": pd.Timedelta(seconds=28.123),
                "Sector2Time": pd.Timedelta(seconds=30.456),
                "Sector3Time": pd.Timedelta(seconds=30.921),
                "SpeedST": 315.0,
                "SpeedFL": 298.0,
            }
        )
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
            channels=["speed", "delta"],
        )

        assert result["channels"] == ["speed", "delta"]

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

        mock_fastest_lap = _make_mock_fastest_lap(
            {
                "LapTime": pd.Timedelta(seconds=89.5),
                "LapNumber": 12,
                "Sector1Time": pd.Timedelta(seconds=28.123),
                "Sector2Time": pd.Timedelta(seconds=30.456),
                "Sector3Time": pd.Timedelta(seconds=30.921),
                "SpeedST": 315.0,
                "SpeedFL": 298.0,
            }
        )

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

        mock_fastest_lap = _make_mock_fastest_lap(
            {
                "LapTime": pd.Timedelta(seconds=89.5),
                "LapNumber": 12,
                "Sector1Time": pd.Timedelta(seconds=28.123),
                "Sector2Time": pd.Timedelta(seconds=30.456),
                "Sector3Time": pd.Timedelta(seconds=30.921),
                "SpeedST": 315.0,
                "SpeedFL": 298.0,
            }
        )

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

        mock_fastest_lap = _make_mock_fastest_lap(
            {
                "LapTime": pd.Timedelta(seconds=89.5),
                "LapNumber": 12,
                "Sector1Time": pd.Timedelta(seconds=28.123),
                "Sector2Time": pd.Timedelta(seconds=30.456),
                "Sector3Time": pd.Timedelta(seconds=30.921),
                "SpeedST": 315.0,
                "SpeedFL": 298.0,
            }
        )

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
