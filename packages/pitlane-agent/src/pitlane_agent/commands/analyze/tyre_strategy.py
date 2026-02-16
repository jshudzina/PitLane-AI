"""Generate tyre strategy visualization from FastF1 data.

Usage:
    pitlane tyre-strategy --year 2024 --gp Monaco --session R
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from pitlane_agent.utils.constants import COMPOUND_COLORS
from pitlane_agent.utils.fastf1_helpers import build_chart_path, load_session_or_testing
from pitlane_agent.utils.plotting import save_figure, setup_plot_style


def generate_tyre_strategy_chart(
    year: int,
    gp: str,
    session_type: str,
    workspace_dir: Path,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Generate a tyre strategy visualization.

    Args:
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (typically 'R' for race, ignored for testing)
        workspace_dir: Workspace directory for outputs and cache
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with chart metadata and strategy info
    """
    # Build output path
    output_path = build_chart_path(
        workspace_dir,
        "tyre_strategy",
        year,
        gp,
        session_type,
        test_number=test_number,
        session_number=session_number,
    )

    # Load session with laps data
    session = load_session_or_testing(year, gp, session_type, test_number=test_number, session_number=session_number)

    # Setup plotting
    setup_plot_style()

    # Get drivers sorted by finishing position
    drivers = session.results.sort_values("Position")["Abbreviation"].tolist()

    # Create figure
    fig, ax = plt.subplots(figsize=(14, max(8, len(drivers) * 0.4)))

    # Track strategy data for each driver
    strategies = []

    for idx, driver in enumerate(drivers):
        driver_laps = session.laps.pick_drivers(driver)

        if driver_laps.empty:
            continue

        # Group consecutive laps by compound
        stints = []
        current_compound = None
        stint_start = None

        for _, lap in driver_laps.iterrows():
            compound = lap["Compound"]
            lap_num = lap["LapNumber"]

            if compound != current_compound:
                if current_compound is not None:
                    stints.append(
                        {
                            "compound": current_compound,
                            "start": stint_start,
                            "end": lap_num - 1,
                        }
                    )
                current_compound = compound
                stint_start = lap_num

        # Add final stint
        if current_compound is not None:
            stints.append(
                {
                    "compound": current_compound,
                    "start": stint_start,
                    "end": driver_laps["LapNumber"].max(),
                }
            )

        # Draw stints as horizontal bars
        for stint in stints:
            compound = stint["compound"] if pd.notna(stint["compound"]) else "UNKNOWN"
            color = COMPOUND_COLORS.get(compound.upper(), COMPOUND_COLORS["UNKNOWN"])

            ax.barh(
                y=idx,
                width=stint["end"] - stint["start"] + 1,
                left=stint["start"] - 1,
                height=0.8,
                color=color,
                edgecolor="#333333",
                linewidth=0.5,
            )

        strategies.append(
            {
                "driver": driver,
                "position": idx + 1,
                "stints": [
                    {
                        "compound": s["compound"],
                        "laps": s["end"] - s["start"] + 1,
                    }
                    for s in stints
                ],
                "total_stops": len(stints) - 1,
            }
        )

    # Customize plot
    ax.set_yticks(range(len(drivers)))
    ax.set_yticklabels(drivers)
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Driver (by finishing position)")
    ax.set_title(f"{session.event['EventName']} {year} - Tyre Strategy")
    ax.set_xlim(0, session.total_laps + 1 if hasattr(session, "total_laps") else None)
    ax.invert_yaxis()  # First place at top

    # Add legend
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor="#333333", label=compound)
        for compound, color in COMPOUND_COLORS.items()
        if compound not in ["UNKNOWN"]
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper right",
        title="Compound",
        framealpha=0.8,
    )

    # Save figure
    save_figure(fig, output_path)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "total_laps": int(session.total_laps)
        if hasattr(session, "total_laps") and pd.notna(session.total_laps)
        else None,
        "strategies": strategies,
    }
