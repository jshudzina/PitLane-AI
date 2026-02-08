"""FastF1 session management utilities.

This module provides shared utilities for FastF1 session loading, cache setup,
and chart path construction used across all F1 data fetching and visualization commands.
"""

from pathlib import Path

import fastf1

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
) -> fastf1.core.Session:
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


def build_chart_path(
    workspace_dir: Path,
    chart_type: str,
    year: int,
    gp: str,
    session_type: str,
    drivers: list[str] | None = None,
) -> Path:
    """Construct standardized chart output path.

    Handles driver list formatting to prevent overly long filenames.
    Creates charts/ subdirectory within workspace if it doesn't exist.

    Args:
        workspace_dir: Workspace base directory
        chart_type: Type of chart (e.g., "lap_times", "tyre_strategy")
        year: Season year
        gp: Grand Prix name
        session_type: Session identifier
        drivers: Optional list of driver abbreviations (for driver-specific charts)

    Returns:
        Path object for chart output location
    """
    gp_sanitized = sanitize_filename(gp)

    # Format driver list for filename
    if drivers:
        # Prevent excessive filename length with many drivers
        drivers_str = f"{len(drivers)}drivers" if len(drivers) > 5 else "_".join(sorted(drivers))
        filename = f"{chart_type}_{year}_{gp_sanitized}_{session_type}_{drivers_str}.png"
    else:
        filename = f"{chart_type}_{year}_{gp_sanitized}_{session_type}.png"

    return workspace_dir / "charts" / filename
