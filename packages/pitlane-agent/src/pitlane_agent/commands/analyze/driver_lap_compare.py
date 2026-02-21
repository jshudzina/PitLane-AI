"""Generate telemetry comparison charts for a single driver across multiple laps or years.

Two public functions:
- generate_multi_lap_chart: compare specific laps within a single session
- generate_year_compare_chart: compare best laps at the same track across multiple seasons
"""

import logging
from pathlib import Path

import pandas as pd

from pitlane_agent.commands.analyze.telemetry import _format_sector_time, _render_telemetry_chart
from pitlane_agent.utils.fastf1_helpers import load_session_or_testing, pick_lap_by_spec
from pitlane_agent.utils.filename import sanitize_filename
from pitlane_agent.utils.telemetry_analysis import analyze_telemetry

_log = logging.getLogger(__name__)

MIN_ENTRIES = 2
MAX_ENTRIES = 6

# Distinct colors optimised for readability on dark backgrounds
_ENTRY_COLORS = [
    "#636EFA",  # blue
    "#EF553B",  # red-orange
    "#00CC96",  # teal
    "#AB63FA",  # purple
    "#FFA15A",  # orange
    "#19D3F3",  # cyan
]

_SOLID_STYLE = {"linestyle": "-", "linewidth": 2}


def _prepare_lap_entry(lap, label: str, key: str, color: str) -> tuple[dict, dict]:
    """Build rendering entry and stats dict for a single lap.

    Returns:
        (entry, stats) where entry is consumed by _render_telemetry_chart and
        stats is returned to the caller for downstream use.

    Raises:
        ValueError: If car data is unavailable for the lap.
    """
    tel = lap.get_car_data().add_distance()
    if tel.empty:
        raise ValueError(f"No car telemetry data available for lap labelled '{label}'")

    tel["Brake"] = tel["Brake"].astype(int)

    analysis = analyze_telemetry(tel)

    tel["SuperClip"] = 0
    for zone in analysis["super_clipping_zones"]:
        mask = (tel["Distance"] >= zone["start_distance"]) & (tel["Distance"] <= zone["end_distance"])
        tel.loc[mask, "SuperClip"] = 1

    entry = {
        "key": key,
        "label": label,
        "telemetry": tel,
        "color": color,
        "style": _SOLID_STYLE,
    }

    stats = {
        "label": label,
        "lap_number": int(lap["LapNumber"]),
        "lap_time": str(lap["LapTime"])[10:18],
        "sector_1_time": _format_sector_time(lap.get("Sector1Time")),
        "sector_2_time": _format_sector_time(lap.get("Sector2Time")),
        "sector_3_time": _format_sector_time(lap.get("Sector3Time")),
        "max_speed": float(tel["Speed"].max()),
        "avg_speed": float(tel["Speed"].mean()),
        "max_rpm": float(tel["RPM"].max()),
        "lift_coast_count": analysis["lift_coast_count"],
        "lift_coast_duration": analysis["total_lift_coast_duration"],
        "clipping_count": analysis["clipping_count"],
        "clipping_duration": analysis["total_clipping_duration"],
    }

    return entry, stats


