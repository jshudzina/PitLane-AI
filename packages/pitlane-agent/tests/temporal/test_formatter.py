"""Tests for temporal context formatter."""

from datetime import UTC, datetime

import pytest
from pitlane_agent.temporal.context import (
    F1Season,
    RaceWeekendContext,
    RaceWeekendPhase,
    SessionContext,
    TemporalContext,
)
from pitlane_agent.temporal.formatter import (
    format_as_text,
    format_for_system_prompt,
)


class TestFormatter:
    """Test temporal context formatting."""

    @pytest.fixture
    def off_season_context(self):
        """Create off-season context."""
        return TemporalContext(
            current_time_utc=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            current_season=2026,
            season_phase=F1Season.OFF_SEASON,
            current_weekend=None,
            last_completed_race=None,
            next_race=None,
            races_completed=0,
            races_remaining=24,
            days_until_next_race=52,
            cache_timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            ttl_seconds=604800,
        )

    @pytest.fixture
    def in_season_context(self):
        """Create in-season context."""
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
            ttl_seconds=43200,
        )

    def test_format_minimal(self, off_season_context):
        """Test minimal formatting."""
        output = format_for_system_prompt(off_season_context, verbosity="minimal")

        assert "## F1 Temporal Context" in output
        assert "2026" in output
        assert "Off Season" in output

    def test_format_normal(self, in_season_context):
        """Test normal formatting."""
        output = format_for_system_prompt(in_season_context, verbosity="normal")

        assert "## F1 Temporal Context" in output
        assert "**Current Season:** 2026" in output
        assert "In Season" in output
        assert "Round 5 of 24 completed" in output

    def test_format_detailed(self, in_season_context):
        """Test detailed formatting."""
        output = format_for_system_prompt(in_season_context, verbosity="detailed")

        assert "## F1 Temporal Context" in output
        assert "**Current Season:** 2026" in output
        assert "**Phase:**" in output

    def test_format_as_text(self, in_season_context):
        """Test text formatting for CLI."""
        output = format_as_text(in_season_context)

        assert "F1 TEMPORAL CONTEXT" in output
        assert "Season: 2026" in output
        assert "Phase: In Season" in output
        assert "Races Completed: 5" in output
        assert "Races Remaining: 19" in output
        assert "CACHE INFO" in output

    def test_format_with_live_session(self):
        """Test formatting with live session."""
        session = SessionContext(
            name="Race",
            session_type="R",
            date_utc=datetime(2026, 5, 26, 13, 0, tzinfo=UTC),
            date_local=datetime(2026, 5, 26, 15, 0, tzinfo=UTC),
            is_live=True,
            is_recent=False,
            minutes_until=None,
            minutes_since=30,
        )

        weekend = RaceWeekendContext(
            round_number=5,
            event_name="Monaco Grand Prix",
            country="Monaco",
            location="Monte Carlo",
            event_date=datetime(2026, 5, 26, tzinfo=UTC),
            phase=RaceWeekendPhase.RACE,
            current_session=session,
            next_session=None,
            all_sessions=[session],
            is_sprint_weekend=False,
        )

        context = TemporalContext(
            current_time_utc=datetime(2026, 5, 26, 13, 30, tzinfo=UTC),
            current_season=2026,
            season_phase=F1Season.IN_SEASON,
            current_weekend=weekend,
            last_completed_race=None,
            next_race=None,
            races_completed=4,
            races_remaining=20,
            days_until_next_race=None,
            cache_timestamp=datetime(2026, 5, 26, 13, 30, tzinfo=UTC),
            ttl_seconds=300,
        )

        output = format_for_system_prompt(context, verbosity="normal")

        assert "ACTIVE RACE WEEKEND" in output
        assert "Monaco Grand Prix" in output
        assert "LIVE" in output
        assert "Race" in output
