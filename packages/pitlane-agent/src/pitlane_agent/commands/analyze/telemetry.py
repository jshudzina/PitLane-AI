"""Generate interactive telemetry visualization from FastF1 car data.

Produces an HTML chart with synchronized subplots for Speed, RPM, Gear,
Throttle, and Brake, with hover tooltips showing driver deltas.

Usage:
    pitlane analyze telemetry --workspace-id <id> --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
"""

import logging
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
from pitlane_agent.utils.telemetry_analysis import analyze_telemetry


def _format_sector_time(sector_time: pd.Timedelta) -> str | None:
    """Format a sector time as SS.mmm or M:SS.mmm, or None if not available."""
    if pd.isna(sector_time):
        return None
    total_seconds = sector_time.total_seconds()
    minutes = int(total_seconds // 60)
    secs = total_seconds % 60
    if minutes > 0:
        return f"{minutes}:{secs:06.3f}"
    return f"{secs:.3f}"


# Telemetry channels mapped to subplot rows and display labels
CHANNELS = [
    {"key": "Speed", "label": "Speed (km/h)", "row": 1, "fmt": ".0f", "unit": "km/h"},
    {"key": "RPM", "label": "RPM", "row": 2, "fmt": ".0f", "unit": ""},
    {"key": "nGear", "label": "Gear", "row": 3, "fmt": ".0f", "unit": ""},
    {"key": "Throttle", "label": "Throttle (%)", "row": 4, "fmt": ".0f", "unit": "%"},
    {"key": "Brake", "label": "Brake", "row": 5, "fmt": ".0f", "unit": ""},
    {"key": "SuperClip", "label": "Super Clip", "row": 6, "fmt": ".0f", "unit": ""},
]


def _entry_key(entry: dict) -> str:
    """Return the column-naming key for an entry (backward-compatible with 'driver' field)."""
    return entry.get("key", entry.get("driver", ""))


def _entry_label(entry: dict) -> str:
    """Return the display label for an entry (backward-compatible with 'driver' field)."""
    return entry.get("label", entry.get("driver", ""))


def _build_merged_telemetry(
    all_telemetry: list[dict],
    channel_keys: list[str],
) -> pd.DataFrame | None:
    """Merge all entries' telemetry onto a common distance grid.

    Returns a DataFrame with columns: Distance, {channel}_{key} for each
    entry/channel pair. Returns None if fewer than 2 entries have data.

    Entry dicts support both new-style (with 'key'/'label') and old-style
    (with 'driver') for backward compatibility.
    """
    if len(all_telemetry) < 2:
        return None

    cols_needed = ["Distance"] + channel_keys
    key0 = _entry_key(all_telemetry[0])
    ref = all_telemetry[0]["telemetry"][cols_needed].copy()
    ref.columns = ["Distance"] + [f"{c}_{key0}" for c in channel_keys]

    for entry in all_telemetry[1:]:
        k = _entry_key(entry)
        other = entry["telemetry"][cols_needed].copy()
        other.columns = ["Distance"] + [f"{c}_{k}" for c in channel_keys]
        ref = pd.merge_asof(
            ref.sort_values("Distance"),
            other.sort_values("Distance"),
            on="Distance",
            direction="nearest",
        )

    return ref


def _build_customdata(
    label: str,
    channel_key: str,
    tel: pd.DataFrame,
    merged: pd.DataFrame,
    other_labels: list[str],
    *,
    key: str | None = None,
    other_keys: list[str] | None = None,
) -> np.ndarray:
    """Build customdata array with deltas vs other entries for tooltip display.

    Args:
        label: Display name of this entry (used only for context; column ops use key)
        channel_key: The telemetry channel key (e.g. "Speed")
        tel: This entry's telemetry DataFrame
        merged: Merged telemetry DataFrame from _build_merged_telemetry
        other_labels: Display labels of other entries (for fallback if other_keys not given)
        key: Column-naming key for this entry (defaults to label if not provided)
        other_keys: Column-naming keys of other entries (defaults to other_labels if not provided)
    """
    if merged is None or not other_labels:
        return np.zeros((len(tel), 1))

    own_key = key if key is not None else label
    _other_keys = other_keys if other_keys is not None else other_labels

    own_col = f"{channel_key}_{own_key}"
    result_cols = []

    for other_key in _other_keys:
        other_col = f"{channel_key}_{other_key}"
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
    label: str,
    channel: dict,
    other_labels: list[str],
) -> str:
    """Build Plotly hovertemplate string with delta lines for each other entry."""
    fmt = channel["fmt"]
    unit = channel["unit"]
    lines = [
        f"<b>{label}</b>",
        "Distance: %{x:.0f}m",
        f"{channel['label']}: %{{y:{fmt}}}{unit}",
    ]
    for i, other in enumerate(other_labels):
        lines.append(f"\u0394 vs {other}: %{{customdata[{i}]:+.1f}}{unit}")
    lines.append("<extra></extra>")
    return "<br>".join(lines)


