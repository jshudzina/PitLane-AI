"""Tests for session management module."""

import time
from unittest.mock import MagicMock, patch

from fastapi import Response
from pitlane_web.session import (
    create_session_cookie_params,
    set_session_cookie,
    update_workspace_metadata_safe,
    validate_session_safely,
)


class TestValidateSessionSafely:
    """Tests for timing-safe session validation."""

    def test_valid_session_with_existing_workspace(self, test_session_id, monkeypatch):
        """Test valid session with existing workspace returns (True, session_id)."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))

        is_valid, validated_session = validate_session_safely(test_session_id)

        assert is_valid is True
        assert validated_session == test_session_id

    def test_invalid_uuid_format(self, monkeypatch):
        """Test invalid UUID format returns (False, None)."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=False))

        is_valid, validated_session = validate_session_safely("not-a-uuid")

        assert is_valid is False
        assert validated_session is None

    def test_valid_uuid_but_nonexistent_workspace(self, test_session_id, monkeypatch):
        """Test valid UUID but non-existent workspace returns (False, None)."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=False))

        is_valid, validated_session = validate_session_safely(test_session_id)

        assert is_valid is False
        assert validated_session is None

    def test_none_input(self, monkeypatch):
        """Test None input returns (False, None)."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=False))

        is_valid, validated_session = validate_session_safely(None)

        assert is_valid is False
        assert validated_session is None

    def test_empty_string(self, monkeypatch):
        """Test empty string returns (False, None)."""
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=False))

        is_valid, validated_session = validate_session_safely("")

        assert is_valid is False
        assert validated_session is None

    def test_workspace_exists_not_called_for_invalid_format(self, monkeypatch):
        """Test workspace_exists is not called when format is invalid (timing safety)."""
        workspace_exists_mock = MagicMock(return_value=False)
        monkeypatch.setattr("pitlane_web.session.workspace_exists", workspace_exists_mock)

        validate_session_safely("not-a-uuid")

        # workspace_exists should not be called for invalid format
        workspace_exists_mock.assert_not_called()

    def test_workspace_exists_called_for_valid_format(self, test_session_id, monkeypatch):
        """Test workspace_exists is called when format is valid."""
        workspace_exists_mock = MagicMock(return_value=True)
        monkeypatch.setattr("pitlane_web.session.workspace_exists", workspace_exists_mock)

        validate_session_safely(test_session_id)

        # workspace_exists should be called for valid format
        workspace_exists_mock.assert_called_once_with(test_session_id)

    def test_timing_consistency_invalid_vs_nonexistent(self, test_session_id, monkeypatch):
        """Test timing is relatively consistent between invalid format and nonexistent workspace.

        This is a basic timing test to ensure there's no obvious timing leak.
        Note: This is not a comprehensive timing attack test, which would require
        statistical analysis over many iterations.
        """
        monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=False))

        # Time invalid format
        start = time.perf_counter()
        for _ in range(100):
            validate_session_safely("not-a-uuid")
        invalid_time = time.perf_counter() - start

        # Time valid format but nonexistent workspace
        start = time.perf_counter()
        for _ in range(100):
            validate_session_safely(test_session_id)
        nonexistent_time = time.perf_counter() - start

        # Times should be relatively similar (within order of magnitude)
        # We're not looking for perfect equality, just no obvious timing leak
        ratio = max(invalid_time, nonexistent_time) / min(invalid_time, nonexistent_time)
        assert ratio < 10.0, f"Timing difference too large: {invalid_time:.6f}s vs {nonexistent_time:.6f}s"


class TestUpdateWorkspaceMetadataSafe:
    """Tests for safe workspace metadata updates."""

    def test_successful_update(self, test_session_id, monkeypatch):
        """Test successful metadata update doesn't raise exception."""
        update_mock = MagicMock()
        monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", update_mock)

        # Should not raise
        update_workspace_metadata_safe(test_session_id)

        update_mock.assert_called_once_with(test_session_id)

    def test_file_not_found_logs_warning(self, test_session_id, monkeypatch, caplog):
        """Test FileNotFoundError is logged as warning and doesn't raise."""
        update_mock = MagicMock(side_effect=FileNotFoundError("Metadata file not found"))
        monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", update_mock)

        # Should not raise
        update_workspace_metadata_safe(test_session_id)

        # Check warning was logged
        assert any("not found" in record.message.lower() for record in caplog.records)
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_permission_error_logs_error(self, test_session_id, monkeypatch, caplog):
        """Test PermissionError is logged as error and doesn't raise."""
        update_mock = MagicMock(side_effect=PermissionError("Access denied"))
        monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", update_mock)

        # Should not raise
        update_workspace_metadata_safe(test_session_id)

        # Check error was logged
        assert any("permission" in record.message.lower() for record in caplog.records)
        assert any(record.levelname == "ERROR" for record in caplog.records)

    def test_generic_exception_logs_with_exc_info(self, test_session_id, monkeypatch, caplog):
        """Test generic exception is logged with exc_info and doesn't raise."""
        update_mock = MagicMock(side_effect=RuntimeError("Unexpected error"))
        monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", update_mock)

        # Should not raise
        update_workspace_metadata_safe(test_session_id)

        # Check error was logged
        assert any("unexpected" in record.message.lower() for record in caplog.records)
        assert any(record.levelname == "ERROR" for record in caplog.records)
        # exc_info should be True for generic exceptions
        assert any(record.exc_info for record in caplog.records)


class TestSessionCookieHelpers:
    """Tests for session cookie helper functions."""

    def test_create_session_cookie_params(self):
        """Test create_session_cookie_params returns correct parameters."""
        params = create_session_cookie_params()

        assert "max_age" in params
        assert "secure" in params
        assert "httponly" in params
        assert "samesite" in params

        # Check types
        assert isinstance(params["max_age"], int)
        assert isinstance(params["secure"], bool)
        assert isinstance(params["httponly"], bool)
        assert isinstance(params["samesite"], str)

        # Check specific values from config
        assert params["httponly"] is True
        assert params["samesite"] == "lax"

    def test_set_session_cookie(self, test_session_id):
        """Test set_session_cookie applies parameters correctly."""
        response = Response()

        set_session_cookie(response, test_session_id)

        # Verify cookie was set
        assert "set-cookie" in response.headers or response.cookies

        # Check the cookie value (method differs based on Response internals)
        if hasattr(response, "cookies"):
            from pitlane_web.config import SESSION_COOKIE_NAME

            # For some FastAPI versions, cookies are in response.cookies
            cookie_set = any(SESSION_COOKIE_NAME in str(cookie) for cookie in response.headers.getlist("set-cookie"))
            assert cookie_set or SESSION_COOKIE_NAME in response.cookies

    def test_set_session_cookie_uses_config_params(self, test_session_id, monkeypatch):
        """Test set_session_cookie uses parameters from create_session_cookie_params."""
        mock_params = {"max_age": 3600, "secure": True, "httponly": True, "samesite": "strict"}

        with patch("pitlane_web.session.create_session_cookie_params", return_value=mock_params):
            response = Response()
            response.set_cookie = MagicMock()

            set_session_cookie(response, test_session_id)

            # Verify set_cookie was called with correct params
            response.set_cookie.assert_called_once()
            call_kwargs = response.set_cookie.call_args[1]

            assert call_kwargs["max_age"] == 3600
            assert call_kwargs["secure"] is True
            assert call_kwargs["httponly"] is True
            assert call_kwargs["samesite"] == "strict"
