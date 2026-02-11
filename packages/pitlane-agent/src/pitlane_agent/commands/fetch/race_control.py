"""Get F1 race control messages from FastF1.

Usage:
    pitlane fetch race-control --workspace-id WORKSPACE_ID --year 2024 --gp Monaco --session R

    # Or using module invocation
    python -m pitlane_agent.commands.fetch.race_control --year 2024 --gp Monaco --session R
"""

from typing import TypedDict

import pandas as pd

from pitlane_agent.utils.constants import (
    FLAG_CHEQUERED,
    FLAG_DOUBLE_YELLOW,
    FLAG_GREEN,
    FLAG_RED,
    MESSAGE_CATEGORY_DRS,
    MESSAGE_CATEGORY_SAFETY_CAR,
)
from pitlane_agent.utils.fastf1_helpers import load_session


class RaceControlMessage(TypedDict):
    """A single race control message.

    Fields:
        lap: Lap number when message occurred (1-based, None for pre-race)
        time: Timestamp in ISO format
        category: Message category (Flag, Other, DRS, SafetyCar)
        message: The actual message text
        flag: Flag type if category is Flag (RED, YELLOW, etc.)
        scope: Scope of the message (Track, Sector, Driver)
        sector: Track sector number if applicable
        racing_number: Driver racing number if applicable
    """

    lap: int | None
    time: str
    category: str
    message: str
    flag: str | None
    scope: str | None
    sector: int | None
    racing_number: str | None


class RaceControlData(TypedDict):
    """Race control messages for a session.

    Fields:
        year: Season year
        event_name: Grand Prix name
        country: Country where event took place
        session_type: Session identifier (R, Q, FP1, etc.)
        session_name: Full session name
        total_messages: Total number of messages before filtering
        filtered_messages: Number of messages after filtering
        filters_applied: Dictionary of filters that were applied
        messages: List of race control messages
    """

    year: int
    event_name: str
    country: str
    session_type: str
    session_name: str
    total_messages: int
    filtered_messages: int
    filters_applied: dict
    messages: list[RaceControlMessage]


def _is_high_impact_message(row: pd.Series) -> bool:
    """Determine if a message is high-impact (race-changing event).

    High-impact messages include:
    - RED flags (race stoppages)
    - SAFETY CAR / VSC messages
    - CHEQUERED flag (race finish)
    - First GREEN light (race start)
    - Major collisions (messages containing "COLLISION")

    Args:
        row: Single row from race_control_messages DataFrame

    Returns:
        True if message is high-impact, False otherwise
    """
    category = row.get("Category")
    flag = row.get("Flag")
    message = str(row.get("Message", "")).upper()

    # RED flag - race stoppage
    if flag == FLAG_RED:
        return True

    # Safety Car category messages
    if category == MESSAGE_CATEGORY_SAFETY_CAR:
        return True

    # Chequered flag - race finish
    if flag == FLAG_CHEQUERED:
        return True

    # First green light - race start (check if it's the pit exit open before race)
    if flag == FLAG_GREEN and "PIT EXIT OPEN" in message:
        # Only consider this high-impact if it's close to race start (lap 1 or None)
        lap = row.get("Lap")
        if lap is None or lap == 1:
            return True

    # Major collisions
    return "COLLISION" in message


def _is_medium_impact_message(row: pd.Series) -> bool:
    """Determine if a message is medium-impact (situational awareness).

    Medium-impact messages include:
    - DOUBLE YELLOW flags
    - YELLOW flags (single)
    - DRS status changes
    - Significant penalties (time penalties, DSQ, etc.)
    - Retirements and DNFs

    Args:
        row: Single row from race_control_messages DataFrame

    Returns:
        True if message is medium-impact, False otherwise
    """
    category = row.get("Category")
    flag = row.get("Flag")
    message = str(row.get("Message", "")).upper()

    # DOUBLE YELLOW flags
    if flag == FLAG_DOUBLE_YELLOW:
        return True

    # Single YELLOW flags
    if flag == "YELLOW":
        return True

    # DRS status changes
    if category == MESSAGE_CATEGORY_DRS:
        return True

    # Penalties (but filter out "NO FURTHER INVESTIGATION")
    if "PENALTY" in message and "NO FURTHER" not in message:
        return True

    # Disqualifications
    if "DISQUALIFIED" in message or "DSQ" in message:
        return True

    # Retirements
    return "RETIRED" in message or "DNF" in message or "WITHDRAWAL" in message


