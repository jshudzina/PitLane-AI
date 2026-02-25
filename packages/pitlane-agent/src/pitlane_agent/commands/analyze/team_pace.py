"""Generate team pace comparison visualization from FastF1 data.

Usage:
    pitlane analyze team-pace --year 2024 --gp Monaco --session R
"""

import hashlib
from pathlib import Path

import matplotlib.pyplot as plt

from pitlane_agent.utils.constants import FIGURE_HEIGHT, FIGURE_WIDTH
from pitlane_agent.utils.fastf1_helpers import build_chart_path, load_session_or_testing
from pitlane_agent.utils.filename import sanitize_filename
from pitlane_agent.utils.plotting import ensure_color_contrast, get_driver_color_safe, save_figure, setup_plot_style


def generate_team_pace_chart(
    year: int,
    gp: str | None,
    session_type: str | None,
    teams: list[str] | None,
    workspace_dir: Path,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Generate a team pace comparison box plot.

    Args:
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (ignored for testing sessions)
        teams: List of team names to include, or None for all teams
        workspace_dir: Workspace directory for outputs and cache
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with chart metadata and per-team statistics

    Raises:
        ValueError: If no quick laps found for any team
    """
    # Build output path — append sanitized team slug when a filter is applied
    base_path = build_chart_path(
        workspace_dir,
        "team_pace",
        year,
        gp,
        session_type,
        None,
        test_number=test_number,
        session_number=session_number,
    )
    if teams is not None:
        sorted_for_slug = sorted(teams)
        if len(sorted_for_slug) <= 5:
            teams_slug = "_".join(sanitize_filename(t) for t in sorted_for_slug)
        else:
            teams_hash = hashlib.md5(",".join(sorted_for_slug).encode()).hexdigest()[:8]
            teams_slug = f"filtered_{teams_hash}"
        output_path = base_path.parent / base_path.name.replace(".png", f"_{teams_slug}.png")
    else:
        output_path = base_path

    # Load session
    session = load_session_or_testing(year, gp, session_type, test_number=test_number, session_number=session_number)

    # Determine which teams to include (preserve session order)
    teams_in_session = (
        session.results[["Abbreviation", "TeamName"]].drop_duplicates(subset="TeamName")["TeamName"].tolist()
    )
    if teams is not None:
        teams_set = set(teams)
        selected_teams = [t for t in teams_in_session if t in teams_set]
        unmatched_teams = [t for t in teams if t not in set(teams_in_session)]
    else:
        selected_teams = teams_in_session
        unmatched_teams = []

    # Collect quick laps per team
    team_lap_data = {}
    team_colors = {}

    for team_name in selected_teams:
        team_drivers = session.results[session.results["TeamName"] == team_name]["Abbreviation"].tolist()
        if not team_drivers:
            continue

        team_laps = session.laps.pick_drivers(team_drivers).pick_quicklaps()
        if team_laps.empty:
            continue

        lap_times_sec = team_laps["LapTime"].dt.total_seconds()
        team_lap_data[team_name] = lap_times_sec

        raw_color = get_driver_color_safe(team_drivers[0], session, fallback="#888888")
        team_colors[team_name] = ensure_color_contrast(raw_color)

    if not team_lap_data:
        raise ValueError("No quick laps found for any team in the selected session")

    # Sort teams fastest median first
    sorted_teams = sorted(team_lap_data.keys(), key=lambda t: team_lap_data[t].median())

    # Create figure
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    box_data = [team_lap_data[t].values for t in sorted_teams]
    positions = list(range(len(sorted_teams)))

    bp = ax.boxplot(
        box_data,
        positions=positions,
        patch_artist=True,
        widths=0.5,
        showfliers=True,
        flierprops={"marker": "o", "markersize": 4, "linestyle": "none", "alpha": 0.5},
        medianprops={"color": "#ffffff", "linewidth": 2},
        whiskerprops={"linewidth": 1.2},
        capprops={"linewidth": 1.2},
        boxprops={"linewidth": 1.2},
    )

    for patch, team_name in zip(bp["boxes"], sorted_teams, strict=False):
        patch.set_facecolor(team_colors[team_name])
        patch.set_alpha(0.7)

    ax.set_xticks(positions)
    ax.set_xticklabels(sorted_teams, rotation=30, ha="right")
    ax.set_xlabel("Team (fastest left)")
    ax.set_ylabel("Lap Time (seconds)")
    ax.set_title(f"{session.event['EventName']} {year} - {session.name}\nTeam Pace Comparison (Quick Laps)")
    ax.grid(True, alpha=0.3, axis="y")

    # Calculate per-team statistics
    fastest_median = team_lap_data[sorted_teams[0]].median()
    statistics = []
    for team_name in sorted_teams:
        laps = team_lap_data[team_name]
        median_s = float(laps.median())
        statistics.append(
            {
                "team": team_name,
                "median_s": round(median_s, 3),
                "mean_s": round(float(laps.mean()), 3),
                "std_dev_s": round(float(laps.std()) if len(laps) > 1 else 0.0, 3),
                "pace_delta_s": round(median_s - float(fastest_median), 3),
                "lap_count": int(len(laps)),
            }
        )

    save_figure(fig, output_path)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "teams_plotted": sorted_teams,
        "unmatched_teams": unmatched_teams,
        "statistics": statistics,
    }
