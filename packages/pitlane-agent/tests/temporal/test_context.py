"""Tests for temporal context data structures."""

from datetime import UTC, datetime

from pitlane_agent.temporal.context import (
    F1Season,
    RaceWeekendContext,
    RaceWeekendPhase,
    SessionContext,
    TemporalContext,
)


class TestDataStructures:
    """Test temporal context data structures."""

    def test_session_context_to_dict(self):
        """Test SessionContext serialization."""
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

        data = session.to_dict()

        assert data["name"] == "Race"
        assert data["session_type"] == "R"
        assert data["is_live"] is True
        assert data["is_recent"] is False
        assert data["minutes_until"] is None
        assert data["minutes_since"] == 30
        assert "date_utc" in data
        assert "date_local" in data

    def test_race_weekend_context_to_dict(self):
        """Test RaceWeekendContext serialization."""
        session = SessionContext(
            name="Race",
            session_type="R",
            date_utc=datetime(2026, 5, 26, 13, 0, tzinfo=UTC),
            date_local=datetime(2026, 5, 26, 15, 0, tzinfo=UTC),
            is_live=False,
            is_recent=True,
            minutes_until=None,
            minutes_since=60,
        )

        weekend = RaceWeekendContext(
            round_number=5,
            event_name="Monaco Grand Prix",
            country="Monaco",
            location="Monte Carlo",
            event_date=datetime(2026, 5, 26, tzinfo=UTC),
            phase=RaceWeekendPhase.POST_RACE,
            current_session=None,
            next_session=None,
            all_sessions=[session],
            is_sprint_weekend=False,
        )

        data = weekend.to_dict()

        assert data["round_number"] == 5
        assert data["event_name"] == "Monaco Grand Prix"
        assert data["country"] == "Monaco"
        assert data["location"] == "Monte Carlo"
        assert data["phase"] == "post_race"
        assert data["is_sprint_weekend"] is False
        assert len(data["all_sessions"]) == 1

    def test_temporal_context_to_dict(self):
        """Test TemporalContext serialization."""
        context = TemporalContext(
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

        data = context.to_dict()

        assert data["current_season"] == 2026
        assert data["season_phase"] == "in_season"
        assert data["races_completed"] == 5
        assert data["races_remaining"] == 19
        assert data["days_until_next_race"] == 7
        assert data["ttl_seconds"] == 43200


class TestF1Season:
    """Test F1Season enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert F1Season.PRE_SEASON.value == "pre_season"
        assert F1Season.IN_SEASON.value == "in_season"
        assert F1Season.POST_SEASON.value == "post_season"
        assert F1Season.OFF_SEASON.value == "off_season"


class TestRaceWeekendPhase:
    """Test RaceWeekendPhase enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert RaceWeekendPhase.BEFORE_WEEKEND.value == "before_weekend"
        assert RaceWeekendPhase.PRACTICE.value == "practice"
        assert RaceWeekendPhase.QUALIFYING.value == "qualifying"
        assert RaceWeekendPhase.SPRINT.value == "sprint"
        assert RaceWeekendPhase.RACE.value == "race"
        assert RaceWeekendPhase.POST_RACE.value == "post_race"
