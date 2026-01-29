"""Tests for agent caching and lifecycle management."""

import uuid
from unittest.mock import MagicMock, patch

from pitlane_web.agent_manager import AgentCache


class TestAgentCacheGetOrCreate:
    """Tests for agent retrieval and creation."""

    def test_first_call_creates_new_agent(self):
        """Test that first call creates a new agent."""
        cache = AgentCache(max_size=10)
        session_id = str(uuid.uuid4())

        with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            agent = cache.get_or_create(session_id)

            # Verify agent was created
            mock_agent_class.assert_called_once_with(session_id=session_id)
            assert agent == mock_agent
            assert cache.size() == 1

    def test_second_call_returns_cached_agent(self):
        """Test that second call with same session_id returns cached agent."""
        cache = AgentCache(max_size=10)
        session_id = str(uuid.uuid4())

        with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            # First call creates agent
            agent1 = cache.get_or_create(session_id)

            # Second call should return same agent without creating new one
            agent2 = cache.get_or_create(session_id)

            # Verify agent was only created once
            mock_agent_class.assert_called_once()
            assert agent1 == agent2
            assert cache.size() == 1

    def test_agent_created_with_correct_session_id(self):
        """Test that agent is created with correct session_id."""
        cache = AgentCache(max_size=10)
        session_id = str(uuid.uuid4())

        with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
            cache.get_or_create(session_id)

            # Verify agent was created with correct session_id
            mock_agent_class.assert_called_once_with(session_id=session_id)

    def test_cache_size_tracked_correctly(self):
        """Test that cache size is tracked correctly as agents are added."""
        cache = AgentCache(max_size=10)

        with patch("pitlane_web.agent_manager.F1Agent"):
            assert cache.size() == 0

            cache.get_or_create(str(uuid.uuid4()))
            assert cache.size() == 1

            cache.get_or_create(str(uuid.uuid4()))
            assert cache.size() == 2

            cache.get_or_create(str(uuid.uuid4()))
            assert cache.size() == 3

    def test_multiple_sessions_dont_interfere(self):
        """Test that multiple sessions create separate agents."""
        cache = AgentCache(max_size=10)
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
            mock_agent_class.side_effect = [MagicMock(), MagicMock()]

            agent1 = cache.get_or_create(session_id_1)
            agent2 = cache.get_or_create(session_id_2)

            # Verify separate agents were created
            assert agent1 != agent2
            assert cache.size() == 2


class TestAgentCacheLRUEviction:
    """Tests for LRU eviction when cache is full."""

    def test_cache_at_limit_no_eviction(self):
        """Test that cache at limit doesn't evict on existing session access."""
        cache = AgentCache(max_size=3)

        with patch("pitlane_web.agent_manager.F1Agent"):
            session_ids = [str(uuid.uuid4()) for _ in range(3)]

            # Fill cache to limit
            for sid in session_ids:
                cache.get_or_create(sid)

            assert cache.size() == 3

            # Access existing session - no eviction should occur
            cache.get_or_create(session_ids[0])
            assert cache.size() == 3

    def test_cache_exceeds_limit_evicts_oldest(self):
        """Test that exceeding cache limit evicts oldest (first inserted) entry."""
        cache = AgentCache(max_size=3)

        with patch("pitlane_web.agent_manager.F1Agent"):
            # Create 3 sessions to fill cache
            session_1 = str(uuid.uuid4())
            session_2 = str(uuid.uuid4())
            session_3 = str(uuid.uuid4())

            cache.get_or_create(session_1)
            cache.get_or_create(session_2)
            cache.get_or_create(session_3)

            assert cache.size() == 3

            # Add 4th session - should evict first (oldest)
            session_4 = str(uuid.uuid4())
            cache.get_or_create(session_4)

            assert cache.size() == 3

            # session_1 should be evicted, others should remain
            # Verify by checking if getting session_1 creates a new agent
            with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
                cache.get_or_create(session_1)
                # If evicted, this should create a new agent
                mock_agent_class.assert_called_once()

    def test_create_many_agents_evicts_in_fifo_order(self):
        """Test that creating many agents evicts in FIFO order."""
        cache = AgentCache(max_size=5)

        with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
            # Create unique mocks for each agent
            mock_agents = [MagicMock() for _ in range(20)]
            mock_agent_class.side_effect = mock_agents

            # Create 10 sessions (max_size is 5)
            session_ids = [str(uuid.uuid4()) for _ in range(10)]

            for sid in session_ids:
                cache.get_or_create(sid)

            # Only last 5 should remain
            assert cache.size() == 5

            # Reset call count to test subsequent calls
            initial_call_count = mock_agent_class.call_count
            assert initial_call_count == 10  # 10 agents were created

            # First 5 should be evicted - getting them should create new agents
            for i in range(5):
                cache.get_or_create(session_ids[i])

            # Should have created 5 more agents (for the evicted sessions)
            assert mock_agent_class.call_count == initial_call_count + 5

            # Last 5 should still be cached - getting them should NOT create new agents
            cache_size_before = cache.size()
            for i in range(5, 10):
                cache.get_or_create(session_ids[i])

            # Call count should not have increased (agents were cached)
            assert mock_agent_class.call_count == initial_call_count + 5
            # Cache size should stay the same
            assert cache.size() == cache_size_before

    def test_cache_size_stays_at_limit_after_eviction(self):
        """Test that cache size stays at limit after eviction occurs."""
        cache = AgentCache(max_size=5)

        with patch("pitlane_web.agent_manager.F1Agent"):
            # Create 100 sessions (max_size is 5)
            for _ in range(100):
                cache.get_or_create(str(uuid.uuid4()))

            # Size should stay at limit
            assert cache.size() == 5


