"""Generate position changes visualization from FastF1 data.

Usage:
    pitlane analyze position-changes --workspace-id <id> --year 2024 --gp Monaco --session R
"""

from pathlib import Path

import fastf1.plotting
import matplotlib.pyplot as plt
from fastf1.core import Session

from pitlane_agent.utils.constants import (
    ALPHA_VALUE,
    DEFAULT_DPI,
    FIGURE_HEIGHT,
    FIGURE_WIDTH,
    GRID_ALPHA,
    LINE_WIDTH,
    MARKER_SIZE,
    PIT_MARKER_SIZE,
)
from pitlane_agent.utils.fastf1_helpers import load_session, load_testing_session
from pitlane_agent.utils.filename import sanitize_filename
from pitlane_agent.utils.plotting import get_driver_color_safe, save_figure, setup_plot_style
from pitlane_agent.utils.race_stats import compute_driver_position_stats


def _extract_driver_position_data(
    driver_abbr: str,
    session: Session,
    ax: plt.Axes,
) -> dict | None:
    """Extract and plot position data for a single driver.

    Args:
        driver_abbr: Driver abbreviation (e.g., 'VER', 'HAM')
        session: FastF1 session object
        ax: Matplotlib axes to plot on

    Returns:
        Dictionary with driver statistics, or None if driver should be excluded
    """
    # Compute stats using shared utility
    stats = compute_driver_position_stats(driver_abbr, session)
    if stats is None:
        return None

    driver_laps = session.laps.pick_drivers(driver_abbr)
    position_data = driver_laps[["LapNumber", "Position"]].copy()
    position_data = position_data.dropna(subset=["Position"])

    # Get driver color from FastF1
    color = get_driver_color_safe(driver_abbr, session)

    # Plot position evolution
    ax.plot(
        position_data["LapNumber"],
        position_data["Position"],
        label=driver_abbr,
        color=color,
        linewidth=LINE_WIDTH,
        marker="o",
        markersize=MARKER_SIZE,
        alpha=ALPHA_VALUE,
    )

    # Mark pit stops with vertical markers
    pit_laps = driver_laps[driver_laps["PitOutTime"].notna()]["LapNumber"].values
    for pit_lap in pit_laps:
        pit_position = position_data[position_data["LapNumber"] == pit_lap]["Position"].values
        if len(pit_position) > 0:
            ax.scatter(
                pit_lap,
                pit_position[0],
                color=color,
                marker="v",
                s=PIT_MARKER_SIZE,
                edgecolor="white",
                linewidth=1,
                zorder=5,
            )

    return stats


def _configure_position_plot(ax: plt.Axes, session: Session, year: int) -> None:
    """Configure plot axes, labels, and styling.

    Args:
        ax: Matplotlib axes to configure
        session: FastF1 session object
        year: Season year
    """
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Position")
    ax.set_title(f"{session.event['EventName']} {year} - Position Changes")

    # Invert y-axis so P1 is at the top
    ax.invert_yaxis()

    # Set y-axis to show all positions as integers
    max_position = int(ax.get_ylim()[0])  # After inversion, top limit is maximum
    ax.set_yticks(range(1, max_position + 1))

    # Add legend outside plot area
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        framealpha=ALPHA_VALUE,
        title="Driver (▼ = Pit Stop)",
    )

    ax.grid(True, alpha=GRID_ALPHA, axis="both")


def _calculate_aggregate_statistics(stats: list[dict]) -> dict:
    """Calculate aggregate statistics from per-driver stats.

    Args:
        stats: List of per-driver statistics dictionaries

    Returns:
        Dictionary with aggregate statistics
    """
    total_overtakes = sum(s["overtakes"] for s in stats)
    total_position_changes = sum(abs(s["net_change"]) for s in stats)
    avg_volatility = sum(s["volatility"] for s in stats) / len(stats) if stats else 0
    mean_pit_stops = sum(s["pit_stops"] for s in stats) / len(stats) if stats else 0

    return {
        "total_overtakes": total_overtakes,
        "total_position_changes": total_position_changes,
        "average_volatility": round(avg_volatility, 2),
        "mean_pit_stops": round(mean_pit_stops, 2),
        "drivers": stats,
    }


def generate_position_changes_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str] | None = None,
    top_n: int | None = None,
    workspace_dir: Path | None = None,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Generate a position changes visualization.

    Args:
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (typically 'R' for race, ignored for testing)
        drivers: Optional list of driver abbreviations to filter
        top_n: Optional number of top finishing drivers to show
        workspace_dir: Workspace directory for outputs and cache
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with chart metadata and position change statistics
    """
    # Determine paths from workspace
    if test_number is not None and session_number is not None:
        session_id = f"test{test_number}_day{session_number}"
    else:
        session_id = f"{sanitize_filename(gp)}_{session_type}"

    # Handle filename based on driver selection
    if drivers is not None:
        drivers_str = f"{len(drivers)}drivers" if len(drivers) > 5 else "_".join(sorted(drivers))
    elif top_n is not None:
        drivers_str = f"top{top_n}"
    else:
        drivers_str = "all"

    filename = f"position_changes_{year}_{session_id}_{drivers_str}.png"
    output_path = workspace_dir / "charts" / filename

    # Load session with laps data
    if test_number is not None and session_number is not None:
        session = load_testing_session(year, test_number, session_number)
    else:
        session = load_session(year, gp, session_type)

    # Determine which drivers to plot
    if drivers is not None:
        selected_drivers = drivers
    elif top_n is not None:
        # Use top N finishers
        top_finishers = session.drivers[:top_n]
        selected_drivers = [session.get_driver(i)["Abbreviation"] for i in top_finishers]
    else:
        # Use all drivers
        selected_drivers = [session.get_driver(i)["Abbreviation"] for i in session.drivers]

    # Setup plotting
    setup_plot_style()
    fastf1.plotting.setup_mpl()

    # Create figure
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # Track statistics for each driver
    stats = []
    excluded_drivers = []

    # Extract position data for each driver
    for driver_abbr in selected_drivers:
        driver_stats = _extract_driver_position_data(driver_abbr, session, ax)
        if driver_stats is None:
            excluded_drivers.append(driver_abbr)
        else:
            stats.append(driver_stats)

    # Configure plot styling
    _configure_position_plot(ax, session, year)

    # Save figure with bbox_inches="tight" for this specific chart
    save_figure(fig, output_path, dpi=DEFAULT_DPI, bbox_inches="tight")

    # Calculate aggregate statistics
    aggregate_stats = _calculate_aggregate_statistics(stats)

    result = {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_plotted": [s["driver"] for s in stats],
        "statistics": aggregate_stats,
    }

    # Add warning if any drivers were excluded
    if excluded_drivers:
        result["excluded_drivers"] = excluded_drivers
        result["warning"] = f"Drivers excluded (no position data): {', '.join(excluded_drivers)}"

    return result
