"""CLI analyze commands for generating visualizations in workspace.

This module provides commands for generating F1 data visualizations (lap times, tyre strategy)
and storing results in the workspace charts directory.
"""

import json
import sys

import click

from pitlane_agent.commands.analyze import (
    generate_championship_possibilities_chart,
    generate_driver_lap_list,
    generate_gear_shifts_map_chart,
    generate_lap_times_chart,
    generate_lap_times_distribution_chart,
    generate_multi_lap_chart,
    generate_position_changes_chart,
    generate_season_summary_chart,
    generate_speed_trace_chart,
    generate_telemetry_chart,
    generate_track_map_chart,
    generate_tyre_strategy_chart,
    generate_year_compare_chart,
)
from pitlane_agent.commands.workspace import get_workspace_path, workspace_exists
from pitlane_agent.utils.fastf1_helpers import validate_session_or_test


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
    validate_session_or_test(gp, session, test_number, session_number)

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
    validate_session_or_test(gp, session, test_number, session_number)

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
@click.option(
    "--session",
    type=str,
    default=None,
    help="Session type: R, Q, FP1, FP2, FP3, S, SQ (defaults to R when --gp is used)",
)
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
    # Default session to "R" when only --gp is provided (backwards compat)
    if gp is not None and session is None and test_number is None:
        session = "R"
    validate_session_or_test(gp, session, test_number, session_number)

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
    validate_session_or_test(gp, session, test_number, session_number)

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


