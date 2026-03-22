"""Generate interactive telemetry visualization from FastF1 car data.

Produces an HTML chart with synchronized subplots for configurable channel groups:
  delta       — Cumulative time gap vs reference driver (pro "outcome first" layout)
  speed       — Speed trace
  throttle_brake — Throttle line + brake fill on shared 0–100% axis
  rpm_gear    — RPM (left axis) + Gear step-line (secondary right axis)
  superclip   — MGU-K clipping indicator

Default channels: delta, speed, throttle_brake, rpm_gear

Usage:
    pitlane analyze telemetry --workspace-id <id> --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
    pitlane analyze telemetry ... --channel speed --channel delta
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pitlane_agent.utils.constants import (
    DEFAULT_TELEMETRY_CHANNELS,
    MAX_TELEMETRY_DRIVERS,
    MIN_TELEMETRY_DRIVERS,
    PLOTLY_DARK_THEME,
    TEAMMATE_LINE_STYLES,
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


# ---------------------------------------------------------------------------
# Channel group definitions
# ---------------------------------------------------------------------------

CHANNEL_GROUPS: dict[str, dict] = {
    "delta": {
        "label": "Δ Time (s)",
        "height_px": 160,
        "computed": True,  # populated by _add_time_delta() before rendering
        "traces": [{"key": "TimeDelta", "unit": "s", "fmt": "+.3f", "secondary": False, "fill": "tozeroy"}],
    },
    "speed": {
        "label": "Speed (km/h)",
        "height_px": 250,
        "traces": [{"key": "Speed", "unit": "km/h", "fmt": ".0f", "secondary": False}],
    },
    "throttle_brake": {
        "label": "Throttle / Brake",
        "height_px": 180,
        "yaxis": {"range": [-5, 105]},
        "traces": [
            {"key": "Throttle", "unit": "%", "fmt": ".0f", "secondary": False, "fill": None},
            # Brake scaled ×100 onto 0–100% axis; rendered as semi-transparent fill
            {
                "key": "Brake",
                "unit": "%",
                "fmt": ".0f",
                "secondary": False,
                "fill": "tozeroy",
                "scale": 100,
                "fill_alpha": 0.25,
            },
        ],
    },
    "rpm_gear": {
        "label": "RPM / Gear",
        "height_px": 180,
        "secondary_y": True,
        "yaxis": {"dtick": 2000},
        "secondary_yaxis": {"range": [0.5, 8.5], "dtick": 1, "tickvals": list(range(1, 9))},
        "traces": [
            {"key": "RPM", "unit": "", "fmt": ".0f", "secondary": False},
            {"key": "nGear", "unit": "", "fmt": ".0f", "secondary": True, "step": True},
        ],
    },
    "superclip": {
        "label": "Super Clip",
        "height_px": 80,
        "yaxis": {"range": [-0.1, 1.1], "dtick": 1, "tickvals": [0, 1], "ticktext": ["Off", "On"]},
        "traces": [{"key": "SuperClip", "unit": "", "fmt": ".0f", "secondary": False, "fill": "tozeroy"}],
    },
}

ALL_CHANNELS = list(CHANNEL_GROUPS.keys())


def _entry_key(entry: dict) -> str:
    """Return the column-naming key for an entry (backward-compatible with 'driver' field)."""
    return entry.get("key", entry.get("driver", ""))


def _entry_label(entry: dict) -> str:
    """Return the display label for an entry (backward-compatible with 'driver' field)."""
    return entry.get("label", entry.get("driver", ""))


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a hex color string to an rgba() CSS string."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _add_time_delta(entries: list[dict]) -> None:
    """Add TimeDelta column (float seconds vs reference driver) to each entry's telemetry.

    Convention: TimeDelta > 0 means this driver arrived later than the reference at this
    distance point (reference is faster here); TimeDelta < 0 means this driver is ahead.
    The reference driver (first entry) always receives TimeDelta = 0.
    """
    for entry in entries:
        entry["telemetry"]["TimeDelta"] = 0.0

    if len(entries) < 2:
        return

    ref_tel = entries[0]["telemetry"].sort_values("Distance").copy()
    ref_tel["_LapTime"] = (ref_tel["Time"] - ref_tel["Time"].iloc[0]).dt.total_seconds()

    for entry in entries[1:]:
        tel = entry["telemetry"]
        sorted_tel = tel.sort_values("Distance").copy()
        sorted_tel["_LapTime"] = (sorted_tel["Time"] - sorted_tel["Time"].iloc[0]).dt.total_seconds()

        aligned = pd.merge_asof(
            sorted_tel[["Distance", "_LapTime"]],
            ref_tel[["Distance", "_LapTime"]].rename(columns={"_LapTime": "_RefLapTime"}),
            on="Distance",
            direction="nearest",
        )
        delta_series = pd.Series(
            aligned["_LapTime"].values - aligned["_RefLapTime"].values,
            index=sorted_tel.index,
        )
        # Restore to original (unsorted) index order
        entry["telemetry"]["TimeDelta"] = delta_series.reindex(tel.index)


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

    cols_needed = ["Distance"] + [k for k in channel_keys if k in all_telemetry[0]["telemetry"].columns]
    key0 = _entry_key(all_telemetry[0])
    ref = all_telemetry[0]["telemetry"][cols_needed].copy()
    data_cols = [c for c in cols_needed if c != "Distance"]
    ref.columns = ["Distance"] + [f"{c}_{key0}" for c in data_cols]

    for entry in all_telemetry[1:]:
        k = _entry_key(entry)
        available = [c for c in cols_needed if c in entry["telemetry"].columns]
        other = entry["telemetry"][available].copy()
        other_data = [c for c in available if c != "Distance"]
        other.columns = ["Distance"] + [f"{c}_{k}" for c in other_data]
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
    merged: pd.DataFrame | None,
    other_labels: list[str],
    *,
    key: str | None = None,
    other_keys: list[str] | None = None,
) -> np.ndarray:
    """Build customdata array with deltas vs other entries for tooltip display."""
    if merged is None or not other_labels:
        return np.zeros((len(tel), 1))

    own_key = key if key is not None else label
    _other_keys = other_keys if other_keys is not None else other_labels

    own_col = f"{channel_key}_{own_key}"
    result_cols = []

    for other_key in _other_keys:
        other_col = f"{channel_key}_{other_key}"
        if own_col not in merged.columns or other_col not in merged.columns:
            result_cols.append(np.zeros(len(tel)))
            continue
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
    channel_label: str,
    unit: str,
    fmt: str,
    other_labels: list[str],
) -> str:
    """Build Plotly hovertemplate string with delta lines for each other entry."""
    lines = [
        f"<b>{label}</b>",
        "Distance: %{x:.0f}m",
        f"{channel_label}: %{{y:{fmt}}}{unit}",
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
    channel_names: list[str],
) -> bool:
    """Render a Plotly telemetry chart to HTML and return whether corners were drawn.

    Args:
        entries: List of entry dicts, each with:
            - 'key': column-naming identifier (no spaces)
            - 'label': display label (may contain spaces)
            - 'telemetry': DataFrame with Distance and channel columns
            - 'color': hex color string
            - 'style': line style dict with 'linestyle' and 'linewidth' keys
        circuit_info: FastF1 circuit info object (for corner annotations), or None
        output_path: Path to write the HTML file
        annotate_corners: Whether to draw corner annotations
        title: Chart title text
        channel_names: Ordered list of channel group names to render

    Returns:
        True if corner annotations were successfully drawn, False otherwise
    """
    active_groups = [CHANNEL_GROUPS[name] for name in channel_names]
    num_rows = len(channel_names)

    # Build make_subplots specs — secondary_y must be declared per row
    specs = [[{"secondary_y": grp.get("secondary_y", False)}] for grp in active_groups]
    row_heights = [grp["height_px"] for grp in active_groups]
    figure_height = sum(row_heights) + 80  # header/legend overhead

    # Collect all raw channel keys for merged telemetry (excluding computed TimeDelta)
    raw_channel_keys: list[str] = []
    for grp in active_groups:
        for trace_spec in grp["traces"]:
            k = trace_spec["key"]
            if k != "TimeDelta" and k not in raw_channel_keys:
                raw_channel_keys.append(k)

    # Include TimeDelta in merged if the delta channel is active (for hover customdata)
    merge_keys = raw_channel_keys.copy()
    if "delta" in channel_names and entries and "TimeDelta" in entries[0]["telemetry"].columns:
        merge_keys.append("TimeDelta")
    merged = _build_merged_telemetry(entries, merge_keys)

    fig = make_subplots(
        rows=num_rows,
        cols=1,
        shared_xaxes=True,
        specs=specs,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=[grp["label"] for grp in active_groups],
    )

    ref_label = _entry_label(entries[0]) if entries else ""
    delta_row: int | None = None
    if "delta" in channel_names:
        delta_row = channel_names.index("delta") + 1

    dash_map = {"-": "solid", "--": "dash"}

    for entry in entries:
        lbl = _entry_label(entry)
        k = _entry_key(entry)
        tel = entry["telemetry"]
        color = entry["color"]
        style = entry["style"]

        other_labels = [_entry_label(e) for e in entries if _entry_key(e) != k]
        other_keys = [_entry_key(e) for e in entries if _entry_key(e) != k]
        dash = dash_map.get(style["linestyle"], "solid")
        linewidth = style["linewidth"]

        for row_idx, (_group_name, grp) in enumerate(zip(channel_names, active_groups, strict=True)):
            row = row_idx + 1

            for trace_spec in grp["traces"]:
                channel_key = trace_spec["key"]
                unit = trace_spec.get("unit", "")
                fmt = trace_spec.get("fmt", ".0f")
                is_secondary = trace_spec.get("secondary", False)
                is_step = trace_spec.get("step", False)
                fill = trace_spec.get("fill", None)
                scale = trace_spec.get("scale", 1)
                fill_alpha = trace_spec.get("fill_alpha", 0.3)

                if channel_key not in tel.columns:
                    continue

                y_values = tel[channel_key] * scale if scale != 1 else tel[channel_key]

                # Gear: thinner line with reduced opacity for secondary context
                trace_linewidth = linewidth * 0.7 if is_secondary else linewidth
                trace_color = color

                # Derive fillcolor with alpha for brake/delta fills
                fillcolor = None
                if fill is not None:
                    fillcolor = _hex_to_rgba(color, fill_alpha)

                # Hover template
                if channel_key == "TimeDelta":
                    # Delta channel: simple hover showing gap value
                    hovertemplate = (
                        f"<b>{lbl}</b><br>Distance: %{{x:.0f}}m<br>Δ vs {ref_label}: %{{y:+.3f}}s<br><extra></extra>"
                    )
                    customdata = np.zeros((len(tel), 1))
                else:
                    customdata = _build_customdata(
                        lbl,
                        channel_key,
                        tel,
                        merged,
                        other_labels,
                        key=k,
                        other_keys=other_keys,
                    )
                    hovertemplate = _build_hover_template(
                        lbl,
                        grp["label"] if len(grp["traces"]) == 1 else channel_key,
                        unit,
                        fmt,
                        other_labels,
                    )

                # Show legend only once per driver (first row)
                show_legend = row == 1 and not is_secondary

                line_shape = "hv" if is_step else "linear"

                trace = go.Scatter(
                    x=tel["Distance"],
                    y=y_values,
                    name=lbl,
                    legendgroup=lbl,
                    showlegend=show_legend,
                    line={
                        "color": trace_color,
                        "width": trace_linewidth,
                        "dash": dash,
                        "shape": line_shape,
                    },
                    mode="lines",
                    fill=fill,
                    fillcolor=fillcolor,
                    customdata=customdata,
                    hovertemplate=hovertemplate,
                    opacity=0.7 if is_secondary else 1.0,
                )
                fig.add_trace(trace, row=row, col=1, secondary_y=is_secondary)

    # Zero reference line for delta panel
    if delta_row is not None:
        fig.add_hline(
            y=0,
            line_dash="dot",
            line_color=PLOTLY_DARK_THEME["zerolinecolor"],
            line_width=1.5,
            row=delta_row,
            col=1,
        )
        # Update delta y-axis title to show reference driver
        delta_yaxis_key = f"yaxis{delta_row}" if delta_row > 1 else "yaxis"
        fig.update_layout(**{delta_yaxis_key: {"title_text": f"Δ vs {ref_label} (s)"}})

    # Corner annotations
    corners_drawn = False
    if annotate_corners and circuit_info is not None:
        try:
            for _, corner in circuit_info.corners.iterrows():
                number = int(corner["Number"])
                letter = str(corner["Letter"]) if pd.notna(corner["Letter"]) and corner["Letter"] else ""
                corner_label = f"{number}{letter}"
                dist = float(corner["Distance"])

                for row in range(1, num_rows + 1):
                    fig.add_shape(
                        type="line",
                        x0=dist,
                        x1=dist,
                        y0=0,
                        y1=1,
                        yref="y domain",
                        xref="x",
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

    # Global layout
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
        height=figure_height,
    )

    # Per-row y-axis styling
    for row_idx, (_group_name, grp) in enumerate(zip(channel_names, active_groups, strict=True)):
        row = row_idx + 1
        yaxis_key = f"yaxis{row}" if row > 1 else "yaxis"
        yaxis_updates = {
            "gridcolor": PLOTLY_DARK_THEME["gridcolor"],
            "zerolinecolor": PLOTLY_DARK_THEME["zerolinecolor"],
        }
        if "yaxis" in grp:
            yaxis_updates.update(grp["yaxis"])
        fig.update_layout(**{yaxis_key: yaxis_updates})

        # Secondary y-axis styling (RPM/Gear right axis)
        if grp.get("secondary_y") and "secondary_yaxis" in grp:
            fig.update_yaxes(
                secondary_y=True,
                row=row,
                col=1,
                gridcolor=PLOTLY_DARK_THEME["gridcolor"],
                zerolinecolor=PLOTLY_DARK_THEME["zerolinecolor"],
                showgrid=False,
                **grp["secondary_yaxis"],
            )

    fig.update_xaxes(gridcolor=PLOTLY_DARK_THEME["gridcolor"])
    fig.update_xaxes(title_text="Distance (m)", row=num_rows, col=1)

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
    annotate_corners: bool = True,
    channels: list[str] | None = None,
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
        annotate_corners: Whether to add corner markers and labels (default: True)
        channels: Ordered list of channel group names to display. Defaults to
            DEFAULT_TELEMETRY_CHANNELS = ["delta", "speed", "throttle_brake", "rpm_gear"].
            Available: delta, speed, throttle_brake, rpm_gear, superclip.
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with chart metadata and telemetry statistics

    Raises:
        ValueError: If drivers list has <2 or >5 entries, or unknown channel names provided
    """
    if len(drivers) < MIN_TELEMETRY_DRIVERS:
        raise ValueError(
            f"Telemetry requires at least {MIN_TELEMETRY_DRIVERS} drivers for comparison, got {len(drivers)}"
        )
    if len(drivers) > MAX_TELEMETRY_DRIVERS:
        raise ValueError(
            f"Telemetry supports maximum {MAX_TELEMETRY_DRIVERS} drivers for readability, got {len(drivers)}"
        )

    channel_names = list(channels) if channels else list(DEFAULT_TELEMETRY_CHANNELS)
    unknown = [c for c in channel_names if c not in ALL_CHANNELS]
    if unknown:
        raise ValueError(f"Unknown channel(s): {unknown}. Available: {ALL_CHANNELS}")

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

    # Compute time delta if requested
    if "delta" in channel_names and entries:
        _add_time_delta(entries)

    circuit_info = None
    if annotate_corners:
        try:
            circuit_info = session.get_circuit_info()
        except Exception:
            logging.getLogger(__name__).warning("Failed to load circuit info for corner annotations", exc_info=True)

    title = f"{session.event['EventName']} {year} — {session.name}<br>Telemetry Comparison"
    corners_drawn = _render_telemetry_chart(entries, circuit_info, output_path, annotate_corners, title, channel_names)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "drivers_compared": [s["driver"] for s in stats],
        "channels": channel_names,
        "statistics": stats,
        "corners_annotated": corners_drawn,
        "output_format": "html",
    }
