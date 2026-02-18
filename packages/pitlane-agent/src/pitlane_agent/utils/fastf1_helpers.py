"""FastF1 session management utilities.

This module provides shared utilities for FastF1 session loading, cache setup,
and chart path construction used across all F1 data fetching and visualization commands.
"""

from pathlib import Path

import click
import fastf1
from fastf1.core import Lap, Session, Telemetry

from pitlane_agent.utils.fastf1_cache import get_fastf1_cache_dir
from pitlane_agent.utils.filename import sanitize_filename


def setup_fastf1_cache() -> None:
    """Initialize FastF1 cache with standard shared directory.

    Uses get_fastf1_cache_dir() from utils to ensure all commands
    share the same cache directory (~/.pitlane/cache/fastf1/).
    """
    cache_dir = get_fastf1_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def load_session(
    year: int,
    gp: str,
    session_type: str,
    telemetry: bool = False,
    weather: bool = False,
    messages: bool = False,
) -> Session:
    """Load FastF1 session with standard configuration.

    Automatically sets up cache before loading session data.

    Args:
        year: Season year (e.g., 2024)
        gp: Grand Prix name (e.g., "Monaco")
        session_type: Session identifier (R, Q, FP1, FP2, FP3, S, SQ)
        telemetry: Whether to load telemetry data (default: False)
        weather: Whether to load weather data (default: False)
        messages: Whether to load messages data (default: False)

    Returns:
        Loaded FastF1 session object

    Raises:
        Exception: If session loading fails
    """
    # Ensure cache is set up
    setup_fastf1_cache()

    # Get session
    session = fastf1.get_session(year, gp, session_type)

    # Load session data with specified options
    session.load(telemetry=telemetry, weather=weather, messages=messages)

    return session


def load_testing_session(
    year: int,
    test_number: int,
    session_number: int,
    telemetry: bool = False,
    weather: bool = False,
    messages: bool = False,
) -> Session:
    """Load FastF1 testing session with standard configuration.

    Testing sessions require a separate API from regular GP sessions.
    FastF1's get_session() cannot load testing events — it will fuzzy-match
    to an incorrect GP or reject round 0.

    Args:
        year: Season year (e.g., 2026)
        test_number: Testing event number (e.g., 1 or 2)
        session_number: Session within testing event (e.g., 1, 2, or 3)
        telemetry: Whether to load telemetry data (default: False)
        weather: Whether to load weather data (default: False)
        messages: Whether to load messages data (default: False)

    Returns:
        Loaded FastF1 session object

    Raises:
        Exception: If session loading fails
    """
    setup_fastf1_cache()

    session = fastf1.get_testing_session(year, test_number, session_number)
    session.load(telemetry=telemetry, weather=weather, messages=messages)

    return session


def load_session_or_testing(
    year: int,
    gp: str | None,
    session_type: str | None,
    test_number: int | None = None,
    session_number: int | None = None,
    telemetry: bool = False,
    weather: bool = False,
    messages: bool = False,
) -> Session:
    """Load either a regular GP session or a testing session.

    Dispatches to load_testing_session when test_number/session_number are
    provided, otherwise falls back to load_session.

    Args:
        year: Season year
        gp: Grand Prix name (for regular sessions)
        session_type: Session identifier (for regular sessions)
        test_number: Testing event number (for testing sessions)
        session_number: Session within testing event (for testing sessions)
        telemetry: Whether to load telemetry data
        weather: Whether to load weather data
        messages: Whether to load messages data

    Returns:
        Loaded FastF1 session object
    """
    if test_number is not None and session_number is not None:
        return load_testing_session(
            year, test_number, session_number, telemetry=telemetry, weather=weather, messages=messages
        )
    return load_session(year, gp, session_type, telemetry=telemetry, weather=weather, messages=messages)


def validate_session_or_test(
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
) -> tuple[bool, bool]:
    """Validate that either --gp/--session or --test/--day is provided, not both.

    Returns:
        Tuple of (has_gp, has_test) booleans.

    Raises:
        click.UsageError: If validation fails.
    """
    has_gp = gp is not None and session is not None
    has_test = test_number is not None and session_number is not None
    if not has_gp and not has_test:
        raise click.UsageError("Must provide either --gp and --session, or --test and --day")
    if has_gp and has_test:
        raise click.UsageError("Cannot use --gp/--session with --test/--day")
    return has_gp, has_test


