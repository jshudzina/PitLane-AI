"""Tests for qualifying_results command."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.analyze.qualifying_results import generate_qualifying_results_chart

# ── Local mock factory ────────────────────────────────────────────────────────


def _td(seconds: float) -> pd.Timedelta:
    """Convenience: float seconds → pd.Timedelta."""
    return pd.Timedelta(seconds=seconds)


def _make_qualifying_session(n_drivers: int = 20) -> MagicMock:
    """Build a mock FastF1 qualifying session with Q1/Q2/Q3 result columns.

    Produces a session with session.results as a real DataFrame containing:
    Position, Abbreviation, TeamName, Q1, Q2, Q3 (pd.Timedelta / pd.NaT).

    Phase assignments by driver count:
        20 drivers: Q3=top 10, Q2=next 5, Q1=bottom 5
        22 drivers: Q3=top 10, Q2=next 6, Q1=bottom 6
    """
    assert n_drivers in (20, 22), "Only 20 or 22 driver counts are supported"

    q3_count = 10
    q2_count = 5 if n_drivers == 20 else 6

    # Base times: pole = 70.000s; each successive driver is a bit slower
    base_q1 = 72.000
    base_q2 = 71.000
    base_q3 = 70.000

    rows = []
    for pos in range(1, n_drivers + 1):
        abbr = f"D{pos:02d}"
        team = f"Team{(pos - 1) // 2 + 1}"
        q1_time = _td(base_q1 + (pos - 1) * 0.15)

        if pos <= q3_count:
            q2_time = _td(base_q2 + (pos - 1) * 0.12)
            q3_time = _td(base_q3 + (pos - 1) * 0.10)
        elif pos <= q3_count + q2_count:
            q2_time = _td(base_q2 + (pos - 1) * 0.12)
            q3_time = pd.NaT
        else:
            q2_time = pd.NaT
            q3_time = pd.NaT

        rows.append(
            {
                "Position": float(pos),  # FastF1 returns float
                "Abbreviation": abbr,
                "TeamName": team,
                "Q1": q1_time,
                "Q2": q2_time,
                "Q3": q3_time,
            }
        )

    session = MagicMock()
    session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
    session.name = "Qualifying"
    session.results = pd.DataFrame(rows)
    return session


def _setup_plt_mock(mock_plt, mock_color, mock_contrast):
    """Shared mock setup for plt and color utilities."""
    mock_color.return_value = "#0600EF"
    mock_contrast.return_value = "#0600EF"
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)
    mock_ax.get_xlim.return_value = (0.0, 5.0)
    return mock_fig, mock_ax


# ── Test class ────────────────────────────────────────────────────────────────


class TestQualifyingResultsChart:
    """Unit tests for generate_qualifying_results_chart."""

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_generate_qualifying_chart_success(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """20-driver session: chart path returned, JSON structure correct, pole driver identified."""
        mock_load.return_value = _make_qualifying_session(20)
        _setup_plt_mock(mock_plt, mock_color, mock_contrast)

        result = generate_qualifying_results_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        assert result["pole_driver"] == "D01"
        assert result["pole_time_s"] == pytest.approx(70.0, abs=0.01)
        assert result["statistics"][0]["gap_to_pole_s"] == 0.0
        assert "chart_path" in result
        assert "statistics" in result
        assert len(result["statistics"]) == 20
        assert result["chart_path"].endswith(".png")
        assert result["workspace"] == str(tmp_output_dir)
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["year"] == 2024

        mock_load.assert_called_once_with(2024, "Monaco", "Q", test_number=None, session_number=None)

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_phase_assignment_20_drivers(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """20-driver session: P1-P10 in Q3, P11-P15 in Q2, P16-P20 in Q1."""
        mock_load.return_value = _make_qualifying_session(20)
        _setup_plt_mock(mock_plt, mock_color, mock_contrast)

        result = generate_qualifying_results_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        stats = result["statistics"]
        q3_stats = [s for s in stats if s["phase"] == "Q3"]
        q2_stats = [s for s in stats if s["phase"] == "Q2"]
        q1_stats = [s for s in stats if s["phase"] == "Q1"]

        assert len(q3_stats) == 10
        assert len(q2_stats) == 5
        assert len(q1_stats) == 5
        assert all(s["position"] <= 10 for s in q3_stats)
        assert all(11 <= s["position"] <= 15 for s in q2_stats)
        assert all(s["position"] >= 16 for s in q1_stats)

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_phase_assignment_22_drivers(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """2026 format (22 cars): P1-P10 in Q3, P11-P16 in Q2, P17-P22 in Q1."""
        mock_load.return_value = _make_qualifying_session(22)
        _setup_plt_mock(mock_plt, mock_color, mock_contrast)

        result = generate_qualifying_results_chart(
            year=2026,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        stats = result["statistics"]
        q3_stats = [s for s in stats if s["phase"] == "Q3"]
        q2_stats = [s for s in stats if s["phase"] == "Q2"]
        q1_stats = [s for s in stats if s["phase"] == "Q1"]

        assert len(q3_stats) == 10
        assert len(q2_stats) == 6
        assert len(q1_stats) == 6
        assert all(s["position"] <= 10 for s in q3_stats)
        assert all(11 <= s["position"] <= 16 for s in q2_stats)
        assert all(s["position"] >= 17 for s in q1_stats)

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_gap_to_pole_calculation(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """P1 gap=0.0, all others positive; Q3 gaps increase monotonically."""
        mock_load.return_value = _make_qualifying_session(20)
        _setup_plt_mock(mock_plt, mock_color, mock_contrast)

        result = generate_qualifying_results_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        stats = result["statistics"]
        assert stats[0]["gap_to_pole_s"] == 0.0
        for i in range(1, len(stats)):
            assert stats[i]["gap_to_pole_s"] > 0.0

        # Within Q3 (positions 1–10), gaps increase monotonically
        q3_gaps = [s["gap_to_pole_s"] for s in stats if s["phase"] == "Q3"]
        for i in range(1, len(q3_gaps)):
            assert q3_gaps[i] > q3_gaps[i - 1]

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_statistics_structure(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """Every statistics entry has required keys with correct types."""
        mock_load.return_value = _make_qualifying_session(20)
        _setup_plt_mock(mock_plt, mock_color, mock_contrast)

        result = generate_qualifying_results_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        required_keys = {"position", "abbreviation", "team", "phase", "best_time_s", "best_time_str", "gap_to_pole_s"}
        for stat in result["statistics"]:
            assert required_keys.issubset(stat.keys())
            assert stat["phase"] in ("Q3", "Q2", "Q1")
            assert isinstance(stat["position"], int)
            assert isinstance(stat["best_time_s"], float)
            assert isinstance(stat["gap_to_pole_s"], float)
            assert stat["best_time_str"] is not None

    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_session_load_error(self, mock_load, tmp_output_dir):
        """Exception from session load propagates unchanged."""
        mock_load.side_effect = Exception("Session not found")

        with pytest.raises(Exception, match="Session not found"):
            generate_qualifying_results_chart(
                year=2024,
                gp="InvalidGP",
                session_type="Q",
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_missing_q_columns_raises_value_error(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """ValueError raised when session.results lacks Q1/Q2/Q3 columns."""
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Qualifying"
        # Results without Q1/Q2/Q3 columns (e.g., a race session passed by mistake)
        session.results = pd.DataFrame(
            {
                "Position": [1.0, 2.0],
                "Abbreviation": ["VER", "LEC"],
                "TeamName": ["Red Bull Racing", "Ferrari"],
            }
        )
        mock_load.return_value = session

        with pytest.raises(ValueError, match="missing columns"):
            generate_qualifying_results_chart(
                year=2024,
                gp="Monaco",
                session_type="Q",
                workspace_dir=tmp_output_dir,
            )

    def test_laptime_format(self):
        """format_lap_time produces M:SS.mmm for standard qualifying times."""
        from pitlane_agent.utils.fastf1_helpers import format_lap_time

        assert format_lap_time(_td(70.270)) == "1:10.270"
        assert format_lap_time(_td(83.456)) == "1:23.456"
        assert format_lap_time(None) is None
        assert format_lap_time(pd.NaT) is None

    @patch("pitlane_agent.commands.analyze.qualifying_results.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.qualifying_results.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.qualifying_results.plt")
    @patch("pitlane_agent.commands.analyze.qualifying_results.load_session_or_testing")
    def test_chart_path_contains_session_type(self, mock_load, mock_plt, mock_contrast, mock_color, tmp_output_dir):
        """Chart filename includes year, sanitized GP name, and session type."""
        mock_load.return_value = _make_qualifying_session(20)
        _setup_plt_mock(mock_plt, mock_color, mock_contrast)

        result = generate_qualifying_results_chart(
            year=2024,
            gp="Monaco",
            session_type="Q",
            workspace_dir=tmp_output_dir,
        )

        chart_path = result["chart_path"]
        assert "qualifying_results" in chart_path
        assert "2024" in chart_path
        assert "monaco" in chart_path.lower()
        assert chart_path.endswith(".png")
