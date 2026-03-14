"""Shared race statistics computation utilities.

Provides position change, volatility, and pit stop statistics
decoupled from visualization logic. Used by both session_info
and position_changes commands.
"""

from typing import TypedDict

import numpy as np
from fastf1.core import Session
from fastf1.exceptions import DataNotLoadedError

from pitlane_agent.utils.circuits import lookup_circuit_length_km
from pitlane_agent.utils.constants import (
    TRACK_STATUS_RED_FLAG,
    TRACK_STATUS_SAFETY_CAR,
    TRACK_STATUS_VSC_DEPLOYED,
)


class DriverPositionStats(TypedDict):
    """Position statistics for a single driver."""

    driver: str
    start_position: int
    finish_position: int
    net_change: int
    overtakes: int
    times_overtaken: int
    biggest_gain: int
    biggest_loss: int
    volatility: float
    total_laps: int
    pit_stops: int


class RaceSummaryStats(TypedDict):
    """Aggregate race statistics across all drivers."""

    total_overtakes: int
    total_position_changes: int
    average_volatility: float
    mean_pit_stops: float
    total_laps: int


def get_circuit_length_km(session: Session) -> float | None:
    """Compute circuit lap distance in kilometres.

    Uses a three-tier lookup:
    1. FastF1 telemetry from the fastest lap (available for 2018+)
    2. Static Wikipedia-sourced reference table keyed by session.event["Location"]
    3. Returns None (caller falls back to AVG_CIRCUIT_LENGTH_KM)

    Args:
        session: FastF1 session object with laps loaded

    Returns:
        Circuit length in km rounded to 3 decimal places, or None
    """
    # Tier 1: telemetry-derived length
    try:
        fastest = session.laps.pick_fastest()
        if fastest is not None:
            telemetry = fastest.get_car_data().add_distance()
            if not telemetry.empty and "Distance" in telemetry.columns:
                return round(telemetry["Distance"].max() / 1000, 3)
    except Exception:
        pass

    # Tier 2: static Wikipedia lookup via session.event["Location"]
    try:
        location = session.event["Location"]
        if location:
            result = lookup_circuit_length_km(str(location))
            if result is not None:
                return result
    except Exception:
        pass

    return None


def count_track_interruptions(session: Session) -> tuple[int, int, int]:
    """Count safety cars, VSCs, and red flags from track status data.

    Returns:
        Tuple of (safety_cars, virtual_safety_cars, red_flags)
    """
    try:
        track_status = session.track_status
        safety_cars = len(track_status[track_status["Status"] == TRACK_STATUS_SAFETY_CAR])
        vscs = len(track_status[track_status["Status"] == TRACK_STATUS_VSC_DEPLOYED])
        red_flags = len(track_status[track_status["Status"] == TRACK_STATUS_RED_FLAG])
        return safety_cars, vscs, red_flags
    except (DataNotLoadedError, KeyError):
        return 0, 0, 0


def get_grid_position(driver_abbr: str, session: Session) -> int | None:
    """Get the qualifying/grid position for a driver from session results.

    Args:
        driver_abbr: Driver abbreviation (e.g., 'VER', 'HAM')
        session: FastF1 session object

    Returns:
        Grid position as integer, or None if unavailable
    """
    try:
        results = session.results
        if results is None or results.empty or "GridPosition" not in results.columns:
            return None
        row = results[results["Abbreviation"] == driver_abbr]
        if row.empty:
            return None
        gp = float(row["GridPosition"].iloc[0])
        if np.isnan(gp) or gp <= 0:
            return None
        return int(gp)
    except Exception:
        return None


