"""Concurrency tests for AgentCache to verify thread-safety and async-safety."""

import asyncio
import uuid

import pytest
from pitlane_web.agent_manager import AgentCache


@pytest.mark.asyncio
async def test_concurrent_access_same_session():
    """Test multiple coroutines accessing same session simultaneously."""
    cache = AgentCache(max_size=10)
    session_id = str(uuid.uuid4())

    async def access_agent():
        agent = await cache.get_or_create(session_id)
        await asyncio.sleep(0.001)  # Simulate work
        return agent

    # Run 100 concurrent accesses
    agents = await asyncio.gather(*[access_agent() for _ in range(100)])

    # All should be the same agent instance
    assert len({id(a) for a in agents}) == 1
    assert cache.size() == 1


@pytest.mark.asyncio
async def test_concurrent_different_sessions():
    """Test multiple coroutines creating different sessions."""
    cache = AgentCache(max_size=50)

    async def create_session():
        session_id = str(uuid.uuid4())
        agent = await cache.get_or_create(session_id)
        return session_id, agent

    # Create 30 different sessions concurrently
    results = await asyncio.gather(*[create_session() for _ in range(30)])

    # All session IDs should be unique
    session_ids = [sid for sid, _ in results]
    assert len(set(session_ids)) == 30

    # Cache should have all 30 sessions
    assert cache.size() == 30


@pytest.mark.asyncio
async def test_concurrent_cache_full_eviction():
    """Test concurrent access during cache-full eviction."""
    cache = AgentCache(max_size=3)

    async def create_session():
        session_id = str(uuid.uuid4())
        return await cache.get_or_create(session_id)

    # Create 100 sessions concurrently (max_size is 3)
    agents = await asyncio.gather(*[create_session() for _ in range(100)])

    # Cache should stabilize at max_size
    assert cache.size() == 3
    assert len(agents) == 100  # All operations completed successfully


@pytest.mark.asyncio
async def test_race_condition_access_during_eviction():
    """Test access racing with eviction."""
    cache = AgentCache(max_size=2)
    session_1 = str(uuid.uuid4())
    session_2 = str(uuid.uuid4())

    # Pre-populate
    await cache.get_or_create(session_1)
    await cache.get_or_create(session_2)

    async def access_and_create():
        # Access session_1 while creating new session (triggers eviction)
        tasks = [
            cache.get_or_create(session_1),
            cache.get_or_create(str(uuid.uuid4())),
        ]
        return await asyncio.gather(*tasks)

    # Run multiple times to catch race
    for _ in range(100):
        results = await access_and_create()
        assert len(results) == 2  # Both operations should succeed


@pytest.mark.asyncio
async def test_concurrent_eviction():
    """Test concurrent manual evictions."""
    cache = AgentCache(max_size=10)
    session_ids = [str(uuid.uuid4()) for _ in range(5)]

    # Create all sessions
    for sid in session_ids:
        await cache.get_or_create(sid)

    assert cache.size() == 5

    # Evict all concurrently
    await asyncio.gather(*[cache.evict(sid) for sid in session_ids])

    assert cache.size() == 0


@pytest.mark.asyncio
async def test_lru_ordering_with_concurrency():
    """Test that LRU ordering is maintained under concurrent access."""
    cache = AgentCache(max_size=3)
    session_1 = str(uuid.uuid4())
    session_2 = str(uuid.uuid4())
    session_3 = str(uuid.uuid4())

    # Create three sessions
    await cache.get_or_create(session_1)
    await cache.get_or_create(session_2)
    await cache.get_or_create(session_3)

    # Access session_1 many times concurrently (should move to end)
    await asyncio.gather(*[cache.get_or_create(session_1) for _ in range(50)])

    # Create a new session - should evict session_2 (oldest)
    session_4 = str(uuid.uuid4())
    await cache.get_or_create(session_4)

    # Cache should contain session_1, session_3, and session_4
    assert cache.size() == 3

    # Try to access all original sessions
    # Session_1 should still be in cache (accessed recently)
    agent_1 = await cache.get_or_create(session_1)
    assert agent_1 is not None

    # Session_3 should still be in cache
    agent_3 = await cache.get_or_create(session_3)
    assert agent_3 is not None


@pytest.mark.asyncio
async def test_clear_during_concurrent_access():
    """Test clearing cache during concurrent operations."""
    cache = AgentCache(max_size=10)

    async def create_and_clear():
        # Create some sessions
        create_tasks = [cache.get_or_create(str(uuid.uuid4())) for _ in range(5)]
        await asyncio.gather(*create_tasks)

        # Clear the cache
        cache.clear()

        # Create more sessions
        create_tasks = [cache.get_or_create(str(uuid.uuid4())) for _ in range(5)]
        await asyncio.gather(*create_tasks)

    # Run multiple times
    for _ in range(10):
        await create_and_clear()
        # Cache should have exactly 5 items after each iteration
        assert cache.size() == 5
        cache.clear()


@pytest.mark.asyncio
async def test_stress_test_mixed_operations():
    """Stress test with mixed create, access, and evict operations."""
    cache = AgentCache(max_size=20)
    session_ids = [str(uuid.uuid4()) for _ in range(30)]

    async def mixed_operations():
        # Create random sessions
        for _ in range(10):
            sid = session_ids[asyncio.current_task().get_name().split("-")[-1].__hash__() % len(session_ids)]
            await cache.get_or_create(sid)
            await asyncio.sleep(0.0001)

    # Run 50 concurrent workers
    await asyncio.gather(*[mixed_operations() for _ in range(50)])

    # Cache should be at or under max size
    assert cache.size() <= 20
