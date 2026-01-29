"""Generate tyre strategy visualization from FastF1 data.

Usage:
    pitlane tyre-strategy --year 2024 --gp Monaco --session R

    # Or using module invocation
    python -m pitlane_agent.scripts.tyre_strategy \
        --year 2024 --gp Monaco --session R \
        --output /tmp/pitlane_charts/tyre_strategy.png
"""

from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd

# Tyre compound colors (F1 2024 style)
COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFF200",
    "HARD": "#EBEBEB",
    "INTERMEDIATE": "#43B02A",
    "WET": "#0067AD",
    "UNKNOWN": "#888888",
}


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


def generate_tyre_strategy_chart(
    year: int,
    gp: str,
    session_type: str,
    workspace_dir: Path,
) -> dict:
    """Generate a tyre strategy visualization.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier (typically 'R' for race)
        workspace_dir: Workspace directory for outputs and cache

    Returns:
        Dictionary with chart metadata and strategy info
    """
    # Determine paths from workspace
    output_path = workspace_dir / "charts" / "tyre_strategy.png"
    cache_dir = Path.home() / ".pitlane" / "cache" / "fastf1"

    # Enable FastF1 cache with shared directory
    fastf1.Cache.enable_cache(str(cache_dir))

    # Load session with laps data
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    # Setup plotting
    setup_plot_style()

    # Get drivers sorted by finishing position
    drivers = session.results.sort_values("Position")["Abbreviation"].tolist()

    # Create figure
    fig, ax = plt.subplots(figsize=(14, max(8, len(drivers) * 0.4)))

    # Track strategy data for each driver
    strategies = []

    for idx, driver in enumerate(drivers):
        driver_laps = session.laps.pick_driver(driver)

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
        "total_laps": int(session.total_laps)
        if hasattr(session, "total_laps") and pd.notna(session.total_laps)
        else None,
        "strategies": strategies,
    }


# CLI interface removed - use pitlane analyze tyre-strategy instead
# This module now only provides the generate_tyre_strategy_chart function
