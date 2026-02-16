"""CLI fetch commands for fetching F1 data into workspace.

This module provides commands for fetching F1 data (session info, driver info, schedule)
and storing results in the workspace data directory.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from pitlane_agent.commands.fetch import (
    get_constructor_standings,
    get_driver_info,
    get_driver_standings,
    get_event_schedule,
    get_race_control_messages,
    get_season_summary,
    get_session_info,
)
from pitlane_agent.commands.workspace import get_workspace_path, workspace_exists
from pitlane_agent.utils.constants import MIN_F1_YEAR
from pitlane_agent.utils.fastf1_helpers import build_data_path


def _validate_standings_request(workspace_id: str, year: int) -> Path:
    """Validate workspace and year for standings fetch commands.

    Args:
        workspace_id: Workspace ID
        year: Championship year

    Returns:
        Path to workspace directory

    Raises:
        SystemExit: If validation fails
    """
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    # Validate year
    current_year = datetime.now().year
    if year < MIN_F1_YEAR or year > current_year + 2:
        click.echo(
            json.dumps({"error": f"Year must be between {MIN_F1_YEAR} and {current_year + 2}"}),
            err=True,
        )
        sys.exit(1)

    return get_workspace_path(workspace_id)


@click.group()
def fetch():
    """Fetch F1 data into workspace."""
    pass


@fetch.command()
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    default=None,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option(
    "--day", "session_number", type=int, default=None, help="Day/session within testing event (e.g., 1, 2, 3)"
)
def session_info(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
):
    """Fetch session information and store in workspace."""
    # Validate mutually exclusive options
    has_gp = gp is not None and session is not None
    has_test = test_number is not None and session_number is not None
    if not has_gp and not has_test:
        click.echo(
            json.dumps({"error": "Must provide either --gp and --session, or --test and --day"}),
            err=True,
        )
        sys.exit(1)
    if has_gp and has_test:
        click.echo(
            json.dumps({"error": "Cannot use --gp/--session with --test/--day"}),
            err=True,
        )
        sys.exit(1)

    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Fetch session info
        info = get_session_info(
            year,
            gp=gp,
            session_type=session,
            test_number=test_number,
            session_number=session_number,
        )

        # Write to workspace
        output_file = build_data_path(
            workspace_path,
            "session_info",
            year=year,
            gp=gp,
            session_type=session,
            test_number=test_number,
            session_number=session_number,
        )
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
@click.option("--workspace-id", required=True, help="Workspace ID")
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
    workspace_id: str,
    driver_code: str | None,
    season: int | None,
    limit: int,
    offset: int,
):
    """Fetch driver information and store in workspace."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
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

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Fetch driver info
        info = get_driver_info(
            driver_code=driver_code,
            season=season,
            limit=limit,
            offset=offset,
        )

        # Write to workspace
        output_file = build_data_path(workspace_path, "driver_info", driver_code=driver_code, season=season)
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
@click.option("--workspace-id", required=True, help="Workspace ID")
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
    workspace_id: str,
    year: int,
    round_number: int | None,
    country: str | None,
    include_testing: bool,
):
    """Fetch event schedule and store in workspace."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
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

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Fetch schedule
        schedule = get_event_schedule(
            year,
            round_number=round_number,
            country=country,
            include_testing=include_testing,
        )

        # Write to workspace
        output_file = build_data_path(workspace_path, "schedule", year=year, round_number=round_number)
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


@fetch.command("driver-standings")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Championship year (e.g., 2024)")
@click.option(
    "--round",
    "round_number",
    type=int,
    default=None,
    help="Filter by specific round number (default: final standings)",
)
def driver_standings(workspace_id: str, year: int, round_number: int | None):
    """Fetch driver championship standings and store in workspace."""
    # Validate request
    workspace_path = _validate_standings_request(workspace_id, year)

    try:
        # Fetch standings
        standings = get_driver_standings(year, round_number)

        # Write to workspace
        output_file = build_data_path(workspace_path, "driver_standings", year=year, round_number=round_number)

        with open(output_file, "w") as f:
            json.dump(standings, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "year": year,
            "round": standings["round"],
            "total_standings": standings["total_standings"],
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@fetch.command("constructor-standings")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Championship year (e.g., 2024)")
@click.option(
    "--round",
    "round_number",
    type=int,
    default=None,
    help="Filter by specific round number (default: final standings)",
)
def constructor_standings(workspace_id: str, year: int, round_number: int | None):
    """Fetch constructor championship standings and store in workspace."""
    # Validate request
    workspace_path = _validate_standings_request(workspace_id, year)

    try:
        # Fetch standings
        standings = get_constructor_standings(year, round_number)

        # Write to workspace
        output_file = build_data_path(workspace_path, "constructor_standings", year=year, round_number=round_number)

        with open(output_file, "w") as f:
            json.dump(standings, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "year": year,
            "round": standings["round"],
            "total_standings": standings["total_standings"],
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@fetch.command("race-control")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    default=None,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option(
    "--day", "session_number", type=int, default=None, help="Day/session within testing event (e.g., 1, 2, 3)"
)
@click.option(
    "--detail",
    type=click.Choice(["high", "medium", "full"], case_sensitive=False),
    default="high",
    help="Detail level: high (major events), medium (+flags/DRS), full (all messages)",
)
@click.option(
    "--category",
    type=str,
    default=None,
    help="Filter by category: Flag, Other, Drs, SafetyCar",
)
@click.option(
    "--flag-type",
    type=str,
    default=None,
    help="Filter by flag type: RED, YELLOW, DOUBLE YELLOW, GREEN, BLUE, CLEAR, CHEQUERED",
)
@click.option(
    "--driver",
    type=str,
    default=None,
    help="Filter by driver racing number (e.g., 1 for Verstappen)",
)
@click.option(
    "--lap-start",
    type=int,
    default=None,
    help="Filter from lap number (inclusive)",
)
@click.option(
    "--lap-end",
    type=int,
    default=None,
    help="Filter to lap number (inclusive)",
)
@click.option(
    "--sector",
    type=int,
    default=None,
    help="Filter by track sector number",
)
def race_control(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    detail: str,
    category: str | None,
    flag_type: str | None,
    driver: str | None,
    lap_start: int | None,
    lap_end: int | None,
    sector: int | None,
):
    """Fetch race control messages and store in workspace."""
    # Validate mutually exclusive options
    has_gp = gp is not None and session is not None
    has_test = test_number is not None and session_number is not None
    if not has_gp and not has_test:
        click.echo(
            json.dumps({"error": "Must provide either --gp and --session, or --test and --day"}),
            err=True,
        )
        sys.exit(1)
    if has_gp and has_test:
        click.echo(
            json.dumps({"error": "Cannot use --gp/--session with --test/--day"}),
            err=True,
        )
        sys.exit(1)

    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Fetch race control messages
        messages = get_race_control_messages(
            year=year,
            gp=gp,
            session_type=session,
            detail=detail,
            category=category,
            flag_type=flag_type,
            driver=driver,
            lap_start=lap_start,
            lap_end=lap_end,
            sector=sector,
            test_number=test_number,
            session_number=session_number,
        )

        # Write to workspace
        output_file = build_data_path(
            workspace_path,
            "race_control",
            year=year,
            gp=gp,
            session_type=session,
            test_number=test_number,
            session_number=session_number,
        )
        with open(output_file, "w") as f:
            json.dump(messages, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "event_name": messages["event_name"],
            "session": messages["session_name"],
            "year": year,
            "total_messages": messages["total_messages"],
            "filtered_messages": messages["filtered_messages"],
            "filters_applied": messages["filters_applied"],
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@fetch.command("season-summary")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Championship year (e.g., 2024)")
def season_summary(workspace_id: str, year: int):
    """Fetch season summary with races ranked by wildness score."""
    workspace_path = _validate_standings_request(workspace_id, year)

    try:
        summary = get_season_summary(year)

        # Write to workspace
        output_file = build_data_path(workspace_path, "season_summary", year=year)
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Return result
        result = {
            "data_file": str(output_file),
            "year": year,
            "total_races": summary["total_races"],
        }
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
