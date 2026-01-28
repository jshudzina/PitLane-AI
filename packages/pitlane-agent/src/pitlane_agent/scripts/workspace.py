"""Workspace management functions for PitLane AI.

This module provides utilities for creating, managing, and cleaning up
workspace directories used by the F1Agent.
"""

import json
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path


def get_workspace_base() -> Path:
    """Get the base directory for all workspaces.

    Returns:
        Path to ~/.pitlane/workspaces/
    """
    return Path.home() / ".pitlane" / "workspaces"


def get_cache_dir() -> Path:
    """Get the shared cache directory for FastF1 data.

    Returns:
        Path to ~/.pitlane/cache/fastf1/
    """
    return Path.home() / ".pitlane" / "cache" / "fastf1"


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
        UUID string to use as session identifier.
    """
    return str(uuid.uuid4())


def get_workspace_path(session_id: str) -> Path:
    """Get the workspace path for a given session ID.

    Args:
        session_id: The session identifier.

    Returns:
        Path to the workspace directory.
    """
    return get_workspace_base() / session_id


def workspace_exists(session_id: str) -> bool:
    """Check if a workspace exists for the given session ID.

    Args:
        session_id: The session identifier.

    Returns:
        True if workspace exists, False otherwise.
    """
    workspace_path = get_workspace_path(session_id)
    return workspace_path.exists() and workspace_path.is_dir()


def create_workspace(session_id: str | None = None, description: str | None = None) -> dict:
    """Create a new workspace directory structure.

    Args:
        session_id: Session identifier. Auto-generated if None.
        description: Optional description for the workspace.

    Returns:
        Dictionary with workspace information:
        {
            "session_id": str,
            "workspace_path": str,
            "created_at": str,
        }

    Raises:
        ValueError: If workspace already exists for the given session_id.
    """
    if session_id is None:
        session_id = generate_session_id()

    if workspace_exists(session_id):
        raise ValueError(f"Workspace already exists for session ID: {session_id}")

    workspace_path = get_workspace_path(session_id)

    # Create directory structure
    workspace_path.mkdir(parents=True, exist_ok=False)
    (workspace_path / "data").mkdir(exist_ok=True)
    (workspace_path / "charts").mkdir(exist_ok=True)

    # Ensure shared cache exists
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Write metadata
    metadata = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_accessed": datetime.utcnow().isoformat() + "Z",
    }

    if description:
        metadata["description"] = description

    metadata_path = workspace_path / ".metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return {
        "session_id": session_id,
        "workspace_path": str(workspace_path),
        "created_at": metadata["created_at"],
    }


def update_workspace_metadata(session_id: str) -> None:
    """Update the last_accessed timestamp in workspace metadata.

    Args:
        session_id: The session identifier.

    Raises:
        ValueError: If workspace doesn't exist.
    """
    if not workspace_exists(session_id):
        raise ValueError(f"Workspace does not exist for session ID: {session_id}")

    workspace_path = get_workspace_path(session_id)
    metadata_path = workspace_path / ".metadata.json"

    if not metadata_path.exists():
        # Metadata missing, recreate it
        metadata = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_accessed": datetime.utcnow().isoformat() + "Z",
        }
    else:
        with open(metadata_path) as f:
            metadata = json.load(f)

        metadata["last_accessed"] = datetime.utcnow().isoformat() + "Z"

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def get_workspace_info(session_id: str) -> dict:
    """Get information about a workspace.

    Args:
        session_id: The session identifier.

    Returns:
        Dictionary with workspace metadata including:
        {
            "session_id": str,
            "workspace_path": str,
            "created_at": str,
            "last_accessed": str,
            "description": str (optional),
            "data_files": list[str],
            "chart_files": list[str],
        }

    Raises:
        ValueError: If workspace doesn't exist.
    """
    if not workspace_exists(session_id):
        raise ValueError(f"Workspace does not exist for session ID: {session_id}")

    workspace_path = get_workspace_path(session_id)
    metadata_path = workspace_path / ".metadata.json"

    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
    else:
        metadata = {
            "session_id": session_id,
            "created_at": "unknown",
            "last_accessed": "unknown",
        }

    # List data and chart files
    data_dir = workspace_path / "data"
    chart_dir = workspace_path / "charts"

    data_files = [f.name for f in data_dir.iterdir() if f.is_file()] if data_dir.exists() else []
    chart_files = [f.name for f in chart_dir.iterdir() if f.is_file()] if chart_dir.exists() else []

    return {
        **metadata,
        "workspace_path": str(workspace_path),
        "data_files": sorted(data_files),
        "chart_files": sorted(chart_files),
    }


def list_workspaces(show_all: bool = False) -> list[dict]:
    """List all workspaces.

    Args:
        show_all: If True, include all workspaces. If False, only recent ones.

    Returns:
        List of workspace information dictionaries sorted by last_accessed (newest first).
    """
    workspace_base = get_workspace_base()

    if not workspace_base.exists():
        return []

    workspaces = []

    for workspace_dir in workspace_base.iterdir():
        if not workspace_dir.is_dir():
            continue

        session_id = workspace_dir.name
        try:
            info = get_workspace_info(session_id)
            workspaces.append(info)
        except Exception:
            # Skip corrupted workspaces
            continue

    # Sort by last_accessed (newest first)
    def get_last_accessed(ws):
        try:
            return datetime.fromisoformat(ws["last_accessed"].rstrip("Z"))
        except Exception:
            return datetime.min

    workspaces.sort(key=get_last_accessed, reverse=True)

    if not show_all:
        # Limit to 10 most recent
        workspaces = workspaces[:10]

    return workspaces


def remove_workspace(session_id: str) -> None:
    """Remove a workspace and all its contents.

    Args:
        session_id: The session identifier.

    Raises:
        ValueError: If workspace doesn't exist.
    """
    if not workspace_exists(session_id):
        raise ValueError(f"Workspace does not exist for session ID: {session_id}")

    workspace_path = get_workspace_path(session_id)
    shutil.rmtree(workspace_path)


def clean_workspaces(older_than_days: int | None = None, remove_all: bool = False) -> dict:
    """Clean up old workspaces.

    Args:
        older_than_days: Remove workspaces not accessed in this many days.
        remove_all: If True, remove all workspaces (overrides older_than_days).

    Returns:
        Dictionary with cleanup statistics:
        {
            "removed_count": int,
            "removed_sessions": list[str],
        }
    """
    workspace_base = get_workspace_base()

    if not workspace_base.exists():
        return {"removed_count": 0, "removed_sessions": []}

    removed_sessions = []

    for workspace_dir in workspace_base.iterdir():
        if not workspace_dir.is_dir():
            continue

        session_id = workspace_dir.name

        # Check if should remove
        should_remove = remove_all

        if not should_remove and older_than_days is not None:
            try:
                info = get_workspace_info(session_id)
                last_accessed = datetime.fromisoformat(info["last_accessed"].rstrip("Z"))
                age = datetime.utcnow() - last_accessed

                if age > timedelta(days=older_than_days):
                    should_remove = True
            except Exception:
                # If can't read metadata, don't remove (play it safe)
                continue

        if should_remove:
            try:
                remove_workspace(session_id)
                removed_sessions.append(session_id)
            except Exception:
                # Skip if removal fails
                continue

    return {
        "removed_count": len(removed_sessions),
        "removed_sessions": removed_sessions,
    }
