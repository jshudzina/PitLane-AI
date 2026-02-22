"""Generate season summary heatmap visualization from FastF1 data.

Usage:
    pitlane analyze season-summary --workspace-id <id> --year 2024
    pitlane analyze season-summary --workspace-id <id> --year 2024 --type constructors
"""

import logging
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from pitlane_agent.utils.constants import DEFAULT_DPI
from pitlane_agent.utils.fastf1_helpers import setup_fastf1_cache
from pitlane_agent.utils.plotting import save_figure, setup_plot_style

logger = logging.getLogger(__name__)


def _fetch_per_round_points(
    year: int,
    schedule: pd.DataFrame,
    summary_type: str,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Fetch per-round points for all drivers/constructors via FastF1.

    Args:
        year: Championship year
        schedule: FastF1 event schedule DataFrame (from fastf1.get_event_schedule)
        summary_type: "drivers" or "constructors"

    Returns:
        Tuple of:
        - points_df: DataFrame with competitors as index, round numbers as columns,
          sorted ascending by total points (champion at top of heatmap)
        - total_points: Series with total season points per competitor, same order
        - short_event_names: Short race name strings in round-number order
    """
    rows: list[dict] = []
    short_event_names: list[str] = []

    for _, event in schedule.iterrows():
        event_name = str(event["EventName"])
        round_number = int(event["RoundNumber"])
        if round_number == 0:
            continue

        short_event_names.append(event_name.replace("Grand Prix", "").strip())

        try:
            race = fastf1.get_session(year, event_name, "R")
            race.load(laps=False, telemetry=False, weather=False, messages=False)
        except Exception as e:
            logger.warning("Could not load R round %d (%s): %s", round_number, event_name, e)
            continue

        sprint = None
        if str(event.get("EventFormat", "")) == "sprint_qualifying":
            try:
                sprint = fastf1.get_session(year, event_name, "S")
                sprint.load(laps=False, telemetry=False, weather=False, messages=False)
            except Exception as e:
                logger.warning("Could not load S round %d (%s): %s", round_number, event_name, e)

        for _, driver_row in race.results.iterrows():
            abbreviation = str(driver_row["Abbreviation"])
            team_name = str(driver_row["TeamName"]) if pd.notna(driver_row["TeamName"]) else "Unknown"
            race_points = float(driver_row["Points"]) if pd.notna(driver_row["Points"]) else 0.0

            sprint_points = 0.0
            if sprint is not None:
                sprint_driver = sprint.results[sprint.results["Abbreviation"] == abbreviation]
                if not sprint_driver.empty:
                    sp = sprint_driver["Points"].values[0]
                    sprint_points = float(sp) if pd.notna(sp) else 0.0

            competitor = team_name if summary_type == "constructors" else abbreviation
            rows.append(
                {
                    "RoundNumber": round_number,
                    "Competitor": competitor,
                    "Points": race_points + sprint_points,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), pd.Series(dtype=float), short_event_names

    if summary_type == "constructors":
        points_df = df.groupby(["Competitor", "RoundNumber"])["Points"].sum().unstack(fill_value=0)
    else:
        points_df = df.pivot(index="Competitor", columns="RoundNumber", values="Points").fillna(0)

    # Ensure columns are in round-number order
    points_df = points_df[sorted(points_df.columns)]

    # Sort ascending by total so the championship leader sits at the top of the heatmap
    total_points = points_df.sum(axis=1)
    sorted_idx = total_points.sort_values(ascending=True).index
    points_df = points_df.loc[sorted_idx]
    total_points = total_points.loc[sorted_idx]

    return points_df, total_points, short_event_names


def _plot_season_heatmap(
    points_df: pd.DataFrame,
    total_points: pd.Series,
    short_event_names: list[str],
    year: int,
    summary_type: str,
    fig: plt.Figure,
) -> None:
    """Render the two-panel season points heatmap onto the figure.

    Left panel (85 %): per-round points grid.
    Right panel (15 %): total season points column.
    """
    gs = fig.add_gridspec(1, 2, width_ratios=[0.85, 0.15], wspace=0.03)
    ax_main = fig.add_subplot(gs[0])
    ax_total = fig.add_subplot(gs[1])

    cmap = "YlGnBu"
    n_rounds = len(points_df.columns)
    x_labels = short_event_names[:n_rounds]
    vmax = float(points_df.values.max()) if points_df.size > 0 else 25.0

    sns.heatmap(
        points_df,
        ax=ax_main,
        cmap=cmap,
        annot=True,
        fmt=".0f",
        linewidths=0.4,
        linecolor="#111111",
        cbar=False,
        xticklabels=x_labels,
        yticklabels=list(points_df.index),
        vmin=0,
        vmax=vmax,
        annot_kws={"size": 7},
    )

    type_label = "Drivers'" if summary_type == "drivers" else "Constructors'"
    ax_main.set_title(f"{year} {type_label} Championship — Points Per Round", fontsize=13, pad=10)
    ax_main.set_xlabel("")
    ax_main.set_ylabel("")
    ax_main.tick_params(axis="x", rotation=45, labelsize=8)
    ax_main.tick_params(axis="y", rotation=0, labelsize=9)

    total_df = total_points.to_frame(name="Total")
    sns.heatmap(
        total_df,
        ax=ax_total,
        cmap=cmap,
        annot=True,
        fmt=".0f",
        linewidths=0.4,
        linecolor="#111111",
        cbar=False,
        xticklabels=["Total"],
        yticklabels=False,
        vmin=0,
        vmax=float(total_points.max()) if len(total_points) > 0 else 1.0,
        annot_kws={"size": 9, "weight": "bold"},
    )
    ax_total.set_title("Total", fontsize=11, pad=10)
    ax_total.set_xlabel("")
    ax_total.set_ylabel("")
    ax_total.tick_params(axis="y", left=False)


def generate_season_summary_chart(
    year: int,
    summary_type: str = "drivers",
    workspace_dir: Path | None = None,
) -> dict:
    """Generate season summary heatmap with per-round championship points.

    Args:
        year: Championship year (e.g., 2024)
        summary_type: "drivers" or "constructors"
        workspace_dir: Workspace directory for output files

    Returns:
        Dictionary with chart metadata and season statistics

    Raises:
        ValueError: If summary_type is invalid or no data is available
    """
    summary_type = summary_type.lower()
    if summary_type not in ("drivers", "constructors"):
        raise ValueError(f"Invalid summary_type: {summary_type!r}. Must be 'drivers' or 'constructors'.")

    setup_fastf1_cache()
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    total_race_events = int((schedule["RoundNumber"] > 0).sum())

    points_df, total_points, short_event_names = _fetch_per_round_points(year, schedule, summary_type)

    if points_df.empty:
        raise ValueError(f"No standings data available for {year} {summary_type} championship.")

    completed_round = int(points_df.columns.max())
    season_complete = completed_round >= total_race_events

    # Build competitor list: champion is last in ascending-sorted index
    competitors = [
        {
            "name": competitor,
            "championship_position": rank,
            "points": float(total_points[competitor]),
        }
        for rank, competitor in enumerate(reversed(list(total_points.index)), start=1)
    ]
    leader = competitors[0] if competitors else {}

    setup_plot_style()
    n_competitors = len(points_df)
    n_rounds = len(points_df.columns)
    fig = plt.figure(figsize=(max(16, n_rounds * 0.8), max(8, n_competitors * 0.5 + 2)))

    _plot_season_heatmap(points_df, total_points, short_event_names, year, summary_type, fig)

    round_label = f"After Round {completed_round}" if not season_complete else f"Final — {completed_round} Races"
    fig.suptitle(round_label, fontsize=10, y=1.01, alpha=0.7)

    filename = f"season_summary_{year}_{summary_type}.png"
    output_path = workspace_dir / "charts" / filename
    save_figure(fig, output_path, dpi=DEFAULT_DPI)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "year": year,
        "summary_type": summary_type,
        "analysis_round": completed_round,
        "total_races": total_race_events,
        "season_complete": season_complete,
        "leader": {
            "name": leader.get("name"),
            "points": leader.get("points"),
            "position": 1,
        },
        "statistics": {
            "total_competitors": len(competitors),
            "competitors": competitors,
        },
    }
