"""Jinja2 filters for PitLane Studio.

Includes the safe_html filter — bleach.clean() wrapped in markupsafe.Markup
so Jinja2 does not double-escape the sanitized HTML. Markdown-oriented
ALLOWED_TAGS (block + inline + table) so markdown-converted prose renders
correctly while XSS payloads are stripped.

Per CLAUDE.md: All `| safe` Jinja2 outputs in pitlane-studio templates MUST
use `| safe_html` instead. Existing pitlane-web templates are out of scope.
"""

import logging
import re

import bleach
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

logger = logging.getLogger(__name__)

# Tags appropriate for markdown-to-HTML output (block + inline + table)
_MARKDOWN_TAGS: frozenset[str] = frozenset(
    {
        "a",
        "abbr",
        "acronym",
        "b",
        "blockquote",
        "br",
        "code",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "s",
        "strong",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }
)

_MARKDOWN_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title"],
    "abbr": ["title"],
    "acronym": ["title"],
}

# Tags whose content (not just the tag) must be removed entirely — XSS vectors
# where the inner text itself is dangerous (e.g. <script>alert(1)</script>).
_STRIP_CONTENT_PATTERN = re.compile(
    r"<(script|style|iframe|object|embed|applet|form|input|button)"
    r"(?:\s[^>]*)?>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


def safe_html(text: str) -> Markup:
    """Sanitize HTML and mark safe for Jinja2 rendering.

    Two-pass approach:
    1. Remove tags whose *content* is itself dangerous (script, style, etc.)
       using a regex pre-pass — bleach strip=True keeps inner text which leaks
       payloads like `alert(1)` even after the tag is stripped.
    2. bleach.clean() with strip=True removes all remaining disallowed tags
       while preserving allowed markdown-output HTML.

    Returns Markup so Jinja2 does not HTML-escape the already-clean output.

    Args:
        text: Untrusted HTML string (e.g. markdown-converted LLM prose).

    Returns:
        Markup-wrapped sanitized HTML safe to render in a template.
    """
    # Pass 1: strip dangerous tags *and* their inner content
    pre_cleaned = _STRIP_CONTENT_PATTERN.sub("", text)

    # Pass 2: bleach strips remaining disallowed tags (keeps inner text, which
    # is safe at this point since script blocks are already gone)
    cleaned = bleach.clean(
        pre_cleaned,
        tags=_MARKDOWN_TAGS,
        attributes=_MARKDOWN_ATTRS,
        strip=True,
    )
    return Markup(cleaned)


def register_filters(templates: Jinja2Templates) -> None:
    """Register custom Jinja2 filters with the templates instance."""
    templates.env.filters["safe_html"] = safe_html


__all__ = ["register_filters", "safe_html"]
