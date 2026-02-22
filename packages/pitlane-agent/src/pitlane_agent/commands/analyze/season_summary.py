"""Generate season summary visualization from FastF1 Ergast data.

Usage:
    pitlane analyze season-summary --workspace-id <id> --year 2024
    pitlane analyze season-summary --workspace-id <id> --year 2024 --type constructors
"""

from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt

from pitlane_agent.commands.fetch.constructor_standings import get_constructor_standings
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.fetch.event_schedule import get_event_schedule
from pitlane_agent.utils.constants import (
    ALPHA_VALUE,
    DEFAULT_DPI,
    FIGURE_HEIGHT,
    FIGURE_WIDTH,
    GRID_ALPHA,
)
from pitlane_agent.utils.ergast import get_ergast_client
from pitlane_agent.utils.plotting import save_figure, setup_plot_style

_POINTS_COLOR = "#3a86ff"
_WINS_COLOR = "#ff006e"
_PODIUMS_COLOR = "#fb5607"
_POLES_COLOR = "#8338ec"


def _count_per_driver(content: list, *, position: int | None = None, fastest_rank: bool = False) -> dict[str, int]:
    """Count occurrences per driverId from Ergast content list."""
    counts: dict[str, int] = {}
    for df in content:
        if fastest_rank:
            filtered = df[df["fastestLapRank"] == 1]
        elif position is not None:
            filtered = df[df["position"] == position]
        else:
            filtered = df
        for _, row in filtered.iterrows():
            driver_id = str(row["driverId"])
            counts[driver_id] = counts.get(driver_id, 0) + 1
    return counts


def _count_per_constructor(content: list, *, position: int | None = None, fastest_rank: bool = False) -> dict[str, int]:
    """Count occurrences per constructorId from Ergast content list."""
    counts: dict[str, int] = {}
    for df in content:
        if fastest_rank:
            filtered = df[df["fastestLapRank"] == 1]
        elif position is not None:
            filtered = df[df["position"] == position]
        else:
            filtered = df
        for _, row in filtered.iterrows():
            ctor_id = str(row["constructorId"])
            counts[ctor_id] = counts.get(ctor_id, 0) + 1
    return counts


