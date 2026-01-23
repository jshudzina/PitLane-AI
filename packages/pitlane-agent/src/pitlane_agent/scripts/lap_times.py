"""Generate lap times visualization from FastF1 data.

Usage:
    python -m pitlane_agent.scripts.lap_times \
        --year 2024 --gp Monaco --session Q \
        --drivers VER HAM LEC \
        --output /tmp/charts/lap_times.png
"""

import argparse
import json
import sys
from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt


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


def generate_lap_times_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str],
    output_path: str,
) -> dict:
    """Generate a lap times scatter plot.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier
        drivers: List of driver abbreviations to include
        output_path: Path to save the chart image

    Returns:
        Dictionary with chart metadata and statistics
    """
    # Enable FastF1 cache
    fastf1.Cache.enable_cache("/tmp/fastf1_cache")

    # Load session with laps data
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    # Setup plotting
    setup_plot_style()
    fastf1.plotting.setup_mpl(misc_mpl_mods=False)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Track statistics for each driver
    stats = []

    # Plot each driver's lap times
    for driver_abbr in drivers:
        driver_laps = session.laps.pick_driver(driver_abbr).pick_quicklaps()

        if driver_laps.empty:
            continue

        # Get driver color from FastF1
        try:
            color = fastf1.plotting.get_driver_color(driver_abbr, session)
        except Exception:
            # Fallback to a default color if not found
            color = None

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

    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save figure
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return {
        "output_path": str(output_path),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_plotted": [s["driver"] for s in stats],
        "statistics": stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate lap times chart")
    parser.add_argument("--year", type=int, required=True, help="Season year")
    parser.add_argument("--gp", type=str, required=True, help="Grand Prix name")
    parser.add_argument("--session", type=str, required=True, help="Session type")
    parser.add_argument(
        "--drivers",
        type=str,
        nargs="+",
        required=True,
        help="Driver abbreviations (e.g., VER HAM)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/tmp/charts/lap_times.png",
        help="Output path for the chart",
    )

    args = parser.parse_args()

    try:
        result = generate_lap_times_chart(
            year=args.year,
            gp=args.gp,
            session_type=args.session,
            drivers=args.drivers,
            output_path=args.output,
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