def compute_driver_position_stats(driver_abbr: str, session: Session) -> DriverPositionStats | None:
    """Compute position statistics for a single driver.

    Args:
        driver_abbr: Driver abbreviation (e.g., 'VER', 'HAM')
        session: FastF1 session object with laps loaded

    Returns:
        Dictionary with driver position statistics, or None if no data available
    """
    driver_laps = session.laps.pick_drivers(driver_abbr)

    if driver_laps.empty:
        return None

    position_data = driver_laps[["LapNumber", "Position"]].copy()
    position_data = position_data.dropna(subset=["Position"])

    if position_data.empty:
        return None

    positions = position_data["Position"].values
    grid_position = get_grid_position(driver_abbr, session)
    start_position = float(grid_position) if grid_position is not None else float(positions[0])
    finish_position = float(positions[-1])

    # Include grid→Lap1 transition in diff calculations when grid position is available
    positions_with_start = np.concatenate([[start_position], positions]) if grid_position is not None else positions
    position_changes = np.diff(positions_with_start)

    overtakes = int(np.sum(position_changes < 0))
    times_overtaken = int(np.sum(position_changes > 0))
    volatility = float(np.std(positions))
    biggest_gain = int(abs(np.min(position_changes))) if len(position_changes) > 0 else 0
    biggest_loss = int(abs(np.max(position_changes))) if len(position_changes) > 0 else 0

    pit_laps = driver_laps[driver_laps["PitOutTime"].notna()]["LapNumber"].values

    return {
        "driver": driver_abbr,
        "start_position": int(start_position),
        "finish_position": int(finish_position),
        "net_change": int(start_position - finish_position),
        "overtakes": overtakes,
        "times_overtaken": times_overtaken,
        "biggest_gain": biggest_gain,
        "biggest_loss": biggest_loss,
        "volatility": round(volatility, 2),
        "total_laps": len(position_data),
        "pit_stops": len(pit_laps),
    }


def compute_race_summary_stats(session: Session) -> RaceSummaryStats | None:
    """Compute aggregate race statistics from a loaded session.

    Args:
        session: FastF1 session object with laps loaded

    Returns:
        Dictionary with aggregate stats, or None if laps data is unavailable
    """
    try:
        laps = session.laps
        if laps.empty:
            return None
    except DataNotLoadedError:
        return None

    driver_abbrs = [session.get_driver(d)["Abbreviation"] for d in session.drivers]

    stats = []
    for abbr in driver_abbrs:
        driver_stats = compute_driver_position_stats(abbr, session)
        if driver_stats is not None:
            stats.append(driver_stats)

    if not stats:
        return None

    total_overtakes = sum(s["overtakes"] for s in stats)
    total_position_changes = sum(abs(s["net_change"]) for s in stats)
    avg_volatility = sum(s["volatility"] for s in stats) / len(stats)
    mean_pit_stops = sum(s["pit_stops"] for s in stats) / len(stats)
    total_laps = max(s["total_laps"] for s in stats)

    return {
        "total_overtakes": total_overtakes,
        "total_position_changes": total_position_changes,
        "average_volatility": round(avg_volatility, 2),
        "mean_pit_stops": round(mean_pit_stops, 2),
        "total_laps": total_laps,
    }


def compute_race_summary_stats_from_results(session: Session) -> RaceSummaryStats | None:
    """Compute partial race stats from session.results when lap data is unavailable (pre-2018).

    Computes total_position_changes and total_overtakes as net position changes from
    grid to finish. Note: total_overtakes is a net-gain proxy (sum of positive net changes)
    — it undercounts vs lap-by-lap tracking but is far better than 0.
    average_volatility and mean_pit_stops cannot be computed without lap data and are 0.0.

    Args:
        session: FastF1 session object

    Returns:
        Dictionary with partial stats, or None if results data is unavailable
    """
    try:
        results = session.results
        if results is None or results.empty:
            return None
        if "GridPosition" not in results.columns or "Position" not in results.columns:
            return None

        # Filter to rows with valid grid positions (>0, not NaN) and valid finish positions
        valid = results[results["GridPosition"].notna() & (results["GridPosition"] > 0) & results["Position"].notna()]

        total_position_changes = int((valid["GridPosition"] - valid["Position"]).abs().sum())
        total_overtakes = int((valid["GridPosition"] - valid["Position"]).clip(lower=0).sum())

        total_laps = 0
        if "Laps" in results.columns:
            laps_series = results["Laps"].dropna()
            if not laps_series.empty:
                total_laps = int(laps_series.max())

        return {
            "total_overtakes": total_overtakes,
            "total_position_changes": total_position_changes,
            "average_volatility": 0.0,
            "mean_pit_stops": 0.0,
            "total_laps": total_laps,
        }
    except Exception:
        return None
