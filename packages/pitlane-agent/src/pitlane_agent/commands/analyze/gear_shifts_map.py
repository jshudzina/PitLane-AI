"""Generate gear shift visualization on track map from FastF1 telemetry.

Usage:
    pitlane analyze gear-shifts-map --workspace-id <id> --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from pitlane_agent.utils.constants import (
    GEAR_COLORMAP,
    GEAR_SHIFTS_LINE_WIDTH,
    MAX_GEAR_SHIFTS_MAP_DRIVERS,
    MIN_GEAR_SHIFTS_MAP_DRIVERS,
)
from pitlane_agent.utils.fastf1_helpers import build_chart_path, load_session
from pitlane_agent.utils.plotting import save_figure, setup_plot_style


def _rotate(xy: np.ndarray, *, angle: float) -> np.ndarray:
    """Rotate 2D coordinates by the given angle in radians.

    Args:
        xy: Array-like of shape (2,) or (N, 2) with X/Y coordinates.
        angle: Rotation angle in radians.

    Returns:
        Rotated coordinates with the same shape as input.
    """
    rot_mat = np.array([[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]])
    return np.matmul(xy, rot_mat)


def _calculate_gear_statistics(telemetry: pd.DataFrame) -> dict:
    """Calculate gear usage statistics from telemetry.

    Args:
        telemetry: DataFrame with nGear column containing gear values.

    Returns:
        Dictionary with gear distribution, most used gear, highest gear, and total gear changes.
    """
    gear_counts = telemetry["nGear"].value_counts()
    total_points = len(telemetry)

    return {
        "gear_distribution": {
            int(gear): {"count": int(count), "percentage": round(float(count / total_points * 100), 1)}
            for gear, count in gear_counts.items()
        },
        "most_used_gear": int(gear_counts.idxmax()),
        "highest_gear": int(telemetry["nGear"].max()),
        "total_gear_changes": int((telemetry["nGear"].diff() != 0).sum()),
    }


def generate_gear_shifts_map_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str],
    workspace_dir: Path,
) -> dict:
    """Generate gear shift visualization on track map for driver comparison.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier (R, Q, FP1, etc.)
        drivers: List of 1-3 driver abbreviations to compare
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and gear statistics

    Raises:
        ValueError: If drivers list has <1 or >3 entries
        ValueError: If telemetry data is unavailable
    """
    # Validate driver count
    if len(drivers) < MIN_GEAR_SHIFTS_MAP_DRIVERS:
        raise ValueError(f"Gear shifts map requires at least {MIN_GEAR_SHIFTS_MAP_DRIVERS} driver")
    if len(drivers) > MAX_GEAR_SHIFTS_MAP_DRIVERS:
        raise ValueError(
            f"Gear shifts map supports maximum {MAX_GEAR_SHIFTS_MAP_DRIVERS} drivers "
            f"for readability, got {len(drivers)}"
        )

    # Build output path
    output_path = build_chart_path(workspace_dir, "gear_shifts_map", year, gp, session_type, drivers)

    # Load session with telemetry
    session = load_session(year, gp, session_type, telemetry=True)

    # Get circuit info for rotation
    circuit_info = session.get_circuit_info()
    track_angle = circuit_info.rotation / 180 * np.pi

    # Setup plotting
    setup_plot_style()

    # Create subplot layout
    num_drivers = len(drivers)
    fig_width = 6 * num_drivers
    fig, axes = plt.subplots(1, num_drivers, figsize=(fig_width, 8), sharey=True)
    if num_drivers == 1:
        axes = [axes]

    # Track statistics
    all_stats = []
    last_lc = None

    # Plot each driver
    for idx, driver_abbr in enumerate(drivers):
        ax = axes[idx]

        # Get fastest lap
        driver_laps = session.laps.pick_drivers(driver_abbr)
        if driver_laps.empty:
            continue

        fastest_lap = driver_laps.pick_fastest()

        # Get telemetry (includes X, Y, nGear)
        telemetry = fastest_lap.get_car_data()

        if telemetry.empty or "nGear" not in telemetry.columns:
            raise ValueError(f"No gear telemetry for {driver_abbr} at {gp} {year}")

        # Extract coordinates and gear
        x = telemetry["X"].to_numpy()
        y = telemetry["Y"].to_numpy()
        gear = telemetry["nGear"].to_numpy()

        # Create line segments
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        # Rotate segments
        rotated_segments = np.zeros_like(segments)
        for i in range(segments.shape[0]):
            rotated_segments[i, 0] = _rotate(segments[i, 0], angle=track_angle)
            rotated_segments[i, 1] = _rotate(segments[i, 1], angle=track_angle)

        # Create LineCollection
        lc = LineCollection(
            rotated_segments,
            cmap=GEAR_COLORMAP,
            norm=plt.Normalize(1, 9),
            linewidth=GEAR_SHIFTS_LINE_WIDTH,
        )
        lc.set_array(gear)
        ax.add_collection(lc)
        last_lc = lc

        # Configure axes
        ax.set_title(f"{driver_abbr}\n{str(fastest_lap['LapTime'])[10:18]}")
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])

        # Auto-scale to fit the track
        ax.autoscale()

        # Calculate statistics
        stats = _calculate_gear_statistics(telemetry)
        all_stats.append(
            {
                "driver": driver_abbr,
                "lap_number": int(fastest_lap["LapNumber"]),
                "lap_time": str(fastest_lap["LapTime"])[10:18],
                **stats,
            }
        )

    # Add shared colorbar
    if last_lc is not None:
        cbar = fig.colorbar(
            last_lc,
            ax=axes,
            label="Gear",
            boundaries=np.arange(1, 10),
            ticks=np.arange(1.5, 9.5),
            orientation="horizontal",
            pad=0.05,
        )
        cbar.set_ticklabels(np.arange(1, 9))

    # Main title
    fig.suptitle(
        f"{session.event['EventName']} {year} - {session.name}\nGear Usage on Track",
        fontsize=14,
    )

    # Save
    save_figure(fig, output_path)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "circuit_name": session.event.get("Location", gp),
        "drivers_analyzed": [s["driver"] for s in all_stats],
        "gear_statistics": all_stats,
    }
