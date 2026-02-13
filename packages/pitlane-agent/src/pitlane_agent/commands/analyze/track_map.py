"""Generate track map visualization with numbered corners from FastF1 circuit data.

Usage:
    pitlane analyze track-map --workspace-id <id> --year 2024 --gp Monaco --session R
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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


def generate_track_map_chart(
    year: int,
    gp: str,
    session_type: str,
    workspace_dir: Path,
) -> dict:
    """Generate a track map with numbered corner labels.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and corner statistics

    Raises:
        ValueError: If position data is unavailable for the session
    """
    # Build output path (no drivers for circuit-level chart)
    output_path = build_chart_path(workspace_dir, "track_map", year, gp, session_type)

    # Load session with telemetry to ensure position data is available
    session = load_session(year, gp, session_type, telemetry=True)

    # Get fastest lap for position data
    lap = session.laps.pick_fastest()
    if lap is None:
        raise ValueError(f"No laps available for {gp} {year} {session_type}")
    pos = lap.get_pos_data()

    if pos.empty:
        raise ValueError(f"No position data available for {gp} {year} {session_type}")

    # Get circuit information (corners, rotation)
    circuit_info = session.get_circuit_info()

    # Setup plotting
    setup_plot_style()

    fig, ax = plt.subplots(figsize=(12, 12))

    # Rotate track coordinates for proper orientation
    track = pos.loc[:, ("X", "Y")].to_numpy()
    track_angle = circuit_info.rotation / 180 * np.pi
    rotated_track = _rotate(track, angle=track_angle)

    # Draw track outline
    ax.plot(rotated_track[:, 0], rotated_track[:, 1], color="white", linewidth=3, alpha=0.9)

    # Draw corner markers
    offset_vector = [500, 0]
    corner_details = []

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
        ax.plot([track_x, text_x], [track_y, text_y], color="grey", linewidth=1, alpha=0.7)
        ax.scatter(text_x, text_y, color="grey", s=140, zorder=5)
        ax.text(text_x, text_y, txt, va="center_baseline", ha="center", size="small", color="white", zorder=6)

        corner_details.append({"number": number, "letter": letter})

    # Configure axes
    ax.set_title(f"{session.event['EventName']} {year} - {session.name}\nTrack Map", fontsize=16)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

    # Save figure
    save_figure(fig, output_path)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "circuit_name": session.event.get("Location", gp),
        "num_corners": len(corner_details),
        "corner_details": corner_details,
    }
