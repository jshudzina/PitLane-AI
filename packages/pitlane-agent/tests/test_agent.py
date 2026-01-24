"""Tests for the F1Agent class."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pitlane_agent.agent import CHARTS_DIR, PACKAGE_DIR, F1Agent


class TestF1AgentInitialization:
    """Tests for F1Agent initialization."""

    def test_init_default_charts_dir(self, tmp_path):
        """Test initialization with default charts directory."""
        with patch("pitlane_agent.agent.CHARTS_DIR", tmp_path / "default_charts"):
            agent = F1Agent()

            assert agent.charts_dir == tmp_path / "default_charts"
            assert agent.charts_dir.exists()

    def test_init_custom_charts_dir(self, tmp_path):
        """Test initialization with custom charts directory."""
        custom_dir = tmp_path / "custom_charts"
        agent = F1Agent(charts_dir=custom_dir)

        assert agent.charts_dir == custom_dir
        assert agent.charts_dir.exists()

    def test_init_creates_charts_dir_if_missing(self, tmp_path):
        """Test that charts directory is created if it doesn't exist."""
        charts_dir = tmp_path / "new" / "nested" / "charts"
        assert not charts_dir.exists()

        agent = F1Agent(charts_dir=charts_dir)

        assert agent.charts_dir == charts_dir
        assert charts_dir.exists()

    def test_init_uses_default_charts_dir_constant(self):
        """Test that default uses CHARTS_DIR constant."""
        agent = F1Agent()
        assert agent.charts_dir == CHARTS_DIR


class TestF1AgentChat:
    """Tests for F1Agent.chat method."""

    @pytest.mark.asyncio
    async def test_chat_yields_text_chunks(self):
        """Test that chat yields text chunks from assistant messages."""
        # Create mock TextBlock objects
        from claude_agent_sdk.types import TextBlock

        text_block_1 = TextBlock(text="Hello ")
        text_block_2 = TextBlock(text="from F1 Agent!")

        # Create mock AssistantMessage with text blocks
        from claude_agent_sdk.types import AssistantMessage

        mock_msg_1 = MagicMock(spec=AssistantMessage)
        mock_msg_1.content = [text_block_1]

        mock_msg_2 = MagicMock(spec=AssistantMessage)
        mock_msg_2.content = [text_block_2]

        # Create mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Mock receive_response to yield assistant messages
        async def mock_receive():
            yield mock_msg_1
            yield mock_msg_2

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Patch ClaudeSDKClient
        with patch("pitlane_agent.agent.ClaudeSDKClient", return_value=mock_client):
            agent = F1Agent()
            chunks = []

            async for chunk in agent.chat("What is F1?"):
                chunks.append(chunk)

            assert chunks == ["Hello ", "from F1 Agent!"]
            mock_client.query.assert_called_once_with("What is F1?")

    @pytest.mark.asyncio
    async def test_chat_passes_correct_options(self):
        """Test that chat passes correct options to ClaudeSDKClient."""
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Mock receive_response as an async generator
        async def mock_receive():
            return
            yield  # Make it an async generator

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pitlane_agent.agent.ClaudeSDKClient") as mock_sdk_client:
            mock_sdk_client.return_value = mock_client

            agent = F1Agent()
            async for _ in agent.chat("Test"):
                pass

            # Verify ClaudeSDKClient was called with correct options
            call_args = mock_sdk_client.call_args
            options = call_args.kwargs["options"]

            assert options.cwd == str(PACKAGE_DIR)
            assert options.setting_sources == ["project"]
            assert options.allowed_tools == ["Skill", "Bash", "Read", "Write"]

    @pytest.mark.asyncio
    async def test_chat_handles_multiple_text_blocks(self):
        """Test that chat handles messages with multiple text blocks."""
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        # Create message with multiple text blocks
        text_blocks = [
            TextBlock(text="First block "),
            TextBlock(text="Second block "),
            TextBlock(text="Third block"),
        ]

        mock_msg = MagicMock(spec=AssistantMessage)
        mock_msg.content = text_blocks

        # Create mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            yield mock_msg

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pitlane_agent.agent.ClaudeSDKClient", return_value=mock_client):
            agent = F1Agent()
            chunks = []

            async for chunk in agent.chat("Test"):
                chunks.append(chunk)

            assert chunks == ["First block ", "Second block ", "Third block"]

    @pytest.mark.asyncio
    async def test_chat_filters_non_text_blocks(self):
        """Test that chat only yields TextBlock content."""
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        # Create message with mixed content types
        text_block = TextBlock(text="Text content")
        non_text_block = MagicMock()  # Some other block type

        mock_msg = MagicMock(spec=AssistantMessage)
        mock_msg.content = [text_block, non_text_block]

        # Create mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            yield mock_msg

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pitlane_agent.agent.ClaudeSDKClient", return_value=mock_client):
            agent = F1Agent()
            chunks = []

            async for chunk in agent.chat("Test"):
                chunks.append(chunk)

            # Should only yield the TextBlock content
            assert chunks == ["Text content"]

    @pytest.mark.asyncio
    async def test_chat_filters_non_assistant_messages(self):
        """Test that chat only processes AssistantMessage types."""
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        # Create an assistant message and a non-assistant message
        text_block = TextBlock(text="Assistant response")
        assistant_msg = MagicMock(spec=AssistantMessage)
        assistant_msg.content = [text_block]

        other_msg = MagicMock()  # Not an AssistantMessage

        # Create mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            yield other_msg
            yield assistant_msg

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pitlane_agent.agent.ClaudeSDKClient", return_value=mock_client):
            agent = F1Agent()
            chunks = []

            async for chunk in agent.chat("Test"):
                chunks.append(chunk)

            # Should only yield content from AssistantMessage
            assert chunks == ["Assistant response"]


