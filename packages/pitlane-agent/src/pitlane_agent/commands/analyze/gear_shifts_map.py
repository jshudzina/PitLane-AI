"""Generate gear shift visualization on track map from FastF1 telemetry.

Usage:
    pitlane analyze gear-shifts-map --workspace-id <id> --year 2024 --gp Monaco --session Q --drivers VER
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from pitlane_agent.utils.constants import (
    GEAR_COLORMAP,
    GEAR_SHIFTS_LINE_WIDTH,
    MIN_TELEMETRY_POINTS_TRACK_MAP,
    TRACK_MAP_CORNER_LABEL_OFFSET,
    TRACK_MAP_CORNER_LINE_ALPHA,
    TRACK_MAP_CORNER_LINE_WIDTH,
    TRACK_MAP_CORNER_MARKER_SIZE,
)
from pitlane_agent.utils.fastf1_helpers import (
    build_chart_path,
    get_merged_telemetry,
    load_session,
)
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


def _format_lap_time(lap_time: pd.Timedelta) -> str:
    """Format lap time as MM:SS.mmm.

    Args:
        lap_time: Pandas Timedelta object representing lap time.

    Returns:
        Formatted lap time string (e.g., "1:23.456").
    """
    total_seconds = lap_time.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"


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
    """Generate gear shift visualization on track map for a single driver.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier (R, Q, FP1, etc.)
        drivers: List containing exactly 1 driver abbreviation
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and gear statistics

    Raises:
        ValueError: If drivers list does not contain exactly 1 driver
        ValueError: If telemetry data is unavailable
    """
    # Validate driver count (exactly 1 driver required)
    if len(drivers) != 1:
        raise ValueError(f"Gear shifts map requires exactly 1 driver, got {len(drivers)}")

    # Build output path
    output_path = build_chart_path(workspace_dir, "gear_shifts_map", year, gp, session_type, drivers)

    # Load session with telemetry
    session = load_session(year, gp, session_type, telemetry=True)

    # Get circuit info for rotation
    circuit_info = session.get_circuit_info()
    rotation = circuit_info.rotation if circuit_info.rotation is not None else 0
    track_angle = rotation / 180 * np.pi

    # Setup plotting
    setup_plot_style()

    # Create single figure (only 1 driver supported)
    fig, ax = plt.subplots(figsize=(10, 8))

    # Get the single driver
    driver_abbr = drivers[0]

    # Get fastest lap
    driver_laps = session.laps.pick_drivers(driver_abbr)
    if driver_laps.empty:
        raise ValueError(f"No laps found for {driver_abbr} at {gp} {year}")

    fastest_lap = driver_laps.pick_fastest()

    # Get merged telemetry with position (X, Y) and car data (nGear, Speed, etc.)
    # Uses helper that validates required channels and handles FastF1's interpolation
    try:
        telemetry = get_merged_telemetry(fastest_lap, required_channels=["X", "Y", "nGear"])
    except ValueError as e:
        # Re-raise with context-specific error message
        raise ValueError(f"{e} for {driver_abbr} at {gp} {year}") from e

    # Validate sufficient data points for visualization
    if len(telemetry) < MIN_TELEMETRY_POINTS_TRACK_MAP:
        raise ValueError(
            f"Insufficient telemetry data for {driver_abbr} at {gp} {year} "
            f"(only {len(telemetry)} points, need at least {MIN_TELEMETRY_POINTS_TRACK_MAP})"
        )

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
    # Note: Normalize to 1-9 (not 1-8) to improve color distinction between gears 7 and 8
    lc = LineCollection(
        rotated_segments,
        cmap=GEAR_COLORMAP,
        norm=plt.Normalize(1, 9),
        linewidth=GEAR_SHIFTS_LINE_WIDTH,
    )
    lc.set_array(gear)
    ax.add_collection(lc)

    # Configure axes
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])

    # Auto-scale to fit the track
    ax.autoscale()

    # Draw corner markers
    offset_vector = [TRACK_MAP_CORNER_LABEL_OFFSET, 0]

    for _, corner in circuit_info.corners.iterrows():
        number = int(corner["Number"])
        letter = str(corner["Letter"]) if pd.notna(corner["Letter"]) and corner["Letter"] else ""
        txt = f"{number}{letter}"

        # Calculate offset position for label
        offset_angle = corner["Angle"] / 180 * np.pi
        offset_x, offset_y = _rotate(offset_vector, angle=offset_angle)

        text_x = corner["X"] + offset_x
        text_y = corner["Y"] + offset_y
        text_x, text_y = _rotate([text_x, text_y], angle=track_angle)
        track_x, track_y = _rotate([corner["X"], corner["Y"]], angle=track_angle)

        # Draw connecting line and label bubble
        ax.plot(
            [track_x, text_x],
            [track_y, text_y],
            color="grey",
            linewidth=TRACK_MAP_CORNER_LINE_WIDTH,
            alpha=TRACK_MAP_CORNER_LINE_ALPHA,
        )
        ax.scatter(text_x, text_y, color="grey", s=TRACK_MAP_CORNER_MARKER_SIZE, zorder=5)
        ax.text(text_x, text_y, txt, va="center_baseline", ha="center", size="small", color="white", zorder=6)

    # Add vertical colorbar on the right side
    cbar = fig.colorbar(
        lc,
        ax=ax,
        label="Gear",
        boundaries=np.arange(1, 10),
        ticks=np.arange(1.5, 9.5),
        orientation="vertical",
        pad=0.02,
        fraction=0.046,
        aspect=20,
    )
    cbar.set_ticklabels(np.arange(1, 9))

    # Calculate statistics
    stats = _calculate_gear_statistics(telemetry)
    all_stats = [
        {
            "driver": driver_abbr,
            "lap_number": int(fastest_lap["LapNumber"]),
            "lap_time": _format_lap_time(fastest_lap["LapTime"]),
            **stats,
        }
    ]

    # Main title with driver info
    fig.suptitle(
        f"{session.event['EventName']} {year} - {session.name}\n"
        f"{driver_abbr} - Lap {fastest_lap['LapNumber']} ({_format_lap_time(fastest_lap['LapTime'])})\n"
        f"Gear Usage on Track",
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
