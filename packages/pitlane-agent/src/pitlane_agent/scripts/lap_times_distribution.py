"""Generate lap times distribution visualization from FastF1 data.

Usage:
    pitlane analyze lap-times-distribution --year 2024 --gp Monaco --session R

    # Or using module invocation
    python -m pitlane_agent.scripts.lap_times_distribution \
        --year 2024 --gp Monaco --session R \
        --output /tmp/charts/lap_times_distribution.png
"""

from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import seaborn as sns

from pitlane_agent.scripts.lap_times import setup_plot_style
from pitlane_agent.utils import sanitize_filename


def generate_lap_times_distribution_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str] | None,
    workspace_dir: Path,
) -> dict:
    """Generate a lap times distribution plot using violin and swarm plots.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier
        drivers: List of driver abbreviations to include, or None for top 10 finishers
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and statistics
    """
    # Determine paths from workspace
    gp_sanitized = sanitize_filename(gp)

    # Handle filename based on driver selection
    if drivers is None:
        drivers_str = "top10"
    elif len(drivers) > 5:
        drivers_str = f"{len(drivers)}drivers"
    else:
        drivers_str = "_".join(sorted(drivers))

    filename = f"lap_times_distribution_{year}_{gp_sanitized}_{session_type}_{drivers_str}.png"
    output_path = workspace_dir / "charts" / filename
    cache_dir = Path.home() / ".pitlane" / "cache" / "fastf1"

    # Enable FastF1 cache with shared directory
    fastf1.Cache.enable_cache(str(cache_dir))

    # Load session with laps data
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    # Determine which drivers to plot
    if drivers is None:
        # Use top 10 finishers
        point_finishers = session.drivers[:10]
        selected_drivers = [session.get_driver(i)["Abbreviation"] for i in point_finishers]
    else:
        selected_drivers = drivers

    # Get all laps for selected drivers, filter quick laps only
    driver_laps = session.laps.pick_drivers(selected_drivers).pick_quicklaps()

    if driver_laps.empty:
        raise ValueError("No quick laps found for selected drivers")

    driver_laps = driver_laps.reset_index()

    # Get finishing order for proper ordering in plot
    finishing_order = []
    for driver_abbr in selected_drivers:
        if driver_abbr in driver_laps["Driver"].values:
            finishing_order.append(driver_abbr)

    # Setup plotting
    setup_plot_style()
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Convert lap times to seconds for seaborn
    driver_laps["LapTime(s)"] = driver_laps["LapTime"].dt.total_seconds()

    # Violin plot for distribution density
    sns.violinplot(
        data=driver_laps,
        x="Driver",
        y="LapTime(s)",
        hue="Driver",
        inner=None,
        density_norm="area",
        order=finishing_order,
        palette=fastf1.plotting.get_driver_color_mapping(session=session),
        ax=ax,
        legend=False,
    )

    # Swarm plot overlay for individual laps colored by compound
    sns.swarmplot(
        data=driver_laps,
        x="Driver",
        y="LapTime(s)",
        order=finishing_order,
        hue="Compound",
        palette=fastf1.plotting.get_compound_mapping(session=session),
        hue_order=["SOFT", "MEDIUM", "HARD"],
        linewidth=0,
        size=4,
        ax=ax,
    )

    # Customize plot
    ax.set_xlabel("Driver")
    ax.set_ylabel("Lap Time (seconds)")
    ax.set_title(f"{session.event['EventName']} {year} - {session.name}\nLap Time Distributions")

    # Move legend outside plot area
    ax.legend(title="Compound", loc="upper right", bbox_to_anchor=(1.0, 1.0))

    # Remove spines for cleaner look
    sns.despine(left=True, bottom=True, ax=ax)

    # Calculate statistics for each driver
    stats = []
    for driver_abbr in finishing_order:
        driver_data = driver_laps[driver_laps["Driver"] == driver_abbr]

        if driver_data.empty:
            continue

        lap_times_sec = driver_data["LapTime(s)"]
        compounds_used = driver_data["Compound"].dropna().unique().tolist()

        stats.append(
            {
                "driver": driver_abbr,
                "best_time": float(lap_times_sec.min()),
                "best_time_formatted": str(driver_data["LapTime"].min())[10:18],
                "median_time": float(lap_times_sec.median()),
                "lap_count": len(driver_data),
                "compounds_used": compounds_used,
            }
        )

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save figure
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_plotted": finishing_order,
        "statistics": stats,
    }
