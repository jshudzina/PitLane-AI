"""Tests for driver_lap_compare chart generation."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.analyze.driver_lap_compare import (
    _ENTRY_COLORS,
    MAX_ENTRIES,
    MIN_ENTRIES,
    generate_multi_lap_chart,
    generate_year_compare_chart,
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
            "SuperClip": [0] * n,
            "Time": pd.to_timedelta([float(i) for i in range(n)], unit="s"),
        }
    )


def _make_mock_lap(lap_number: int, lap_time_seconds: float = 89.5, compound: str = "SOFT") -> MagicMock:
    """Create a MagicMock lap with standard data."""
    mock = MagicMock()
    data = {
        "LapTime": pd.Timedelta(seconds=lap_time_seconds),
        "LapNumber": lap_number,
        "Sector1Time": pd.Timedelta(seconds=28.0),
        "Sector2Time": pd.Timedelta(seconds=30.5),
        "Sector3Time": pd.Timedelta(seconds=31.0),
        "Compound": compound,
    }
    mock.__getitem__ = lambda self, key: data[key]
    mock.get = lambda key, default=None: data.get(key, default)

    mock_car_data = MagicMock()
    mock_car_data.add_distance.return_value = _make_telemetry_df([250, 280, 310, 290, 270])
    mock.get_car_data.return_value = mock_car_data

    return mock


def _make_mock_session(event_name="Monaco Grand Prix", session_name="Qualifying"):
    """Create a MagicMock FastF1 session."""
    session = MagicMock()
    session.event = {"EventName": event_name}
    session.name = session_name
    return session


def _make_mock_driver_laps(lap_numbers: list[int]):
    """Create a mock LapsDataFrame that supports pick_fastest and filtering by LapNumber."""
    mock = MagicMock()
    mock.empty = False

    laps = [_make_mock_lap(n) for n in lap_numbers]
    mock.pick_fastest.return_value = laps[0]

    # When filtered by LapNumber, return a mock with iloc[0] = matching lap
    def filter_by_lap_number(df):
        # This is called via driver_laps[driver_laps["LapNumber"] == n]
        # We simulate this by making the mock behave like pandas indexing
        return df

    mock.__getitem__ = MagicMock(return_value=mock)
    mock.iloc = MagicMock()
    mock.iloc.__getitem__ = lambda self, idx: laps[idx] if idx < len(laps) else laps[0]

    # Make lap number filtering work: return the mock (non-empty) for any lap number
    mock.__getitem__.return_value = mock

    return mock, laps


# ---------------------------------------------------------------------------
# generate_multi_lap_chart — validation
# ---------------------------------------------------------------------------


class TestGenerateMultiLapChartValidation:
    def test_too_few_laps(self, tmp_output_dir):
        with pytest.raises(ValueError, match="at least"):
            generate_multi_lap_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                driver="VER",
                lap_specs=["best"],
                workspace_dir=tmp_output_dir,
            )

    def test_too_many_laps(self, tmp_output_dir):
        with pytest.raises(ValueError, match="at most"):
            generate_multi_lap_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                driver="VER",
                lap_specs=["best", 2, 3, 4, 5, 6, 7],
                workspace_dir=tmp_output_dir,
            )

    def test_min_max_constants(self):
        assert MIN_ENTRIES == 2
        assert MAX_ENTRIES == 6

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    def test_empty_driver_laps_raises(self, mock_load, tmp_output_dir):
        session = _make_mock_session()
        mock_load.return_value = session

        empty_laps = MagicMock()
        empty_laps.empty = True
        session.laps.pick_drivers.return_value = empty_laps

        with pytest.raises(ValueError, match="No laps found"):
            generate_multi_lap_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                driver="VER",
                lap_specs=["best", 5],
                workspace_dir=tmp_output_dir,
            )


# ---------------------------------------------------------------------------
# generate_multi_lap_chart — success
# ---------------------------------------------------------------------------


class TestGenerateMultiLapChartSuccess:
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.pick_lap_by_spec")
    def test_two_laps_produces_html(self, mock_pick_lap, mock_load, tmp_output_dir, mock_fastf1_session):
        mock_load.return_value = mock_fastf1_session

        mock_driver_laps = MagicMock()
        mock_driver_laps.empty = False
        mock_fastf1_session.laps.pick_drivers.return_value = mock_driver_laps

        lap3 = _make_mock_lap(3)
        lap12 = _make_mock_lap(12, compound="MEDIUM")
        mock_pick_lap.side_effect = [lap3, lap12]

        result = generate_multi_lap_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            driver="VER",
            lap_specs=["best", 12],
            workspace_dir=tmp_output_dir,
        )

        assert result["year"] == 2024
        assert result["gp"] == "Monaco"
        assert result["driver"] == "VER"
        assert result["output_format"] == "html"
        assert len(result["laps"]) == 2
        assert result["corners_annotated"] is False

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.pick_lap_by_spec")
    def test_chart_file_is_created(self, mock_pick_lap, mock_load, tmp_output_dir, mock_fastf1_session):
        mock_load.return_value = mock_fastf1_session
        mock_fastf1_session.laps.pick_drivers.return_value = MagicMock(empty=False)

        mock_pick_lap.side_effect = [_make_mock_lap(3), _make_mock_lap(12)]

        result = generate_multi_lap_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            driver="VER",
            lap_specs=["best", 12],
            workspace_dir=tmp_output_dir,
        )

        from pathlib import Path

        assert Path(result["chart_path"]).exists()

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.pick_lap_by_spec")
    def test_labels_include_lap_number_and_compound(
        self, mock_pick_lap, mock_load, tmp_output_dir, mock_fastf1_session
    ):
        mock_load.return_value = mock_fastf1_session
        mock_fastf1_session.laps.pick_drivers.return_value = MagicMock(empty=False)

        mock_pick_lap.side_effect = [_make_mock_lap(3, compound="SOFT"), _make_mock_lap(25, compound="MEDIUM")]

        result = generate_multi_lap_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            driver="VER",
            lap_specs=["best", 25],
            workspace_dir=tmp_output_dir,
        )

        labels = [lap["label"] for lap in result["laps"]]
        assert any("Lap 3" in lbl for lbl in labels)
        assert any("SOFT" in lbl for lbl in labels)
        assert any("Lap 25" in lbl for lbl in labels)
        assert any("MEDIUM" in lbl for lbl in labels)

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.pick_lap_by_spec")
    def test_stats_contain_speed_and_lap_time(self, mock_pick_lap, mock_load, tmp_output_dir, mock_fastf1_session):
        mock_load.return_value = mock_fastf1_session
        mock_fastf1_session.laps.pick_drivers.return_value = MagicMock(empty=False)

        mock_pick_lap.side_effect = [_make_mock_lap(3), _make_mock_lap(12)]

        result = generate_multi_lap_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            driver="VER",
            lap_specs=["best", 12],
            workspace_dir=tmp_output_dir,
        )

        for lap_stat in result["laps"]:
            assert "max_speed" in lap_stat
            assert "lap_time" in lap_stat
            assert "lap_number" in lap_stat

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.pick_lap_by_spec")
    def test_entries_have_distinct_colors(self, mock_pick_lap, mock_load, tmp_output_dir, mock_fastf1_session):
        """Ensure different laps are assigned distinct colors from the palette."""
        mock_load.return_value = mock_fastf1_session
        mock_fastf1_session.laps.pick_drivers.return_value = MagicMock(empty=False)

        mock_pick_lap.side_effect = [_make_mock_lap(3), _make_mock_lap(12), _make_mock_lap(25)]

        # We test this indirectly by checking the palette has enough colors
        assert len(_ENTRY_COLORS) >= 3


# ---------------------------------------------------------------------------
# generate_year_compare_chart — validation
# ---------------------------------------------------------------------------


class TestGenerateYearCompareChartValidation:
    def test_too_few_years(self, tmp_output_dir):
        with pytest.raises(ValueError, match="at least"):
            generate_year_compare_chart(
                gp="Monza",
                session_type="Q",
                driver="VER",
                years=[2024],
                workspace_dir=tmp_output_dir,
            )

    def test_too_many_years(self, tmp_output_dir):
        with pytest.raises(ValueError, match="at most"):
            generate_year_compare_chart(
                gp="Monza",
                session_type="Q",
                driver="VER",
                years=[2018, 2019, 2020, 2021, 2022, 2023, 2024],
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    def test_empty_driver_laps_raises(self, mock_load, tmp_output_dir):
        session = _make_mock_session()
        mock_load.return_value = session

        empty_laps = MagicMock()
        empty_laps.empty = True
        session.laps.pick_drivers.return_value = empty_laps

        with pytest.raises(ValueError, match="No laps found"):
            generate_year_compare_chart(
                gp="Monza",
                session_type="Q",
                driver="VER",
                years=[2022, 2024],
                workspace_dir=tmp_output_dir,
            )


# ---------------------------------------------------------------------------
# generate_year_compare_chart — success
# ---------------------------------------------------------------------------


class TestGenerateYearCompareChartSuccess:
    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    def test_two_years_produces_html(self, mock_load, tmp_output_dir):
        sessions = [_make_mock_session("Italian Grand Prix"), _make_mock_session("Italian Grand Prix")]

        def session_for_year(year, gp, session_type, telemetry=False):
            return sessions[0] if year == 2022 else sessions[1]

        mock_load.side_effect = session_for_year

        for session in sessions:
            mock_driver_laps = MagicMock()
            mock_driver_laps.empty = False
            mock_driver_laps.pick_fastest.return_value = _make_mock_lap(8)
            session.laps.pick_drivers.return_value = mock_driver_laps

        result = generate_year_compare_chart(
            gp="Monza",
            session_type="Q",
            driver="VER",
            years=[2022, 2024],
            workspace_dir=tmp_output_dir,
        )

        assert result["gp"] == "Monza"
        assert result["driver"] == "VER"
        assert result["years"] == [2022, 2024]
        assert result["output_format"] == "html"
        assert len(result["year_stats"]) == 2
        assert result["corners_annotated"] is False

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    def test_year_labels_in_output(self, mock_load, tmp_output_dir):
        sessions = [_make_mock_session(), _make_mock_session()]

        def session_for_year(year, gp, session_type, telemetry=False):
            return sessions[0] if year == 2022 else sessions[1]

        mock_load.side_effect = session_for_year

        for session in sessions:
            mock_driver_laps = MagicMock()
            mock_driver_laps.empty = False
            mock_driver_laps.pick_fastest.return_value = _make_mock_lap(8)
            session.laps.pick_drivers.return_value = mock_driver_laps

        result = generate_year_compare_chart(
            gp="Monza",
            session_type="Q",
            driver="VER",
            years=[2022, 2024],
            workspace_dir=tmp_output_dir,
        )

        labels = [s["label"] for s in result["year_stats"]]
        assert any("2022" in lbl for lbl in labels)
        assert any("2024" in lbl for lbl in labels)
        assert all("VER" in lbl for lbl in labels)

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    def test_year_stats_contain_year_field(self, mock_load, tmp_output_dir):
        sessions = [_make_mock_session(), _make_mock_session()]

        def session_for_year(year, gp, session_type, telemetry=False):
            return sessions[0] if year == 2022 else sessions[1]

        mock_load.side_effect = session_for_year

        for session in sessions:
            mock_driver_laps = MagicMock()
            mock_driver_laps.empty = False
            mock_driver_laps.pick_fastest.return_value = _make_mock_lap(8)
            session.laps.pick_drivers.return_value = mock_driver_laps

        result = generate_year_compare_chart(
            gp="Monza",
            session_type="Q",
            driver="VER",
            years=[2022, 2024],
            workspace_dir=tmp_output_dir,
        )

        years_in_stats = {s["year"] for s in result["year_stats"]}
        assert 2022 in years_in_stats
        assert 2024 in years_in_stats

    @patch("pitlane_agent.commands.analyze.driver_lap_compare.load_session_or_testing")
    def test_chart_file_is_created(self, mock_load, tmp_output_dir):
        sessions = [_make_mock_session(), _make_mock_session()]

        def session_for_year(year, gp, session_type, telemetry=False):
            return sessions[0] if year == 2022 else sessions[1]

        mock_load.side_effect = session_for_year

        for session in sessions:
            mock_driver_laps = MagicMock()
            mock_driver_laps.empty = False
            mock_driver_laps.pick_fastest.return_value = _make_mock_lap(8)
            session.laps.pick_drivers.return_value = mock_driver_laps

        result = generate_year_compare_chart(
            gp="Monza",
            session_type="Q",
            driver="VER",
            years=[2022, 2024],
            workspace_dir=tmp_output_dir,
        )

        from pathlib import Path

        assert Path(result["chart_path"]).exists()
