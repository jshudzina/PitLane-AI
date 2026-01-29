"""Agent caching and lifecycle management for PitLane AI web application."""

import logging

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
        self._cache: dict[str, F1Agent] = {}
        self._max_size = max_size

    def get_or_create(self, session_id: str) -> F1Agent:
        """Get cached agent or create new one for session.

        Implements LRU-style eviction when cache is full (FIFO order).

        Args:
            session_id: Session ID for the agent

        Returns:
            F1Agent instance for the session
        """
        if session_id in self._cache:
            logger.debug(f"Using cached agent for session: {session_id}")
            return self._cache[session_id]

        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            # Remove first item (oldest in insertion order)
            oldest_session = next(iter(self._cache))
            logger.info(f"Agent cache full ({self._max_size}), evicting oldest session: {oldest_session}")
            del self._cache[oldest_session]

        # Create new agent
        logger.info(f"Creating new agent for session: {session_id}")
        agent = F1Agent(session_id=session_id)
        self._cache[session_id] = agent
        logger.debug(f"Agent cache size: {len(self._cache)}/{self._max_size}")
        return agent

    def evict(self, session_id: str) -> None:
        """Manually evict agent from cache.

        Args:
            session_id: Session ID to evict
        """
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
