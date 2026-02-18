"""Generate interactive telemetry visualization from FastF1 car data.

Produces an HTML chart with synchronized subplots for Speed, RPM, Gear,
Throttle, and Brake, with hover tooltips showing driver deltas.

Usage:
    pitlane analyze telemetry --workspace-id <id> --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pitlane_agent.utils.constants import (
    MAX_TELEMETRY_DRIVERS,
    MIN_TELEMETRY_DRIVERS,
    PLOTLY_DARK_THEME,
    TEAMMATE_LINE_STYLES,
    TELEMETRY_ROW_HEIGHTS,
)
from pitlane_agent.utils.fastf1_helpers import build_chart_path, load_session_or_testing
from pitlane_agent.utils.plotting import (
    ensure_color_contrast,
    get_driver_color_safe,
    get_driver_team,
)

# Telemetry channels mapped to subplot rows and display labels
CHANNELS = [
    {"key": "Speed", "label": "Speed (km/h)", "row": 1, "fmt": ".0f", "unit": "km/h"},
    {"key": "RPM", "label": "RPM", "row": 2, "fmt": ".0f", "unit": ""},
    {"key": "nGear", "label": "Gear", "row": 3, "fmt": ".0f", "unit": ""},
    {"key": "Throttle", "label": "Throttle (%)", "row": 4, "fmt": ".0f", "unit": "%"},
    {"key": "Brake", "label": "Brake", "row": 5, "fmt": ".0f", "unit": ""},
]


def _build_merged_telemetry(
    all_telemetry: list[dict],
    channel_keys: list[str],
) -> pd.DataFrame | None:
    """Merge all drivers' telemetry onto a common distance grid.

    Returns a DataFrame with columns: Distance, {channel}_{driver} for each
    driver/channel pair. Returns None if fewer than 2 drivers have data.
    """
    if len(all_telemetry) < 2:
        return None

    cols_needed = ["Distance"] + channel_keys
    ref = all_telemetry[0]["telemetry"][cols_needed].copy()
    ref.columns = ["Distance"] + [f"{c}_{all_telemetry[0]['driver']}" for c in channel_keys]

    for entry in all_telemetry[1:]:
        drv = entry["driver"]
        other = entry["telemetry"][cols_needed].copy()
        other.columns = ["Distance"] + [f"{c}_{drv}" for c in channel_keys]
        ref = pd.merge_asof(
            ref.sort_values("Distance"),
            other.sort_values("Distance"),
            on="Distance",
            direction="nearest",
        )

    return ref


def _build_customdata(
    driver: str,
    channel_key: str,
    tel: pd.DataFrame,
    merged: pd.DataFrame,
    other_drivers: list[str],
) -> np.ndarray:
    """Build customdata array with deltas vs other drivers for tooltip display."""
    if merged is None or not other_drivers:
        return np.zeros((len(tel), 1))

    own_col = f"{channel_key}_{driver}"
    result_cols = []

    for other_drv in other_drivers:
        other_col = f"{channel_key}_{other_drv}"
        aligned = pd.merge_asof(
            tel[["Distance"]].sort_values("Distance"),
            merged[["Distance", own_col, other_col]].sort_values("Distance"),
            on="Distance",
            direction="nearest",
        )
        delta = (aligned[own_col] - aligned[other_col]).round(1)
        result_cols.append(delta.values)

    return np.column_stack(result_cols)


def _build_hover_template(
    driver: str,
    channel: dict,
    other_drivers: list[str],
) -> str:
    """Build Plotly hovertemplate string with delta lines for each other driver."""
    fmt = channel["fmt"]
    unit = channel["unit"]
    lines = [
        f"<b>{driver}</b>",
        "Distance: %{x:.0f}m",
        f"{channel['label']}: %{{y:{fmt}}}{unit}",
    ]
    for i, other in enumerate(other_drivers):
        lines.append(f"\u0394 vs {other}: %{{customdata[{i}]:+.1f}}{unit}")
    lines.append("<extra></extra>")
    return "<br>".join(lines)


def generate_telemetry_chart(
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str],
    workspace_dir: Path,
    annotate_corners: bool = False,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Generate an interactive telemetry comparison chart for fastest laps.

    Args:
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (ignored for testing sessions)
        drivers: List of 2-5 driver abbreviations to compare
        workspace_dir: Workspace directory for outputs and cache
        annotate_corners: Whether to add corner markers and labels
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with chart metadata and telemetry statistics

    Raises:
        ValueError: If drivers list has <2 or >5 entries
    """
    if len(drivers) < MIN_TELEMETRY_DRIVERS:
        raise ValueError(
            f"Telemetry requires at least {MIN_TELEMETRY_DRIVERS} drivers for comparison, got {len(drivers)}"
        )
    if len(drivers) > MAX_TELEMETRY_DRIVERS:
        raise ValueError(
            f"Telemetry supports maximum {MAX_TELEMETRY_DRIVERS} drivers for readability, got {len(drivers)}"
        )

    output_path = build_chart_path(
        workspace_dir,
        "telemetry",
        year,
        gp,
        session_type,
        drivers,
        test_number=test_number,
        session_number=session_number,
        extension="html",
    )

    session = load_session_or_testing(
        year, gp, session_type, test_number=test_number, session_number=session_number, telemetry=True
    )

    # Build team membership for teammate line style differentiation
    team_drivers: dict[str, list[str]] = {}
    for driver_abbr in drivers:
        team = get_driver_team(driver_abbr, session)
        if team:
            team_drivers.setdefault(team, []).append(driver_abbr)

    # Collect per-driver telemetry
    all_telemetry: list[dict] = []
    stats: list[dict] = []
    channel_keys = [ch["key"] for ch in CHANNELS]

    for driver_abbr in drivers:
        driver_laps = session.laps.pick_drivers(driver_abbr)
        if driver_laps.empty:
            continue

        fastest_lap = driver_laps.pick_fastest()
        tel = fastest_lap.get_car_data().add_distance()
        if tel.empty:
            continue

        # Brake is boolean in FastF1 — cast to int for plotting and delta math
        tel["Brake"] = tel["Brake"].astype(int)

        color = get_driver_color_safe(driver_abbr, session)
        color = ensure_color_contrast(color) if color else "#ffffff"

        # Determine teammate line style
        team = get_driver_team(driver_abbr, session)
        teammate_index = 0
        if team and team in team_drivers:
            teammate_index = team_drivers[team].index(driver_abbr)
        style = TEAMMATE_LINE_STYLES[min(teammate_index, len(TEAMMATE_LINE_STYLES) - 1)]

        all_telemetry.append(
            {
                "driver": driver_abbr,
                "telemetry": tel,
                "color": color,
                "style": style,
            }
        )

        stats.append(
            {
                "driver": driver_abbr,
                "max_speed": float(tel["Speed"].max()),
                "avg_speed": float(tel["Speed"].mean()),
                "max_rpm": float(tel["RPM"].max()),
                "fastest_lap_time": str(fastest_lap["LapTime"])[10:18],
                "fastest_lap_number": int(fastest_lap["LapNumber"]),
            }
        )

    # Pre-compute merged telemetry for delta tooltips
    merged = _build_merged_telemetry(all_telemetry, channel_keys)

    # Build Plotly figure with shared X axis
    fig = make_subplots(
        rows=5,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=TELEMETRY_ROW_HEIGHTS,
        subplot_titles=[ch["label"] for ch in CHANNELS],
    )

    # Add traces for each driver on each channel
    for entry in all_telemetry:
        drv = entry["driver"]
        tel = entry["telemetry"]
        color = entry["color"]
        style = entry["style"]
        other_drivers = [e["driver"] for e in all_telemetry if e["driver"] != drv]

        dash_map = {"-": "solid", "--": "dash"}
        dash = dash_map.get(style["linestyle"], "solid")

        for channel in CHANNELS:
            customdata = _build_customdata(drv, channel["key"], tel, merged, other_drivers)

            fig.add_trace(
                go.Scatter(
                    x=tel["Distance"],
                    y=tel[channel["key"]],
                    name=drv,
                    legendgroup=drv,
                    showlegend=(channel["row"] == 1),
                    line={"color": color, "width": style["linewidth"], "dash": dash},
                    mode="lines",
                    customdata=customdata,
                    hovertemplate=_build_hover_template(drv, channel, other_drivers),
                ),
                row=channel["row"],
                col=1,
            )

    # Corner annotations
    corners_drawn = False
    if annotate_corners:
        try:
            circuit_info = session.get_circuit_info()
            for _, corner in circuit_info.corners.iterrows():
                number = int(corner["Number"])
                letter = str(corner["Letter"]) if pd.notna(corner["Letter"]) and corner["Letter"] else ""
                label = f"{number}{letter}"
                dist = float(corner["Distance"])

                for row in range(1, 6):
                    fig.add_vline(
                        x=dist,
                        line={"color": PLOTLY_DARK_THEME["corner_line_color"], "width": 1, "dash": "dash"},
                        row=row,
                        col=1,
                    )

                fig.add_annotation(
                    x=dist,
                    y=1.02,
                    yref="y domain",
                    xref="x",
                    text=label,
                    showarrow=False,
                    font={"color": PLOTLY_DARK_THEME["corner_label_color"], "size": 9},
                    row=1,
                    col=1,
                )
            corners_drawn = True
        except Exception:
            pass

    # Apply dark theme
    fig.update_layout(
        paper_bgcolor=PLOTLY_DARK_THEME["paper_bgcolor"],
        plot_bgcolor=PLOTLY_DARK_THEME["plot_bgcolor"],
        font={"color": PLOTLY_DARK_THEME["font_color"]},
        title={
            "text": f"{session.event['EventName']} {year} — {session.name}<br>Telemetry Comparison",
            "font": {"size": 16},
        },
        hovermode="x",
        legend={
            "bgcolor": "rgba(30,30,30,0.8)",
            "bordercolor": "#555555",
            "borderwidth": 1,
        },
        height=1000,
    )

    # Style all Y axes
    for i in range(1, 6):
        yaxis_key = f"yaxis{i}" if i > 1 else "yaxis"
        fig.update_layout(
            **{
                yaxis_key: {
                    "gridcolor": PLOTLY_DARK_THEME["gridcolor"],
                    "zerolinecolor": PLOTLY_DARK_THEME["zerolinecolor"],
                }
            }
        )

    # Fix RPM axis to use round tick intervals (row 2 = yaxis2)
    fig.update_yaxes(dtick=2000, row=2, col=1)
    # Fix Gear axis to integer ticks (row 3 = yaxis3)
    fig.update_yaxes(dtick=1, row=3, col=1)

    # Style X axes — only label the bottom one
    fig.update_xaxes(gridcolor=PLOTLY_DARK_THEME["gridcolor"])
    fig.update_xaxes(title_text="Distance (m)", row=5, col=1)

    # Save as self-contained HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(
        str(output_path),
        include_plotlyjs=True,
        full_html=True,
        config={
            "displayModeBar": True,
            "scrollZoom": True,
        },
    )

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_compared": [s["driver"] for s in stats],
        "statistics": stats,
        "corners_annotated": corners_drawn,
        "output_format": "html",
    }
