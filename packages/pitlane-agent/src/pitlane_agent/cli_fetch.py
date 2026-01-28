"""CLI fetch commands for fetching F1 data into workspace.

This module provides commands for fetching F1 data (session info, driver info, schedule)
and storing results in the workspace data directory.
"""

import json
import sys
from datetime import datetime

import click

from pitlane_agent.scripts.driver_info import get_driver_info
from pitlane_agent.scripts.event_schedule import get_event_schedule
from pitlane_agent.scripts.session_info import get_session_info
from pitlane_agent.scripts.workspace import get_workspace_path, workspace_exists


@click.group()
def fetch():
    """Fetch F1 data into workspace."""
    pass


@fetch.command()
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
def session_info(session_id: str, year: int, gp: str, session: str):
    """Fetch session information and store in workspace."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)
    data_dir = workspace_path / "data"

    try:
        # Fetch session info
        info = get_session_info(year, gp, session)

        # Write to workspace
        output_file = data_dir / "session_info.json"
        with open(output_file, "w") as f:
            json.dump(info, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "event_name": info["event_name"],
            "session": info["session_name"],
            "year": year,
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@fetch.command()
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option(
    "--driver-code",
    type=str,
    default=None,
    help="Filter by 3-letter driver code (e.g., VER, HAM, LEC)",
)
@click.option(
    "--season",
    type=int,
    default=None,
    help="Filter by season year (e.g., 2024)",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of drivers to return (default: 100)",
)
@click.option(
    "--offset",
    type=int,
    default=0,
    help="Number of drivers to skip for pagination (default: 0)",
)
def driver_info(
    session_id: str,
    driver_code: str | None,
    season: int | None,
    limit: int,
    offset: int,
):
    """Fetch driver information and store in workspace."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    # Validate season if provided
    if season is not None:
        current_year = datetime.now().year
        if season < 1950 or season > current_year + 2:
            click.echo(
                json.dumps({"error": f"Season must be between 1950 and {current_year + 2}"}),
                err=True,
            )
            sys.exit(1)

    workspace_path = get_workspace_path(session_id)
    data_dir = workspace_path / "data"

    try:
        # Fetch driver info
        info = get_driver_info(
            driver_code=driver_code,
            season=season,
            limit=limit,
            offset=offset,
        )

        # Write to workspace
        output_file = data_dir / "drivers.json"
        with open(output_file, "w") as f:
            json.dump(info, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "total_drivers": info["total_drivers"],
            "filters": info["filters"],
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@fetch.command()
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option(
    "--year",
    type=int,
    required=True,
    help="Championship year (e.g., 2024)",
)
@click.option(
    "--round",
    "round_number",
    type=int,
    default=None,
    help="Filter by specific round number",
)
@click.option(
    "--country",
    type=str,
    default=None,
    help="Filter by country name",
)
@click.option(
    "--include-testing/--no-testing",
    default=True,
    help="Include testing sessions (default: True)",
)
def event_schedule(
    session_id: str,
    year: int,
    round_number: int | None,
    country: str | None,
    include_testing: bool,
):
    """Fetch event schedule and store in workspace."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    # Validate year input
    current_year = datetime.now().year
    if year < 1950 or year > current_year + 2:
        click.echo(
            json.dumps({"error": f"Year must be between 1950 and {current_year + 2}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)
    data_dir = workspace_path / "data"

    try:
        # Fetch schedule
        schedule = get_event_schedule(
            year,
            round_number=round_number,
            country=country,
            include_testing=include_testing,
        )

        # Write to workspace
        output_file = data_dir / "schedule.json"
        with open(output_file, "w") as f:
            json.dump(schedule, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "year": year,
            "total_events": schedule["total_events"],
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