def _filter_by_detail_level(
    messages_df: pd.DataFrame,
    detail: str,
) -> pd.DataFrame:
    """Filter messages based on detail level (progressive disclosure).

    Args:
        messages_df: DataFrame of race control messages
        detail: Detail level ("high", "medium", or "full")

    Returns:
        Filtered DataFrame based on detail level

    Raises:
        ValueError: If detail level is not one of "high", "medium", or "full"
    """
    # Validate detail level
    valid_levels = ("high", "medium", "full")
    if detail not in valid_levels:
        raise ValueError(f"Invalid detail level: '{detail}'. Must be one of {valid_levels}")

    if detail == "full":
        return messages_df

    if detail == "high":
        # Only high-impact messages
        mask = messages_df.apply(_is_high_impact_message, axis=1)
        return messages_df[mask]

    # detail == "medium"
    # High-impact OR medium-impact messages
    mask = messages_df.apply(
        lambda row: _is_high_impact_message(row) or _is_medium_impact_message(row),
        axis=1,
    )
    return messages_df[mask]


def _filter_by_category(
    messages_df: pd.DataFrame,
    category: str | None,
) -> pd.DataFrame:
    """Filter messages by category.

    Args:
        messages_df: DataFrame of race control messages
        category: Category to filter by (Flag, Other, DRS, SafetyCar) or None

    Returns:
        Filtered DataFrame
    """
    if category is None:
        return messages_df

    return messages_df[messages_df["Category"] == category]


def _filter_by_flag_type(
    messages_df: pd.DataFrame,
    flag_type: str | None,
) -> pd.DataFrame:
    """Filter messages by flag type.

    Args:
        messages_df: DataFrame of race control messages
        flag_type: Flag type to filter by (RED, YELLOW, etc.) or None

    Returns:
        Filtered DataFrame
    """
    if flag_type is None:
        return messages_df

    return messages_df[messages_df["Flag"] == flag_type.upper()]


def _filter_by_driver(
    messages_df: pd.DataFrame,
    driver: str | None,
) -> pd.DataFrame:
    """Filter messages by driver racing number.

    Args:
        messages_df: DataFrame of race control messages
        driver: Racing number to filter by or None

    Returns:
        Filtered DataFrame
    """
    if driver is None:
        return messages_df

    return messages_df[messages_df["RacingNumber"] == driver]


def _filter_by_lap_range(
    messages_df: pd.DataFrame,
    lap_start: int | None,
    lap_end: int | None,
) -> pd.DataFrame:
    """Filter messages by lap range.

    Args:
        messages_df: DataFrame of race control messages
        lap_start: Start lap (inclusive) or None
        lap_end: End lap (inclusive) or None

    Returns:
        Filtered DataFrame
    """
    if lap_start is None and lap_end is None:
        return messages_df

    result = messages_df.copy()

    if lap_start is not None:
        result = result[result["Lap"] >= lap_start]

    if lap_end is not None:
        result = result[result["Lap"] <= lap_end]

    return result


def _filter_by_sector(
    messages_df: pd.DataFrame,
    sector: int | None,
) -> pd.DataFrame:
    """Filter messages by track sector.

    Args:
        messages_df: DataFrame of race control messages
        sector: Sector number to filter by or None

    Returns:
        Filtered DataFrame
    """
    if sector is None:
        return messages_df

    return messages_df[messages_df["Sector"] == sector]


