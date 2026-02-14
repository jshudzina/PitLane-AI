"""Shared race statistics computation utilities.

Provides position change, volatility, and pit stop statistics
decoupled from visualization logic. Used by both session_info
and position_changes commands.
"""

from typing import TypedDict

import numpy as np
from fastf1.core import Session
from fastf1.exceptions import DataNotLoadedError


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
    start_position = float(positions[0])
    finish_position = float(positions[-1])
    position_changes = np.diff(positions)

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

    return {
        "total_overtakes": total_overtakes,
        "total_position_changes": total_position_changes,
        "average_volatility": round(avg_volatility, 2),
        "mean_pit_stops": round(mean_pit_stops, 2),
    }
