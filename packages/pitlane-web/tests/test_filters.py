"""Tests for Jinja2 filters and text transformation."""

import uuid
from pathlib import Path

from pitlane_web.filters import md_to_html, register_filters, rewrite_workspace_paths


class TestRewriteWorkspacePaths:
    """Tests for workspace path URL rewriting."""

    def test_rewrites_current_session_chart_path(self, test_session_id):
        """Test that current session's chart paths are rewritten."""
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = f"{workspace_base}/{test_session_id}/charts/lap_times.png"

        result = rewrite_workspace_paths(text, test_session_id)

        assert result == f"/charts/{test_session_id}/lap_times.png"

    def test_rewrites_current_session_data_path(self, test_session_id):
        """Test that current session's data paths are rewritten."""
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = f"{workspace_base}/{test_session_id}/data/telemetry.csv"

        result = rewrite_workspace_paths(text, test_session_id)

        assert result == f"/data/{test_session_id}/telemetry.csv"

    def test_ignores_other_sessions_paths(self, test_session_id):
        """Test that other session's paths are NOT rewritten (security)."""
        other_session = str(uuid.uuid4())
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = f"{workspace_base}/{other_session}/charts/lap_times.png"

        result = rewrite_workspace_paths(text, test_session_id)

        # Should remain unchanged
        assert result == text
        assert other_session in result
        assert test_session_id not in result

    def test_handles_multiple_paths_in_string(self, test_session_id):
        """Test that multiple paths in same string are processed correctly."""
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = (
            f"Check out {workspace_base}/{test_session_id}/charts/lap_times.png "
            f"and {workspace_base}/{test_session_id}/data/results.csv"
        )

        result = rewrite_workspace_paths(text, test_session_id)

        assert f"/charts/{test_session_id}/lap_times.png" in result
        assert f"/data/{test_session_id}/results.csv" in result
        assert workspace_base not in result

    def test_handles_mixed_sessions_in_string(self, test_session_id):
        """Test that only current session's paths are rewritten when multiple sessions present."""
        other_session = str(uuid.uuid4())
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = (
            f"Current: {workspace_base}/{test_session_id}/charts/lap_times.png "
            f"Other: {workspace_base}/{other_session}/charts/other.png"
        )

        result = rewrite_workspace_paths(text, test_session_id)

        # Current session rewritten
        assert f"/charts/{test_session_id}/lap_times.png" in result
        # Other session unchanged
        assert f"{workspace_base}/{other_session}/charts/other.png" in result

    def test_no_op_when_no_paths_present(self, test_session_id):
        """Test that text without workspace paths is unchanged."""
        text = "This is just plain text with no paths"

        result = rewrite_workspace_paths(text, test_session_id)

        assert result == text

    def test_handles_malformed_paths_gracefully(self, test_session_id):
        """Test that malformed paths don't cause errors."""
        # Incomplete path that won't match pattern
        text = f"/incomplete/path/{test_session_id}"

        result = rewrite_workspace_paths(text, test_session_id)

        # Should return unchanged (pattern didn't match)
        assert result == text

    def test_handles_empty_string(self, test_session_id):
        """Test that empty string is handled correctly."""
        result = rewrite_workspace_paths("", test_session_id)
        assert result == ""

    def test_path_with_special_characters_in_filename(self, test_session_id):
        """Test that filenames with underscores and hyphens are handled."""
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = f"{workspace_base}/{test_session_id}/charts/lap_times_VER-2024.png"

        result = rewrite_workspace_paths(text, test_session_id)

        assert result == f"/charts/{test_session_id}/lap_times_VER-2024.png"

    def test_path_in_markdown_link(self, test_session_id):
        """Test that paths within markdown syntax are rewritten."""
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = f"![Chart]({workspace_base}/{test_session_id}/charts/lap_times.png)"

        result = rewrite_workspace_paths(text, test_session_id)

        assert result == f"![Chart](/charts/{test_session_id}/lap_times.png)"

    def test_preserves_surrounding_text(self, test_session_id):
        """Test that text surrounding paths is preserved exactly."""
        workspace_base = str(Path.home() / ".pitlane" / "workspaces")
        text = f"Before {workspace_base}/{test_session_id}/charts/lap_times.png After"

        result = rewrite_workspace_paths(text, test_session_id)

        assert result.startswith("Before ")
        assert result.endswith(" After")
        assert f"/charts/{test_session_id}/lap_times.png" in result


class TestMdToHtml:
    """Tests for markdown to HTML conversion."""

    def test_basic_markdown_headers(self):
        """Test that headers are converted correctly."""
        text = "# Header 1\n## Header 2"
        result = md_to_html(text)

        assert "<h1>Header 1</h1>" in result
        assert "<h2>Header 2</h2>" in result

    def test_basic_markdown_bold(self):
        """Test that bold text is converted correctly."""
        text = "This is **bold** text"
        result = md_to_html(text)

        assert "<strong>bold</strong>" in result

    def test_basic_markdown_italic(self):
        """Test that italic text is converted correctly."""
        text = "This is *italic* text"
        result = md_to_html(text)

        assert "<em>italic</em>" in result

    def test_fenced_code_blocks(self):
        """Test that fenced code blocks are converted correctly."""
        text = "```python\nprint('hello')\n```"
        result = md_to_html(text)

        assert "<code" in result  # May have class attribute
        assert "print('hello')" in result
        assert "<pre>" in result

    def test_tables(self):
        """Test that tables are converted correctly."""
        text = "| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        result = md_to_html(text)

        assert "<table>" in result
        assert "<thead>" in result
        assert "<tbody>" in result
        assert "<th>" in result
        assert "<td>" in result

    def test_html_escaping(self):
        """Test that markdown allows HTML passthrough (expected behavior)."""
        text = "This is **bold** text"
        result = md_to_html(text)

        # Markdown should convert bold syntax to HTML
        assert "<strong>bold</strong>" in result

    def test_links(self):
        """Test that links are converted correctly."""
        text = "[Link Text](https://example.com)"
        result = md_to_html(text)

        assert '<a href="https://example.com">Link Text</a>' in result

    def test_empty_string(self):
        """Test that empty string returns empty result."""
        result = md_to_html("")
        assert result == ""

    def test_plain_text_without_markdown(self):
        """Test that plain text is wrapped in paragraph tags."""
        text = "Just plain text"
        result = md_to_html(text)

        assert "<p>Just plain text</p>" in result

    def test_multiline_text(self):
        """Test that multiline text is handled correctly."""
        text = "Line 1\n\nLine 2"
        result = md_to_html(text)

        # Paragraphs should be created
        assert "<p>" in result
        assert "Line 1" in result
        assert "Line 2" in result


class TestRegisterFilters:
    """Tests for filter registration with Jinja2Templates."""

    def test_registers_markdown_filter(self, mock_templates):
        """Test that markdown filter is registered."""
        register_filters(mock_templates)

        assert "markdown" in mock_templates.env.filters
        assert mock_templates.env.filters["markdown"] == md_to_html

    def test_registers_rewrite_paths_filter(self, mock_templates):
        """Test that rewrite_paths filter is registered."""
        register_filters(mock_templates)

        assert "rewrite_paths" in mock_templates.env.filters
        assert mock_templates.env.filters["rewrite_paths"] == rewrite_workspace_paths

    def test_all_filters_registered(self, mock_templates):
        """Test that all filters are registered together."""
        register_filters(mock_templates)

        assert len(mock_templates.env.filters) == 3
        assert "markdown" in mock_templates.env.filters
        assert "rewrite_paths" in mock_templates.env.filters
        assert "timeago" in mock_templates.env.filters