def generate_multi_lap_chart(
    year: int,
    gp: str,
    session_type: str,
    driver: str,
    lap_specs: list[str | int],
    workspace_dir: Path,
    annotate_corners: bool = False,
) -> dict:
    """Compare multiple laps for a single driver within a session.

    Args:
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier (Q, R, FP1, FP2, FP3, S, SQ)
        driver: Driver abbreviation (e.g. "VER")
        lap_specs: List of lap specifiers — "best" for fastest lap or an integer lap number.
                   Must have between 2 and 6 entries.
        workspace_dir: Workspace directory for chart output
        annotate_corners: Whether to add corner markers

    Returns:
        Dictionary with chart path, per-lap statistics, and metadata

    Raises:
        ValueError: If fewer than 2 or more than 6 lap specs are provided,
                    or if a specified lap number does not exist
    """
    if len(lap_specs) < MIN_ENTRIES:
        raise ValueError(f"multi-lap requires at least {MIN_ENTRIES} lap specs, got {len(lap_specs)}")
    if len(lap_specs) > MAX_ENTRIES:
        raise ValueError(f"multi-lap supports at most {MAX_ENTRIES} lap specs for readability, got {len(lap_specs)}")

    session = load_session_or_testing(year, gp, session_type, telemetry=True)
    driver_laps = session.laps.pick_drivers(driver)

    if driver_laps.empty:
        raise ValueError(f"No laps found for driver {driver} in {year} {gp} {session_type}")

    entries: list[dict] = []
    lap_stats: list[dict] = []

    for i, spec in enumerate(lap_specs):
        lap = pick_lap_by_spec(driver_laps, spec)
        lap_number = int(lap["LapNumber"])

        compound = lap.get("Compound", None)
        compound_str = f" ({compound})" if compound and pd.notna(compound) else ""
        label = f"{driver} Lap {lap_number}{compound_str}"
        key = f"{driver}_L{lap_number}"
        color = _ENTRY_COLORS[i % len(_ENTRY_COLORS)]

        entry, stats = _prepare_lap_entry(lap, label, key, color)
        entries.append(entry)
        lap_stats.append(stats)

    circuit_info = None
    if annotate_corners:
        try:
            circuit_info = session.get_circuit_info()
        except Exception:
            _log.warning("Failed to load circuit info for corner annotations", exc_info=True)

    gp_sanitized = sanitize_filename(gp)
    filename = f"multi_lap_{year}_{gp_sanitized}_{session_type}_{driver}.html"
    output_path = workspace_dir / "charts" / filename

    title = f"{session.event['EventName']} {year} — {session.name}<br>{driver} Lap Comparison"
    corners_drawn = _render_telemetry_chart(entries, circuit_info, output_path, annotate_corners, title)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "gp": gp,
        "driver": driver,
        "laps": lap_stats,
        "corners_annotated": corners_drawn,
        "output_format": "html",
    }


def generate_year_compare_chart(
    gp: str,
    session_type: str,
    driver: str,
    years: list[int],
    workspace_dir: Path,
    annotate_corners: bool = False,
) -> dict:
    """Compare a driver's best lap at the same track across multiple seasons.

    Loads each session independently and picks the fastest lap for the driver.
    Circuit info is taken from the first session (same track layout assumed).

    Useful for analysing how regulation changes affect lap times, braking points,
    speed profiles, and driving technique over multiple seasons.

    Args:
        gp: Grand Prix name (same track must exist in all specified years)
        session_type: Session identifier (Q, R, FP1, FP2, FP3, S, SQ)
        driver: Driver abbreviation (e.g. "HAM")
        years: List of season years to compare. Must have between 2 and 6 entries.
        workspace_dir: Workspace directory for chart output
        annotate_corners: Whether to add corner markers

    Returns:
        Dictionary with chart path, per-year statistics, and metadata

    Raises:
        ValueError: If fewer than 2 or more than 6 years are provided,
                    or if the driver has no laps in a session
    """
    if len(years) < MIN_ENTRIES:
        raise ValueError(f"year-compare requires at least {MIN_ENTRIES} years, got {len(years)}")
    if len(years) > MAX_ENTRIES:
        raise ValueError(f"year-compare supports at most {MAX_ENTRIES} years for readability, got {len(years)}")

    entries: list[dict] = []
    year_stats: list[dict] = []
    first_session = None

    for i, year in enumerate(years):
        session = load_session_or_testing(year, gp, session_type, telemetry=True)

        if first_session is None:
            first_session = session

        driver_laps = session.laps.pick_drivers(driver)
        if driver_laps.empty:
            raise ValueError(f"No laps found for driver {driver} in {year} {gp} {session_type}")

        fastest_lap = driver_laps.pick_fastest()
        label = f"{driver} {year}"
        key = f"{driver}_{year}"
        color = _ENTRY_COLORS[i % len(_ENTRY_COLORS)]

        entry, stats = _prepare_lap_entry(fastest_lap, label, key, color)
        stats["year"] = year
        entries.append(entry)
        year_stats.append(stats)

    circuit_info = None
    if annotate_corners and first_session is not None:
        try:
            circuit_info = first_session.get_circuit_info()
        except Exception:
            _log.warning("Failed to load circuit info for corner annotations", exc_info=True)

    gp_sanitized = sanitize_filename(gp)
    years_str = "_".join(str(y) for y in sorted(years))
    filename = f"year_compare_{gp_sanitized}_{session_type}_{driver}_{years_str}.html"
    output_path = workspace_dir / "charts" / filename

    title = f"{gp} — {session_type}<br>{driver} Year-over-Year Comparison ({', '.join(str(y) for y in years)})"
    corners_drawn = _render_telemetry_chart(entries, circuit_info, output_path, annotate_corners, title)

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "gp": gp,
        "session": session_type,
        "driver": driver,
        "years": years,
        "year_stats": year_stats,
        "corners_annotated": corners_drawn,
        "output_format": "html",
    }