def _fetch_season_race_stats(
    year: int,
    completed_round: int,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Fetch season race stats for all drivers and constructors.

    Makes efficient Ergast API calls using position filters, plus per-round
    calls (cached) for DNF and avg finish position data.

    Args:
        year: Championship year
        completed_round: Last completed race round number

    Returns:
        Tuple of (driver_stats, constructor_stats), each mapping id -> stat counts
    """
    ergast_api = get_ergast_client()

    # P2 finishers (1 API call)
    p2_results = ergast_api.get_race_results(season=year, results_position=2, limit=100)
    p2_by_driver = _count_per_driver(p2_results.content, position=2)
    p2_by_ctor = _count_per_constructor(p2_results.content, position=2)

    # P3 finishers (1 API call)
    p3_results = ergast_api.get_race_results(season=year, results_position=3, limit=100)
    p3_by_driver = _count_per_driver(p3_results.content, position=3)
    p3_by_ctor = _count_per_constructor(p3_results.content, position=3)

    # Fastest laps (1 API call)
    fl_results = ergast_api.get_race_results(season=year, fastest_rank=1, limit=100)
    fl_by_driver = _count_per_driver(fl_results.content, fastest_rank=True)
    fl_by_ctor = _count_per_constructor(fl_results.content, fastest_rank=True)

    # Qualifying poles (1 API call - filter position==1 per round for accuracy)
    quali_results = ergast_api.get_qualifying_results(season=year, results_position=1, limit=100)
    poles_by_driver: dict[str, int] = {}
    poles_by_ctor: dict[str, int] = {}
    for df in quali_results.content:
        pole_rows = df[df["position"] == 1]
        for _, row in pole_rows.iterrows():
            driver_id = str(row["driverId"])
            ctor_id = str(row["constructorId"])
            poles_by_driver[driver_id] = poles_by_driver.get(driver_id, 0) + 1
            poles_by_ctor[ctor_id] = poles_by_ctor.get(ctor_id, 0) + 1

    # Per-round results for DNFs and finish positions (cached by FastF1)
    dnfs_by_driver: dict[str, int] = {}
    finish_positions_by_driver: dict[str, list[int]] = {}
    dnfs_by_ctor: dict[str, int] = {}
    finish_positions_by_ctor: dict[str, list[int]] = {}

    for round_num in range(1, completed_round + 1):
        round_results = ergast_api.get_race_results(season=year, round=round_num)
        if not round_results.content:
            continue
        df = round_results.content[0]
        for _, row in df.iterrows():
            driver_id = str(row["driverId"])
            ctor_id = str(row["constructorId"])
            position_text = str(row.get("positionText", ""))
            # DNF: positionText is not a numeric classified finish
            is_dnf = not position_text.isdigit()

            if driver_id not in dnfs_by_driver:
                dnfs_by_driver[driver_id] = 0
                finish_positions_by_driver[driver_id] = []
            if is_dnf:
                dnfs_by_driver[driver_id] += 1
            else:
                finish_positions_by_driver[driver_id].append(int(position_text))

            if ctor_id not in dnfs_by_ctor:
                dnfs_by_ctor[ctor_id] = 0
                finish_positions_by_ctor[ctor_id] = []
            if is_dnf:
                dnfs_by_ctor[ctor_id] += 1
            elif position_text.isdigit():
                finish_positions_by_ctor[ctor_id].append(int(position_text))

    driver_stats = {
        "p2": p2_by_driver,
        "p3": p3_by_driver,
        "fl": fl_by_driver,
        "poles": poles_by_driver,
        "dnfs": dnfs_by_driver,
        "finish_positions": finish_positions_by_driver,
    }
    constructor_stats = {
        "p2": p2_by_ctor,
        "p3": p3_by_ctor,
        "fl": fl_by_ctor,
        "poles": poles_by_ctor,
        "dnfs": dnfs_by_ctor,
        "finish_positions": finish_positions_by_ctor,
    }
    return driver_stats, constructor_stats


def _add_value_labels(ax: plt.Axes, bars: list, color: str = "white") -> None:
    """Add value labels to the end of each horizontal bar."""
    for bar in bars:
        width = bar.get_width()
        if width > 0:
            ax.text(
                width + 0.05,
                bar.get_y() + bar.get_height() / 2,
                str(int(width)),
                va="center",
                ha="left",
                fontsize=8,
                color=color,
                weight="bold",
            )


def _plot_horizontal_bar(
    ax: plt.Axes,
    names: list[str],
    values: list[int | float],
    title: str,
    xlabel: str,
    color: str,
) -> None:
    """Plot a horizontal bar chart on the given axes."""
    y_pos = list(range(len(names)))
    bars = ax.barh(y_pos, values, height=0.65, color=color, alpha=ALPHA_VALUE)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(title, fontsize=11, pad=8)
    ax.grid(True, alpha=GRID_ALPHA, axis="x")
    _add_value_labels(ax, bars)


def _generate_season_summary_chart_panels(
    competitor_stats: list[dict],
    year: int,
    summary_type: str,
    fig: plt.Figure,
    gs: gridspec.GridSpec,
) -> None:
    """Render the four chart panels onto the figure."""
    # Sort bottom-up for horizontal bar charts (P1 at top = highest y index)
    sorted_stats = sorted(competitor_stats, key=lambda x: x["championship_position"], reverse=True)

    names = [c["name"] for c in sorted_stats]
    points = [c["points"] for c in sorted_stats]
    wins = [c["wins"] for c in sorted_stats]
    podiums = [c["podiums"] for c in sorted_stats]
    poles = [c["poles"] for c in sorted_stats]

    type_label = "Drivers'" if summary_type == "drivers" else "Constructors'"
    main_title = f"{year} {type_label} Championship Season Summary"

    # Top panel: Points
    ax_points = fig.add_subplot(gs[0, :])
    _plot_horizontal_bar(ax_points, names, points, main_title, "Championship Points", _POINTS_COLOR)

    # Bottom row: Wins | Podiums | Poles
    ax_wins = fig.add_subplot(gs[1, 0])
    _plot_horizontal_bar(ax_wins, names, wins, "Race Wins", "Wins", _WINS_COLOR)

    ax_podiums = fig.add_subplot(gs[1, 1])
    _plot_horizontal_bar(ax_podiums, names, podiums, "Podium Finishes (P1–P3)", "Podiums", _PODIUMS_COLOR)

    ax_poles = fig.add_subplot(gs[1, 2])
    _plot_horizontal_bar(ax_poles, names, poles, "Pole Positions", "Poles", _POLES_COLOR)


def generate_season_summary_chart(
    year: int,
    summary_type: str = "drivers",
    workspace_dir: Path | None = None,
) -> dict:
    """Generate season summary visualization with championship statistics.

    Args:
        year: Championship year (e.g., 2024)
        summary_type: "drivers" or "constructors"
        workspace_dir: Workspace directory for output files

    Returns:
        Dictionary with chart metadata and season statistics

    Raises:
        ValueError: If summary_type is invalid or no data is available
    """
    summary_type = summary_type.lower()
    if summary_type not in ("drivers", "constructors"):
        raise ValueError(f"Invalid summary_type: {summary_type!r}. Must be 'drivers' or 'constructors'.")

    # Fetch championship standings (includes points, wins, championship position)
    if summary_type == "drivers":
        standings_data = get_driver_standings(year)
        standings = standings_data["standings"]
        id_field = "driver_id"
        name_field = "full_name"
    else:
        standings_data = get_constructor_standings(year)
        standings = standings_data["standings"]
        id_field = "constructor_id"
        name_field = "constructor_name"

    if not standings:
        raise ValueError(f"No standings data available for {year} {summary_type} championship.")

    completed_round = standings_data["round"]

    # Determine total race events in the season
    schedule_data = get_event_schedule(year, include_testing=False)
    total_race_events = sum(
        1 for event in schedule_data["events"] if any(s["name"] == "Race" for s in event.get("sessions", []))
    )
    season_complete = completed_round >= total_race_events

    # Fetch additional race stats from Ergast
    driver_stats, constructor_stats = _fetch_season_race_stats(year, completed_round)
    race_stats = driver_stats if summary_type == "drivers" else constructor_stats

    # Build per-competitor statistics
    competitor_stats = []
    for competitor in sorted(standings, key=lambda x: x["position"]):
        comp_id = competitor[id_field]
        p2 = race_stats["p2"].get(comp_id, 0)
        p3 = race_stats["p3"].get(comp_id, 0)
        wins = int(competitor["wins"])
        podiums = wins + p2 + p3
        poles = race_stats["poles"].get(comp_id, 0)
        fastest_laps = race_stats["fl"].get(comp_id, 0)
        dnfs = race_stats["dnfs"].get(comp_id, 0)

        finish_positions = race_stats["finish_positions"].get(comp_id, [])
        avg_finish = round(sum(finish_positions) / len(finish_positions), 2) if finish_positions else None

        competitor_stats.append(
            {
                "name": competitor[name_field],
                id_field: comp_id,
                "championship_position": int(competitor["position"]),
                "points": float(competitor["points"]),
                "wins": wins,
                "podiums": podiums,
                "poles": poles,
                "fastest_laps": fastest_laps,
                "dnfs": dnfs,
                "avg_finish_position": avg_finish,
            }
        )

    # Setup and generate chart
    setup_plot_style()

    n_competitors = len(competitor_stats)
    # Scale figure height based on number of competitors for readability
    fig_height = max(FIGURE_HEIGHT, n_competitors * 0.45 + 4)
    fig = plt.figure(figsize=(FIGURE_WIDTH, fig_height))
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.5)

    _generate_season_summary_chart_panels(competitor_stats, year, summary_type, fig, gs)

    # Round indicator in figure suptitle for partial seasons
    round_label = f"After Round {completed_round}" if not season_complete else f"Final — {completed_round} Races"
    fig.suptitle(round_label, fontsize=10, y=0.98, alpha=0.7)

    # Save
    filename = f"season_summary_{year}_{summary_type}.png"
    output_path = workspace_dir / "charts" / filename
    save_figure(fig, output_path, dpi=DEFAULT_DPI)

    leader = competitor_stats[0] if competitor_stats else {}

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "year": year,
        "summary_type": summary_type,
        "analysis_round": completed_round,
        "total_races": total_race_events,
        "season_complete": season_complete,
        "leader": {
            "name": leader.get("name"),
            "points": leader.get("points"),
            "position": leader.get("championship_position"),
        },
        "statistics": {
            "total_competitors": len(competitor_stats),
            "competitors": competitor_stats,
        },
    }
