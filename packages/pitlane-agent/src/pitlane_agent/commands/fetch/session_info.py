"""Get F1 session information from FastF1.

Usage:
    pitlane session-info --year 2024 --gp Monaco --session R

    # Or using module invocation
    python -m pitlane_agent.commands.fetch.session_info --year 2024 --gp Monaco --session R
"""

import contextlib
from typing import TypedDict

import pandas as pd
from fastf1.core import Session
from fastf1.exceptions import DataNotLoadedError

from pitlane_agent.utils.constants import (
    TRACK_STATUS_RED_FLAG,
    TRACK_STATUS_SAFETY_CAR,
    TRACK_STATUS_VSC_DEPLOYED,
)
from pitlane_agent.utils.fastf1_helpers import load_session, load_testing_session
from pitlane_agent.utils.race_stats import (
    RaceSummaryStats,
    compute_race_summary_stats,
    get_circuit_length_km,
)


class DriverInfo(TypedDict):
    """Information about a single driver's session result."""

    abbreviation: str
    name: str
    team: str
    number: int | None
    position: int | None
    grid_position: int | None
    classified_position: str | None  # Human-readable: "1st", "Retired", "Disqualified", etc.
    status: str | None               # FastF1 Status: "+1 Lap", "Engine", "Finished", etc.
    race_time: str | None            # Winner's total race time; gap to leader for all other finishers (race/sprint only)
    points: float | None
    q1_time: str | None              # Best lap in Q1 segment (Q/SQ sessions); null means did not participate
    q2_time: str | None              # Best lap in Q2 segment (Q/SQ sessions); null means eliminated in Q1
    q3_time: str | None              # Best lap in Q3 segment (Q/SQ sessions); null means eliminated before Q3


class RaceConditions(TypedDict):
    """Race condition counts."""

    num_safety_cars: int
    num_virtual_safety_cars: int
    num_red_flags: int


class WeatherStats(TypedDict):
    """Statistics for a single weather metric."""

    min: float | None
    max: float | None
    avg: float | None


class WeatherData(TypedDict):
    """Weather statistics for the session.

    Units:
        - air_temp: degrees Celsius
        - track_temp: degrees Celsius
        - humidity: percentage (0-100)
        - pressure: hectopascals (hPa)
        - wind_speed: meters per second (m/s)
    """

    air_temp: WeatherStats
    track_temp: WeatherStats
    humidity: WeatherStats
    pressure: WeatherStats
    wind_speed: WeatherStats
    rain_percentage: float | None


class SessionInfo(TypedDict):
    """Complete session information including metadata, drivers, race conditions, and weather.

    This is the return type for get_session_info().
    """

    year: int
    event_name: str
    country: str
    session_type: str
    session_name: str
    date: str | None
    total_laps: int | None
    circuit_length_km: float | None
    race_conditions: RaceConditions | None
    weather: WeatherData | None
    race_summary: RaceSummaryStats | None
    drivers: list[DriverInfo]


# Mapping of FastF1 ClassifiedPosition codes to plain English.
_CLASSIFIED_POSITION_MAP: dict[str, str] = {
    "R": "Retired",
    "D": "Disqualified",
    "E": "Excluded",
    "W": "Withdrawn",
    "F": "Failed to Qualify",
    "N": "Not Classified",
}


def _ordinal(n: int) -> str:
    """Return the ordinal string for a positive integer (e.g. 1 → '1st', 11 → '11th')."""
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_classified_position(val: object) -> str | None:
    """Convert a FastF1 ClassifiedPosition value to plain English.

    Examples:
        1 / "1" → "1st"
        "R"     → "Retired"
        "D"     → "Disqualified"
        NaN     → None
    """
    try:
        if pd.isna(val):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if s in _CLASSIFIED_POSITION_MAP:
        return _CLASSIFIED_POSITION_MAP[s]
    try:
        return _ordinal(int(float(s)))
    except (ValueError, TypeError):
        return s or None


def _format_finish_time(val: object) -> str | None:
    """Format a timedelta race time as 'H:MM:SS.sss' (or 'M:SS.sss' if under an hour).

    Returns None for NaT or non-timedelta values.
    """
    try:
        if pd.isna(val):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    try:
        total_seconds = pd.Timedelta(val).total_seconds()  # type: ignore[arg-type]
    except Exception:
        return None
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:06.3f}"
    return f"{minutes}:{seconds:06.3f}"


def _nonempty_str(val: object) -> str | None:
    """Return val as a string, or None if it is NaN/NaT or an empty string."""
    try:
        if pd.isna(val):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    return s or None


def _extract_track_status(session: Session) -> RaceConditions | None:
    """Extract race condition counts from track status data.

    Args:
        session: FastF1 session object

    Returns:
        Dict with num_safety_cars, num_virtual_safety_cars, num_red_flags
        or None if track status data is unavailable
    """
    try:
        track_status = session.track_status

        num_safety_cars = len(track_status[track_status["Status"] == TRACK_STATUS_SAFETY_CAR])
        num_red_flags = len(track_status[track_status["Status"] == TRACK_STATUS_RED_FLAG])
        # Count VSC as deployments, not endings
        num_virtual_safety_cars = len(track_status[track_status["Status"] == TRACK_STATUS_VSC_DEPLOYED])

        return {
            "num_safety_cars": num_safety_cars,
            "num_virtual_safety_cars": num_virtual_safety_cars,
            "num_red_flags": num_red_flags,
        }
    except DataNotLoadedError:
        return None


