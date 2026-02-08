"""Get F1 event schedule from FastF1.

Usage:
    pitlane event-schedule --year 2024
    pitlane event-schedule --year 2024 --round 6
    pitlane event-schedule --year 2024 --country Italy
"""

import fastf1
import pandas as pd

from pitlane_agent.utils.fastf1_helpers import setup_fastf1_cache


def get_event_schedule(
    year: int,
    round_number: int | None = None,
    country: str | None = None,
    include_testing: bool = True,
) -> dict:
    """Load event schedule from FastF1 and return as dict.

    Args:
        year: Championship year (e.g., 2024)
        round_number: Optional filter for specific round
        country: Optional filter for country name (case-insensitive)
        include_testing: Whether to include testing sessions (default: True)

    Returns:
        Dictionary with schedule data and event information
    """
    # Enable FastF1 cache
    setup_fastf1_cache()

    # Get the event schedule
    schedule = fastf1.get_event_schedule(year, include_testing=include_testing)

    # Convert DataFrame to list of dicts
    events = []
    for _, event in schedule.iterrows():
        # Apply filters if specified
        if round_number is not None and event["RoundNumber"] != round_number:
            continue
        if country is not None and event["Country"].lower() != country.lower():
            continue

        # Build event dict with all relevant fields
        event_data = {
            "round": int(event["RoundNumber"]) if pd.notna(event["RoundNumber"]) else 0,
            "country": event["Country"],
            "location": event["Location"],
            "official_name": event["OfficialEventName"],
            "event_name": event["EventName"],
            "event_date": event["EventDate"].isoformat() if pd.notna(event["EventDate"]) else None,
            "event_format": event["EventFormat"],
            "f1_api_support": bool(event["F1ApiSupport"]),
            "sessions": [],
        }

        # Add session information
        for i in range(1, 6):
            session_key = f"Session{i}"
            session_date_key = f"Session{i}Date"
            session_date_utc_key = f"Session{i}DateUtc"

            session_name = event.get(session_key)
            # Skip if session name is None, empty, or the string "None"
            if session_name and session_name != "" and str(session_name) != "None":
                # Check if session date is valid (not NaT)
                session_date = event.get(session_date_key)
                if pd.notna(session_date):
                    session_info = {
                        "name": session_name,
                        "date_local": (
                            event[session_date_key].isoformat() if pd.notna(event.get(session_date_key)) else None
                        ),
                        "date_utc": (
                            event[session_date_utc_key].isoformat()
                            if pd.notna(event.get(session_date_utc_key))
                            else None
                        ),
                    }
                    event_data["sessions"].append(session_info)

        events.append(event_data)

    # Sort by round number for consistent output
    events.sort(key=lambda x: x["round"])

    return {
        "year": year,
        "total_events": len(events),
        "include_testing": include_testing,
        "filters": {
            "round": round_number,
            "country": country,
        },
        "events": events,
    }
