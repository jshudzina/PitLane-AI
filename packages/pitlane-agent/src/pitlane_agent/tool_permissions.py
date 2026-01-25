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


async def can_use_tool(
    tool_name: str,
    input_params: dict[str, Any],
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    """Validate tool usage with domain restrictions for WebFetch.

    Args:
        tool_name: Name of the tool being invoked.
        input_params: Parameters passed to the tool.
        context: Permission context including suggestions.

    Returns:
        PermissionResultAllow if the tool usage is permitted.
        PermissionResultDeny if the tool usage should be blocked.
    """
    # Only restrict WebFetch tool
    if tool_name != "WebFetch":
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
