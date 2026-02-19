"""Jinja2 filters and text transformation for PitLane AI web application."""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import markdown
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)


def rewrite_workspace_paths(text: str, session_id: str) -> str:
    """Rewrite absolute workspace paths to web-relative URLs.

    Transforms:
      /Users/.../.pitlane/workspaces/{session-id}/charts/lap_times.png
      → /charts/{session-id}/lap_times.png

    Security: Only rewrites paths for the current session to prevent data leaks.

    Args:
        text: Response text containing absolute paths
        session_id: Current session ID

    Returns:
        Text with rewritten paths
    """
    workspace_base = str(Path.home() / ".pitlane" / "workspaces")
    escaped_base = re.escape(workspace_base)

    # Pattern: /path/to/workspaces/{uuid}/{charts|data}/{filename}
    # Support both upper and lowercase UUIDs, stop at whitespace, quotes, or parens
    pattern = rf"{escaped_base}/([a-fA-F0-9\-]+)/(charts|data)/([^\s\)\"\'>]+)"

    rewrite_count = 0

    def replacer(match):
        nonlocal rewrite_count
        matched_session = match.group(1)
        subdir = match.group(2)
        filename = match.group(3)

        # Only rewrite current session's paths (security) - case-insensitive comparison
        if matched_session.lower() == session_id.lower():
            rewrite_count += 1
            rewritten = f"/{subdir}/{matched_session}/{filename}"
            logger.debug(f"Rewriting path: {match.group(0)} -> {rewritten}")
            return rewritten
        logger.debug(f"Skipping path (session mismatch): {matched_session} != {session_id}")
        return match.group(0)

    result = re.sub(pattern, replacer, text)
    if rewrite_count > 0:
        logger.debug(f"Rewrote {rewrite_count} workspace path(s) for session {session_id}")

    return result


def html_charts_to_iframes(text: str) -> str:
    """Convert .html chart references from markdown image syntax to iframe tags.

    Transforms:
      ![label](/charts/{session-id}/chart.html)
      → <iframe src="/charts/{session-id}/chart.html" ...></iframe>

    Also converts img tags with .html src (in case markdown ran first):
      <img ... src="/charts/{session-id}/chart.html" ... />
      → <iframe src="/charts/{session-id}/chart.html" ...></iframe>

    Non-.html references (e.g. .png) are left unchanged.

    Args:
        text: Text potentially containing HTML chart references

    Returns:
        Text with .html chart references converted to iframes
    """
    # Markdown image syntax: ![alt](/charts/session/file.html)
    md_pattern = r"!\[([^\]]*)\]\((/charts/[^\s\)]+\.html)\)"
    text = re.sub(
        md_pattern,
        r'<iframe src="\2" title="\1" width="100%" height="700" style="border:none; border-radius:8px;"></iframe>',
        text,
    )

    # HTML img tags: <img ... src="/charts/.../file.html" ... />
    img_pattern = r'<img[^>]*src="(/charts/[^"]+\.html)"[^>]*/?\s*>'
    text = re.sub(
        img_pattern,
        r'<iframe src="\1" width="100%" height="700" style="border:none; border-radius:8px;"></iframe>',
        text,
    )

    return text


def md_to_html(text: str) -> str:
    """Convert markdown to HTML.

    Args:
        text: Markdown text to convert

    Returns:
        HTML string
    """
    return markdown.markdown(text, extensions=["fenced_code", "tables"])


def timeago(iso_timestamp: str) -> str:
    """Convert ISO timestamp to human-readable relative time.

    Args:
        iso_timestamp: ISO 8601 formatted timestamp string

    Returns:
        Human-readable relative time (e.g., "2 hours ago", "yesterday")
    """
    try:
        # Parse ISO timestamp (handle trailing Z)
        timestamp_str = iso_timestamp.rstrip("Z")
        dt = datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)
        now = datetime.now(UTC)
        delta = now - dt

        seconds = delta.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 172800:
            return "yesterday"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            # For older timestamps, show the date
            return dt.strftime("%b %d, %Y")
    except (ValueError, AttributeError):
        return iso_timestamp


def register_filters(templates: Jinja2Templates) -> None:
    """Register custom Jinja2 filters with the templates instance.

    Args:
        templates: Jinja2Templates instance to register filters with
    """
    templates.env.filters["markdown"] = md_to_html
    templates.env.filters["rewrite_paths"] = rewrite_workspace_paths
    templates.env.filters["html_charts_to_iframes"] = html_charts_to_iframes
    templates.env.filters["timeago"] = timeago


__all__ = [
    "rewrite_workspace_paths",
    "html_charts_to_iframes",
    "md_to_html",
    "timeago",
    "register_filters",
]