@analyze.command("telemetry")
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
def telemetry(
    workspace_id: str,
    year: int,
    gp: str | None,
    session: str | None,
    test_number: int | None,
    session_number: int | None,
    drivers: tuple[str, ...],
    annotate_corners: bool,
):
    """Generate interactive telemetry chart (speed, RPM, gear, throttle, brake) for fastest laps."""
    validate_session_or_test(gp, session, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    if len(drivers) < 2:
        click.echo(json.dumps({"error": "Telemetry requires at least 2 drivers for comparison"}), err=True)
        sys.exit(1)
    if len(drivers) > 5:
        click.echo(json.dumps({"error": "Telemetry supports maximum 5 drivers for readability"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_telemetry_chart(
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
    validate_session_or_test(gp, session, test_number, session_number)

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
    validate_session_or_test(gp, session, test_number, session_number)

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
    validate_session_or_test(gp, session, test_number, session_number)

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


@analyze.command("multi-lap")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    "session_type",
    type=str,
    default=None,
    help="Session type: R, Q, FP1, FP2, FP3, S, SQ",
)
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option("--driver", required=True, help="Driver abbreviation (e.g., VER)")
@click.option(
    "--lap",
    "laps",
    multiple=True,
    required=True,
    help="Lap specifier: 'best' for fastest lap or an integer lap number. Specify 2-6 times.",
)
@click.option(
    "--annotate-corners",
    is_flag=True,
    default=False,
    help="Add corner markers and labels to the chart",
)
def multi_lap(
    workspace_id: str,
    year: int,
    gp: str | None,
    session_type: str | None,
    test_number: int | None,
    session_number: int | None,
    driver: str,
    laps: tuple[str, ...],
    annotate_corners: bool,
):
    """Compare multiple laps for a single driver within a session.

    Each --lap value is either 'best' (fastest lap) or an integer lap number.
    Useful for comparing a driver's Q1/Q3 attempts, or stint pace across a race.

    Example (GP session):
      pitlane analyze multi-lap --year 2024 --gp Monaco --session Q
        --driver VER --lap best --lap 3

    Example (testing session):
      pitlane analyze multi-lap --year 2024 --test 1 --day 2
        --driver VER --lap best --lap 3
    """
    validate_session_or_test(gp, session_type, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    if len(laps) < 2:
        click.echo(json.dumps({"error": "multi-lap requires at least 2 --lap values"}), err=True)
        sys.exit(1)
    if len(laps) > 6:
        click.echo(json.dumps({"error": "multi-lap supports at most 6 --lap values for readability"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    # Parse lap specs: coerce numeric strings to int, keep "best" as string
    lap_specs: list[str | int] = []
    for spec in laps:
        if spec.lower() == "best":
            lap_specs.append("best")
        else:
            try:
                lap_specs.append(int(spec))
            except ValueError:
                click.echo(
                    json.dumps({"error": f"Invalid --lap value '{spec}': must be 'best' or an integer"}), err=True
                )
                sys.exit(1)

    try:
        result = generate_multi_lap_chart(
            year=year,
            gp=gp,
            session_type=session_type,
            driver=driver,
            lap_specs=lap_specs,
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


@analyze.command("year-compare")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option(
    "--gp",
    type=str,
    default=None,
    help="Grand Prix name (e.g., Monza) — must exist in all specified years",
)
@click.option(
    "--session",
    "session_type",
    type=str,
    default=None,
    help="Session type: R, Q, FP1, FP2, FP3, S, SQ",
)
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option("--driver", required=True, help="Driver abbreviation (e.g., VER)")
@click.option(
    "--years",
    multiple=True,
    required=True,
    type=int,
    help="Season year to include. Specify 2-6 times (e.g., --years 2022 --years 2024).",
)
@click.option(
    "--annotate-corners",
    is_flag=True,
    default=False,
    help="Add corner markers and labels to the chart",
)
def year_compare(
    workspace_id: str,
    gp: str | None,
    session_type: str | None,
    test_number: int | None,
    session_number: int | None,
    driver: str,
    years: tuple[int, ...],
    annotate_corners: bool,
):
    """Compare a driver's best lap at the same track across multiple seasons.

    Useful for analysing the impact of regulation changes on lap time, braking,
    speed profiles, and driving technique across eras.

    Example (GP session):
      pitlane analyze year-compare --gp Monza --session Q
        --driver VER --years 2022 --years 2024

    Example (testing session):
      pitlane analyze year-compare --test 1 --day 2
        --driver VER --years 2022 --years 2024
    """
    validate_session_or_test(gp, session_type, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    if len(years) < 2:
        click.echo(json.dumps({"error": "year-compare requires at least 2 --years values"}), err=True)
        sys.exit(1)
    if len(years) > 6:
        click.echo(json.dumps({"error": "year-compare supports at most 6 --years values for readability"}), err=True)
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_year_compare_chart(
            gp=gp,
            session_type=session_type,
            driver=driver,
            years=list(years),
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


@analyze.command("driver-laps")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option("--gp", type=str, default=None, help="Grand Prix name (e.g., Monaco)")
@click.option(
    "--session",
    "session_type",
    type=str,
    default=None,
    help="Session type: R, Q, FP1, FP2, FP3, S, SQ",
)
@click.option("--test", "test_number", type=int, default=None, help="Testing event number (e.g., 1 or 2)")
@click.option("--day", "session_number", type=int, default=None, help="Day/session within testing event (1-3)")
@click.option("--driver", required=True, help="Driver abbreviation (e.g., VER)")
def driver_laps(
    workspace_id: str,
    year: int,
    gp: str | None,
    session_type: str | None,
    test_number: int | None,
    session_number: int | None,
    driver: str,
):
    """Fetch per-lap data for a single driver — no chart generated.

    Returns structured JSON with lap times, tyre compounds, stint numbers, pit
    events, position, and whether each lap is race-representative (is_accurate).
    Use this before multi-lap to identify which lap numbers are worth comparing.

    Example (GP session):
      pitlane analyze driver-laps --year 2024 --gp Monaco --session R --driver VER

    Example (testing session):
      pitlane analyze driver-laps --year 2024 --test 1 --day 2 --driver VER
    """
    validate_session_or_test(gp, session_type, test_number, session_number)

    if not workspace_exists(workspace_id):
        click.echo(json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}), err=True)
        sys.exit(1)

    try:
        result = generate_driver_lap_list(
            year=year,
            gp=gp,
            session_type=session_type,
            driver=driver,
            test_number=test_number,
            session_number=session_number,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@analyze.command("season-summary")
@click.option("--workspace-id", required=True, help="Workspace ID")
@click.option("--year", type=int, required=True, help="Season year (e.g., 2024)")
@click.option(
    "--type",
    "summary_type",
    type=click.Choice(["drivers", "constructors"], case_sensitive=False),
    default="drivers",
    help="Summary type: drivers or constructors (default: drivers)",
)
def season_summary(workspace_id: str, year: int, summary_type: str):
    """Generate season summary visualization with championship statistics.

    Aggregates points, wins, podiums, poles, fastest laps, and DNFs across
    all completed races and produces a multi-panel bar chart.

    Example:
      pitlane analyze season-summary --workspace-id $PITLANE_WORKSPACE_ID --year 2024
      pitlane analyze season-summary --workspace-id $PITLANE_WORKSPACE_ID --year 2024 --type constructors
    """
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for workspace ID: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        result = generate_season_summary_chart(
            year=year,
            summary_type=summary_type,
            workspace_dir=workspace_path,
        )
        result["workspace_id"] = workspace_id
        click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
