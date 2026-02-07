"""Get F1 driver championship standings from FastF1 Ergast API.

Usage:
    pitlane fetch driver-standings --session-id SESSION_ID --year 2024
    pitlane fetch driver-standings --session-id SESSION_ID --year 2024 --round 10
"""

import fastf1.ergast as ergast
import pandas as pd


def get_driver_standings(
    year: int,
    round_number: int | None = None,
) -> dict:
    """Load driver championship standings from FastF1 Ergast API.

    Points reflect the system used in that season. Sprint race points (where
    applicable) are included in the total. Historical seasons use their
    contemporary points systems.

    Args:
        year: Championship year (e.g., 2024)
        round_number: Optional specific round number (default: final standings)

    Returns:
        Dictionary with driver standings and metadata

    Raises:
        Exception: If Ergast API request fails
    """
    # Initialize Ergast API
    ergast_api = ergast.Ergast()

    # Fetch driver standings
    # Use 'last' for final standings if round_number not specified
    round_param = round_number if round_number is not None else "last"
    response = ergast_api.get_driver_standings(season=year, round=round_param)

    # Extract round information from response description
    description = response.description
    actual_round = int(description.iloc[0]["round"]) if len(description) > 0 else round_number

    # Get standings data from content
    standings_data = []
    if len(response.content) > 0:
        standings_df = response.content[0]

        # Convert each row to dict
        for _, row in standings_df.iterrows():
            # Handle date of birth - convert Timestamp to string
            date_of_birth = row.get("dateOfBirth")
            if pd.isna(date_of_birth):
                date_of_birth = "Unknown"
            elif isinstance(date_of_birth, pd.Timestamp):
                date_of_birth = date_of_birth.strftime("%Y-%m-%d")

            # Handle driver number - may be NaN for older drivers
            driver_number = row.get("driverNumber")
            driver_number = int(driver_number) if pd.notna(driver_number) else None

            # Extract constructor information (stored as lists in the DataFrame)
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
