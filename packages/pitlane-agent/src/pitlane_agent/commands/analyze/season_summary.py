"""Generate season summary heatmap visualization from FastF1 data.

Usage:
    pitlane analyze season-summary --workspace-id <id> --year 2024
    pitlane analyze season-summary --workspace-id <id> --year 2024 --type constructors
"""

import logging
from pathlib import Path
from typing import TypedDict

import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pitlane_agent.utils.fastf1_helpers import setup_fastf1_cache

logger = logging.getLogger(__name__)


class CompetitorSummary(TypedDict):
    """Championship standing entry for a single competitor."""

    name: str
    championship_position: int
    points: float
    team: str


def _fetch_per_round_points(
    year: int,
    schedule: pd.DataFrame,
    summary_type: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, list[str], pd.Series]:
    """Fetch per-round points (and finishing positions) via FastF1.

    Args:
        year: Championship year
        schedule: FastF1 event schedule DataFrame (from fastf1.get_event_schedule)
        summary_type: "drivers" or "constructors"

    Returns:
        Tuple of:
        - points_df: pivot of competitor × round → points, sorted ascending by
          total (champion sits at the top of the heatmap)
        - position_df: pivot of driver × round → finishing position (drivers
          mode only; empty DataFrame for constructors)
        - total_points: Series of total season points per competitor, same order
        - short_event_names: short race name strings in round-number order
        - competitor_teams: Series mapping competitor name → team name
          (for drivers mode: driver abbreviation → team; for constructors: name → name)
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

            # Convert position to int for clean hover display
            raw_pos = driver_row["Position"]
            position = int(raw_pos) if pd.notna(raw_pos) else None

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
                    "TeamName": team_name,
                    "Points": race_points + sprint_points,
                    "Position": position,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=float), short_event_names, pd.Series(dtype=str)

    if summary_type == "constructors":
        points_df = df.groupby(["Competitor", "RoundNumber"])["Points"].sum().unstack(fill_value=0)
        position_df = pd.DataFrame()
    else:
        points_df = df.pivot(index="Competitor", columns="RoundNumber", values="Points").fillna(0)
        position_df = df.pivot(index="Competitor", columns="RoundNumber", values="Position").fillna("N/A")

    # Ensure columns are in round-number order
    points_df = points_df[sorted(points_df.columns)]

    # Sort ascending by total so the championship leader sits at the top of the heatmap
    total_points = points_df.sum(axis=1)
    sorted_idx = total_points.sort_values(ascending=True).index
    points_df = points_df.loc[sorted_idx]
    total_points = total_points.loc[sorted_idx]

    if not position_df.empty:
        position_df = position_df.loc[sorted_idx, sorted(position_df.columns)]

    # Build competitor → team mapping (most recent entry wins for a driver)
    competitor_teams: pd.Series = df.groupby("Competitor")["TeamName"].last()

    return points_df, position_df, total_points, short_event_names, competitor_teams


def _build_season_heatmap(
    points_df: pd.DataFrame,
    position_df: pd.DataFrame,
    total_points: pd.Series,
    short_event_names: list[str],
    year: int,
    summary_type: str,
) -> go.Figure:
    """Build the two-panel Plotly heatmap and return the figure.

    Left panel (85 %): per-round points with hover showing finishing position.
    Right panel (15 %): total season points.
    """
    n_rounds = len(points_df.columns)
    x_labels = short_event_names[:n_rounds]
    type_label = "Drivers'" if summary_type == "drivers" else "Constructors'"
    vmax_main = float(points_df.values.max()) if points_df.size > 0 else 25.0

    # Build per-cell hover customdata (list-of-lists of dicts with position)
    if not position_df.empty:
        hover_info = [
            [
                {"position": position_df.at[driver, race] if race in position_df.columns else "N/A"}
                for race in points_df.columns
            ]
            for driver in points_df.index
        ]
        hovertemplate = "Driver: %{y}<br>Race: %{x}<br>Points: %{z}<br>Position: %{customdata.position}<extra></extra>"
    else:
        hover_info = None
        hovertemplate = "Constructor: %{y}<br>Race: %{x}<br>Points: %{z}<extra></extra>"

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.85, 0.15],
        subplot_titles=(f"F1 {year} {type_label} Championship", "Total Points"),
    )
    fig.update_layout(
        width=max(900, n_rounds * 45 + 200),
        height=max(500, len(points_df) * 28 + 120),
    )

    main_trace = go.Heatmap(
        x=x_labels,
        y=list(points_df.index),
        z=points_df.values,
        text=points_df.values,
        texttemplate="%{text:.0f}",
        textfont={"size": 10},
        colorscale="YlGnBu",
        showscale=False,
        zmin=0,
        zmax=vmax_main,
        hovertemplate=hovertemplate,
    )
    if hover_info is not None:
        main_trace.customdata = hover_info

    fig.add_trace(main_trace, row=1, col=1)

    fig.add_trace(
        go.Heatmap(
            x=["Total Points"] * len(total_points),
            y=list(points_df.index),
            z=total_points.values,
            text=total_points.values,
            texttemplate="%{text:.0f}",
            textfont={"size": 11},
            colorscale="YlGnBu",
            showscale=False,
            zmin=0,
            zmax=float(total_points.max()) if len(total_points) > 0 else 1.0,
        ),
        row=1,
        col=2,
    )

    return fig


def generate_season_summary_chart(
    year: int,
    workspace_dir: Path,
    summary_type: str = "drivers",
) -> dict:
    """Generate an interactive season summary heatmap with per-round points.

    Saves the chart as an HTML file so the Plotly hover tooltips are preserved.

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

    points_df, position_df, total_points, short_event_names, competitor_teams = _fetch_per_round_points(
        year, schedule, summary_type
    )

    if points_df.empty:
        raise ValueError(f"No standings data available for {year} {summary_type} championship.")

    completed_round = int(points_df.columns.max())
    season_complete = len(points_df.columns) >= total_race_events

    # Build competitor list — champion is last in the ascending-sorted index
    competitors: list[CompetitorSummary] = [
        {
            "name": competitor,
            "championship_position": rank,
            "points": float(total_points[competitor]),
            "team": str(competitor_teams.get(competitor, competitor)),
        }
        for rank, competitor in enumerate(reversed(list(total_points.index)), start=1)
    ]
    leader = competitors[0] if competitors else None

    fig = _build_season_heatmap(points_df, position_df, total_points, short_event_names, year, summary_type)

    round_label = f"After Round {completed_round}" if not season_complete else f"Final — {completed_round} Races"
    fig.update_layout(title_text=round_label, title_x=0.5, title_font_size=12)

    filename = f"season_summary_{year}_{summary_type}.html"
    output_path = workspace_dir / "charts" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "year": year,
        "summary_type": summary_type,
        "analysis_round": completed_round,
        "total_races": total_race_events,
        "season_complete": season_complete,
        "leader": {
            "name": leader["name"] if leader else None,
            "points": leader["points"] if leader else None,
            "team": leader["team"] if leader else None,
            "position": 1,
        },
        "statistics": {
            "total_competitors": len(competitors),
            "competitors": competitors,
        },
    }
