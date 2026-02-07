"""Generate position changes visualization from FastF1 data.

Usage:
    pitlane analyze position-changes --session-id <id> --year 2024 --gp Monaco --session R
"""

from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import numpy as np

from pitlane_agent.utils import get_fastf1_cache_dir, sanitize_filename

# Visualization constants
FIGURE_WIDTH = 14
FIGURE_HEIGHT = 8
DEFAULT_DPI = 150
LINE_WIDTH = 2
MARKER_SIZE = 3
PIT_MARKER_SIZE = 100
ALPHA_VALUE = 0.8
GRID_ALPHA = 0.3


def setup_plot_style():
    """Configure matplotlib for F1-style dark theme."""
    plt.style.use("dark_background")
    plt.rcParams.update(
        {
            "figure.facecolor": "#1e1e1e",
            "axes.facecolor": "#2d2d2d",
            "axes.edgecolor": "#555555",
            "axes.labelcolor": "#ffffff",
            "text.color": "#ffffff",
            "xtick.color": "#ffffff",
            "ytick.color": "#ffffff",
            "grid.color": "#444444",
            "grid.alpha": GRID_ALPHA,
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
        }
    )


def _extract_driver_position_data(
    driver_abbr: str,
    session: fastf1.core.Session,
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
    driver_laps = session.laps.pick_driver(driver_abbr)

    if driver_laps.empty:
        return None

    # Get position for each lap (filter out NaN positions for DNS/DNF cases)
    position_data = driver_laps[["LapNumber", "Position"]].copy()
    position_data = position_data.dropna(subset=["Position"])

    if position_data.empty:
        return None

    # Get driver color from FastF1
    try:
        color = fastf1.plotting.get_driver_color(driver_abbr, session)
    except Exception:
        color = None

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
        # Find position at pit lap
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

    # Calculate statistics
    positions = position_data["Position"].values
    start_position = float(positions[0])
    finish_position = float(positions[-1])
    position_changes = np.diff(positions)

    # Count overtakes (position improvements) - negative change means better position
    overtakes = int(np.sum(position_changes < 0))
    times_overtaken = int(np.sum(position_changes > 0))

    # Calculate volatility (standard deviation of positions)
    volatility = float(np.std(positions))

    # Biggest gain and loss in a single lap
    biggest_gain = int(abs(np.min(position_changes))) if len(position_changes) > 0 else 0
    biggest_loss = int(abs(np.max(position_changes))) if len(position_changes) > 0 else 0

    return {
        "driver": driver_abbr,
        "start_position": int(start_position),
        "finish_position": int(finish_position),
        "net_change": int(start_position - finish_position),  # positive = gained positions
        "overtakes": overtakes,
        "times_overtaken": times_overtaken,
        "biggest_gain": biggest_gain,
        "biggest_loss": biggest_loss,
        "volatility": round(volatility, 2),
        "total_laps": len(position_data),
        "pit_stops": len(pit_laps),
    }


def _configure_position_plot(ax: plt.Axes, session: fastf1.core.Session, year: int) -> None:
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

    return {
        "total_overtakes": total_overtakes,
        "total_position_changes": total_position_changes,
        "average_volatility": round(avg_volatility, 2),
        "drivers": stats,
    }


def generate_position_changes_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str] | None = None,
    top_n: int | None = None,
    workspace_dir: Path | None = None,
) -> dict:
    """Generate a position changes visualization.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier (typically 'R' for race)
        drivers: Optional list of driver abbreviations to filter
        top_n: Optional number of top finishing drivers to show
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and position change statistics
    """
    # Determine paths from workspace
    gp_sanitized = sanitize_filename(gp)

    # Handle filename based on driver selection
    if drivers is not None:
        drivers_str = f"{len(drivers)}drivers" if len(drivers) > 5 else "_".join(sorted(drivers))
    elif top_n is not None:
        drivers_str = f"top{top_n}"
    else:
        drivers_str = "all"

    filename = f"position_changes_{year}_{gp_sanitized}_{session_type}_{drivers_str}.png"
    output_path = workspace_dir / "charts" / filename

    # Enable FastF1 cache with shared directory
    fastf1.Cache.enable_cache(str(get_fastf1_cache_dir()))

    # Load session with laps data
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

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
    fastf1.plotting.setup_mpl(misc_mpl_mods=False)

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

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save figure
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=DEFAULT_DPI, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    plt.close(fig)

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