def _render_telemetry_chart(
    entries: list[dict],
    circuit_info,
    output_path: Path,
    annotate_corners: bool,
    title: str,
) -> bool:
    """Render a Plotly telemetry chart to HTML and return whether corners were drawn.

    Args:
        entries: List of entry dicts, each with:
            - 'key': column-naming identifier (no spaces)
            - 'label': display label (may contain spaces)
            - 'telemetry': DataFrame with Distance, Speed, RPM, nGear, Throttle, Brake, SuperClip
            - 'color': hex color string
            - 'style': line style dict with 'linestyle' and 'linewidth' keys
        circuit_info: FastF1 circuit info object (for corner annotations), or None
        output_path: Path to write the HTML file
        annotate_corners: Whether to draw corner annotations
        title: Chart title text

    Returns:
        True if corner annotations were successfully drawn, False otherwise
    """
    channel_keys = [ch["key"] for ch in CHANNELS]
    merged = _build_merged_telemetry(entries, channel_keys)

    fig = make_subplots(
        rows=len(CHANNELS),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=TELEMETRY_ROW_HEIGHTS,
        subplot_titles=[ch["label"] for ch in CHANNELS],
    )

    for entry in entries:
        lbl = _entry_label(entry)
        k = _entry_key(entry)
        tel = entry["telemetry"]
        color = entry["color"]
        style = entry["style"]

        other_labels = [_entry_label(e) for e in entries if _entry_key(e) != k]
        other_keys = [_entry_key(e) for e in entries if _entry_key(e) != k]

        dash_map = {"-": "solid", "--": "dash"}
        dash = dash_map.get(style["linestyle"], "solid")

        for channel in CHANNELS:
            customdata = _build_customdata(
                lbl,
                channel["key"],
                tel,
                merged,
                other_labels,
                key=k,
                other_keys=other_keys,
            )
            fill = "tozeroy" if channel["key"] == "SuperClip" else None

            fig.add_trace(
                go.Scatter(
                    x=tel["Distance"],
                    y=tel[channel["key"]],
                    name=lbl,
                    legendgroup=lbl,
                    showlegend=(channel["row"] == 1),
                    line={"color": color, "width": style["linewidth"], "dash": dash},
                    mode="lines",
                    fill=fill,
                    customdata=customdata,
                    hovertemplate=_build_hover_template(lbl, channel, other_labels),
                ),
                row=channel["row"],
                col=1,
            )

    corners_drawn = False
    if annotate_corners and circuit_info is not None:
        try:
            for _, corner in circuit_info.corners.iterrows():
                number = int(corner["Number"])
                letter = str(corner["Letter"]) if pd.notna(corner["Letter"]) and corner["Letter"] else ""
                corner_label = f"{number}{letter}"
                dist = float(corner["Distance"])

                for row in range(1, len(CHANNELS) + 1):
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
                    text=corner_label,
                    showarrow=False,
                    font={"color": PLOTLY_DARK_THEME["corner_label_color"], "size": 9},
                    row=1,
                    col=1,
                )
            corners_drawn = True
        except Exception:
            logging.getLogger(__name__).warning("Failed to draw corner annotations", exc_info=True)

    fig.update_layout(
        paper_bgcolor=PLOTLY_DARK_THEME["paper_bgcolor"],
        plot_bgcolor=PLOTLY_DARK_THEME["plot_bgcolor"],
        font={"color": PLOTLY_DARK_THEME["font_color"]},
        title={"text": title, "font": {"size": 16}},
        hovermode="x",
        legend={
            "bgcolor": "rgba(30,30,30,0.8)",
            "bordercolor": "#555555",
            "borderwidth": 1,
        },
        height=1100,
    )

    for i in range(1, len(CHANNELS) + 1):
        yaxis_key = f"yaxis{i}" if i > 1 else "yaxis"
        fig.update_layout(
            **{
                yaxis_key: {
                    "gridcolor": PLOTLY_DARK_THEME["gridcolor"],
                    "zerolinecolor": PLOTLY_DARK_THEME["zerolinecolor"],
                }
            }
        )

    fig.update_yaxes(dtick=2000, row=2, col=1)
    fig.update_yaxes(dtick=1, row=3, col=1)
    _superclip_row = next(ch["row"] for ch in CHANNELS if ch["key"] == "SuperClip")
    fig.update_yaxes(range=[-0.1, 1.1], dtick=1, tickvals=[0, 1], ticktext=["Off", "On"], row=_superclip_row, col=1)

    fig.update_xaxes(gridcolor=PLOTLY_DARK_THEME["gridcolor"])
    fig.update_xaxes(title_text="Distance (m)", row=len(CHANNELS), col=1)

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

    return corners_drawn


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

    entries: list[dict] = []
    stats: list[dict] = []

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

        # Telemetry technique analysis (lift-and-coast, super clipping)
        analysis = analyze_telemetry(tel)

        # Add derived SuperClip channel: 1 inside a clipping zone, 0 elsewhere
        tel["SuperClip"] = 0
        for zone in analysis["super_clipping_zones"]:
            mask = (tel["Distance"] >= zone["start_distance"]) & (tel["Distance"] <= zone["end_distance"])
            tel.loc[mask, "SuperClip"] = 1

        entries.append(
            {
                "driver": driver_abbr,  # kept for backward compatibility with tests
                "key": driver_abbr,
                "label": driver_abbr,
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
                "sector_1_time": _format_sector_time(fastest_lap.get("Sector1Time")),
                "sector_2_time": _format_sector_time(fastest_lap.get("Sector2Time")),
                "sector_3_time": _format_sector_time(fastest_lap.get("Sector3Time")),
                "speed_trap": float(fastest_lap["SpeedST"]) if pd.notna(fastest_lap.get("SpeedST")) else None,
                "speed_fl": float(fastest_lap["SpeedFL"]) if pd.notna(fastest_lap.get("SpeedFL")) else None,
                "lift_coast_count": analysis["lift_coast_count"],
                "lift_coast_duration": analysis["total_lift_coast_duration"],
                "lift_coast_zones": analysis["lift_and_coast_zones"],
                "clipping_count": analysis["clipping_count"],
                "clipping_duration": analysis["total_clipping_duration"],
                "clipping_zones": analysis["super_clipping_zones"],
            }
        )

    circuit_info = None
    if annotate_corners:
        try:
            circuit_info = session.get_circuit_info()
        except Exception:
            logging.getLogger(__name__).warning("Failed to load circuit info for corner annotations", exc_info=True)

    title = f"{session.event['EventName']} {year} — {session.name}<br>Telemetry Comparison"
    corners_drawn = _render_telemetry_chart(entries, circuit_info, output_path, annotate_corners, title)

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