def _extract_weather_data(session: Session) -> WeatherData | None:
    """Extract weather statistics from session weather data.

    Args:
        session: FastF1 session object

    Returns:
        Dict with min/max/avg for air_temp, humidity, pressure, wind_speed
        or None if weather data is unavailable
    """
    try:
        weather: pd.DataFrame = session.weather_data

        if weather.empty:
            return None

        def get_stats(column_name: str) -> WeatherStats:
            """Return min/max/avg for a column, handling missing data."""
            if column_name not in weather.columns:
                return {"min": None, "max": None, "avg": None}

            col = weather[column_name]
            col_clean = col.dropna()

            if col_clean.empty:
                return {"min": None, "max": None, "avg": None}

            return {
                "min": round(float(col_clean.min()), 2),
                "max": round(float(col_clean.max()), 2),
                "avg": round(float(col_clean.mean()), 2),
            }

        rain_percentage = None
        if "Rainfall" in weather.columns:
            rainfall_col = weather["Rainfall"].dropna()
            if not rainfall_col.empty:
                rain_percentage = round(float(rainfall_col.mean()) * 100, 2)

        return {
            "air_temp": get_stats("AirTemp"),
            "track_temp": get_stats("TrackTemp"),
            "humidity": get_stats("Humidity"),
            "pressure": get_stats("Pressure"),
            "wind_speed": get_stats("WindSpeed"),
            "rain_percentage": rain_percentage,
        }
    except DataNotLoadedError:
        return None


def get_session_info(
    year: int,
    gp: str | None = None,
    session_type: str | None = None,
    test_number: int | None = None,
    session_number: int | None = None,
) -> SessionInfo:
    """Load session info from FastF1 and return as dict.

    For regular GP sessions, provide gp and session_type.
    For testing sessions, provide test_number and session_number.

    Args:
        year: Season year (e.g., 2024)
        gp: Grand Prix name (e.g., "Monaco", "Silverstone")
        session_type: Session identifier (R, Q, FP1, FP2, FP3, S, SQ)
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)

    Returns:
        Dictionary with session metadata, driver info, race conditions, and weather statistics.
        Race conditions include counts of safety cars, virtual safety cars, and red flags.
        Weather includes min/max/avg for air temperature, humidity, pressure, and wind speed.
    """
    resolved_session_type: str
    if test_number is not None and session_number is not None:
        session = load_testing_session(year, test_number, session_number, weather=True, messages=True)
        resolved_session_type = session.name  # e.g., "Practice 1"
    else:
        session = load_session(year, gp, session_type, weather=True, messages=True)
        assert session_type is not None, "session_type required for GP sessions"
        resolved_session_type = session_type

    drivers: list[DriverInfo] = []
    for _, driver in session.results.iterrows():
        drivers.append(
            {
                "abbreviation": driver["Abbreviation"],
                "name": f"{driver['FirstName']} {driver['LastName']}",
                "team": driver["TeamName"],
                "number": int(driver.get("DriverNumber")) if pd.notna(driver.get("DriverNumber")) else None,
                "position": int(driver.get("Position")) if pd.notna(driver.get("Position")) else None,
                "grid_position": int(driver.get("GridPosition")) if pd.notna(driver.get("GridPosition")) else None,
                "classified_position": _format_classified_position(driver.get("ClassifiedPosition")),
                "status": _nonempty_str(driver.get("Status")),
                "race_time": _format_finish_time(driver.get("Time")),
                "points": float(driver.get("Points")) if pd.notna(driver.get("Points")) else None,
                "q1_time": _format_finish_time(driver.get("Q1")),
                "q2_time": _format_finish_time(driver.get("Q2")),
                "q3_time": _format_finish_time(driver.get("Q3")),
            }
        )

    race_conditions = _extract_track_status(session)
    weather = _extract_weather_data(session)

    race_summary = None
    if resolved_session_type in ("R", "S"):
        race_summary = compute_race_summary_stats(session)

    total_laps = None
    with contextlib.suppress(DataNotLoadedError):
        total_laps = None if pd.isna(session.total_laps) else int(session.total_laps)

    circuit_length_km = get_circuit_length_km(session)

    return {
        "year": year,
        "event_name": session.event["EventName"],
        "country": session.event["Country"],
        "session_type": resolved_session_type,
        "session_name": session.name,
        "date": str(session.date.date()) if pd.notna(session.date) else None,
        "total_laps": total_laps,
        "circuit_length_km": circuit_length_km,
        "race_conditions": race_conditions,
        "weather": weather,
        "race_summary": race_summary,
        "drivers": drivers,
    }
