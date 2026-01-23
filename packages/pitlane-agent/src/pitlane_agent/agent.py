"""F1 Agent using Claude Agent SDK with ClaudeSDKClient.

This module provides the F1Agent class that handles chat interactions
using the Claude Agent SDK with session management and skills support.
"""

from collections.abc import AsyncIterator
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import AssistantMessage, TextBlock

# Package directory (contains .claude/skills/)
PACKAGE_DIR = Path(__file__).parent

# Charts output directory
CHARTS_DIR = Path("/tmp/pitlane_charts")


class F1Agent:
    """AI agent for F1 data analysis using Claude Agent SDK."""

    def __init__(self, charts_dir: Path | None = None):
        """Initialize the F1 agent.

        Args:
            charts_dir: Directory for chart output. Defaults to /tmp/pitlane_charts.
        """
        self.charts_dir = charts_dir or CHARTS_DIR
        self.charts_dir.mkdir(parents=True, exist_ok=True)

    async def chat(self, message: str) -> AsyncIterator[str]:
        """Process a chat message and yield response text chunks.

        Args:
            message: The user's question or message.

        Yields:
            Text chunks from the assistant's response.
        """
        options = ClaudeAgentOptions(
            cwd=str(PACKAGE_DIR),
            setting_sources=["project"],
            allowed_tools=["Skill", "Bash", "Read", "Write"],
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query(message)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            yield block.text

    async def chat_full(self, message: str) -> str:
        """Process a chat message and return the full response.

        Args:
            message: The user's question or message.

        Returns:
            The complete response text.
        """
        parts = []
        async for chunk in self.chat(message):
            parts.append(chunk)
        return "\n".join(parts) if parts else ""
