"""Comprehensive security validation tests."""

import uuid
from pathlib import Path

from pitlane_web.security import (
    is_allowed_file_extension,
    is_safe_filename,
    is_valid_session_id,
    validate_file_path,
)


class TestIsValidSessionId:
    """Tests for session ID UUID validation."""

    def test_valid_uuidv4(self):
        """Test that valid UUIDv4 is accepted."""
        session_id = str(uuid.uuid4())
        assert is_valid_session_id(session_id) is True

    def test_valid_uuid_with_uppercase(self):
        """Test that UUID with uppercase letters is accepted."""
        session_id = str(uuid.uuid4()).upper()
        assert is_valid_session_id(session_id) is True

    def test_invalid_format(self, invalid_session_ids):
        """Test that invalid formats are rejected."""
        for invalid_id in invalid_session_ids:
            if invalid_id is not None and isinstance(invalid_id, str):
                assert is_valid_session_id(invalid_id) is False

    def test_none_input(self):
        """Test that None is rejected."""
        assert is_valid_session_id(None) is False

    def test_empty_string(self):
        """Test that empty string is rejected."""
        assert is_valid_session_id("") is False

    def test_integer_input(self):
        """Test that integer input is rejected."""
        assert is_valid_session_id(123) is False

    def test_path_traversal_attempt(self):
        """Test that path traversal attempts are rejected."""
        assert is_valid_session_id("../../../etc/passwd") is False

    def test_uuid_too_short(self):
        """Test that UUID that's too short is rejected."""
        assert is_valid_session_id("00000000-0000-0000-0000-00000000000") is False

    def test_uuid_too_long(self):
        """Test that UUID that's too long is rejected."""
        assert is_valid_session_id("00000000-0000-0000-0000-0000000000000") is False


class TestIsSafeFilename:
    """Tests for filename validation and path traversal prevention."""

    # Valid filenames that should pass
    def test_simple_filename(self):
        """Test simple filename is accepted."""
        assert is_safe_filename("chart.png") is True

    def test_filename_with_underscore(self):
        """Test filename with underscore is accepted."""
        assert is_safe_filename("lap_times.png") is True

    def test_filename_with_hyphen(self):
        """Test filename with hyphen is accepted."""
        assert is_safe_filename("data-2024.csv") is True

    def test_filename_with_numbers(self):
        """Test filename with numbers is accepted."""
        assert is_safe_filename("chart123.png") is True

    def test_filename_with_uppercase(self):
        """Test filename with uppercase is accepted."""
        assert is_safe_filename("LapTimes_VER.png") is True

    def test_filename_with_single_dot_extension(self):
        """Test filename with single dot extension is accepted."""
        assert is_safe_filename("file.png") is True

    def test_filename_with_multiple_dots_valid(self):
        """Test filename with multiple dots but valid pattern is accepted."""
        assert is_safe_filename("file.name.123.png") is True

    # Invalid filenames that should fail
    def test_empty_filename(self):
        """Test empty filename is rejected."""
        assert is_safe_filename("") is False

    def test_none_filename(self):
        """Test None filename is rejected."""
        assert is_safe_filename(None) is False

    def test_basic_path_traversal(self):
        """Test basic path traversal is rejected."""
        assert is_safe_filename("../../../etc/passwd") is False

    def test_single_parent_directory(self):
        """Test single parent directory reference is rejected."""
        assert is_safe_filename("../file.png") is False

    def test_url_encoded_traversal(self):
        """Test URL encoded path traversal is rejected."""
        assert is_safe_filename("..%2F..%2Fetc%2Fpasswd") is False

    def test_double_url_encoded_traversal(self):
        """Test double URL encoded traversal is rejected."""
        assert is_safe_filename("..%252F..%252Fetc") is False

    def test_leading_dot(self):
        """Test filename with leading dot is rejected."""
        assert is_safe_filename(".hidden") is False

    def test_trailing_dot(self):
        """Test filename with trailing dot is rejected."""
        assert is_safe_filename("file.") is False

    def test_consecutive_dots(self):
        """Test filename with consecutive dots is rejected."""
        assert is_safe_filename("file..name") is False

    def test_double_dots_in_middle(self):
        """Test filename with .. in middle is rejected."""
        assert is_safe_filename("file..png") is False

    def test_directory_separator_forward_slash(self):
        """Test filename with forward slash is rejected."""
        assert is_safe_filename("path/traversal.png") is False

    def test_directory_separator_backslash(self):
        """Test filename with backslash is rejected."""
        assert is_safe_filename("path\\traversal.png") is False

    def test_null_byte_injection(self):
        """Test null byte injection is rejected."""
        assert is_safe_filename("safe.png\x00../../evil.sh") is False

    def test_special_characters(self):
        """Test filename with special characters is rejected."""
        assert is_safe_filename("file@#$.png") is False

    def test_spaces(self):
        """Test filename with spaces is rejected."""
        assert is_safe_filename("file name.png") is False

    def test_unicode_characters(self):
        """Test filename with unicode characters is rejected."""
        assert is_safe_filename("file™.png") is False

    def test_parentheses(self):
        """Test filename with parentheses is rejected."""
        assert is_safe_filename("file(1).png") is False

    def test_only_dots(self):
        """Test filename with only dots is rejected."""
        assert is_safe_filename("...") is False

    def test_current_directory_reference(self):
        """Test current directory reference is rejected."""
        assert is_safe_filename("./file.png") is False


