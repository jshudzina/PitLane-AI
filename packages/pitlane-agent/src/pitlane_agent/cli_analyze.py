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


def _validate_session_or_test(
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
) -> tuple[bool, bool]:
    """Validate that either --gp/--session or --test/--day is provided, not both.

    Returns:
        Tuple of (has_gp, has_test) booleans.

    Raises:
        SystemExit: If validation fails.
    """
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
    return has_gp, has_test


@click.group()
def analyze():
    """Generate analysis and visualizations."""
    pass


@analyze.command()
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type: R, Q, FP1, FP2, FP3, S, SQ")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option(
    "--drivers",
    multiple=True,
    required=True,
    help="Driver abbreviation (can be specified multiple times: --drivers VER --drivers HAM)",
)
def lap_times(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    drivers: tuple[str, ...],
):
    """Generate lap times chart for specified drivers."""
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_lap_times_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=list(drivers),
            workspace_dir=workspace_path,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("lap-times-distribution")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type: R, Q, FP1, FP2, FP3, S, SQ")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option(
    "--drivers",
    multiple=True,
    required=False,
    help="Driver abbreviations (optional; defaults to top 10 finishers)",
)
def lap_times_distribution(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    drivers: tuple[str, ...],
):
    """Generate lap times distribution chart showing statistical spread."""
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        drivers_list = list(drivers) if drivers else None
        result = generate_lap_times_distribution_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=drivers_list,
            workspace_dir=workspace_path,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command()
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type (default: R for Race)")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
def tyre_strategy(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
):
    """Generate tyre strategy visualization for a race."""
    # For tyre_strategy, default session to "R" if gp is provided but session is not
    if gp is not None and session is None and test_number is None:
        session = "R"
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_tyre_strategy_chart(
            year=year,
            gp=gp,
            session_type=session,
            workspace_dir=workspace_path,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("speed-trace")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type: R, Q, FP1, FP2, FP3, S, SQ")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option(
    "--drivers",
    multiple=True,
    required=True,
    help="Driver abbreviations to compare (2-5 drivers: --drivers VER --drivers HAM)",
)
@click.option(
    "--annotate-corners",
    is_flag=True,
    default=False,
    help="Add corner markers and labels to the chart",
)
def speed_trace(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    drivers: tuple[str, ...],
    annotate_corners: bool,
):
    """Generate speed trace comparison for fastest laps of specified drivers."""
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    if len(drivers) < 2:
        click.echo(json.dumps({"error": "Speed trace requires at least 2 drivers for comparison"}), err=True)
        sys.exit(1)
    if len(drivers) > 5:
        click.echo(json.dumps({"error": "Speed trace supports maximum 5 drivers for readability"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_speed_trace_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=list(drivers),
            workspace_dir=workspace_path,
            annotate_corners=annotate_corners,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("position-changes")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type: R (Race), S (Sprint), SQ")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
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
def position_changes(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    drivers: tuple[str, ...],
    top_n: int | None,
):
    """Generate position changes chart showing driver positions throughout the race."""
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        drivers_list = list(drivers) if drivers else None
        result = generate_position_changes_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=drivers_list,
            top_n=top_n,
            workspace_dir=workspace_path,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("track-map")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type: R, Q, FP1, FP2, FP3, S, SQ")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
def track_map(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
):
    """Generate track map with numbered corner labels."""
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_track_map_chart(
            year=year,
            gp=gp,
            session_type=session,
            workspace_dir=workspace_path,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("gear-shifts-map")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option("--session", type=str, default=None, help="Session type: R, Q, FP1, FP2, FP3, S, SQ")
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option(
    "--drivers",
    multiple=True,
    required=True,
    help="Driver abbreviation (exactly 1 driver, e.g., VER)",
)
def gear_shifts_map(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    drivers: tuple[str, ...],
):
    """Generate gear shift visualization on track map."""
    _validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_gear_shifts_map_chart(
            year=year,
            gp=gp,
            session_type=session,
            drivers=list(drivers),
            workspace_dir=workspace_path,
            test_number=test_number,
            session_number=session_number,
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
