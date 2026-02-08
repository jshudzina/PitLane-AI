"""PitLane AI CLI - Workspace-based interface for F1 data analysis.

Usage:
    pitlane --help
    pitlane workspace create --session-id my-analysis
    pitlane fetch session-info --session-id my-analysis --year 2024 --gp Monaco --session R
    pitlane analyze lap-times --session-id my-analysis --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
"""

import json
import logging
import sys
import warnings

import click

from pitlane_agent.cli_analyze import analyze
from pitlane_agent.cli_fetch import fetch
from pitlane_agent.commands.workspace import (
    clean_workspaces,
    create_workspace,
    get_workspace_info,
    list_workspaces,
    remove_workspace,
    workspace_exists,
)
from pitlane_agent.temporal import get_temporal_context
from pitlane_agent.temporal.formatter import format_as_text, format_for_system_prompt


@click.group()
def pitlane():
    """PitLane AI - F1 data analysis tools powered by FastF1 and Claude."""
    # Suppress logging from underlying libraries
    logging.getLogger("fastf1").setLevel(logging.WARNING)
    # Suppress deprecation warnings from FastF1
    warnings.filterwarnings("ignore", category=FutureWarning, module="fastf1")


@click.group()
def workspace():
    """Manage workspaces."""
    pass


@workspace.command()
@click.option("--session-id", help="Session ID (auto-generated if not provided)")
@click.option("--description", help="Workspace description")
def create(session_id: str | None, description: str | None):
    """Create a new workspace."""
    try:
        result = create_workspace(session_id=session_id, description=description)
        click.echo(json.dumps(result, indent=2))
    except ValueError as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@workspace.command()
@click.option("--show-all", is_flag=True, help="Show all workspaces (default: 10 most recent)")
def list(show_all: bool):
    """List workspaces."""
    try:
        workspaces = list_workspaces(show_all=show_all)
        result = {
            "total": len(workspaces),
            "workspaces": workspaces,
        }
        click.echo(json.dumps(result, indent=2))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@workspace.command()
@click.option("--session-id", required=True, help="Session ID")
def info(session_id: str):
    """Show workspace information."""
    try:
        info_data = get_workspace_info(session_id)
        click.echo(json.dumps(info_data, indent=2))
    except ValueError as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@workspace.command()
@click.option("--older-than", type=int, help="Remove workspaces older than N days")
@click.option("--all", "all_workspaces", is_flag=True, help="Remove all workspaces")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clean(older_than: int | None, all_workspaces: bool, yes: bool):
    """Clean old workspaces."""
    if not all_workspaces and older_than is None:
        click.echo(
            json.dumps({"error": "Must specify either --older-than or --all"}),
            err=True,
        )
        sys.exit(1)

    # Confirmation prompt
    if not yes:
        message = "Remove ALL workspaces?" if all_workspaces else f"Remove workspaces older than {older_than} days?"

        if not click.confirm(message):
            click.echo(json.dumps({"message": "Cancelled"}))
            return

    try:
        result = clean_workspaces(older_than_days=older_than, remove_all=all_workspaces)
        click.echo(json.dumps(result, indent=2))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@workspace.command()
@click.option("--session-id", required=True, help="Session ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def remove(session_id: str, yes: bool):
    """Remove a specific workspace."""
    if not workspace_exists(session_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist for session ID: {session_id}"}),
            err=True,
        )
        sys.exit(1)

    # Confirmation prompt
    if not yes and not click.confirm(f"Remove workspace {session_id}?"):
        click.echo(json.dumps({"message": "Cancelled"}))
        return

    try:
        remove_workspace(session_id)
        click.echo(json.dumps({"message": f"Workspace {session_id} removed successfully"}))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@pitlane.command()
@click.option(
    "--format",
    type=click.Choice(["json", "text", "prompt"]),
    default="text",
    help="Output format",
)
@click.option("--refresh", is_flag=True, help="Force refresh from FastF1 (ignore cache)")
@click.option(
    "--verbosity",
    type=click.Choice(["minimal", "normal", "detailed"]),
    default="normal",
    help="Detail level for prompt format",
)
def temporal_context(format: str, refresh: bool, verbosity: str):
    """Show current F1 temporal context.

    This command displays the current state of the F1 season including:
    - Current season year and phase (pre/in/post/off-season)
    - Active race weekend (if any)
    - Current or recent sessions
    - Next upcoming race
    - Last completed race
    """
    try:
        context = get_temporal_context(force_refresh=refresh)

        if format == "json":
            click.echo(json.dumps(context.to_dict(), indent=2, default=str))
        elif format == "prompt":
            prompt_text = format_for_system_prompt(context, verbosity=verbosity)
            click.echo(prompt_text)
        else:
            # Human-readable text format
            text_output = format_as_text(context)
            click.echo(text_output)

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


# Register command groups
pitlane.add_command(workspace)
pitlane.add_command(fetch)
pitlane.add_command(analyze)


if __name__ == "__main__":
    pitlane()
