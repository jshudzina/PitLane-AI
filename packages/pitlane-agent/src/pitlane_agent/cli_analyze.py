"""CLI analyze commands for generating visualizations in workspace.

This module provides commands for generating F1 data visualizations (lap times, tyre strategy)
and storing results in the workspace charts directory.
"""

import json
import sys

import click

from pitlane_agent.commands.analyze import (
    generate_championship_possibilities_chart,
    generate_gear_shifts_map_chart,
    generate_lap_times_chart,
    generate_lap_times_distribution_chart,
    generate_position_changes_chart,
    generate_speed_trace_chart,
    generate_track_map_chart,
    generate_tyre_strategy_chart,
)
from pitlane_agent.commands.workspace import get_workspace_path, workspace_exists


def validate_mutually_exclusive(ctx, param, value):
    """Validate that --drivers and --top-n are mutually exclusive."""
    # Get the other parameter's value from context
    if param.name == "drivers":
        other_value = ctx.params.get("top_n")
    elif param.name == "top_n":
        other_value = ctx.params.get("drivers")
    else:
        return value

    # Check if both are provided
    if value and other_value:
        raise click.BadParameter("Cannot specify both --drivers and --top-n options", ctx=ctx, param=param)

    return value


@click.group()
def analyze():
    """Generate analysis and visualizations."""
    pass


@analyze.command()
@click.option("--workspace-id", required=True, help="Workspace ID")
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
def lap_times(workspace_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate lap times chart for specified drivers."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

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
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("lap-times-distribution")
@click.option("--workspace-id", required=True, help="Workspace ID")
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
def lap_times_distribution(workspace_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate lap times distribution chart showing statistical spread."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

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
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command()
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default="R", help="Session type (default: R for Race)")
def tyre_strategy(workspace_id: str, year: int, gp: str, session: str):
    """Generate tyre strategy visualization for a race."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Generate chart (refactored function expects workspace_dir parameter)
        result = generate_tyre_strategy_chart(
            year=year,
            gp=gp,
            session_type=session,
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("speed-trace")
@click.option("--workspace-id", required=True, help="Workspace ID")
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
def speed_trace(workspace_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate speed trace comparison for fastest laps of specified drivers."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
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

    workspace_path = get_workspace_path(workspace_id)

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
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("position-changes")
@click.option("--workspace-id", required=True, help="Workspace ID")
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
    callback=validate_mutually_exclusive,
    help="Driver abbreviations (optional: --drivers VER --drivers HAM). Mutually exclusive with --top-n.",
)
@click.option(
    "--top-n",
    type=int,
    required=False,
    callback=validate_mutually_exclusive,
    help="Show only top N finishers (optional, e.g., --top-n 10). Mutually exclusive with --drivers.",
)
def position_changes(workspace_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...], top_n: int | None):
    """Generate position changes chart showing driver positions throughout the race."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

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
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("track-map")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, required=True, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    type=str,
    required=True,
    help="Session type: R (Race), Q (Qualifying), FP1, FP2, FP3, S (Sprint), SQ",
)
def track_map(workspace_id: str, year: int, gp: str, session: str):
    """Generate track map with numbered corner labels."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Generate chart
        result = generate_track_map_chart(
            year=year,
            gp=gp,
            session_type=session,
            workspace_dir=workspace_path,
        )

        # Add session info to result
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("gear-shifts-map")
@click.option("--workspace-id", required=True, help="Workspace ID")
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
    help="Driver abbreviation (exactly 1 driver, e.g., VER)",
)
def gear_shifts_map(workspace_id: str, year: int, gp: str, session: str, drivers: tuple[str, ...]):
    """Generate gear shift visualization on track map."""
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_gear_shifts_map_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=list(drivers),
            workspace_dir=workspace_path,
        )

        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("championship-possibilities")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option(
    "--championship",
    type=click.Choice(["drivers", "constructors"], case_sensitive=False),
    default="drivers",
    help="Championship type: drivers or constructors (default: drivers)",
)
@click.option(
    "--after-round",
    type=int,
    required=False,
    help="Analyze standings after a specific round for 'what if' scenarios (e.g., --after-round 10)",
)
def championship_possibilities(workspace_id: str, year: int, championship: str, after_round: int | None):
    """Calculate who can still mathematically win the championship."""
    # Verify workspace exists
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        # Generate chart
        result = generate_championship_possibilities_chart(
            year=year,
            championship=championship,
            workspace_dir=workspace_path,
            after_round=after_round,
        )

        # Add session info to result
        result["workspace_id"] = workspace_id

        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
