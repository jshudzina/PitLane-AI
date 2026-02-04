"""Integration tests for temporal analyzer with real FastF1 data.

These tests verify temporal analysis using real schedule data from FastF1.
"""

from datetime import UTC, datetime

import pytest
from pitlane_agent.temporal.analyzer import TemporalAnalyzer
from pitlane_agent.temporal.context import F1Season


@pytest.mark.integration
@pytest.mark.slow
class TestTemporalAnalyzerIntegration:
    """Integration tests for temporal analysis with real schedule data."""

    def test_analyze_mid_season_2025(self, fastf1_cache_dir):
        """Test temporal analysis during 2025 season.

        Monaco GP 2025 was in May - test during a known race weekend.
        """
        analyzer = TemporalAnalyzer()

        # Monaco GP 2025 - use a date during the race weekend
        # This should detect as IN_SEASON with an active weekend
        test_time = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)

        context = analyzer.analyze(test_time)

        assert context.current_season == 2025
        assert context.season_phase == F1Season.IN_SEASON

        # If we hit the exact weekend, should have current_weekend
        # If not, current_weekend may be None (depends on exact timing)
        if context.current_weekend is not None:
            assert "Monaco" in context.current_weekend.event_name or context.current_weekend.location == "Monaco"

    def test_analyze_off_season(self, fastf1_cache_dir):
        """Test temporal analysis during off-season.

        Late January is typically off-season between seasons.
        """
        analyzer = TemporalAnalyzer()

        # Late January - off season
        test_time = datetime(2025, 1, 20, 12, 0, tzinfo=UTC)

        context = analyzer.analyze(test_time)

        # Should detect off-season or pre-season
        assert context.season_phase in [F1Season.OFF_SEASON, F1Season.PRE_SEASON]
        assert context.current_weekend is None  # No active weekend

    def test_analyze_season_start(self, fastf1_cache_dir):
        """Test temporal analysis at season start.

        Bahrain is typically the first race of the season.
        """
        analyzer = TemporalAnalyzer()

        # Early March - around Bahrain GP time
        test_time = datetime(2025, 3, 1, 12, 0, tzinfo=UTC)

        context = analyzer.analyze(test_time)

        # Should be in pre-season or early in-season
        assert context.season_phase in [F1Season.PRE_SEASON, F1Season.IN_SEASON]
        assert context.current_season == 2025

    def test_ttl_computation(self, fastf1_cache_dir):
        """Test that TTL is computed appropriately for different states."""
        analyzer = TemporalAnalyzer()

        # Off-season should have longer TTL
        off_season = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
        context = analyzer.analyze(off_season)

        # TTL should be at least a few hours for off-season
        assert context.ttl_seconds >= 3600  # At least 1 hour

    def test_current_season_detection(self, fastf1_cache_dir):
        """Test that current season is correctly identified."""
        analyzer = TemporalAnalyzer()

        # Test with a known date in 2025
        test_time = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        context = analyzer.analyze(test_time)

        assert context.current_season == 2025

    def test_next_event_detection(self, fastf1_cache_dir):
        """Test detection of next upcoming event."""
        analyzer = TemporalAnalyzer()

        # Use a date early in the season when next event should be clear
        test_time = datetime(2025, 3, 10, 12, 0, tzinfo=UTC)
        context = analyzer.analyze(test_time)

        # Should have a next race identified (unless we're at the last race)
        if context.season_phase == F1Season.IN_SEASON:
            # During season, should generally have a next race
            # (May be None if we're at the very end)
            assert context.next_race is not None or context.current_weekend is not None

    def test_previous_event_detection(self, fastf1_cache_dir):
        """Test detection of previous event."""
        analyzer = TemporalAnalyzer()

        # Use a date later in the season when there should be previous events
        test_time = datetime(2025, 7, 15, 12, 0, tzinfo=UTC)
        context = analyzer.analyze(test_time)

        # Mid-season, should have previous races
        if context.season_phase == F1Season.IN_SEASON:
            assert context.last_completed_race is not None

    def test_analyzer_uses_real_schedule_data(self, fastf1_cache_dir):
        """Verify that analyzer is using real FastF1 schedule data, not mocks."""
        analyzer = TemporalAnalyzer()

        test_time = datetime(2025, 5, 1, 12, 0, tzinfo=UTC)
        context = analyzer.analyze(test_time)

        # The context should have real data
        assert context.current_season == 2025

        # If we're in-season and have races, they should have real names
        if context.next_race is not None:
            assert len(context.next_race.event_name) > 0
            assert context.next_race.round_number > 0
