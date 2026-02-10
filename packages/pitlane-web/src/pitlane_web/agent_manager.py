"""Agent caching and lifecycle management for PitLane AI web application.

Note: The 'session_id' parameter in this module refers to the workspace identifier,
not the Claude SDK agent session ID.
"""

import asyncio
import logging
from collections import OrderedDict

from pitlane_agent import F1Agent

from .config import AGENT_CACHE_MAX_SIZE

logger = logging.getLogger(__name__)


class AgentCache:
    """Cache for F1Agent instances with LRU-style eviction.

    Manages a pool of F1Agent instances, one per session, with automatic
    eviction of oldest entries when the cache reaches its size limit.
    """

    def __init__(self, max_size: int = AGENT_CACHE_MAX_SIZE):
        """Initialize the agent cache.

        Args:
            max_size: Maximum number of agents to cache
        """
        self._cache: OrderedDict[str, F1Agent] = OrderedDict()
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str) -> F1Agent:
        """Get cached agent or create new one for session.

        Implements LRU-style eviction when cache is full.
        When accessing an existing agent, it's moved to the end (most recently used).

        This method is async-safe and uses a lock to prevent race conditions
        in concurrent access scenarios.

        Args:
            session_id: Session ID for the agent

        Returns:
            F1Agent instance for the session
        """
        async with self._lock:
            if session_id in self._cache:
                logger.debug(f"Using cached agent for session: {session_id}")
                # Move to end to mark as recently used (LRU) - atomic operation
                self._cache.move_to_end(session_id)
                return self._cache[session_id]

            # Evict oldest entry if cache is full
            if len(self._cache) >= self._max_size:
                # Remove first item (least recently used)
                oldest_session = next(iter(self._cache))
                logger.info(
                    f"Agent cache full ({self._max_size}), evicting least recently used session: {oldest_session}"
                )
                del self._cache[oldest_session]

            # Create new agent
            logger.info(f"Creating new agent for session: {session_id}")
            agent = F1Agent(session_id=session_id)
            self._cache[session_id] = agent
            logger.debug(f"Agent cache size: {len(self._cache)}/{self._max_size}")
            return agent

    async def evict(self, session_id: str) -> None:
        """Manually evict agent from cache.

        This method is async-safe and uses a lock to prevent race conditions.

        Args:
            session_id: Session ID to evict
        """
        async with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                logger.info(f"Manually evicted agent for session: {session_id}")

    def clear(self) -> None:
        """Clear all cached agents."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared agent cache ({count} agents removed)")

    def size(self) -> int:
        """Return current cache size.

        Returns:
            Number of agents currently in cache
        """
        return len(self._cache)


# Global singleton instance
_agent_cache = AgentCache()


__all__ = ["AgentCache", "_agent_cache"]
