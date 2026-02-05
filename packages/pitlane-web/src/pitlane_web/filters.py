"""Jinja2 filters and text transformation for PitLane AI web application."""

import re
from datetime import UTC, datetime
from pathlib import Path

import markdown
from fastapi.templating import Jinja2Templates


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
    pattern = rf"{escaped_base}/([a-f0-9\-]+)/(charts|data)/([^\s\)]+)"

    def replacer(match):
        matched_session = match.group(1)
        subdir = match.group(2)
        filename = match.group(3)

        # Only rewrite current session's paths (security)
        if matched_session == session_id:
            return f"/{subdir}/{matched_session}/{filename}"
        return match.group(0)

    return re.sub(pattern, replacer, text)


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
    templates.env.filters["timeago"] = timeago


__all__ = ["rewrite_workspace_paths", "md_to_html", "timeago", "register_filters"]
