"""Shared CLI utilities for pitlane subcommands."""

import os

import click

from pitlane_agent.commands.workspace import create_workspace, workspace_exists

_DEFAULT_WORKSPACE_ID = "default"


def get_workspace_id() -> str:
    """Resolve the active workspace ID from the environment.

    Reads PITLANE_WORKSPACE_ID set by F1Agent. Falls back to the "default"
    workspace (creating it if necessary) and emits a warning to stderr.

    Returns:
        Workspace ID string.
    """
    workspace_id = os.environ.get("PITLANE_WORKSPACE_ID")
    if not workspace_id:
        workspace_id = _DEFAULT_WORKSPACE_ID
        if not workspace_exists(workspace_id):
            create_workspace(workspace_id, description="Default workspace")
        click.echo(
            f"Warning: PITLANE_WORKSPACE_ID not set, using default workspace '{workspace_id}'",
            err=True,
        )
    return workspace_id