class TestF1AgentChatFull:
    """Tests for F1Agent.chat_full method."""

    @pytest.mark.asyncio
    async def test_chat_full_returns_complete_response(self):
        """Test that chat_full returns the complete response."""
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        # Create mock messages
        text_block_1 = TextBlock(text="First chunk")
        text_block_2 = TextBlock(text="Second chunk")
        text_block_3 = TextBlock(text="Third chunk")

        mock_msg_1 = MagicMock(spec=AssistantMessage)
        mock_msg_1.content = [text_block_1]

        mock_msg_2 = MagicMock(spec=AssistantMessage)
        mock_msg_2.content = [text_block_2, text_block_3]

        # Create mock client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            yield mock_msg_1
            yield mock_msg_2

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pitlane_agent.agent.ClaudeSDKClient", return_value=mock_client):
            agent = F1Agent()
            response = await agent.chat_full("What is F1?")

            # Should join all chunks with newlines
            assert response == "First chunk\nSecond chunk\nThird chunk"
            mock_client.query.assert_called_once_with("What is F1?")

    @pytest.mark.asyncio
    async def test_chat_full_returns_empty_string_for_no_response(self):
        """Test that chat_full returns empty string when there's no response."""
        # Create mock client with no messages
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        async def mock_receive():
            return
            yield  # Make it an async generator

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pitlane_agent.agent.ClaudeSDKClient", return_value=mock_client):
            agent = F1Agent()
            response = await agent.chat_full("Test")

            assert response == ""

    @pytest.mark.asyncio
    async def test_chat_full_uses_chat_method(self):
        """Test that chat_full internally uses the chat method."""
        agent = F1Agent()

        # Mock the chat method
        async def mock_chat(message):
            yield "Chunk 1"
            yield "Chunk 2"

        with patch.object(agent, "chat", side_effect=mock_chat):
            response = await agent.chat_full("Test message")

            assert response == "Chunk 1\nChunk 2"


class TestF1AgentConstants:
    """Tests for module-level constants."""

    def test_package_dir_is_correct(self):
        """Test that PACKAGE_DIR points to the package directory."""
        # PACKAGE_DIR should point to the pitlane_agent package directory
        assert PACKAGE_DIR.name == "pitlane_agent"
        assert PACKAGE_DIR.is_dir()
        assert (PACKAGE_DIR / "__init__.py").exists()

    def test_charts_dir_constant(self):
        """Test that CHARTS_DIR has expected value."""
        assert Path("/tmp/pitlane_charts") == CHARTS_DIR