def build_chart_path(
    workspace_dir: Path,
    chart_type: str,
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str] | None = None,
    test_number: int | None = None,
    session_number: int | None = None,
    extension: str = "png",
) -> Path:
    """Construct standardized chart output path.

    Handles driver list formatting to prevent overly long filenames.
    Creates charts/ subdirectory within workspace if it doesn't exist.

    Args:
        workspace_dir: Workspace base directory
        chart_type: Type of chart (e.g., "lap_times", "tyre_strategy")
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (ignored for testing sessions)
        drivers: Optional list of driver abbreviations (for driver-specific charts)
        test_number: Testing event number (for testing sessions)
        session_number: Session within testing event (for testing sessions)
        extension: File extension for output (default: "png")

    Returns:
        Path object for chart output location
    """
    # Build session identifier portion of filename
    if test_number is not None and session_number is not None:
        session_id = f"{year}_test{test_number}_day{session_number}"
    else:
        gp_sanitized = sanitize_filename(gp)
        session_id = f"{year}_{gp_sanitized}_{session_type}"

    # Format driver list for filename
    if drivers:
        # Prevent excessive filename length with many drivers
        drivers_str = f"{len(drivers)}drivers" if len(drivers) > 5 else "_".join(sorted(drivers))
        filename = f"{chart_type}_{session_id}_{drivers_str}.{extension}"
    else:
        filename = f"{chart_type}_{session_id}.{extension}"

    return workspace_dir / "charts" / filename


def build_data_path(
    workspace_dir: Path,
    data_type: str,
    year: int | None = None,
    gp: str | None = None,
    session_type: str | None = None,
    round_number: int | None = None,
    driver_code: str | None = None,
    season: int | None = None,
    test_number: int | None = None,
    session_number: int | None = None,
) -> Path:
    """Construct standardized data output path.

    Creates unique filenames for fetch command outputs to prevent overwrites
    when fetching different sessions. Follows similar pattern to build_chart_path().

    Args:
        workspace_dir: Workspace base directory
        data_type: Type of data (e.g., "session_info", "driver_standings")
        year: Season year (for session-scoped or year-scoped data)
        gp: Grand Prix name (for session-scoped data)
        session_type: Session identifier (for session-scoped data)
        round_number: Round number (for round-scoped standings)
        driver_code: Driver code (for driver-scoped data)
        season: Season year for driver data
        test_number: Testing event number (for testing sessions)
        session_number: Session within testing event (for testing sessions)

    Returns:
        Path object for data output location (in workspace/data/ subdirectory)
    """
    parts = [data_type]

    if year is not None and test_number is not None and session_number is not None:
        # Testing session-scoped
        parts.extend([str(year), f"test{test_number}", f"day{session_number}"])
    elif year is not None and gp is not None and session_type is not None:
        # Session-scoped: session_info, race_control
        parts.extend([str(year), sanitize_filename(gp), session_type])
    elif year is not None and round_number is not None:
        # Year+round-scoped: standings at a specific round
        parts.extend([str(year), f"round{round_number}"])
    elif year is not None:
        # Year-scoped: schedule, season_summary, final standings
        parts.append(str(year))
    elif driver_code is not None and season is not None:
        # Driver+season-scoped
        parts.extend([driver_code.lower(), str(season)])
    elif driver_code is not None:
        # Driver-scoped (all seasons)
        parts.append(driver_code.lower())

    filename = "_".join(parts) + ".json"
    return workspace_dir / "data" / filename


def get_merged_telemetry(lap: Lap, required_channels: list[str] | None = None) -> Telemetry:
    """Get merged telemetry with validation.

    Uses FastF1's get_telemetry() which merges position and car data with proper
    interpolation to handle different sampling rates between telemetry channels.

    This prevents gaps in visualizations caused by misaligned timestamps when
    manually merging get_pos_data() and get_car_data() with inner joins.

    Args:
        lap: FastF1 Lap object
        required_channels: Optional list of required column names to validate

    Returns:
        DataFrame-like telemetry object with merged data (X, Y, Speed, nGear, etc.)

    Raises:
        ValueError: If telemetry is empty or required channels are missing

    Example:
        >>> telemetry = get_merged_telemetry(fastest_lap, required_channels=["X", "Y", "nGear"])
        >>> print(telemetry[["X", "Y", "nGear"]].head())
    """
    telemetry = lap.get_telemetry()

    if telemetry.empty:
        raise ValueError("No telemetry data available for lap")

    if required_channels:
        missing = [col for col in required_channels if col not in telemetry.columns]
        if missing:
            raise ValueError(f"Missing required telemetry channels: {missing}")

    return telemetry
