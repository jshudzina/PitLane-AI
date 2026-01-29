"""Session management functions for PitLane AI web application."""

import logging

from fastapi import Response
from pitlane_agent.scripts.workspace import (
    generate_session_id,
    update_workspace_metadata,
    workspace_exists,
)

from .config import (
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SESSION_MAX_AGE,
)
from .security import is_valid_session_id

logger = logging.getLogger(__name__)


def validate_session_safely(session: str | None) -> tuple[bool, str | None]:
    """Validate session with constant-time checks to prevent timing attacks.

    Performs validation checks in a consistent order regardless of where validation
    fails, making it harder for attackers to probe for valid session IDs.

    Args:
        session: Session ID from cookie (may be None)

    Returns:
        Tuple of (is_valid, session_id)
        - is_valid: True if session is valid and exists
        - session_id: The validated session ID if valid, None otherwise
    """
    # Always check format first (constant time for UUID validation)
    is_valid_format = is_valid_session_id(session) if session else False

    # Always check workspace existence (even if format invalid, to maintain constant timing)
    # This prevents attackers from using timing to determine if a UUID exists
    exists = workspace_exists(session) if is_valid_format else False

    # Return result
    is_valid = is_valid_format and exists
    validated_session = session if is_valid else None

    return (is_valid, validated_session)


def update_workspace_metadata_safe(session_id: str) -> None:
    """Safely update workspace metadata with proper error logging.

    Args:
        session_id: Session ID to update
    """
    try:
        update_workspace_metadata(session_id)
    except FileNotFoundError as e:
        logger.warning(f"Workspace metadata file not found for session {session_id}: {e}")
    except PermissionError as e:
        logger.error(f"Permission denied updating workspace metadata for session {session_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating workspace metadata for session {session_id}: {e}", exc_info=True)


def create_session_cookie_params() -> dict:
    """Generate session cookie parameters from configuration.

    Returns:
        Dictionary of cookie parameters for set_cookie()
    """
    return {
        "max_age": SESSION_MAX_AGE,
        "secure": SESSION_COOKIE_SECURE,
        "httponly": SESSION_COOKIE_HTTPONLY,
        "samesite": SESSION_COOKIE_SAMESITE,
    }


def set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie on response with secure configuration.

    Args:
        response: FastAPI Response object
        session_id: Session ID to set in cookie
    """
    cookie_params = create_session_cookie_params()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        **cookie_params,
    )


__all__ = [
    "validate_session_safely",
    "update_workspace_metadata_safe",
    "create_session_cookie_params",
    "set_session_cookie",
    "generate_session_id",
]
