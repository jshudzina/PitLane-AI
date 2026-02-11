"""Get F1 driver championship standings from FastF1 Ergast API.

Usage:
    pitlane fetch driver-standings --workspace-id WORKSPACE_ID --year 2024
    pitlane fetch driver-standings --workspace-id WORKSPACE_ID --year 2024 --round 10
"""

from pitlane_agent.utils.constants import FINAL_ROUND
from pitlane_agent.utils.ergast import get_ergast_client, parse_driver_standings_response


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
    ergast_api = get_ergast_client()

    # Fetch driver standings
    # Use FINAL_ROUND for final standings if round_number not specified
    round_param = round_number if round_number is not None else FINAL_ROUND
    response = ergast_api.get_driver_standings(season=year, round=round_param)

    # Parse and return response
    return parse_driver_standings_response(response, year, round_number)