def get_race_control_messages(
    year: int,
    gp: str,
    session_type: str,
    detail: str = "high",
    category: str | None = None,
    flag_type: str | None = None,
    driver: str | None = None,
    lap_start: int | None = None,
    lap_end: int | None = None,
    sector: int | None = None,
) -> RaceControlData:
    """Load race control messages from FastF1 with optional filtering.

    Args:
        year: Season year (e.g., 2024)
        gp: Grand Prix name (e.g., "Monaco")
        session_type: Session identifier (R, Q, FP1, FP2, FP3, S, SQ)
        detail: Detail level for progressive disclosure ("high", "medium", "full")
        category: Filter by category (Flag, Other, DRS, SafetyCar) or None
        flag_type: Filter by flag type (RED, YELLOW, etc.) or None
        driver: Filter by racing number or None
        lap_start: Filter from lap number (inclusive) or None
        lap_end: Filter to lap number (inclusive) or None
        sector: Filter by track sector or None

    Returns:
        Dictionary with race control messages and metadata
    """
    # Load session with messages data
    session = load_session(year, gp, session_type, messages=True)

    # Get race control messages DataFrame
    try:
        messages_df = session.race_control_messages

        if messages_df is None or messages_df.empty:
            # No messages available
            return {
                "year": year,
                "event_name": session.event["EventName"],
                "country": session.event["Country"],
                "session_type": session_type,
                "session_name": session.name,
                "total_messages": 0,
                "filtered_messages": 0,
                "filters_applied": {},
                "messages": [],
            }

        total_messages = len(messages_df)

        # Apply filters in sequence
        filtered_df = messages_df.copy()

        # Apply category filter first if specified
        filtered_df = _filter_by_category(filtered_df, category)

        # Apply flag type filter
        filtered_df = _filter_by_flag_type(filtered_df, flag_type)

        # Apply driver filter
        filtered_df = _filter_by_driver(filtered_df, driver)

        # Apply lap range filter
        filtered_df = _filter_by_lap_range(filtered_df, lap_start, lap_end)

        # Apply sector filter
        filtered_df = _filter_by_sector(filtered_df, sector)

        # Apply detail level filter last (unless detail is "full")
        filtered_df = _filter_by_detail_level(filtered_df, detail)

        # Convert to list of messages
        messages = []
        for _, row in filtered_df.iterrows():
            messages.append(
                {
                    "lap": int(row["Lap"]) if pd.notna(row["Lap"]) else None,
                    "time": row["Time"].isoformat() if pd.notna(row["Time"]) else None,
                    "category": row["Category"] if pd.notna(row["Category"]) else None,
                    "message": row["Message"] if pd.notna(row["Message"]) else "",
                    "flag": row["Flag"] if pd.notna(row["Flag"]) else None,
                    "scope": row["Scope"] if pd.notna(row["Scope"]) else None,
                    "sector": int(row["Sector"]) if pd.notna(row["Sector"]) else None,
                    "racing_number": row["RacingNumber"] if pd.notna(row["RacingNumber"]) else None,
                }
            )

        # Track which filters were applied
        filters_applied = {"detail": detail}
        if category is not None:
            filters_applied["category"] = category
        if flag_type is not None:
            filters_applied["flag_type"] = flag_type
        if driver is not None:
            filters_applied["driver"] = driver
        if lap_start is not None:
            filters_applied["lap_start"] = lap_start
        if lap_end is not None:
            filters_applied["lap_end"] = lap_end
        if sector is not None:
            filters_applied["sector"] = sector

        return {
            "year": year,
            "event_name": session.event["EventName"],
            "country": session.event["Country"],
            "session_type": session_type,
            "session_name": session.name,
            "total_messages": total_messages,
            "filtered_messages": len(messages),
            "filters_applied": filters_applied,
            "messages": messages,
        }

    except AttributeError:
        # Race control messages not available for this session
        return {
            "year": year,
            "event_name": session.event["EventName"],
            "country": session.event["Country"],
            "session_type": session_type,
            "session_name": session.name,
            "total_messages": 0,
            "filtered_messages": 0,
            "filters_applied": {},
            "messages": [],
        }