class TestAgentCacheManagement:
    """Tests for manual cache management operations."""

    def test_evict_removes_specific_agent(self):
        """Test that evict() removes specific agent from cache."""
        cache = AgentCache(max_size=10)
        session_id = str(uuid.uuid4())

        with patch("pitlane_web.agent_manager.F1Agent"):
            cache.get_or_create(session_id)
            assert cache.size() == 1

            cache.evict(session_id)
            assert cache.size() == 0

    def test_evict_nonexistent_session_does_nothing(self):
        """Test that evicting non-existent session doesn't raise error."""
        cache = AgentCache(max_size=10)
        session_id = str(uuid.uuid4())

        # Should not raise
        cache.evict(session_id)
        assert cache.size() == 0

    def test_clear_removes_all_agents(self):
        """Test that clear() removes all agents from cache."""
        cache = AgentCache(max_size=10)

        with patch("pitlane_web.agent_manager.F1Agent"):
            # Add multiple agents
            for _ in range(5):
                cache.get_or_create(str(uuid.uuid4()))

            assert cache.size() == 5

            cache.clear()
            assert cache.size() == 0

    def test_clear_empty_cache_does_nothing(self):
        """Test that clearing empty cache doesn't raise error."""
        cache = AgentCache(max_size=10)

        # Should not raise
        cache.clear()
        assert cache.size() == 0

    def test_size_returns_correct_count(self):
        """Test that size() returns correct number of cached agents."""
        cache = AgentCache(max_size=10)

        with patch("pitlane_web.agent_manager.F1Agent"):
            assert cache.size() == 0

            for i in range(1, 6):
                cache.get_or_create(str(uuid.uuid4()))
                assert cache.size() == i

    def test_evict_then_recreate_creates_new_agent(self):
        """Test that after eviction, get_or_create creates a new agent."""
        cache = AgentCache(max_size=10)
        session_id = str(uuid.uuid4())

        with patch("pitlane_web.agent_manager.F1Agent") as mock_agent_class:
            mock_agent_class.side_effect = [MagicMock(), MagicMock()]

            # Create agent
            agent1 = cache.get_or_create(session_id)

            # Evict
            cache.evict(session_id)

            # Recreate should create new agent
            agent2 = cache.get_or_create(session_id)

            # Verify two separate agents were created
            assert mock_agent_class.call_count == 2
            assert agent1 != agent2


class TestAgentCacheInitialization:
    """Tests for AgentCache initialization."""

    def test_default_max_size(self):
        """Test that default max_size is from config."""
        with patch("pitlane_web.agent_manager.AGENT_CACHE_MAX_SIZE", 100):
            cache = AgentCache()
            assert cache._max_size == 100

    def test_custom_max_size(self):
        """Test that custom max_size is respected."""
        cache = AgentCache(max_size=50)
        assert cache._max_size == 50

    def test_initial_cache_is_empty(self):
        """Test that newly created cache is empty."""
        cache = AgentCache(max_size=10)
        assert cache.size() == 0
