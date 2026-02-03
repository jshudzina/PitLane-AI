"""Tests for temporal cache."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from pitlane_agent.temporal.cache import TemporalCache
from pitlane_agent.temporal.context import F1Season, TemporalContext


class TestTemporalCache:
    """Test temporal cache functionality."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory."""
        cache_dir = tmp_path / "temporal_cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create cache instance with temp directory."""
        return TemporalCache(temp_cache_dir)

    @pytest.fixture
    def sample_context(self):
        """Create sample temporal context."""
        return TemporalContext(
            current_time_utc=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            current_season=2026,
            season_phase=F1Season.IN_SEASON,
            current_weekend=None,
            last_completed_race=None,
            next_race=None,
            races_completed=5,
            races_remaining=19,
            days_until_next_race=7,
            cache_timestamp=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            ttl_seconds=43200,  # 12 hours
        )

    def test_cache_set_and_get(self, cache, sample_context):
        """Test setting and getting cache."""
        # Set cache
        cache.set(sample_context)

        # Get cache (within TTL)
        current_time = sample_context.current_time_utc + timedelta(hours=1)
        cached = cache.get(current_time)

        assert cached is not None
        assert cached.current_season == 2026
        assert cached.season_phase == F1Season.IN_SEASON
        assert cached.races_completed == 5

    def test_cache_expiration(self, cache, sample_context):
        """Test cache expiration after TTL."""
        # Set cache
        cache.set(sample_context)

        # Get cache after TTL (13 hours later)
        current_time = sample_context.current_time_utc + timedelta(hours=13)
        cached = cache.get(current_time)

        assert cached is None

    def test_cache_file_created(self, cache, sample_context, temp_cache_dir):
        """Test cache file is created."""
        cache.set(sample_context)

        cache_file = temp_cache_dir / "context_cache.json"
        assert cache_file.exists()

        # Verify JSON structure
        with open(cache_file) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "ttl_seconds" in data
        assert "expires_at" in data
        assert "context" in data

    def test_cache_clear(self, cache, sample_context, temp_cache_dir):
        """Test cache clearing."""
        cache.set(sample_context)

        cache_file = temp_cache_dir / "context_cache.json"
        assert cache_file.exists()

        cache.clear()
        assert not cache_file.exists()

    def test_get_nonexistent_cache(self, cache):
        """Test getting cache when file doesn't exist."""
        current_time = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)
        cached = cache.get(current_time)

        assert cached is None

    def test_get_invalid_cache_file(self, cache, temp_cache_dir):
        """Test getting cache with invalid JSON."""
        # Write invalid JSON
        cache_file = temp_cache_dir / "context_cache.json"
        with open(cache_file, "w") as f:
            f.write("invalid json{{{")

        current_time = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)
        cached = cache.get(current_time)

        assert cached is None
