"""Ergast API utilities for F1 data fetching.

This module provides shared utilities for working with the FastF1 Ergast API,
including client initialization and response parsing.
"""

from typing import Any

import fastf1.ergast as ergast
import pandas as pd


def get_ergast_client() -> ergast.Ergast:
    """Get initialized Ergast API client.

    Returns:
        Ergast API client instance
    """
    return ergast.Ergast()


def extract_round_from_response(response: Any, fallback: int | None = None) -> int:
    """Extract actual round number from Ergast response description.

    Args:
        response: Ergast API response object
        fallback: Fallback round number if extraction fails

    Returns:
        Extracted round number or fallback value
    """
    description = response.description
    if len(description) > 0:
        return int(description.iloc[0]["round"])
    return fallback


def parse_driver_standings_response(
    response: Any,
    year: int,
    round_number: int | None,
) -> dict:
    """Parse Ergast driver standings response into standard format.

    Handles Timestamp conversion, NaN handling, and data extraction.

    Args:
        response: Ergast API response from get_driver_standings
        year: Championship year
        round_number: Requested round number (None for final standings)

    Returns:
        Dictionary with parsed driver standings and metadata
    """
    # Extract actual round from response
    actual_round = extract_round_from_response(response, round_number)

    # Parse standings data
    standings_data = []
    if len(response.content) > 0:
        standings_df = response.content[0]

        for _, row in standings_df.iterrows():
            # Handle date of birth - convert Timestamp to string
            date_of_birth = row.get("dateOfBirth")
            if pd.isna(date_of_birth):
                date_of_birth = None
            elif isinstance(date_of_birth, pd.Timestamp):
                date_of_birth = date_of_birth.strftime("%Y-%m-%d")

            # Handle driver number - may be NaN for older drivers
            driver_number = row.get("driverNumber")
            driver_number = int(driver_number) if pd.notna(driver_number) else None

            # Extract constructor information (stored as lists in DataFrame)
            constructor_ids = row.get("constructorIds", [])
            constructor_names = row.get("constructorNames", [])

            standings_data.append(
                {
                    "position": int(row["position"]),
                    "points": float(row["points"]),
                    "wins": int(row["wins"]),
                    "driver_id": row["driverId"],
                    "driver_code": row.get("driverCode"),
                    "driver_number": driver_number,
                    "given_name": row["givenName"],
                    "family_name": row["familyName"],
                    "full_name": f"{row['givenName']} {row['familyName']}",
                    "nationality": row["driverNationality"],
                    "date_of_birth": date_of_birth,
                    "teams": list(constructor_names) if constructor_names else [],
                    "team_ids": list(constructor_ids) if constructor_ids else [],
                }
            )

    return {
        "year": year,
        "round": actual_round,
        "total_standings": len(standings_data),
        "filters": {
            "round": round_number,
        },
        "standings": standings_data,
    }


def parse_constructor_standings_response(
    response: Any,
    year: int,
    round_number: int | None,
) -> dict:
    """Parse Ergast constructor standings response into standard format.

    Args:
        response: Ergast API response from get_constructor_standings
        year: Championship year
        round_number: Requested round number (None for final standings)

    Returns:
        Dictionary with parsed constructor standings and metadata
    """
    # Extract actual round from response
    actual_round = extract_round_from_response(response, round_number)

    # Parse standings data
    standings_data = []
    if len(response.content) > 0:
        standings_df = response.content[0]

        for _, row in standings_df.iterrows():
            standings_data.append(
                {
                    "position": int(row["position"]),
                    "points": float(row["points"]),
                    "wins": int(row["wins"]),
                    "constructor_id": row["constructorId"],
                    "constructor_name": row["constructorName"],
                    "nationality": row["constructorNationality"],
                }
            )

    return {
        "year": year,
        "round": actual_round,
        "total_standings": len(standings_data),
        "filters": {
            "round": round_number,
        },
        "standings": standings_data,
    }
