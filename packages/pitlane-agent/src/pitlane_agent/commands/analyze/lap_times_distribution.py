"""Generate lap times distribution visualization from FastF1 data.

Usage:
    pitlane analyze lap-times-distribution --year 2024 --gp Monaco --session R
"""

from pathlib import Path

import fastf1.plotting
import matplotlib.pyplot as plt
import seaborn as sns

from pitlane_agent.utils.fastf1_helpers import build_chart_path, load_session_or_testing
from pitlane_agent.utils.plotting import save_figure, setup_plot_style


def generate_lap_times_distribution_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str] | None,
    workspace_dir: Path,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Generate a lap times distribution plot using violin and swarm plots.

    Args:
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (ignored for testing sessions)
        drivers: List of driver abbreviations to include, or None for top 10 finishers
        workspace_dir: Workspace directory for outputs and cache
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with chart metadata and statistics
    """
    # Build output path (handle None drivers case specially)
    if drivers is None:
        output_path = build_chart_path(
            workspace_dir,
            "lap_times_distribution",
            year,
            gp,
            session_type,
            None,
            test_number=test_number,
            session_number=session_number,
        )
        # Adjust filename for top10 indicator
        output_path = output_path.parent / output_path.name.replace(".png", "_top10.png")
    else:
        output_path = build_chart_path(
            workspace_dir,
            "lap_times_distribution",
            year,
            gp,
            session_type,
            drivers,
            test_number=test_number,
            session_number=session_number,
        )

    # Load session with laps data
    session = load_session_or_testing(year, gp, session_type, test_number=test_number, session_number=session_number)

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
    # Track drivers with no quick laps for warning
    finishing_order = []
    excluded_drivers = []
    for driver_abbr in selected_drivers:
        if driver_abbr in driver_laps["Driver"].values:
            finishing_order.append(driver_abbr)
        else:
            excluded_drivers.append(driver_abbr)

    # Setup plotting
    setup_plot_style()
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True)

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
                "std_dev": float(lap_times_sec.std()),
                "lap_count": len(driver_data),
                "compounds_used": compounds_used,
            }
        )

    # Save figure
    save_figure(fig, output_path)

    result = {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_plotted": finishing_order,
        "statistics": stats,
    }

    # Add warning if any drivers were excluded due to no quick laps
    if excluded_drivers:
        result["excluded_drivers"] = excluded_drivers
        result["warning"] = f"Drivers excluded (no quick laps): {', '.join(excluded_drivers)}"

    return result
