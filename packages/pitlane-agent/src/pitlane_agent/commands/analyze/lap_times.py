"""Generate lap times visualization from FastF1 data.

Usage:
    pitlane lap-times --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM --drivers LEC
"""

from pathlib import Path

import fastf1.plotting
import matplotlib.pyplot as plt

from pitlane_agent.utils.fastf1_helpers import build_chart_path, load_session
from pitlane_agent.utils.plotting import get_driver_color_safe, save_figure, setup_plot_style


def generate_lap_times_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str],
    workspace_dir: Path,
) -> dict:
    """Generate a lap times scatter plot.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier
        drivers: List of driver abbreviations to include
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and statistics
    """
    # Build output path
    output_path = build_chart_path(workspace_dir, "lap_times", year, gp, session_type, drivers)

    # Load session with laps data
    session = load_session(year, gp, session_type)

    # Setup plotting
    setup_plot_style()
    fastf1.plotting.setup_mpl()

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Track statistics for each driver
    stats = []

    # Plot each driver's lap times
    for driver_abbr in drivers:
        driver_laps = session.laps.pick_drivers(driver_abbr).pick_quicklaps()

        if driver_laps.empty:
            continue

        # Get driver color from FastF1
        color = get_driver_color_safe(driver_abbr, session)

        # Convert lap times to seconds for plotting
        lap_times_sec = driver_laps["LapTime"].dt.total_seconds()

        # Plot scatter
        ax.scatter(
            driver_laps["LapNumber"],
            lap_times_sec,
            label=driver_abbr,
            color=color,
            s=50,
            alpha=0.8,
        )

        # Calculate statistics
        stats.append(
            {
                "driver": driver_abbr,
                "best_time": float(lap_times_sec.min()),
                "best_time_formatted": str(driver_laps["LapTime"].min())[10:18],
                "median_time": float(lap_times_sec.median()),
                "lap_count": len(driver_laps),
            }
        )

    # Customize plot
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (seconds)")
    ax.set_title(f"{session.event['EventName']} {year} - {session.name}\nLap Times Comparison")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    # Add some padding to y-axis
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    ax.set_ylim(y_min - y_range * 0.05, y_max + y_range * 0.05)

    # Save figure
    save_figure(fig, output_path)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_plotted": [s["driver"] for s in stats],
        "statistics": stats,
    }
