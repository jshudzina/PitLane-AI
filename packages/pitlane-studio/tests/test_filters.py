"""PKG-03 unit test — safe_html filter sanitizes XSS via bleach.clean()."""

from __future__ import annotations

import pytest


def test_script_tag_is_stripped():
    """<script>alert(1)</script> is stripped — XSS payload removed."""
    from markupsafe import Markup

    from pitlane_studio.filters import safe_html

    result = safe_html("<script>alert(1)</script>hello")
    assert isinstance(result, Markup)
    assert "<script>" not in str(result)
    assert "alert(1)" not in str(result)
    assert "hello" in str(result)


def test_allowed_markdown_tags_pass_through():
    """<p>, <h1>, <strong>, <a href> are preserved."""
    from pitlane_studio.filters import safe_html

    result = str(safe_html('<p>x</p><h1>y</h1><strong>z</strong><a href="https://x">l</a>'))
    assert "<p>x</p>" in result
    assert "<h1>y</h1>" in result
    assert "<strong>z</strong>" in result
    assert 'href="https://x"' in result


def test_returns_markup_not_str():
    """Filter returns markupsafe.Markup, not plain str (else Jinja2 double-escapes)."""
    from markupsafe import Markup

    from pitlane_studio.filters import safe_html

    assert isinstance(safe_html("hello"), Markup)


def test_disallowed_block_tag_stripped():
    """<div> tag is stripped (strip=True), inner text preserved."""
    from pitlane_studio.filters import safe_html

    result = str(safe_html("<div>content</div>"))
    assert "<div>" not in result
    assert "content" in result


def test_javascript_protocol_anchor_stripped():
    """<a href='javascript:...'> protocol is stripped by bleach default ALLOWED_PROTOCOLS."""
    from pitlane_studio.filters import safe_html

    result = str(safe_html('<a href="javascript:alert(1)">click</a>'))
    assert "javascript:" not in result
    assert "click" in result


def test_table_tags_preserved():
    """Markdown table family tags are in ALLOWED_TAGS."""
    from pitlane_studio.filters import safe_html

    result = str(safe_html("<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>d</td></tr></tbody></table>"))
    for tag in ["<table>", "<thead>", "<tr>", "<th>", "<tbody>", "<td>"]:
        assert tag in result
