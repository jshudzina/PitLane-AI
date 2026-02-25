"""Tests for team_pace command."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.analyze.team_pace import generate_team_pace_chart


def _make_mock_laps(driver_times: dict[str, list[float]]) -> pd.DataFrame:
    """Build a laps DataFrame with LapTime as Timedelta for given drivers."""
    rows = []
    for driver, times in driver_times.items():
        for i, t in enumerate(times):
            rows.append({"Driver": driver, "LapNumber": i + 1, "LapTime": pd.Timedelta(seconds=t)})
    return pd.DataFrame(rows)


def _make_boxplot_return(n_teams: int) -> dict:
    """Build a mock boxplot return value with n_teams box patches."""
    return {
        "boxes": [MagicMock() for _ in range(n_teams)],
        "medians": [],
        "whiskers": [],
        "caps": [],
        "fliers": [],
    }


@pytest.fixture()
def two_team_session(mock_fastf1_session):
    """Narrow mock_fastf1_session to 2 deterministic teams."""
    mock_fastf1_session.results = pd.DataFrame(
        {
            "Abbreviation": ["VER", "PER", "LEC", "SAI"],
            "TeamName": ["Red Bull Racing", "Red Bull Racing", "Ferrari", "Ferrari"],
        }
    )
    return mock_fastf1_session


class TestTeamPaceChart:
    """Unit tests for generate_team_pace_chart."""

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_generate_all_teams_success(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test successful chart generation with all 4 teams from fixture."""
        mock_load_session.return_value = mock_fastf1_session

        mock_laps = _make_mock_laps(
            {
                "VER": [85.1, 85.2, 85.3],
                "PER": [85.4, 85.5, 85.6],
                "HAM": [85.7, 85.8, 85.9],
                "RUS": [86.0, 86.1, 86.2],
                "LEC": [85.9, 86.0, 86.1],
                "SAI": [86.2, 86.3, 86.4],
                "NOR": [85.5, 85.6, 85.7],
                "PIA": [85.8, 85.9, 86.0],
            }
        )
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.boxplot.return_value = _make_boxplot_return(4)

        mock_get_color.return_value = "#0600EF"
        mock_ensure_contrast.return_value = "#0600EF"

        result = generate_team_pace_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            teams=None,
            workspace_dir=tmp_output_dir,
        )

        assert result["year"] == 2024
        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Qualifying"
        assert "chart_path" in result
        assert "statistics" in result
        assert "teams_plotted" in result
        assert result["chart_path"] == str(tmp_output_dir / "charts" / "team_pace_2024_monaco_R.png")
        assert result["workspace"] == str(tmp_output_dir)
        assert len(result["teams_plotted"]) == 4

        mock_load_session.assert_called_once_with(2024, "Monaco", "R", test_number=None, session_number=None)

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_generate_with_teams_filter(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test chart generation with specific teams filter."""
        mock_load_session.return_value = mock_fastf1_session

        mock_laps = _make_mock_laps(
            {
                "LEC": [85.9, 86.0, 86.1],
                "SAI": [86.2, 86.3, 86.4],
                "HAM": [85.7, 85.8, 85.9],
                "RUS": [86.0, 86.1, 86.2],
            }
        )
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.boxplot.return_value = _make_boxplot_return(2)

        mock_get_color.return_value = "#FF0000"
        mock_ensure_contrast.return_value = "#FF0000"

        result = generate_team_pace_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            teams=["Ferrari", "Mercedes"],
            workspace_dir=tmp_output_dir,
        )

        assert len(result["teams_plotted"]) == 2
        assert "Ferrari" in result["teams_plotted"]
        assert "Mercedes" in result["teams_plotted"]
        # Filtered filename should include team slugs
        assert "ferrari" in result["chart_path"]
        assert "mercedes" in result["chart_path"]

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_teams_sorted_fastest_first(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        two_team_session,
    ):
        """Test that teams_plotted is ordered fastest median first."""
        mock_load_session.return_value = two_team_session

        def side_effect(drivers):
            mock_result = MagicMock()
            if "VER" in drivers or "PER" in drivers:
                # Red Bull is faster
                mock_result.pick_quicklaps.return_value = _make_mock_laps({"VER": [85.0, 85.1]})
            else:
                # Ferrari is slower
                mock_result.pick_quicklaps.return_value = _make_mock_laps({"LEC": [87.0, 87.1]})
            return mock_result

        two_team_session.laps.pick_drivers.side_effect = side_effect

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.boxplot.return_value = _make_boxplot_return(2)
        mock_get_color.return_value = "#0600EF"
        mock_ensure_contrast.return_value = "#0600EF"

        result = generate_team_pace_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            teams=None,
            workspace_dir=tmp_output_dir,
        )

        assert result["teams_plotted"][0] == "Red Bull Racing"
        assert result["teams_plotted"][1] == "Ferrari"

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_statistics_structure(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        two_team_session,
    ):
        """Test statistics keys are present and pace_delta_s is 0 for fastest team."""
        mock_load_session.return_value = two_team_session

        def side_effect(drivers):
            mock_result = MagicMock()
            if "VER" in drivers or "PER" in drivers:
                mock_result.pick_quicklaps.return_value = _make_mock_laps({"VER": [85.1, 85.2, 85.3, 85.4]})
            else:
                mock_result.pick_quicklaps.return_value = _make_mock_laps({"LEC": [86.0, 86.1, 86.2, 86.3]})
            return mock_result

        two_team_session.laps.pick_drivers.side_effect = side_effect

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.boxplot.return_value = _make_boxplot_return(2)
        mock_get_color.return_value = "#0600EF"
        mock_ensure_contrast.return_value = "#0600EF"

        result = generate_team_pace_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            teams=None,
            workspace_dir=tmp_output_dir,
        )

        stats = result["statistics"]
        assert len(stats) == 2

        required_keys = {"team", "median_s", "mean_s", "std_dev_s", "pace_delta_s", "lap_count"}
        for stat in stats:
            assert required_keys.issubset(stat.keys())

        fastest = stats[0]
        assert fastest["team"] == "Red Bull Racing"
        assert fastest["pace_delta_s"] == 0.0

        slower = stats[1]
        assert slower["team"] == "Ferrari"
        assert slower["pace_delta_s"] > 0.0
        assert slower["lap_count"] == 4

    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_session_load_error(self, mock_load_session, tmp_output_dir):
        """Test exception propagation when session load fails."""
        mock_load_session.side_effect = Exception("Session not found")

        with pytest.raises(Exception, match="Session not found"):
            generate_team_pace_chart(
                year=2024,
                gp="InvalidGP",
                session_type="R",
                teams=None,
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_no_quick_laps_raises_value_error(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """Test ValueError raised when no teams have quick laps."""
        mock_load_session.return_value = mock_fastf1_session

        empty_df = pd.DataFrame(columns=["Driver", "LapNumber", "LapTime"])
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = empty_df

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_get_color.return_value = "#0600EF"
        mock_ensure_contrast.return_value = "#0600EF"

        with pytest.raises(ValueError, match="No quick laps found"):
            generate_team_pace_chart(
                year=2024,
                gp="Monaco",
                session_type="R",
                teams=None,
                workspace_dir=tmp_output_dir,
            )

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_unmatched_teams_reported(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        two_team_session,
    ):
        """Unrecognized team names in the filter appear in unmatched_teams; matched teams are plotted."""
        mock_load_session.return_value = two_team_session

        mock_laps = _make_mock_laps({"VER": [85.0, 85.1], "PER": [85.2, 85.3]})
        two_team_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.boxplot.return_value = _make_boxplot_return(1)
        mock_get_color.return_value = "#0600EF"
        mock_ensure_contrast.return_value = "#0600EF"

        result = generate_team_pace_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            teams=["Red Bull Racing", "Haas F1 Team"],  # Haas not in two_team_session
            workspace_dir=tmp_output_dir,
        )

        assert result["teams_plotted"] == ["Red Bull Racing"]
        assert result["unmatched_teams"] == ["Haas F1 Team"]

    @patch("pitlane_agent.commands.analyze.team_pace.get_driver_color_safe")
    @patch("pitlane_agent.commands.analyze.team_pace.ensure_color_contrast")
    @patch("pitlane_agent.commands.analyze.team_pace.plt")
    @patch("pitlane_agent.commands.analyze.team_pace.load_session_or_testing")
    def test_many_teams_filter_uses_hash_filename(
        self,
        mock_load_session,
        mock_plt,
        mock_ensure_contrast,
        mock_get_color,
        tmp_output_dir,
        mock_fastf1_session,
    ):
        """When more than 5 teams are requested, the filename uses a hash instead of a slug."""
        mock_load_session.return_value = mock_fastf1_session

        mock_laps = _make_mock_laps({"VER": [85.0, 85.1]})
        mock_fastf1_session.laps.pick_drivers.return_value.pick_quicklaps.return_value = mock_laps

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_ax.boxplot.return_value = _make_boxplot_return(4)
        mock_get_color.return_value = "#0600EF"
        mock_ensure_contrast.return_value = "#0600EF"

        six_teams = ["Ferrari", "Mercedes", "Red Bull Racing", "McLaren", "Aston Martin", "Williams"]
        result = generate_team_pace_chart(
            year=2024,
            gp="Monaco",
            session_type="R",
            teams=six_teams,
            workspace_dir=tmp_output_dir,
        )

        assert "filtered_" in result["chart_path"]
        # No individual team name should appear as a slug in the path
        for team in six_teams:
            assert team.lower().replace(" ", "_") not in result["chart_path"]
