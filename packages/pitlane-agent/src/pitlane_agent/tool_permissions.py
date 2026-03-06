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

# FastF1 makes direct HTTP calls (not via Claude tools). These domains cannot
# be filtered by the SDK bash sandbox without a proxy (see follow-up issue).
FASTF1_NETWORK_DOMAINS = [
    "livetiming.formula1.com",  # F1 live timing primary source
    "livetiming-static.formula1.com",  # Static live timing files
    "api.formula1.com",  # F1 official API (fastf1 >= 3.4)
    "api.ergast.com",  # Historical data (legacy, still used)
    "raw.githubusercontent.com",  # fastf1 datasets (driver numbers, etc.)
]

# Allowed domains for WebFetch tool
ALLOWED_WEBFETCH_DOMAINS = {
    "wikipedia.org",
    "en.wikipedia.org",
    "ergast.com",
    "api.ergast.com",
    "formula1.com",
    "www.formula1.com",
    "www.fia.com",
    "api.fia.com",
}

# Allowed domains for WebSearch tool
ALLOWED_WEBSEARCH_DOMAINS = {
    "wikipedia.org",
    "en.wikipedia.org",
    "formula1.com",
    "www.formula1.com",
    "www.fia.com",
    "api.fia.com",
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

    if cmd.startswith("pitlane "):
        return True

    # Allow echoing whitelisted environment variables (exactly: echo $VARNAME)
    echo_parts = cmd.split()
    if len(echo_parts) == 2 and echo_parts[0] == "echo" and echo_parts[1].startswith("$"):
        var_name = echo_parts[1][1:]
        return var_name in ALLOWED_ENV_VARS

    return False


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
        return file_resolved.is_relative_to(workspace_resolved)
    except Exception:
        return False


def make_can_use_tool_callback(workspace_dir: str, workspace_id: str, skills_dir: str | None = None):
    """Create a can_use_tool callback pre-loaded with workspace context.

    Args:
        workspace_dir: Absolute path to the workspace directory.
        workspace_id: Workspace identifier.
        skills_dir: Absolute path to the skills/package directory (read-only).

    Returns:
        Async callable suitable for ClaudeAgentOptions.can_use_tool.
    """

    async def can_use_tool_with_context(tool_name, input_params, _context):
        return await can_use_tool(
            tool_name,
            input_params,
            {"workspace_dir": workspace_dir, "workspace_id": workspace_id, "skills_dir": skills_dir},
        )

    return can_use_tool_with_context


def make_pre_tool_use_hook(workspace_dir: str, workspace_id: str, skills_dir: str | None = None):
    """Create a PreToolUse hook that enforces permissions and optional tracing.

    This hook must be used (not can_use_tool alone) for tools listed in
    allowed_tools, because the SDK skips the can_use_tool callback for them.

    Args:
        workspace_dir: Absolute path to the workspace directory.
        workspace_id: Workspace identifier.
        skills_dir: Absolute path to the skills/package directory (read-only).

    Returns:
        Async callable suitable for a PreToolUse HookMatcher.
    """

    async def permission_and_tracing_hook(hook_input, tool_use_id, hook_context):
        tool_name = hook_input["tool_name"]
        tool_input = hook_input["tool_input"]
        key_param = tracing.extract_key_param(tool_name, tool_input)

        result = await can_use_tool(
            tool_name,
            tool_input,
            {"workspace_dir": workspace_dir, "workspace_id": workspace_id, "skills_dir": skills_dir},
        )
        if isinstance(result, PermissionResultDeny):
            logger.warning("Tool use denied: %s %s — %s", tool_name, key_param, result.message)
            if tracing.is_tracing_enabled():
                tracing.log_tool_call(
                    tool_name,
                    {
                        "tool.key_param": key_param,
                        "tool.permission": "denied",
                        "tool.denial_reason": result.message,
                    },
                )
            return {
                "continue_": False,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": result.message,
                },
            }

        if tracing.is_tracing_enabled():
            tracing.log_tool_call(tool_name, {"tool.key_param": key_param})
        return {"continue_": True}

    return permission_and_tracing_hook


async def can_use_tool(
    tool_name: str,
    input_params: dict[str, Any],
    context: ToolPermissionContext | dict[str, Any],
) -> PermissionResultAllow | PermissionResultDeny:
    """Validate tool usage with restrictions for Bash, Read, Write, WebFetch, and WebSearch.

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
                "The 'pitlane' binary is available directly in PATH — "
                "use 'pitlane <subcommand>' without 'cd', 'uv run', or other wrappers. "
                "Example: 'pitlane fetch session-info --year 2026 --gp Australia --session FP2'"
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

    # Restrict Read to workspace paths or skills directory
    if tool_name == "Read":
        file_path = input_params.get("file_path", "")
        workspace_dir = context_dict.get("workspace_dir")
        skills_dir = context_dict.get("skills_dir")

        if _is_within_workspace(file_path, workspace_dir) or _is_within_workspace(file_path, skills_dir):
            return PermissionResultAllow()

        denial_msg = f"Read access denied. File must be within workspace directory ({workspace_dir})" + (
            f" or skills directory ({skills_dir})" if skills_dir else ""
        )
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

    # WebSearch domain restrictions
    if tool_name == "WebSearch":
        allowed_domains = input_params.get("allowed_domains")

        if not allowed_domains:
            denial_msg = (
                "WebSearch requires 'allowed_domains' to be specified. "
                f"Allowed domains: {', '.join(sorted(ALLOWED_WEBSEARCH_DOMAINS))}"
            )
            logger.warning(
                "WebSearch permission denied: allowed_domains not specified",
                extra={"tool": tool_name, "reason": "missing_allowed_domains"},
            )
            tracing.log_permission_check(tool_name, False, denial_msg)
            return PermissionResultDeny(message=denial_msg)

        disallowed = [d for d in allowed_domains if d not in ALLOWED_WEBSEARCH_DOMAINS]
        if disallowed:
            denial_msg = (
                f"WebSearch domain(s) not allowed: {', '.join(disallowed)}. "
                f"Allowed domains: {', '.join(sorted(ALLOWED_WEBSEARCH_DOMAINS))}"
            )
            logger.warning(
                "WebSearch permission denied: domain not allowed",
                extra={
                    "tool": tool_name,
                    "disallowed_domains": disallowed,
                    "reason": "domain_not_allowed",
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
