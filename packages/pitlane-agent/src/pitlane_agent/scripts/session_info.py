"""Get F1 session information from FastF1.

Usage:
    pitlane session-info --year 2024 --gp Monaco --session R

    # Or using module invocation
    python -m pitlane_agent.scripts.session_info --year 2024 --gp Monaco --session R
"""

import json
import sys

import click
import fastf1


def get_session_info(year: int, gp: str, session_type: str) -> dict:
    """Load session info from FastF1 and return as dict.

    Args:
        year: Season year (e.g., 2024)
        gp: Grand Prix name (e.g., "Monaco", "Silverstone")
        session_type: Session identifier (R, Q, FP1, FP2, FP3, S, SQ)

    Returns:
        Dictionary with session metadata and driver info
    """
    # Enable FastF1 cache for faster subsequent loads
    fastf1.Cache.enable_cache("/tmp/fastf1_cache")

    # Load the session
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    # Get driver info
    drivers = []
    for _, driver in session.results.iterrows():
        drivers.append(
            {
                "abbreviation": driver["Abbreviation"],
                "name": f"{driver['FirstName']} {driver['LastName']}",
                "team": driver["TeamName"],
                "number": int(driver["DriverNumber"]) if driver["DriverNumber"] else None,
                "position": int(driver["Position"]) if driver["Position"] else None,
            }
        )

    return {
        "year": year,
        "event_name": session.event["EventName"],
        "country": session.event["Country"],
        "session_type": session_type,
        "session_name": session.name,
        "date": str(session.date.date()) if session.date else None,
        "total_laps": int(session.total_laps) if hasattr(session, "total_laps") else None,
        "drivers": drivers,
    }


@click.command()
@click.option(
    "--year",
    type=int,
    required=True,
    help="Season year (e.g., 2024)"
)
@click.option(
    "--gp",
    type=str,
    required=True,
    help="Grand Prix name (e.g., Monaco, Silverstone)"
)
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ"
)
def cli(year, gp, session):
    """Get F1 session information including drivers and metadata."""
    try:
        info = get_session_info(year, gp, session)
        click.echo(json.dumps(info, indent=2))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
