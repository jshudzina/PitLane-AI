"""Tests for workspace management and conversation functions."""

import json
from unittest.mock import patch

import pytest
from pitlane_agent.commands.workspace.operations import (
    _generate_title,
    create_conversation,
    get_active_conversation,
    get_conversations_path,
    load_conversations,
    save_conversations,
    set_active_conversation,
    update_conversation,
)


class TestGenerateTitle:
    """Tests for _generate_title helper."""

    def test_short_message_unchanged(self):
        """Test that short messages are returned as-is."""
        message = "Hello world"
        assert _generate_title(message) == "Hello world"

    def test_long_message_truncated_at_word_boundary(self):
        """Test that long messages are truncated at word boundaries."""
        message = "This is a very long message that exceeds the maximum length allowed"
        result = _generate_title(message, max_length=30)
        assert result == "This is a very long message..."
        assert len(result) <= 33  # 30 + "..."

    def test_whitespace_normalized(self):
        """Test that extra whitespace is normalized."""
        message = "  Hello    world   "
        assert _generate_title(message) == "Hello world"

    def test_exact_length_no_truncation(self):
        """Test message at exact max length is not truncated."""
        message = "A" * 50
        assert _generate_title(message, max_length=50) == message

    def test_single_long_word(self):
        """Test single word longer than max length."""
        message = "Supercalifragilisticexpialidocious"
        result = _generate_title(message, max_length=20)
        # rsplit on space returns the whole word, so it gets ellipsis
        assert result.endswith("...")


class TestLoadConversations:
    """Tests for load_conversations function."""

    def test_returns_empty_structure_when_file_missing(self, tmp_path, monkeypatch):
        """Test that missing file returns empty structure."""
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: tmp_path / "conversations.json",
        )
        result = load_conversations("test-session")
        assert result == {
            "version": 1,
            "active_conversation_id": None,
            "conversations": [],
        }

    def test_loads_existing_file(self, tmp_path, monkeypatch):
        """Test that existing file is loaded correctly."""
        conv_path = tmp_path / "conversations.json"
        data = {
            "version": 1,
            "active_conversation_id": "conv_123",
            "conversations": [{"id": "conv_123", "title": "Test"}],
        }
        conv_path.write_text(json.dumps(data))

        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        result = load_conversations("test-session")
        assert result == data

    def test_returns_empty_on_corrupted_json(self, tmp_path, monkeypatch):
        """Test that corrupted JSON returns empty structure."""
        conv_path = tmp_path / "conversations.json"
        conv_path.write_text("not valid json {{{")

        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        result = load_conversations("test-session")
        assert result == {
            "version": 1,
            "active_conversation_id": None,
            "conversations": [],
        }


