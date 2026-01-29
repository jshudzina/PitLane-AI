"""Security validation functions for PitLane AI web application."""

import re
import uuid
from pathlib import Path


def is_valid_session_id(session_id: str) -> bool:
    """Validate that session_id is a valid UUID.

    Args:
        session_id: The session ID to validate

    Returns:
        True if session_id is a valid UUID, False otherwise
    """
    if not isinstance(session_id, str):
        return False
    try:
        uuid.UUID(session_id)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def is_safe_filename(filename: str) -> bool:
    """Validate filename using whitelist pattern to prevent path traversal.

    Only allows alphanumeric characters, underscores, hyphens, and dots.
    Prevents path traversal attempts including URL encoding and Unicode normalization.

    Args:
        filename: The filename to validate

    Returns:
        True if filename is safe, False otherwise
    """
    if not filename:
        return False

    # Whitelist pattern: only allow safe characters
    # Letters, numbers, underscore, hyphen, and single dots (for extensions)
    if not re.match(r"^[a-zA-Z0-9_.-]+$", filename):
        return False

    # Additional checks to prevent edge cases
    if filename.startswith(".") or filename.endswith("."):
        return False

    # Double dots still not allowed (prevents traversal attacks)
    return ".." not in filename


def validate_file_path(file_path: Path, workspace_path: Path) -> bool:
    """Validate that resolved file path is within workspace directory.

    Resolves symlinks and verifies the file is within the workspace boundaries.
    This prevents path traversal and symlink attacks.

    Args:
        file_path: The file path to validate
        workspace_path: The workspace directory path

    Returns:
        True if file is within workspace, False otherwise
    """
    try:
        # Reject broken symlinks - check if it's a symlink and the target doesn't exist
        if file_path.is_symlink() and not file_path.exists():
            return False

        resolved_file = file_path.resolve()
        resolved_workspace = workspace_path.resolve()

        # Check if the resolved file path starts with the workspace path
        return str(resolved_file).startswith(str(resolved_workspace))
    except (OSError, RuntimeError):
        # Handle errors during path resolution (broken symlinks, permission errors, etc.)
        return False


def is_allowed_file_extension(file_path: Path, allowed_extensions: set[str]) -> bool:
    """Validate that file extension is in the allowed whitelist.

    Args:
        file_path: The file path to check
        allowed_extensions: Set of allowed file extensions (e.g., {".png", ".jpg"})

    Returns:
        True if extension is allowed, False otherwise
    """
    return file_path.suffix.lower() in allowed_extensions
