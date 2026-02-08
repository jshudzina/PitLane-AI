"""Workspace management functions for PitLane AI.

This module provides utilities for creating, managing, and cleaning up
workspace directories used by the F1Agent.
"""

import json
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


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


def create_workspace(session_id: str | None = None, description: str | None = None, max_retries: int = 3) -> dict:
    """Create a new workspace directory structure.

    Implements collision retry logic for auto-generated session IDs.

    Args:
        session_id: Session identifier. Auto-generated if None.
        description: Optional description for the workspace.
        max_retries: Maximum retry attempts for UUID collision (default: 3).

    Returns:
        Dictionary with workspace information:
        {
            "session_id": str,
            "workspace_path": str,
            "created_at": str,
        }

    Raises:
        ValueError: If workspace already exists for the given session_id.
        RuntimeError: If failed to generate unique session ID after max_retries.
    """
    if session_id is not None:
        # Explicit session_id provided - no retry logic
        if workspace_exists(session_id):
            raise ValueError(f"Workspace already exists for session ID: {session_id}")
        return _create_workspace_internal(session_id, description)

    # Auto-generate session ID with collision retry
    for _attempt in range(max_retries):
        session_id = generate_session_id()
        if not workspace_exists(session_id):
            return _create_workspace_internal(session_id, description)

    raise RuntimeError(f"Failed to generate unique session ID after {max_retries} attempts")


