"""CLI analyze commands for generating visualizations in workspace.

This module provides commands for generating F1 data visualizations (lap times, tyre strategy)
and storing results in the workspace charts directory.
"""

import json
import sys

import click

from pitlane_agent.scripts.lap_times import generate_lap_times_chart
from pitlane_agent.scripts.lap_times_distribution import generate_lap_times_distribution_chart
from pitlane_agent.scripts.position_changes import generate_position_changes_chart
from pitlane_agent.scripts.speed_trace import generate_speed_trace_chart
from pitlane_agent.scripts.tyre_strategy import generate_tyre_strategy_chart
from pitlane_agent.scripts.workspace import get_workspace_path, workspace_exists


@click.group()
def analyze():
    """Generate analysis and visualizations."""
    pass


@analyze.command()
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
@click.option(
    "--drivers",
    multiple=True,
    required=True,
    help="Driver abbreviation (can be specified multiple times: --drivers VER --drivers HAM)",
)
def lap_times(session_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate lap times chart for specified drivers."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)

    try:
        # Generate chart (refactored function expects workspace_dir parameter)
        result = generate_lap_times_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=list(drivers),
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["session_id"] = session_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("lap-times-distribution")
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
@click.option(
    "--drivers",
    multiple=True,
    required=False,
    help="Driver abbreviations (optional; defaults to top 10 finishers)",
)
def lap_times_distribution(session_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate lap times distribution chart showing statistical spread."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)

    try:
        # Convert empty drivers tuple to None for default behavior
        drivers_list = list(drivers) if drivers else None

        # Generate chart
        result = generate_lap_times_distribution_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=drivers_list,
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["session_id"] = session_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command()
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default="R", help="Session type (default: R for Race)")
def tyre_strategy(session_id: str, year: int, gp: str, session: str):
    """Generate tyre strategy visualization for a race."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)

    try:
        # Generate chart (refactored function expects workspace_dir parameter)
        result = generate_tyre_strategy_chart(
            year=year,
            gp=gp,
            session_type=session,
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["session_id"] = session_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("speed-trace")
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
@click.option(
    "--drivers",
    multiple=True,
    required=True,
    help="Driver abbreviations to compare (2-5 drivers: --drivers VER --drivers HAM)",
)
def speed_trace(session_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate speed trace comparison for fastest laps of specified drivers."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    # Validate driver count (2-5 drivers)
    if len(drivers) < 2:
        click.echo(
            json.dumps({"error": "Speed trace requires at least 2 drivers for comparison"}),
            err=True,
        )
        sys.exit(1)

    if len(drivers) > 5:
        click.echo(
            json.dumps({"error": "Speed trace supports maximum 5 drivers for readability"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)

    try:
        # Generate chart
        result = generate_speed_trace_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=list(drivers),
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["session_id"] = session_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("position-changes")
@click.option("--session-id", required=True, help="Workspace session ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), S (Sprint), SQ (Sprint Qualifying)",
)
@click.option(
    "--drivers",
    multiple=True,
    required=False,
    help="Driver abbreviations (optional: --drivers VER --drivers HAM)",
)
@click.option(
    "--top-n",
    type=int,
    required=False,
    help="Show only top N finishers (optional, e.g., --top-n 10)",
)
def position_changes(session_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...], top_n: int | None):
    """Generate position changes chart showing driver positions throughout the race."""
    # Verify workspace exists
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    # Validate mutually exclusive options
    if drivers and top_n:
        click.echo(
            json.dumps({"error": "Cannot specify both --drivers and --top-n options"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(session_id)

    try:
        # Convert empty drivers tuple to None for default behavior
        drivers_list = list(drivers) if drivers else None

        # Generate chart
        result = generate_position_changes_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=drivers_list,
            top_n=top_n,
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["session_id"] = session_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
