"""Generate championship possibilities visualization from FastF1 data.

Usage:
    pitlane analyze championship-possibilities --session-id <id> --year 2024
    pitlane analyze championship-possibilities --session-id <id> --year 2024 --championship constructors
    pitlane analyze championship-possibilities --session-id <id> --year 2024 --after-round 10
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

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
from pitlane_agent.utils.plotting import save_figure, setup_plot_style


def _count_remaining_races(year: int, current_round: int) -> tuple[int, int]:
    """Count remaining races and sprint races in the season.

    Args:
        year: Championship year
        current_round: Current round number

    Returns:
        Tuple of (remaining_races, remaining_sprints)
    """
    schedule_data = get_event_schedule(year, include_testing=False)
    events = schedule_data["events"]

    remaining_races = 0
    remaining_sprints = 0

    for event in events:
        round_num = event["round"]
        # Only count races after the current round
        if round_num > current_round:
            # Check if it's a race weekend (has Race session)
            has_race = any(session["name"] == "Race" for session in event.get("sessions", []))
            if has_race:
                remaining_races += 1

            # Check if it's a sprint weekend (has Sprint session)
            has_sprint = any(session["name"] == "Sprint" for session in event.get("sessions", []))
            if has_sprint:
                remaining_sprints += 1

    return remaining_races, remaining_sprints


def _calculate_max_points_available(remaining_races: int, remaining_sprints: int) -> int:
    """Calculate maximum points available for remaining races.

    Args:
        remaining_races: Number of remaining races
        remaining_sprints: Number of remaining sprint races

    Returns:
        Maximum points available
    """
    # Points per race: 25 (win) + 1 (fastest lap) = 26
    # Points per sprint: 8 (win)
    max_race_points = 26 * remaining_races
    max_sprint_points = 8 * remaining_sprints

    return max_race_points + max_sprint_points


def _calculate_championship_scenarios(
    standings: list[dict],
    max_points_available: int,
    championship_type: str,
) -> tuple[list[dict], dict]:
    """Calculate championship scenarios for each competitor.

    Args:
        standings: List of standings dictionaries
        max_points_available: Maximum points available in remaining races
        championship_type: "drivers" or "constructors"

    Returns:
        Tuple of (competitor_stats, leader_info)
    """
    if not standings:
        return [], {}

    # Sort by current points (should already be sorted, but ensure it)
    standings = sorted(standings, key=lambda x: x["points"], reverse=True)

    leader = standings[0]
    leader_points = leader["points"]

    # Get name field based on championship type
    name_field = "full_name" if championship_type == "drivers" else "constructor_name"

    leader_info = {
        "name": leader[name_field],
        "points": leader_points,
        "position": leader["position"],
    }

    competitor_stats = []

    for competitor in standings:
        current_points = competitor["points"]
        max_possible_points = current_points + max_points_available
        points_behind = leader_points - current_points

        # Can win if max possible points > leader's current points
        # (assuming leader scores 0 more points)
        can_win = max_possible_points > leader_points

        # Generate required scenario description
        if competitor["position"] == 1:
            required_scenario = "Leading the championship"
        elif can_win:
            points_needed = points_behind + 1
            required_scenario = f"Needs {points_needed}+ points more than leader"
        else:
            required_scenario = "Mathematically eliminated"

        competitor_stats.append(
            {
                "name": competitor[name_field],
                "position": competitor["position"],
                "current_points": current_points,
                "max_possible_points": max_possible_points,
                "points_behind": points_behind if competitor["position"] > 1 else 0,
                "can_win": can_win,
                "required_scenario": required_scenario,
            }
        )

    return competitor_stats, leader_info


def _generate_championship_chart(
    competitor_stats: list[dict],
    year: int,
    championship_type: str,
    ax: plt.Axes,
    after_round: int | None = None,
) -> None:
    """Generate horizontal bar chart for championship possibilities.

    Args:
        competitor_stats: List of competitor statistics
        year: Championship year
        championship_type: "drivers" or "constructors"
        ax: Matplotlib axes to plot on
        after_round: Optional round number for historical analysis
    """
    # Sort by current points for display
    competitor_stats = sorted(competitor_stats, key=lambda x: x["current_points"], reverse=False)

    names = [c["name"] for c in competitor_stats]
    current_points = [c["current_points"] for c in competitor_stats]
    max_points = [c["max_possible_points"] for c in competitor_stats]
    can_win = [c["can_win"] for c in competitor_stats]

    y_positions = np.arange(len(names))

    # Plot current points (filled bars)
    for i, (y_pos, current, maximum, viable) in enumerate(
        zip(y_positions, current_points, max_points, can_win, strict=True)
    ):
        # Color based on whether they can still win
        color = "#43B02A" if viable else "#888888"  # Green for viable, gray for eliminated

        # Current points (solid bar)
        ax.barh(y_pos, current, height=0.6, color=color, alpha=ALPHA_VALUE, label="Current points" if i == 0 else "")

        # Potential additional points (hatched bar)
        additional_points = maximum - current
        ax.barh(
            y_pos,
            additional_points,
            height=0.6,
            left=current,
            color=color,
            alpha=0.3,
            hatch="///",
            edgecolor=color,
            linewidth=0.5,
            label="Potential points" if i == 0 else "",
        )

    # Configure axes
    ax.set_yticks(y_positions)
    ax.set_yticklabels(names)
    ax.set_xlabel("Championship Points")
    championship_label = "Drivers" if championship_type == "drivers" else "Constructors"

    # Add "After Round X" to title if analyzing historical data
    round_suffix = f" (After Round {after_round})" if after_round is not None else ""
    ax.set_title(f"{year} {championship_label}' Championship - Who Can Still Win?{round_suffix}")

    # Add grid
    ax.grid(True, alpha=GRID_ALPHA, axis="x")

    # Add legend
    ax.legend(loc="lower right", framealpha=ALPHA_VALUE)

    # Add value labels on bars
    for y_pos, current in zip(y_positions, current_points, strict=True):
        # Current points label
        ax.text(
            current,
            y_pos,
            f" {int(current)}",
            va="center",
            ha="left",
            fontsize=9,
            color="white",
            weight="bold",
        )


def generate_championship_possibilities_chart(
    year: int,
    championship: str = "drivers",
    workspace_dir: Path | None = None,
    after_round: int | None = None,
) -> dict:
    """Generate championship possibilities visualization.

    Args:
        year: Season year
        championship: Championship type - "drivers" or "constructors"
        workspace_dir: Workspace directory for outputs
        after_round: Optional round number to analyze historical "what if" scenarios

    Returns:
        Dictionary with chart metadata and championship statistics
    """
    championship = championship.lower()
    if championship not in ["drivers", "constructors"]:
        raise ValueError(f"Invalid championship type: {championship}. Must be 'drivers' or 'constructors'.")

    # Get standings (current or historical)
    if championship == "drivers":
        standings_data = get_driver_standings(year, round_number=after_round)
        standings = standings_data["standings"]
    else:
        standings_data = get_constructor_standings(year, round_number=after_round)
        standings = standings_data["standings"]

    if not standings:
        raise ValueError(f"No standings data available for {year} {championship} championship")

    # Use the round from standings data (either specified after_round or current)
    analysis_round = standings_data["round"]

    # Count remaining races
    remaining_races, remaining_sprints = _count_remaining_races(year, analysis_round)

    # Calculate maximum points available
    max_points_available = _calculate_max_points_available(remaining_races, remaining_sprints)

    # Calculate championship scenarios
    competitor_stats, leader_info = _calculate_championship_scenarios(standings, max_points_available, championship)

    # Setup plotting
    setup_plot_style()

    # Create figure
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # Generate chart
    _generate_championship_chart(competitor_stats, year, championship, ax, after_round=analysis_round)

    # Save figure (include round in filename if analyzing historical data)
    round_suffix = f"_round_{analysis_round}" if after_round is not None else ""
    filename = f"championship_possibilities_{year}_{championship}{round_suffix}.png"
    output_path = workspace_dir / "charts" / filename
    save_figure(fig, output_path, dpi=DEFAULT_DPI)

    # Calculate aggregate statistics
    total_competitors = len(competitor_stats)
    still_possible = sum(1 for c in competitor_stats if c["can_win"])
    eliminated = total_competitors - still_possible

    # Build result
    result = {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "year": year,
        "championship_type": championship,
        "analysis_round": analysis_round,
        "remaining_races": remaining_races,
        "remaining_sprints": remaining_sprints,
        "max_points_available": max_points_available,
        "leader": leader_info,
        "statistics": {
            "total_competitors": total_competitors,
            "still_possible": still_possible,
            "eliminated": eliminated,
            "competitors": competitor_stats,
        },
    }

    return result