def _create_workspace_internal(session_id: str, description: str | None) -> dict:
    """Internal workspace creation logic.

    Args:
        session_id: The session identifier.
        description: Optional description for the workspace.

    Returns:
        Dictionary with workspace information.
    """
    workspace_path = get_workspace_path(session_id)

    # Create directory structure
    workspace_path.mkdir(parents=True, exist_ok=False)
    (workspace_path / "data").mkdir(exist_ok=True)
    (workspace_path / "charts").mkdir(exist_ok=True)

    # Ensure shared cache exists
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)

    # Write metadata
    metadata = {
        "session_id": session_id,
        "created_at": now.isoformat() + "Z",
        "last_accessed": now.isoformat() + "Z",
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

    # Read existing metadata or create new
    if not metadata_path.exists():
        # Metadata missing, recreate it
        now = datetime.now(UTC)
        metadata = {
            "session_id": session_id,
            "created_at": now.isoformat() + "Z",
            "last_accessed": now.isoformat() + "Z",
        }
    else:
        with open(metadata_path) as f:
            metadata = json.load(f)

        metadata["last_accessed"] = datetime.now(UTC).isoformat() + "Z"

    # Atomic write using tempfile + rename
    # Create temp file in same directory to ensure same filesystem
    fd, temp_path = tempfile.mkstemp(dir=workspace_path, prefix=".metadata.tmp.", suffix=".json")

    try:
        with os.fdopen(fd, "w") as f:
            json.dump(metadata, f, indent=2)

        # Atomic rename (POSIX guarantee)
        os.replace(temp_path, metadata_path)
    except Exception:
        # Clean up temp file on error
        with suppress(Exception):
            os.unlink(temp_path)
        raise


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
                last_accessed = datetime.fromisoformat(info["last_accessed"].rstrip("Z")).replace(tzinfo=UTC)
                age = datetime.now(UTC) - last_accessed

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


# =============================================================================
# Conversation Management
# =============================================================================


def get_conversations_path(session_id: str) -> Path:
    """Get path to conversations.json for a workspace.

    Args:
        session_id: The web session identifier.

    Returns:
        Path to the conversations.json file.
    """
    return get_workspace_path(session_id) / "conversations.json"


def load_conversations(session_id: str) -> dict:
    """Load conversation metadata for a workspace.

    Args:
        session_id: The web session identifier.

    Returns:
        Dictionary with version, active_conversation_id, and conversations list.
        Returns empty structure if file doesn't exist.
    """
    conversations_path = get_conversations_path(session_id)

    if not conversations_path.exists():
        return {
            "version": 1,
            "active_conversation_id": None,
            "conversations": [],
        }

    try:
        with open(conversations_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Return empty structure on corruption
        return {
            "version": 1,
            "active_conversation_id": None,
            "conversations": [],
        }


def save_conversations(session_id: str, data: dict) -> None:
    """Save conversation metadata atomically.

    Args:
        session_id: The web session identifier.
        data: The conversation data dictionary to save.

    Raises:
        ValueError: If workspace doesn't exist.
    """
    if not workspace_exists(session_id):
        raise ValueError(f"Workspace does not exist for session ID: {session_id}")

    conversations_path = get_conversations_path(session_id)
    workspace_path = get_workspace_path(session_id)

    # Atomic write using tempfile + rename
    fd, temp_path = tempfile.mkstemp(
        dir=workspace_path,
        prefix=".conversations.tmp.",
        suffix=".json",
    )

    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, conversations_path)
    except Exception:
        with suppress(Exception):
            os.unlink(temp_path)
        raise


def _generate_title(message: str, max_length: int = 50) -> str:
    """Generate a title from the first message.

    Args:
        message: The user's first message.
        max_length: Maximum title length.

    Returns:
        A truncated title suitable for display.
    """
    # Remove extra whitespace
    clean = " ".join(message.split())
    if len(clean) <= max_length:
        return clean
    # Truncate at word boundary
    truncated = clean[:max_length].rsplit(" ", 1)[0]
    return truncated + "..."


def create_conversation(
    session_id: str,
    agent_session_id: str,
    first_message: str,
) -> dict:
    """Create a new conversation entry.

    Args:
        session_id: Web session ID (workspace identifier).
        agent_session_id: Claude SDK session ID for resumption.
        first_message: First user message (used for title/preview).

    Returns:
        The created conversation dict.

    Raises:
        ValueError: If workspace doesn't exist.
    """
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat() + "Z"

    conversation = {
        "id": conv_id,
        "agent_session_id": agent_session_id,
        "title": _generate_title(first_message),
        "created_at": now,
        "last_message_at": now,
        "message_count": 1,
        "preview": first_message[:100] + ("..." if len(first_message) > 100 else ""),
    }

    data = load_conversations(session_id)
    data["conversations"].insert(0, conversation)  # Most recent first
    data["active_conversation_id"] = conv_id
    save_conversations(session_id, data)

    return conversation


def update_conversation(
    session_id: str,
    conversation_id: str,
    message_count_delta: int = 1,
) -> None:
    """Update conversation metadata after a message.

    Args:
        session_id: Web session ID (workspace identifier).
        conversation_id: The conversation to update.
        message_count_delta: Number of messages to add to count.
    """
    data = load_conversations(session_id)

    found = False
    for conv in data["conversations"]:
        if conv["id"] == conversation_id:
            conv["last_message_at"] = datetime.now(UTC).isoformat() + "Z"
            conv["message_count"] += message_count_delta
            found = True
            break

    if not found:
        logger.warning(f"Conversation {conversation_id} not found in session {session_id}")
        return

    save_conversations(session_id, data)


def get_active_conversation(session_id: str) -> dict | None:
    """Get the currently active conversation for a workspace.

    Args:
        session_id: Web session ID (workspace identifier).

    Returns:
        The active conversation dict, or None if no active conversation.
    """
    data = load_conversations(session_id)
    active_id = data.get("active_conversation_id")

    if not active_id:
        return None

    for conv in data["conversations"]:
        if conv["id"] == active_id:
            return conv
    return None


def set_active_conversation(session_id: str, conversation_id: str | None) -> None:
    """Set the active conversation for a workspace.

    Args:
        session_id: Web session ID (workspace identifier).
        conversation_id: The conversation ID to set as active, or None to clear.
    """
    data = load_conversations(session_id)
    data["active_conversation_id"] = conversation_id
    save_conversations(session_id, data)
