"""Tests for hook factory functions in tool_permissions."""

from unittest.mock import patch

import pytest
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny
from pitlane_agent.tool_permissions import make_can_use_tool_callback, make_pre_tool_use_hook


class TestMakePreToolUseHook:
    """Tests for make_pre_tool_use_hook factory."""

    @pytest.fixture
    def hook(self):
        return make_pre_tool_use_hook("/tmp/workspace", "ws-123")

    def test_returns_callable(self):
        hook = make_pre_tool_use_hook("/tmp/workspace", "ws-123")
        assert callable(hook)

    @pytest.mark.asyncio
    async def test_allows_approved_webfetch_domain(self, hook):
        result = await hook(
            {"tool_name": "WebFetch", "tool_input": {"url": "https://wikipedia.org/wiki/F1"}},
            "tool-1",
            {},
        )
        assert result == {"continue_": True}

    @pytest.mark.asyncio
    async def test_denies_disallowed_domain(self, hook):
        result = await hook(
            {"tool_name": "WebFetch", "tool_input": {"url": "https://evil.com/data"}},
            "tool-1",
            {},
        )
        assert result["continue_"] is False
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "evil.com" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_denial_includes_correct_hook_event_name(self, hook):
        result = await hook(
            {"tool_name": "WebFetch", "tool_input": {"url": "https://evil.com/data"}},
            "tool-1",
            {},
        )
        assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    @pytest.mark.asyncio
    async def test_allows_pitlane_bash_command(self, hook):
        result = await hook(
            {"tool_name": "Bash", "tool_input": {"command": "pitlane analyze"}},
            "tool-2",
            {},
        )
        assert result == {"continue_": True}

    @pytest.mark.asyncio
    async def test_denies_non_pitlane_bash_command(self, hook):
        result = await hook(
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
            "tool-2",
            {},
        )
        assert result["continue_"] is False
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_allows_read_within_workspace(self):
        hook = make_pre_tool_use_hook("/tmp/my-workspace", "ws-456")
        result = await hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/my-workspace/data.csv"}},
            "tool-3",
            {},
        )
        assert result == {"continue_": True}

    @pytest.mark.asyncio
    async def test_denies_read_outside_workspace(self):
        hook = make_pre_tool_use_hook("/tmp/my-workspace", "ws-456")
        result = await hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}},
            "tool-3",
            {},
        )
        assert result["continue_"] is False

    @pytest.mark.asyncio
    async def test_allows_write_within_workspace(self):
        hook = make_pre_tool_use_hook("/tmp/my-workspace", "ws-456")
        result = await hook(
            {"tool_name": "Write", "tool_input": {"file_path": "/tmp/my-workspace/out.json", "content": "{}"}},
            "tool-4",
            {},
        )
        assert result == {"continue_": True}

    @pytest.mark.asyncio
    async def test_allows_skill_tool(self, hook):
        result = await hook(
            {"tool_name": "Skill", "tool_input": {"skill": "f1-analyst"}},
            "tool-5",
            {},
        )
        assert result == {"continue_": True}

    @pytest.mark.asyncio
    async def test_logs_denial_via_warning(self, hook, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            await hook(
                {"tool_name": "WebFetch", "tool_input": {"url": "https://evil.com/data"}},
                "tool-1",
                {},
            )

        assert any("Tool use denied" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_logs_tool_call_on_allow_when_tracing_enabled(self, hook, enable_tracing):
        with patch("pitlane_agent.tool_permissions.tracing") as mock_tracing:
            mock_tracing.is_tracing_enabled.return_value = True
            mock_tracing._extract_key_param.return_value = "https://wikipedia.org"

            result = await hook(
                {"tool_name": "WebFetch", "tool_input": {"url": "https://wikipedia.org/wiki/F1"}},
                "tool-1",
                {},
            )

        assert result == {"continue_": True}
        mock_tracing._log_tool_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_tool_call_on_deny_when_tracing_enabled(self, hook, enable_tracing):
        with patch("pitlane_agent.tool_permissions.tracing") as mock_tracing:
            mock_tracing.is_tracing_enabled.return_value = True
            mock_tracing._extract_key_param.return_value = "https://evil.com"

            result = await hook(
                {"tool_name": "WebFetch", "tool_input": {"url": "https://evil.com/data"}},
                "tool-1",
                {},
            )

        assert result["continue_"] is False
        mock_tracing._log_tool_call.assert_called_once()
        call_kwargs = mock_tracing._log_tool_call.call_args[0][1]
        assert call_kwargs.get("tool.permission") == "denied"

    @pytest.mark.asyncio
    async def test_no_tracing_call_when_tracing_disabled(self, hook, disable_tracing):
        with patch("pitlane_agent.tool_permissions.tracing") as mock_tracing:
            mock_tracing.is_tracing_enabled.return_value = False
            mock_tracing._extract_key_param.return_value = "https://wikipedia.org"

            await hook(
                {"tool_name": "WebFetch", "tool_input": {"url": "https://wikipedia.org/wiki/F1"}},
                "tool-1",
                {},
            )

        mock_tracing._log_tool_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_hook_captures_workspace_context_for_read(self):
        """Verify that hooks created with different workspaces enforce their own paths."""
        hook_a = make_pre_tool_use_hook("/tmp/ws-a", "ws-a")
        hook_b = make_pre_tool_use_hook("/tmp/ws-b", "ws-b")

        # hook_a allows its own workspace
        result_a = await hook_a(
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/ws-a/data.csv"}},
            "tool-1",
            {},
        )
        assert result_a == {"continue_": True}

        # hook_b denies hook_a's workspace
        result_b = await hook_b(
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/ws-a/data.csv"}},
            "tool-1",
            {},
        )
        assert result_b["continue_"] is False


class TestMakeCanUseToolCallback:
    """Tests for make_can_use_tool_callback factory."""

    def test_returns_callable(self):
        callback = make_can_use_tool_callback("/tmp/workspace", "ws-123")
        assert callable(callback)

    @pytest.mark.asyncio
    async def test_allows_skill_tool(self):
        callback = make_can_use_tool_callback("/tmp/workspace", "ws-123")
        result = await callback("Skill", {"skill": "f1"}, {})
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_injects_workspace_for_read(self):
        callback = make_can_use_tool_callback("/tmp/ws", "ws-789")
        result = await callback("Read", {"file_path": "/tmp/ws/data.txt"}, {})
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_denies_read_outside_injected_workspace(self):
        callback = make_can_use_tool_callback("/tmp/ws", "ws-789")
        result = await callback("Read", {"file_path": "/etc/passwd"}, {})
        assert isinstance(result, PermissionResultDeny)

    @pytest.mark.asyncio
    async def test_injects_workspace_for_write(self):
        callback = make_can_use_tool_callback("/tmp/ws", "ws-789")
        result = await callback("Write", {"file_path": "/tmp/ws/out.json", "content": "{}"}, {})
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_allows_pitlane_bash(self):
        callback = make_can_use_tool_callback("/tmp/ws", "ws-123")
        result = await callback("Bash", {"command": "pitlane lap-times"}, {})
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_denies_non_pitlane_bash(self):
        callback = make_can_use_tool_callback("/tmp/ws", "ws-123")
        result = await callback("Bash", {"command": "cat /etc/passwd"}, {})
        assert isinstance(result, PermissionResultDeny)

    @pytest.mark.asyncio
    async def test_ignores_extra_context_arg(self):
        """Callback should use the injected workspace, not the context arg."""
        callback = make_can_use_tool_callback("/tmp/ws", "ws-123")
        # Even if caller passes a different workspace in context, injected one wins
        result = await callback("Read", {"file_path": "/tmp/ws/data.txt"}, {"workspace_dir": "/other"})
        assert isinstance(result, PermissionResultAllow)
