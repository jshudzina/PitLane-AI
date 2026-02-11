"""Restrictions for tool calls.

Allows WebFetch calls for a limited set of domains.
"""

import logging
from typing import Any
from urllib.parse import urlparse

from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

from pitlane_agent import tracing

# Module logger
logger = logging.getLogger(__name__)

# Allowed domains for WebFetch tool
ALLOWED_WEBFETCH_DOMAINS = {
    "wikipedia.org",
    "en.wikipedia.org",
    "ergast.com",
    "api.ergast.com",
    "formula1.com",
    "www.formula1.com",
}

# Allowed environment variables for Bash commands
# Only these environment variables can be set when running pitlane CLI commands
ALLOWED_ENV_VARS = {
    "PITLANE_WORKSPACE_ID",
    "PITLANE_CACHE_DIR",
    "PITLANE_TRACING_ENABLED",
    "PITLANE_SPAN_PROCESSOR",
}


def _is_allowed_bash_command(command: str) -> bool:
    """Check if Bash command is allowed (pitlane CLI only).

    Validates that:
    1. Only whitelisted environment variables are used
    2. The command starts with "pitlane "

    Args:
        command: The bash command to validate.

    Returns:
        True if command is allowed, False otherwise.
    """
    if not command:
        return False

    cmd = command.strip()
    parts = cmd.split()

    # Extract and validate environment variables
    env_vars = []
    for i, part in enumerate(parts):
        if "=" not in part:
            # Found the actual command (not an env var assignment)
            cmd = " ".join(parts[i:])
            break
        # Extract env var name before '='
        env_var = part.split("=")[0]
        env_vars.append(env_var)
    else:
        # All parts are env vars, no command
        return False

    # Check if any env var is not in whitelist
    for env_var in env_vars:
        if env_var not in ALLOWED_ENV_VARS:
            return False

    return cmd.startswith("pitlane ")


def _is_within_workspace(file_path: str, workspace_dir: str | None) -> bool:
    """Check if file path is within the workspace directory.

    Args:
        file_path: The file path to validate.
        workspace_dir: The workspace directory path.

    Returns:
        True if file is within workspace, False otherwise.
    """
    if workspace_dir is None:
        return False

    try:
        from pathlib import Path

        file_resolved = Path(file_path).resolve()
        workspace_resolved = Path(workspace_dir).resolve()

        # Check if file_path is within workspace_dir
        return str(file_resolved).startswith(str(workspace_resolved))
    except Exception:
        return False


async def can_use_tool(
    tool_name: str,
    input_params: dict[str, Any],
    context: ToolPermissionContext | dict[str, Any],
) -> PermissionResultAllow | PermissionResultDeny:
    """Validate tool usage with restrictions for Bash, Read, Write, and WebFetch.

    Args:
        tool_name: Name of the tool being invoked.
        input_params: Parameters passed to the tool.
        context: Permission context including workspace directory (dict or ToolPermissionContext).

    Returns:
        PermissionResultAllow if the tool usage is permitted.
        PermissionResultDeny if the tool usage should be blocked.
    """
    # Convert context to dict if needed
    context_dict = context if isinstance(context, dict) else {}

    # Restrict Bash to pitlane CLI only
    if tool_name == "Bash":
        command = input_params.get("command", "")

        if not _is_allowed_bash_command(command):
            denial_msg = (
                "Bash is restricted to 'pitlane' CLI commands only. "
                "Use 'pitlane <subcommand>' to execute F1 data operations."
            )
            logger.warning(
                "Bash permission denied: command not allowed",
                extra={
                    "tool": tool_name,
                    "command": command,
                    "reason": "not_pitlane_command",
                },
            )
            tracing.log_permission_check(tool_name, False, denial_msg)
            return PermissionResultDeny(message=denial_msg)

        return PermissionResultAllow()

    # Restrict Read to workspace paths
    if tool_name == "Read":
        file_path = input_params.get("file_path", "")
        workspace_dir = context_dict.get("workspace_dir")

        if not _is_within_workspace(file_path, workspace_dir):
            denial_msg = f"Read access denied. File must be within workspace directory: {workspace_dir}"
            logger.warning(
                "Read permission denied: file outside workspace",
                extra={
                    "tool": tool_name,
                    "file_path": file_path,
                    "workspace_dir": workspace_dir,
                    "reason": "outside_workspace",
                },
            )
            tracing.log_permission_check(tool_name, False, denial_msg)
            return PermissionResultDeny(message=denial_msg)

        return PermissionResultAllow()

    # Restrict Write to workspace paths
    if tool_name == "Write":
        file_path = input_params.get("file_path", "")
        workspace_dir = context_dict.get("workspace_dir")

        if not _is_within_workspace(file_path, workspace_dir):
            denial_msg = f"Write access denied. File must be within workspace directory: {workspace_dir}"
            logger.warning(
                "Write permission denied: file outside workspace",
                extra={
                    "tool": tool_name,
                    "file_path": file_path,
                    "workspace_dir": workspace_dir,
                    "reason": "outside_workspace",
                },
            )
            tracing.log_permission_check(tool_name, False, denial_msg)
            return PermissionResultDeny(message=denial_msg)

        return PermissionResultAllow()

    # WebFetch domain restrictions (existing logic)
    if tool_name == "WebFetch":
        pass  # Continue to WebFetch validation below
    else:
        # Allow all other tools
        return PermissionResultAllow()

    # Extract URL from WebFetch parameters
    url = input_params.get("url", "")
    if not url:
        denial_msg = "WebFetch requires a URL parameter"
        logger.warning(
            "WebFetch permission denied: missing URL parameter",
            extra={"tool": tool_name, "reason": "missing_url"},
        )
        tracing.log_permission_check(tool_name, False, denial_msg)
        return PermissionResultDeny(message=denial_msg)

    # Parse and validate domain
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove 'www.' prefix for comparison
        domain_base = domain[4:] if domain.startswith("www.") else domain

        # Check if domain or its base is allowed
        if domain in ALLOWED_WEBFETCH_DOMAINS or domain_base in ALLOWED_WEBFETCH_DOMAINS:
            return PermissionResultAllow()

        # Check if it's a subdomain of allowed domains
        for allowed_domain in ALLOWED_WEBFETCH_DOMAINS:
            if domain.endswith(f".{allowed_domain}"):
                return PermissionResultAllow()

        denial_msg = (
            f"Domain '{domain}' is not in the allowed list. "
            f"Allowed domains: {', '.join(sorted(ALLOWED_WEBFETCH_DOMAINS))}"
        )
        logger.warning(
            "WebFetch permission denied: domain not allowed",
            extra={
                "tool": tool_name,
                "domain": domain,
                "url": url,
                "reason": "domain_not_allowed",
            },
        )
        tracing.log_permission_check(tool_name, False, denial_msg)
        return PermissionResultDeny(message=denial_msg)

    except Exception as e:
        denial_msg = f"Failed to parse URL: {e}"
        logger.warning(
            "WebFetch permission denied: invalid URL",
            extra={
                "tool": tool_name,
                "url": url,
                "reason": "parse_error",
                "error": str(e),
            },
        )
        tracing.log_permission_check(tool_name, False, denial_msg)
        return PermissionResultDeny(message=denial_msg)
