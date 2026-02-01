"""Generate speed trace visualization from FastF1 telemetry data.

Usage:
    pitlane analyze speed-trace --session-id <id> --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
"""

from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd

from pitlane_agent.utils import get_fastf1_cache_dir, sanitize_filename


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
            "grid.alpha": 0.3,
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
        }
    )


def generate_speed_trace_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str],
    workspace_dir: Path,
) -> dict:
    """Generate a speed trace comparison for fastest laps.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier
        drivers: List of 2-5 driver abbreviations to compare
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and speed statistics

    Raises:
        ValueError: If drivers list has <2 or >5 entries
    """
    # Validation
    if len(drivers) < 2:
        raise ValueError(f"Speed trace requires at least 2 drivers for comparison, got {len(drivers)}")
    if len(drivers) > 5:
        raise ValueError(f"Speed trace supports maximum 5 drivers for readability, got {len(drivers)}")

    # Determine paths from workspace
    gp_sanitized = sanitize_filename(gp)
    drivers_str = "_".join(sorted(drivers))
    filename = f"speed_trace_{year}_{gp_sanitized}_{session_type}_{drivers_str}.png"
    output_path = workspace_dir / "charts" / filename

    # Enable FastF1 cache with shared directory
    fastf1.Cache.enable_cache(str(get_fastf1_cache_dir()))

    # Load session WITH telemetry data
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=True, weather=False, messages=False)

    # Setup plotting
    setup_plot_style()
    fastf1.plotting.setup_mpl(misc_mpl_mods=False)

    # Create figure with wide format for full lap distance
    fig, ax = plt.subplots(figsize=(14, 7))

    # Track statistics for each driver
    stats = []
    all_telemetry = []

    # Plot each driver's speed trace
    for driver_abbr in drivers:
        # Get fastest lap for the driver
        driver_laps = session.laps.pick_driver(driver_abbr)

        if driver_laps.empty:
            continue

        fastest_lap = driver_laps.pick_fastest()

        # Get telemetry data with distance
        telemetry = fastest_lap.get_car_data().add_distance()

        if telemetry.empty:
            continue

        # Get driver color from FastF1
        try:
            color = fastf1.plotting.get_driver_color(driver_abbr, session)
        except Exception:
            # Fallback to a default color if not found
            color = None

        # Plot speed trace
        ax.plot(
            telemetry["Distance"],
            telemetry["Speed"],
            label=driver_abbr,
            color=color,
            linewidth=2,
            alpha=0.9,
        )

        # Store telemetry for delta calculation
        all_telemetry.append(
            {
                "driver": driver_abbr,
                "telemetry": telemetry[["Distance", "Speed"]].copy(),
            }
        )

        # Calculate statistics
        stats.append(
            {
                "driver": driver_abbr,
                "max_speed": float(telemetry["Speed"].max()),
                "average_speed": float(telemetry["Speed"].mean()),
                "fastest_lap_time": str(fastest_lap["LapTime"])[10:18],
                "fastest_lap_number": int(fastest_lap["LapNumber"]),
            }
        )

    # Calculate speed delta (maximum difference between drivers)
    speed_delta = None
    if len(all_telemetry) >= 2:
        try:
            # Merge all telemetry data on distance
            merged = all_telemetry[0]["telemetry"].copy()
            merged = merged.rename(columns={"Speed": f"Speed_{all_telemetry[0]['driver']}"})

            for telem_data in all_telemetry[1:]:
                driver = telem_data["driver"]
                telem_df = telem_data["telemetry"].copy()
                telem_df = telem_df.rename(columns={"Speed": f"Speed_{driver}"})
                merged = pd.merge_asof(
                    merged.sort_values("Distance"),
                    telem_df.sort_values("Distance"),
                    on="Distance",
                    direction="nearest",
                )

            # Calculate speed range (max - min) at each distance point
            speed_cols = [col for col in merged.columns if col.startswith("Speed_")]
            merged["speed_range"] = merged[speed_cols].max(axis=1) - merged[speed_cols].min(axis=1)

            # Find maximum speed difference
            max_delta_idx = merged["speed_range"].idxmax()

            speed_delta = {
                "max_difference": float(merged.loc[max_delta_idx, "speed_range"]),
                "max_difference_location": float(merged.loc[max_delta_idx, "Distance"]),
            }
        except Exception:
            # If delta calculation fails, continue without it
            speed_delta = None

    # Customize plot
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.set_title(f"{session.event['EventName']} {year} - {session.name}\nSpeed Trace Comparison")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    # Add some padding to y-axis
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    ax.set_ylim(y_min - y_range * 0.05, y_max + y_range * 0.05)

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
        "drivers_compared": [s["driver"] for s in stats],
        "statistics": stats,
        "speed_delta": speed_delta,
    }
