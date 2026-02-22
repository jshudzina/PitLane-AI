"""Fetch per-lap data for a single driver from a session.

Returns structured JSON with lap times, tyre compounds, stint info, pit events,
and position data — no chart generated. Use this to select meaningful laps for
multi-lap telemetry analysis.
"""

import logging

import pandas as pd

from pitlane_agent.utils.fastf1_helpers import format_lap_time, format_sector_time, load_session_or_testing

_log = logging.getLogger(__name__)


def _safe_int(value) -> int | None:
    """Convert to int, returning None for NaN/NaT."""
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> float | None:
    """Convert to float, returning None for NaN/NaT."""
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_stint_numbers(driver_laps: pd.DataFrame) -> list[int | None]:
    """Compute stint numbers from compound changes when FastF1 Stint column is absent.

    A new stint begins whenever the compound changes or a pit-out lap is detected.
    """
    stints: list[int | None] = []
    current_stint = 1
    prev_compound = None

    for _, lap in driver_laps.iterrows():
        compound = lap.get("Compound")
        pit_out = lap.get("PitOutTime")

        is_pit_out = not pd.isna(pit_out) if pit_out is not None else False
        compound_val = compound if (compound is not None and not pd.isna(compound)) else None

        if prev_compound is not None and compound_val != prev_compound:
            current_stint += 1
        elif is_pit_out and stints:
            # Pit-out on same compound (e.g. minor repair) counts as new stint
            current_stint += 1

        stints.append(current_stint)
        if compound_val is not None:
            prev_compound = compound_val

    return stints


def generate_driver_lap_list(
    year: int,
    gp: str | None,
    session_type: str | None,
    driver: str,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Return structured per-lap data for a single driver.

    Does not load telemetry — uses session.laps only, making this fast.

    Args:
        year: Season year
        gp: Grand Prix name (None when using testing session)
        session_type: Session identifier (Q, R, FP1, FP2, FP3, S, SQ; None for testing)
        driver: Driver abbreviation (e.g. "VER")
        test_number: Testing event number (mutually exclusive with gp/session_type)
        session_number: Day/session within testing event

    Returns:
        Dictionary with per-lap data, pit stop summary, and session metadata.

    Raises:
        ValueError: If the driver has no laps in the session.
    """
    session = load_session_or_testing(
        year, gp, session_type, telemetry=False, test_number=test_number, session_number=session_number
    )
    driver_laps = session.laps.pick_drivers(driver)

    if driver_laps.empty:
        session_desc = (
            f"testing event {test_number} day {session_number}" if test_number is not None else f"{gp} {session_type}"
        )
        raise ValueError(f"No laps found for driver {driver} in {year} {session_desc}")

    # Use FastF1 Stint column when available and populated
    has_stint_col = "Stint" in driver_laps.columns and driver_laps["Stint"].notna().any()
    stint_numbers = driver_laps["Stint"].tolist() if has_stint_col else _compute_stint_numbers(driver_laps)

    # Build per-lap list
    laps_out: list[dict] = []
    prev_position: int | None = None

    for i, (_, lap) in enumerate(driver_laps.iterrows()):
        lap_time_td = lap.get("LapTime")
        lap_time_str = format_lap_time(lap_time_td)
        lap_time_sec = None if pd.isna(lap_time_td) else float(lap_time_td.total_seconds())

        compound = lap.get("Compound")
        compound_val = compound if (compound is not None and not pd.isna(compound)) else None

        tyre_life = _safe_int(lap.get("TyreLife"))

        stint_raw = stint_numbers[i]
        stint_val = _safe_int(stint_raw)

        pit_out = lap.get("PitOutTime")
        pit_in = lap.get("PitInTime")
        is_pit_out_lap = not pd.isna(pit_out) if pit_out is not None else False
        is_pit_in_lap = not pd.isna(pit_in) if pit_in is not None else False

        is_accurate_raw = lap.get("IsAccurate")
        is_accurate = bool(is_accurate_raw) if is_accurate_raw is not None and not pd.isna(is_accurate_raw) else False

        position = _safe_int(lap.get("Position"))
        position_change = prev_position - position if position is not None and prev_position is not None else 0
        if position is not None:
            prev_position = position

        laps_out.append(
            {
                "lap_number": _safe_int(lap["LapNumber"]),
                "lap_time": lap_time_str,
                "lap_time_seconds": lap_time_sec,
                "compound": compound_val,
                "tyre_life": tyre_life,
                "stint_number": stint_val,
                "is_pit_out_lap": is_pit_out_lap,
                "is_pit_in_lap": is_pit_in_lap,
                "is_accurate": is_accurate,
                "position": position,
                "position_change": position_change,
                "sector_1_time": format_sector_time(lap.get("Sector1Time")),
                "sector_2_time": format_sector_time(lap.get("Sector2Time")),
                "sector_3_time": format_sector_time(lap.get("Sector3Time")),
            }
        )

    # Derive pit stops from stint transitions
    pit_stops: list[dict] = []
    prev_compound: str | None = None
    prev_stint: int | None = None

    for lap_entry in laps_out:
        current_compound = lap_entry["compound"]
        current_stint = lap_entry["stint_number"]

        if prev_stint is not None and current_stint is not None and current_stint != prev_stint:
            pit_stops.append(
                {
                    "lap_number": lap_entry["lap_number"],
                    "from_compound": prev_compound,
                    "to_compound": current_compound,
                }
            )

        if current_compound is not None:
            prev_compound = current_compound
        if current_stint is not None:
            prev_stint = current_stint

    # Fastest lap number (minimum LapTime)
    valid_times = driver_laps[driver_laps["LapTime"].notna()]
    fastest_lap_number = (
        _safe_int(valid_times.loc[valid_times["LapTime"].idxmin(), "LapNumber"]) if not valid_times.empty else None
    )

    return {
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "gp": gp,
        "driver": driver,
        "total_laps": len(laps_out),
        "fastest_lap_number": fastest_lap_number,
        "laps": laps_out,
        "pit_stops": pit_stops,
    }