class TestValidateFilePath:
    """Tests for file path validation within workspace."""

    def test_file_in_workspace(self, tmp_workspace):
        """Test file within workspace is accepted."""
        file_path = tmp_workspace / "charts" / "lap_times.png"
        assert validate_file_path(file_path, tmp_workspace) is True

    def test_file_in_workspace_subdirectory(self, tmp_workspace):
        """Test file in workspace subdirectory is accepted."""
        subdir = tmp_workspace / "charts" / "2024"
        subdir.mkdir()
        file_path = subdir / "race.png"
        assert validate_file_path(file_path, tmp_workspace) is True

    def test_file_equals_workspace(self, tmp_workspace):
        """Test when file path equals workspace path."""
        # This edge case should be handled - workspace root is technically "in" workspace
        assert validate_file_path(tmp_workspace, tmp_workspace) is True

    def test_file_outside_workspace(self, tmp_workspace, tmp_path):
        """Test file outside workspace is rejected."""
        outside_file = tmp_path / "outside" / "evil.sh"
        outside_file.parent.mkdir()
        outside_file.write_text("malicious code")
        assert validate_file_path(outside_file, tmp_workspace) is False

    def test_symlink_outside_workspace(self, tmp_workspace, tmp_path):
        """Test symlink pointing outside workspace is rejected."""
        # Create a file outside workspace
        outside_file = tmp_path / "outside" / "evil.sh"
        outside_file.parent.mkdir()
        outside_file.write_text("malicious code")

        # Create symlink inside workspace pointing to outside file
        symlink = tmp_workspace / "charts" / "innocent.png"
        symlink.symlink_to(outside_file)

        # Should be rejected because resolved path is outside workspace
        assert validate_file_path(symlink, tmp_workspace) is False

    def test_path_traversal_via_relative_path(self, tmp_workspace):
        """Test path traversal using ../.. is rejected."""
        traversal_path = tmp_workspace / "charts" / ".." / ".." / "etc" / "passwd"
        assert validate_file_path(traversal_path, tmp_workspace) is False

    def test_broken_symlink(self, tmp_workspace):
        """Test broken symlink is rejected."""
        symlink = tmp_workspace / "charts" / "broken.png"
        symlink.symlink_to(tmp_workspace / "nonexistent" / "file.png")

        # Should be rejected due to resolution error
        assert validate_file_path(symlink, tmp_workspace) is False

    def test_permission_error(self, tmp_workspace, monkeypatch):
        """Test that permission errors during resolution are handled."""

        def mock_resolve():
            raise PermissionError("Access denied")

        file_path = tmp_workspace / "charts" / "test.png"
        monkeypatch.setattr(Path, "resolve", lambda self: mock_resolve())

        # Should be rejected due to resolution error
        assert validate_file_path(file_path, tmp_workspace) is False


class TestIsAllowedFileExtension:
    """Tests for file extension whitelist validation."""

    def test_allowed_png_lowercase(self, tmp_path):
        """Test .png extension is allowed."""
        file_path = tmp_path / "chart.png"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is True

    def test_allowed_jpg(self, tmp_path):
        """Test .jpg extension is allowed."""
        file_path = tmp_path / "chart.jpg"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is True

    def test_allowed_svg(self, tmp_path):
        """Test .svg extension is allowed."""
        file_path = tmp_path / "chart.svg"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is True

    def test_case_insensitive_png_uppercase(self, tmp_path):
        """Test .PNG extension is allowed (case insensitive)."""
        file_path = tmp_path / "chart.PNG"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is True

    def test_case_insensitive_mixed_case(self, tmp_path):
        """Test .Png extension is allowed (case insensitive)."""
        file_path = tmp_path / "chart.Png"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is True

    def test_disallowed_extension_exe(self, tmp_path):
        """Test .exe extension is rejected."""
        file_path = tmp_path / "malware.exe"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is False

    def test_disallowed_extension_sh(self, tmp_path):
        """Test .sh extension is rejected."""
        file_path = tmp_path / "script.sh"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is False

    def test_disallowed_extension_py(self, tmp_path):
        """Test .py extension is rejected."""
        file_path = tmp_path / "script.py"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is False

    def test_no_extension(self, tmp_path):
        """Test file without extension is rejected."""
        file_path = tmp_path / "noextension"
        allowed = {".png", ".jpg", ".svg"}
        assert is_allowed_file_extension(file_path, allowed) is False

    def test_multiple_extensions_uses_last(self, tmp_path):
        """Test file with multiple extensions uses the last one."""
        file_path = tmp_path / "file.tar.gz"
        allowed = {".gz"}
        assert is_allowed_file_extension(file_path, allowed) is True

        # Test that .tar would be rejected
        allowed_tar = {".tar"}
        assert is_allowed_file_extension(file_path, allowed_tar) is False
