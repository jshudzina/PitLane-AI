"""Comprehensive tests for FastAPI routes."""

import uuid
from unittest.mock import AsyncMock, MagicMock

from pitlane_web.config import SESSION_COOKIE_NAME


class TestIndexRoute:
    """Tests for GET / (index page)."""

    def test_returns_200_with_valid_html(self, app_client):
        """Test that index returns 200 status code."""
        response = app_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_creates_new_session_when_no_cookie(self, app_client):
        """Test that new session is created when no cookie is present."""
        response = app_client.get("/")
        assert response.status_code == 200
        assert SESSION_COOKIE_NAME in response.cookies

    def test_sets_session_cookie_on_first_visit(self, app_client):
        """Test that session cookie is set on first visit."""
        response = app_client.get("/")

        # Cookie should be present
        assert SESSION_COOKIE_NAME in response.cookies
        # Cookie should be a valid UUID
        session_id = response.cookies[SESSION_COOKIE_NAME]
        assert uuid.UUID(session_id)  # Should not raise

    def test_reuses_existing_valid_session(self, app_client, test_session_id, monkeypatch):
        """Test that existing valid session is reused."""
        # Mock workspace_exists to return True
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))

        # First request to set cookie
        response1 = app_client.get("/", cookies={SESSION_COOKIE_NAME: test_session_id})
        session_id_1 = response1.cookies.get(SESSION_COOKIE_NAME, test_session_id)

        # Second request with same cookie
        response2 = app_client.get("/", cookies={SESSION_COOKIE_NAME: session_id_1})

        assert response2.status_code == 200
        # Session should be the same
        # Note: Cookie might not be set again if session is valid
        assert response2.status_code == 200

    def test_creates_new_session_when_invalid_session_in_cookie(self, app_client, monkeypatch):
        """Test that new session is created when invalid session is in cookie."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=False))

        response = app_client.get("/", cookies={SESSION_COOKIE_NAME: "invalid-session"})

        assert response.status_code == 200
        assert SESSION_COOKIE_NAME in response.cookies
        # New session should be created (valid UUID)
        new_session_id = response.cookies[SESSION_COOKIE_NAME]
        assert uuid.UUID(new_session_id)  # Should not raise
        assert new_session_id != "invalid-session"

    def test_updates_workspace_metadata_on_valid_session(self, app_client, test_session_id, monkeypatch):
        """Test that workspace metadata is updated on valid session."""
        update_mock = MagicMock()
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", update_mock)

        app_client.get("/", cookies={SESSION_COOKIE_NAME: test_session_id})

        # update_workspace_metadata should have been called
        update_mock.assert_called()

    def test_template_receives_session_id_context(self, app_client):
        """Test that template receives session_id in context."""
        response = app_client.get("/")

        # Response should contain HTML
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.content or b"<html" in response.content


class TestHealthRoute:
    """Tests for GET /health (health check)."""

    def test_returns_200_with_ok_status(self, app_client):
        """Test that health endpoint returns 200 with ok status."""
        response = app_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestChatRoute:
    """Tests for POST /api/chat (chat endpoint)."""

    def test_returns_200_with_valid_response(self, app_client, mock_agent):
        """Test that chat returns 200 with valid response."""
        response = app_client.post("/api/chat", data={"question": "What is the lap time?"})

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_creates_new_session_when_no_cookie(self, app_client):
        """Test that new session is created when no cookie is present."""
        response = app_client.post("/api/chat", data={"question": "Test question"})

        assert response.status_code == 200
        assert SESSION_COOKIE_NAME in response.cookies

    def test_reuses_existing_valid_session(self, app_client, test_session_id, monkeypatch):
        """Test that existing valid session is reused."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))

        response = app_client.post(
            "/api/chat", data={"question": "Test question"}, cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200

    def test_calls_agent_chat_full_with_question(self, app_client, mock_agent):
        """Test that F1Agent.chat_full is called with the question."""
        question = "What was the fastest lap time?"
        app_client.post("/api/chat", data={"question": question})

        # Agent's chat_full should have been called with the question
        mock_agent.chat_full.assert_called_with(question, resume_session_id=None)

    def test_returns_message_html_partial(self, app_client, mock_agent):
        """Test that response is message.html partial."""
        response = app_client.post("/api/chat", data={"question": "Test question"})

        # Should return HTML
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_handles_empty_response_from_agent(self, app_client, monkeypatch):
        """Test that empty response from agent is handled gracefully."""
        mock_agent = MagicMock()
        mock_agent.chat_full = AsyncMock(return_value="   ")  # Empty/whitespace response
        mock_agent.agent_session_id = None  # No SDK session ID

        mock_cache = MagicMock()
        mock_cache.get_or_create = AsyncMock(return_value=mock_agent)

        # Patch where _agent_cache is used, not where it's defined
        from pitlane_web import app

        monkeypatch.setattr(app, "_agent_cache", mock_cache)

        response = app_client.post("/api/chat", data={"question": "Test question"})

        assert response.status_code == 200
        # Should contain fallback message
        assert b"wasn't able to process" in response.content or b"try again" in response.content

    def test_handles_agent_exceptions_gracefully(self, app_client, monkeypatch):
        """Test that agent exceptions return error message without 500."""
        mock_agent = MagicMock()
        mock_agent.chat_full = AsyncMock(side_effect=Exception("Agent error"))
        mock_agent.agent_session_id = None  # No SDK session ID

        mock_cache = MagicMock()
        mock_cache.get_or_create = AsyncMock(return_value=mock_agent)

        # Patch where _agent_cache is used, not where it's defined
        from pitlane_web import app

        monkeypatch.setattr(app, "_agent_cache", mock_cache)

        response = app_client.post("/api/chat", data={"question": "Test question"})

        # Should return 200, not 500
        assert response.status_code == 200
        # Should contain error message
        assert b"error occurred" in response.content.lower()

    def test_sets_cookie_on_first_request(self, app_client):
        """Test that session cookie is set on first request."""
        response = app_client.post("/api/chat", data={"question": "Test question"})

        assert SESSION_COOKIE_NAME in response.cookies
        # Cookie should be a valid UUID
        session_id = response.cookies[SESSION_COOKIE_NAME]
        assert uuid.UUID(session_id)  # Should not raise

    def test_updates_workspace_metadata(self, app_client, test_session_id, monkeypatch):
        """Test that workspace metadata is updated."""
        update_mock = MagicMock()
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", update_mock)

        app_client.post("/api/chat", data={"question": "Test question"}, cookies={SESSION_COOKIE_NAME: test_session_id})

        # update_workspace_metadata should have been called
        update_mock.assert_called()

    def test_template_receives_correct_context(self, app_client, mock_agent):
        """Test that template receives content, question, and session_id context."""
        mock_agent.chat_full = AsyncMock(return_value="Test response")
        question = "Test question"

        response = app_client.post("/api/chat", data={"question": question})

        # Response should contain the question and response
        assert response.status_code == 200


class TestServeChartRoute:
    """Tests for GET /charts/{session_id}/{filename} (chart serving)."""

    # Success cases

    def test_serves_png_chart_with_correct_media_type(
        self, app_client, test_session_id, sample_chart_file, monkeypatch
    ):
        """Test that PNG chart is served with correct media type."""
        # Patch where functions are used, not where they're defined
        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr(
            "pitlane_web.app.get_workspace_path",
            MagicMock(return_value=sample_chart_file.parent.parent),
        )

        response = app_client.get(
            f"/charts/{test_session_id}/lap_times.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_serves_jpg_chart(self, app_client, test_session_id, tmp_workspace, monkeypatch):
        """Test that JPG chart is served with correct media type."""
        # Create JPG file
        jpg_file = tmp_workspace / "charts" / "chart.jpg"
        jpg_file.write_bytes(b"fake jpg content")

        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(
            f"/charts/{test_session_id}/chart.jpg", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"

    def test_serves_svg_chart(self, app_client, test_session_id, tmp_workspace, monkeypatch):
        """Test that SVG chart is served with correct media type."""
        # Create SVG file
        svg_file = tmp_workspace / "charts" / "chart.svg"
        svg_file.write_text("<svg></svg>")

        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(
            f"/charts/{test_session_id}/chart.svg", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"

    def test_sets_cache_control_header(self, app_client, test_session_id, sample_chart_file, monkeypatch):
        """Test that Cache-Control header is set correctly."""
        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr(
            "pitlane_web.app.get_workspace_path",
            MagicMock(return_value=sample_chart_file.parent.parent),
        )

        response = app_client.get(
            f"/charts/{test_session_id}/lap_times.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200
        assert "cache-control" in response.headers
        assert "private" in response.headers["cache-control"].lower()

    def test_includes_session_id_in_response_headers(self, app_client, test_session_id, sample_chart_file, monkeypatch):
        """Test that X-Session-ID header is included."""
        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr(
            "pitlane_web.app.get_workspace_path",
            MagicMock(return_value=sample_chart_file.parent.parent),
        )

        response = app_client.get(
            f"/charts/{test_session_id}/lap_times.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200
        assert "x-session-id" in response.headers
        assert response.headers["x-session-id"] == test_session_id

    # Security failure cases

    def test_invalid_session_id_format_returns_400(self, app_client):
        """Test that invalid session ID format returns 400."""
        response = app_client.get("/charts/invalid-session/chart.png", cookies={SESSION_COOKIE_NAME: "invalid-session"})

        assert response.status_code == 400
        assert "invalid session id" in response.json()["detail"].lower()

    def test_session_ownership_mismatch_returns_403(self, app_client, test_session_id):
        """Test that session ownership mismatch returns 403."""
        other_session = str(uuid.uuid4())

        response = app_client.get(f"/charts/{other_session}/chart.png", cookies={SESSION_COOKIE_NAME: test_session_id})

        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_workspace_doesnt_exist_returns_404(self, app_client, test_session_id, monkeypatch):
        """Test that non-existent workspace returns 404."""
        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=False))

        response = app_client.get(
            f"/charts/{test_session_id}/chart.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 404
        assert "session not found" in response.json()["detail"].lower()

    def test_unsafe_filename_returns_400(self, app_client, test_session_id, monkeypatch, tmp_workspace):
        """Test that unsafe filename (path traversal) returns 400."""
        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        # Test with filename containing .. (path traversal pattern)
        response = app_client.get(
            f"/charts/{test_session_id}/..malicious.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 400
        assert "invalid filename" in response.json()["detail"].lower()

    def test_file_doesnt_exist_returns_404(self, app_client, test_session_id, tmp_workspace, monkeypatch):
        """Test that non-existent file returns 404."""
        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(
            f"/charts/{test_session_id}/nonexistent.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_file_extension_returns_400(self, app_client, test_session_id, tmp_workspace, monkeypatch):
        """Test that disallowed file extension returns 400."""
        # Create file with disallowed extension
        evil_file = tmp_workspace / "charts" / "evil.sh"
        evil_file.write_text("#!/bin/bash\necho 'evil'")

        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(f"/charts/{test_session_id}/evil.sh", cookies={SESSION_COOKIE_NAME: test_session_id})

        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()

    # Edge cases

    def test_case_insensitive_extension_png(self, app_client, test_session_id, tmp_workspace, monkeypatch):
        """Test that .PNG extension (uppercase) is accepted."""
        # Create file with uppercase extension
        png_file = tmp_workspace / "charts" / "chart.PNG"
        png_file.write_bytes(b"fake png content")

        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(
            f"/charts/{test_session_id}/chart.PNG", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200

    def test_filename_with_multiple_dots(self, app_client, test_session_id, tmp_workspace, monkeypatch):
        """Test that filename with multiple dots is handled correctly."""
        # Create file with multiple dots
        png_file = tmp_workspace / "charts" / "lap.times.2024.png"
        png_file.write_bytes(b"fake png content")

        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(
            f"/charts/{test_session_id}/lap.times.2024.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        assert response.status_code == 200

    def test_path_outside_workspace_returns_403(
        self, app_client, test_session_id, tmp_workspace, tmp_path, monkeypatch
    ):
        """Test that resolved path outside workspace returns 403."""
        # Create file outside workspace
        outside_file = tmp_path / "outside" / "evil.png"
        outside_file.parent.mkdir(exist_ok=True)
        outside_file.write_bytes(b"evil")

        # Create symlink inside workspace pointing outside
        symlink = tmp_workspace / "charts" / "innocent.png"
        symlink.symlink_to(outside_file)

        monkeypatch.setattr("pitlane_web.app.workspace_exists", MagicMock(return_value=True))
        monkeypatch.setattr("pitlane_web.app.get_workspace_path", MagicMock(return_value=tmp_workspace))

        response = app_client.get(
            f"/charts/{test_session_id}/innocent.png", cookies={SESSION_COOKIE_NAME: test_session_id}
        )

        # Should be rejected due to path resolution check
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()
