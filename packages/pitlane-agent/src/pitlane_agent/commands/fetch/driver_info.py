"""Get F1 driver information from FastF1 Ergast API.

Usage:
    pitlane driver-info --driver-code VER
    pitlane driver-info --season 2024
    pitlane driver-info --limit 50
"""

from datetime import datetime

import pandas as pd

from pitlane_agent.utils.ergast import get_ergast_client


def get_driver_info(
    driver_code: str | None = None,
    season: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Load driver information from FastF1 Ergast API.

    Args:
        driver_code: Optional 3-letter driver code (e.g., "VER", "HAM")
        season: Optional season year to filter drivers (e.g., 2024)
        limit: Maximum number of results to return
        offset: Number of results to skip for pagination

    Returns:
        Dictionary with driver information and metadata
    """
    # Initialize Ergast API
    ergast_api = get_ergast_client()

    # Call get_driver_info with appropriate filters
    if driver_code:
        # Ergast API expects driver ID, not driver code
        # Try driver code as-is first (in case it's actually an ID like "hamilton")
        driver_data = ergast_api.get_driver_info(driver=driver_code.lower())

        # If no results and it looks like a 3-letter code,
        # fetch recent season data and filter by driver code
        if len(driver_data) == 0 and len(driver_code) == 3:
            current_year = datetime.now().year
            for year in range(current_year, current_year - 5, -1):
                season_drivers = ergast_api.get_driver_info(season=year)
                if "driverCode" in season_drivers.columns:
                    matches = season_drivers[season_drivers["driverCode"] == driver_code.upper()]
                    if len(matches) > 0:
                        driver_data = matches
                        break
    elif season:
        driver_data = ergast_api.get_driver_info(season=season)
    else:
        driver_data = ergast_api.get_driver_info()

    # Convert DataFrame to list of dicts with pagination
    drivers = []
    for idx, (_, driver) in enumerate(driver_data.iterrows()):
        if idx < offset:
            continue
        if len(drivers) >= limit:
            break

        # Handle date_of_birth - convert Timestamp to string
        date_of_birth = driver.get("dateOfBirth")
        if pd.isna(date_of_birth):
            date_of_birth = "Unknown"
        elif isinstance(date_of_birth, pd.Timestamp | datetime):
            date_of_birth = date_of_birth.strftime("%Y-%m-%d")

        driver_number = driver.get("driverNumber")
        driver_number = int(driver_number) if pd.notna(driver_number) else None

        drivers.append(
            {
                "driver_id": driver.get("driverId"),
                "driver_code": driver.get("driverCode"),
                "driver_number": driver_number,
                "given_name": driver.get("givenName"),
                "family_name": driver.get("familyName"),
                "full_name": f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip(),
                "date_of_birth": date_of_birth,
                "nationality": driver.get("driverNationality"),
                "url": driver.get("driverUrl"),
            }
        )

    return {
        "total_drivers": len(drivers),
        "filters": {
            "driver_code": driver_code,
            "season": season,
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
        "drivers": drivers,
    }