class TestSaveConversations:
    """Tests for save_conversations function."""

    def test_saves_data_atomically(self, tmp_path, monkeypatch):
        """Test that data is saved correctly."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        data = {"version": 1, "active_conversation_id": None, "conversations": []}
        save_conversations("test-session", data)

        assert conv_path.exists()
        loaded = json.loads(conv_path.read_text())
        assert loaded == data

    def test_raises_on_missing_workspace(self, monkeypatch):
        """Test that missing workspace raises ValueError."""
        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: False)

        with pytest.raises(ValueError, match="Workspace does not exist"):
            save_conversations("nonexistent-session", {})


class TestCreateConversation:
    """Tests for create_conversation function."""

    def test_creates_conversation_with_correct_fields(self, tmp_path, monkeypatch):
        """Test that conversation is created with all required fields."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        conv = create_conversation(
            session_id="test-session",
            agent_session_id="sdk-session-123",
            first_message="What was Hamilton's fastest lap?",
        )

        assert conv["id"].startswith("conv_")
        assert conv["agent_session_id"] == "sdk-session-123"
        assert conv["title"] == "What was Hamilton's fastest lap?"
        assert "created_at" in conv
        assert conv["message_count"] == 1

    def test_sets_as_active_conversation(self, tmp_path, monkeypatch):
        """Test that new conversation is set as active."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        conv = create_conversation("test-session", "sdk-123", "Hello")
        data = json.loads(conv_path.read_text())

        assert data["active_conversation_id"] == conv["id"]


class TestUpdateConversation:
    """Tests for update_conversation function."""

    def test_updates_message_count_and_timestamp(self, tmp_path, monkeypatch):
        """Test that message count and timestamp are updated."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"

        initial_data = {
            "version": 1,
            "active_conversation_id": "conv_123",
            "conversations": [
                {
                    "id": "conv_123",
                    "message_count": 1,
                    "last_message_at": "2024-01-01T00:00:00Z",
                }
            ],
        }
        conv_path.write_text(json.dumps(initial_data))

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        update_conversation("test-session", "conv_123", message_count_delta=2)

        updated = json.loads(conv_path.read_text())
        assert updated["conversations"][0]["message_count"] == 3
        assert updated["conversations"][0]["last_message_at"] != "2024-01-01T00:00:00Z"

    def test_logs_warning_for_missing_conversation(self, tmp_path, monkeypatch):
        """Test that warning is logged when conversation not found."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"

        initial_data = {
            "version": 1,
            "active_conversation_id": None,
            "conversations": [],
        }
        conv_path.write_text(json.dumps(initial_data))

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        with patch("pitlane_agent.commands.workspace.operations.logger") as mock_logger:
            update_conversation("test-session", "nonexistent")
            mock_logger.warning.assert_called_once()
            assert "nonexistent" in mock_logger.warning.call_args[0][0]


class TestGetActiveConversation:
    """Tests for get_active_conversation function."""

    def test_returns_none_when_no_active(self, tmp_path, monkeypatch):
        """Test that None is returned when no active conversation."""
        conv_path = tmp_path / "conversations.json"
        data = {"version": 1, "active_conversation_id": None, "conversations": []}
        conv_path.write_text(json.dumps(data))

        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        assert get_active_conversation("test-session") is None

    def test_returns_active_conversation(self, tmp_path, monkeypatch):
        """Test that active conversation is returned."""
        conv_path = tmp_path / "conversations.json"
        data = {
            "version": 1,
            "active_conversation_id": "conv_456",
            "conversations": [
                {"id": "conv_123", "title": "First"},
                {"id": "conv_456", "title": "Active"},
            ],
        }
        conv_path.write_text(json.dumps(data))

        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        result = get_active_conversation("test-session")
        assert result["id"] == "conv_456"
        assert result["title"] == "Active"

    def test_returns_none_when_active_id_not_found(self, tmp_path, monkeypatch):
        """Test that None is returned when active ID references missing conversation."""
        conv_path = tmp_path / "conversations.json"
        data = {
            "version": 1,
            "active_conversation_id": "conv_deleted",
            "conversations": [{"id": "conv_123", "title": "Only"}],
        }
        conv_path.write_text(json.dumps(data))

        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        assert get_active_conversation("test-session") is None


class TestSetActiveConversation:
    """Tests for set_active_conversation function."""

    def test_sets_active_conversation(self, tmp_path, monkeypatch):
        """Test that active conversation is set."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"
        data = {"version": 1, "active_conversation_id": None, "conversations": []}
        conv_path.write_text(json.dumps(data))

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        set_active_conversation("test-session", "conv_new")
        updated = json.loads(conv_path.read_text())
        assert updated["active_conversation_id"] == "conv_new"

    def test_clears_active_with_none(self, tmp_path, monkeypatch):
        """Test that active conversation can be cleared."""
        workspace_path = tmp_path / "workspace"
        workspace_path.mkdir()
        conv_path = workspace_path / "conversations.json"
        data = {"version": 1, "active_conversation_id": "conv_123", "conversations": []}
        conv_path.write_text(json.dumps(data))

        monkeypatch.setattr("pitlane_agent.commands.workspace.operations.workspace_exists", lambda sid: True)
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_conversations_path",
            lambda sid: conv_path,
        )
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        set_active_conversation("test-session", None)
        updated = json.loads(conv_path.read_text())
        assert updated["active_conversation_id"] is None


class TestGetConversationsPath:
    """Tests for get_conversations_path function."""

    def test_returns_correct_path(self, tmp_path, monkeypatch):
        """Test that correct path is returned."""
        workspace_path = tmp_path / "workspaces" / "test-session"
        monkeypatch.setattr(
            "pitlane_agent.commands.workspace.operations.get_workspace_path",
            lambda sid: workspace_path,
        )

        result = get_conversations_path("test-session")
        assert result == workspace_path / "conversations.json"
