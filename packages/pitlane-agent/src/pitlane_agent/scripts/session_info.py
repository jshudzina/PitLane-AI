"""Get F1 session information from FastF1.

Usage:
    pitlane session-info --year 2024 --gp Monaco --session R

    # Or using module invocation
    python -m pitlane_agent.scripts.session_info --year 2024 --gp Monaco --session R
"""

import contextlib
from pathlib import Path
from typing import TypedDict

import fastf1
import pandas as pd
from fastf1.core import DataNotLoadedError, Session


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
    """Weather statistics for the session."""

    air_temp: WeatherStats
    humidity: WeatherStats
    pressure: WeatherStats
    wind_speed: WeatherStats


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

        # Count occurrences of each status code
        # Status '4': Safety Car
        # Status '5': Red Flag
        # Status '6': Virtual Safety Car deployed
        # Status '7': Virtual Safety Car ending
        num_safety_cars = len(track_status[track_status["Status"] == "4"])
        num_red_flags = len(track_status[track_status["Status"] == "5"])

        # Count VSC as deployments (status '6'), not endings ('7')
        num_virtual_safety_cars = len(track_status[track_status["Status"] == "6"])

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

        # Check if DataFrame is empty
        if weather.empty:
            return None

        # Calculate statistics for each metric
        def get_stats(column_name: str):
            """Get min, max, avg for a column, handling missing data."""
            if column_name not in weather.columns:
                return {"min": None, "max": None, "avg": None}

            col = weather[column_name]
            # Filter out NaN values
            col_clean = col.dropna()

            if col_clean.empty:
                return {"min": None, "max": None, "avg": None}

            return {
                "min": round(float(col_clean.min()), 2),
                "max": round(float(col_clean.max()), 2),
                "avg": round(float(col_clean.mean()), 2),
            }

        return {
            "air_temp_celsius": get_stats("AirTemp"),
            "track_temp_celsius": get_stats("TrackTemp"),
            "humidity": get_stats("Humidity"),
            "pressure": get_stats("Pressure"),
            "wind_speed_mps": get_stats("WindSpeed"),
        }
    except DataNotLoadedError:
        return None


def get_session_info(year: int, gp: str, session_type: str) -> dict:
    """Load session info from FastF1 and return as dict.

    Args:
        year: Season year (e.g., 2024)
        gp: Grand Prix name (e.g., "Monaco", "Silverstone")
        session_type: Session identifier (R, Q, FP1, FP2, FP3, S, SQ)

    Returns:
        Dictionary with session metadata, driver info, race conditions, and weather statistics.
        Race conditions include counts of safety cars, virtual safety cars, and red flags.
        Weather includes min/max/avg for air temperature, humidity, pressure, and wind speed.
    """

    # Enable FastF1 cache with shared directory
    cache_dir = Path.home() / ".pitlane" / "cache" / "fastf1"
    fastf1.Cache.enable_cache(str(cache_dir))

    # Load the session
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=True, messages=True)

    # Get driver info
    drivers = []
    for _, driver in session.results.iterrows():
        drivers.append(
            {
                "abbreviation": driver["Abbreviation"],
                "name": f"{driver['FirstName']} {driver['LastName']}",
                "team": driver["TeamName"],
                "number": int(driver["DriverNumber"]) if pd.notna(driver["DriverNumber"]) else None,
                "position": int(driver["Position"]) if pd.notna(driver["Position"]) else None,
            }
        )

    # Extract race conditions and weather data
    race_conditions = _extract_track_status(session)
    weather = _extract_weather_data(session)

    total_laps = None
    with contextlib.suppress(DataNotLoadedError):
        total_laps = None if pd.isna(session.total_laps) else int(session.total_laps)

    return {
        "year": year,
        "event_name": session.event["EventName"],
        "country": session.event["Country"],
        "session_type": session_type,
        "session_name": session.name,
        "date": str(session.date.date()) if pd.notna(session.date) else None,
        "total_laps": total_laps,
        "drivers": drivers,
        "race_conditions": race_conditions,
        "weather": weather,
    }
