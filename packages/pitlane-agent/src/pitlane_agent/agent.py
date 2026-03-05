"""F1 Agent using Claude Agent SDK with ClaudeSDKClient.

This module provides the F1Agent class that handles chat interactions
using the Claude Agent SDK with session management and skills support.
"""

import logging
from collections.abc import AsyncIterator
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    HookMatcher,
    SystemMessage,
    TextBlock,
)

from pitlane_agent.commands.workspace import (
    create_workspace,
    generate_workspace_id,
    get_workspace_path,
    update_workspace_metadata,
    workspace_exists,
)
from pitlane_agent.temporal import format_for_system_prompt, get_temporal_context
from pitlane_agent.tool_permissions import make_can_use_tool_callback, make_pre_tool_use_hook

from . import tracing

logger = logging.getLogger(__name__)

# Package directory (contains .claude/skills/)
PACKAGE_DIR = Path(__file__).parent

# Deprecated: Charts directory constant (for backward compatibility with tests)
# New code should use workspace_dir / "charts" instead
CHARTS_DIR = Path("/tmp/pitlane_charts")


class F1Agent:
    """AI agent for F1 data analysis using Claude Agent SDK."""

    def __init__(
        self,
        workspace_id: str | None = None,
        workspace_dir: Path | None = None,
        enable_tracing: bool | None = None,
        inject_temporal_context: bool = True,
    ):
        """Initialize the F1 agent.

        Args:
            workspace_id: Workspace identifier. Auto-generated if None.
            workspace_dir: Explicit workspace path. Derived from workspace_id if None.
            enable_tracing: Enable OpenTelemetry tracing. If None, uses PITLANE_TRACING_ENABLED env var.
            inject_temporal_context: Enable temporal context in system prompt. Default True.
        """
        self.workspace_id = workspace_id or generate_workspace_id()
        self.workspace_dir = workspace_dir or get_workspace_path(self.workspace_id)
        self.inject_temporal_context = inject_temporal_context
        self._agent_session_id: str | None = None  # Captured from Claude SDK

        # Verify workspace exists or create it
        if not self.workspace_dir.exists():
            create_workspace(self.workspace_id)
        elif workspace_exists(self.workspace_id):
            # Update last accessed timestamp
            update_workspace_metadata(self.workspace_id)

        # Configure tracing
        if enable_tracing is not None:
            if enable_tracing:
                tracing.enable_tracing()
            else:
                tracing.disable_tracing()

    @property
    def charts_dir(self) -> Path:
        """Get the charts directory for this workspace.

        Backward-compatible property for accessing the charts directory.

        Returns:
            Path to the workspace charts directory.
        """
        return self.workspace_dir / "charts"

    @property
    def agent_session_id(self) -> str | None:
        """Get the Claude Agent SDK session ID for resumption.

        This ID is captured from the SDK's init message during chat()
        and can be used to resume the conversation later.

        Returns:
            The SDK session ID, or None if not yet captured.
        """
        return self._agent_session_id

    def _build_system_prompt(self) -> str | None:
        """Build the system prompt append string with optional temporal context."""
        if not self.inject_temporal_context:
            return None
        try:
            temporal_ctx = get_temporal_context()
            return format_for_system_prompt(temporal_ctx, verbosity="normal")
        except Exception:
            return None

    async def chat(self, message: str, resume_session_id: str | None = None) -> AsyncIterator[str]:
        """Process a chat message and yield response text chunks.

        Args:
            message: The user's question or message.
            resume_session_id: Optional SDK session ID to resume a previous conversation.

        Yields:
            Text chunks from the assistant's response.
        """
        import os

        # Set workspace ID as environment variable so skills can access it
        os.environ["PITLANE_WORKSPACE_ID"] = self.workspace_id

        workspace_dir = str(self.workspace_dir)

        skills_dir = str(PACKAGE_DIR)

        # PreToolUse is always registered — it's the only mechanism that can block
        # tools listed in allowed_tools (the SDK skips can_use_tool for those).
        hooks: dict = {
            "PreToolUse": [
                HookMatcher(
                    matcher=None,
                    hooks=[make_pre_tool_use_hook(workspace_dir, self.workspace_id, skills_dir)],
                )
            ],
        }
        if tracing.is_tracing_enabled():
            hooks["PostToolUse"] = [HookMatcher(matcher=None, hooks=[tracing.post_tool_use_hook])]

        system_prompt_append = self._build_system_prompt()

        options = ClaudeAgentOptions(
            cwd=str(PACKAGE_DIR),
            setting_sources=["project"],
            allowed_tools=["Skill", "Bash", "Read", "Write", "WebFetch", "WebSearch"],
            can_use_tool=make_can_use_tool_callback(workspace_dir, self.workspace_id, skills_dir),
            hooks=hooks,
            resume=resume_session_id,
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": system_prompt_append,
            }
            if system_prompt_append
            else None,
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query(message)

            async for msg in client.receive_response():
                # Capture session ID from init message for future resumption
                if isinstance(msg, SystemMessage):
                    session_id = msg.data.get("session_id")
                    if session_id:
                        self._agent_session_id = session_id
                        logger.debug(f"Captured SDK session ID: {session_id}")
                elif isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            yield block.text

    async def chat_full(self, message: str, resume_session_id: str | None = None) -> str:
        """Process a chat message and return the full response.

        Args:
            message: The user's question or message.
            resume_session_id: Optional SDK session ID to resume a previous conversation.

        Returns:
            The complete response text.
        """
        parts = []
        async for chunk in self.chat(message, resume_session_id=resume_session_id):
            parts.append(chunk)
        return "\n".join(parts) if parts else ""
