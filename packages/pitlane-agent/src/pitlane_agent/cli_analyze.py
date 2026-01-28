"""CLI analyze commands for generating visualizations in workspace.

This module provides commands for generating F1 data visualizations (lap times, tyre strategy)
and storing results in the workspace charts directory.
"""

import json
import sys

import click

from pitlane_agent.scripts.lap_times import generate_lap_times_chart
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
