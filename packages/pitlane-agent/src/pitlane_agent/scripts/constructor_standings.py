"""Get F1 constructor championship standings from FastF1 Ergast API.

Usage:
    pitlane fetch constructor-standings --session-id SESSION_ID --year 2024
    pitlane fetch constructor-standings --session-id SESSION_ID --year 2024 --round 10
"""

import fastf1.ergast as ergast

# Constants
MIN_F1_YEAR = 1950
FINAL_ROUND = "last"


def get_constructor_standings(
    year: int,
    round_number: int | None = None,
) -> dict:
    """Load constructor championship standings from FastF1 Ergast API.

    Points reflect the system used in that season. Sprint race points (where
    applicable) are included in the total. Historical seasons use their
    contemporary points systems.

    Args:
        year: Championship year (e.g., 2024)
        round_number: Optional specific round number (default: final standings)

    Returns:
        Dictionary with constructor standings and metadata

    Raises:
        Exception: If Ergast API request fails
    """
    # Initialize Ergast API
    ergast_api = ergast.Ergast()

    # Fetch constructor standings
    # Use FINAL_ROUND for final standings if round_number not specified
    round_param = round_number if round_number is not None else FINAL_ROUND
    response = ergast_api.get_constructor_standings(season=year, round=round_param)

    # Extract round information from response description
    description = response.description
    actual_round = int(description.iloc[0]["round"]) if len(description) > 0 else round_number

    # Get standings data from content
    standings_data = []
    if len(response.content) > 0:
        standings_df = response.content[0]

        # Convert each row to dict
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
