"""Core temporal context data structures and manager."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path


class F1Season(str, Enum):
    """F1 season phase."""

    PRE_SEASON = "pre_season"  # Before first race
    IN_SEASON = "in_season"  # During championship
    POST_SEASON = "post_season"  # After final race
    OFF_SEASON = "off_season"  # Dec-Feb gap


class RaceWeekendPhase(str, Enum):
    """Current phase within a race weekend."""

    BEFORE_WEEKEND = "before_weekend"
    PRACTICE = "practice"
    QUALIFYING = "qualifying"
    SPRINT = "sprint"
    RACE = "race"
    POST_RACE = "post_race"


@dataclass
class SessionContext:
    """Information about a specific session."""

    name: str  # e.g., "Race", "Qualifying"
    session_type: str  # R, Q, FP1, etc.
    date_utc: datetime
    date_local: datetime
    is_live: bool  # Currently happening
    is_recent: bool  # Within last 24h
    minutes_until: int | None  # None if past
    minutes_since: int | None  # None if future

    def to_dict(self) -> dict:
        """Convert to dictionary with ISO format dates."""
        return {
            "name": self.name,
            "session_type": self.session_type,
            "date_utc": self.date_utc.isoformat(),
            "date_local": self.date_local.isoformat(),
            "is_live": self.is_live,
            "is_recent": self.is_recent,
            "minutes_until": self.minutes_until,
            "minutes_since": self.minutes_since,
        }


@dataclass
class RaceWeekendContext:
    """Information about a race weekend."""

    round_number: int
    event_name: str  # e.g., "Monaco Grand Prix"
    country: str
    location: str
    event_date: datetime
    phase: RaceWeekendPhase
    current_session: SessionContext | None
    next_session: SessionContext | None
    all_sessions: list[SessionContext]
    is_sprint_weekend: bool

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "round_number": self.round_number,
            "event_name": self.event_name,
            "country": self.country,
            "location": self.location,
            "event_date": self.event_date.isoformat(),
            "phase": self.phase.value,
            "current_session": self.current_session.to_dict() if self.current_session else None,
            "next_session": self.next_session.to_dict() if self.next_session else None,
            "all_sessions": [s.to_dict() for s in self.all_sessions],
            "is_sprint_weekend": self.is_sprint_weekend,
        }


@dataclass
class TemporalContext:
    """Complete temporal context for F1 agent."""

    current_time_utc: datetime
    current_season: int
    season_phase: F1Season

    # Current race weekend (if any)
    current_weekend: RaceWeekendContext | None

    # Most recently completed race
    last_completed_race: RaceWeekendContext | None

    # Next upcoming race
    next_race: RaceWeekendContext | None

    # Quick stats
    races_completed: int
    races_remaining: int
    days_until_next_race: int | None

    # Metadata
    cache_timestamp: datetime
    ttl_seconds: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "current_time_utc": self.current_time_utc.isoformat(),
            "current_season": self.current_season,
            "season_phase": self.season_phase.value,
            "current_weekend": self.current_weekend.to_dict() if self.current_weekend else None,
            "last_completed_race": self.last_completed_race.to_dict() if self.last_completed_race else None,
            "next_race": self.next_race.to_dict() if self.next_race else None,
            "races_completed": self.races_completed,
            "races_remaining": self.races_remaining,
            "days_until_next_race": self.days_until_next_race,
            "cache_timestamp": self.cache_timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
        }


class TemporalContextManager:
    """Manages F1 temporal context with intelligent caching."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize temporal context manager.

        Args:
            cache_dir: Override cache directory (defaults to ~/.pitlane/cache/temporal)
        """
        from pitlane_agent.temporal.analyzer import TemporalAnalyzer
        from pitlane_agent.temporal.cache import TemporalCache

        self.cache = TemporalCache(cache_dir)
        self.analyzer = TemporalAnalyzer()

    def get_context(self, force_refresh: bool = False, current_time: datetime | None = None) -> TemporalContext:
        """Get current temporal context.

        Args:
            force_refresh: Force fetch from FastF1 (ignore cache)
            current_time: Override current time (for testing)

        Returns:
            Complete temporal context
        """
        now = current_time or datetime.now(UTC)

        # Check cache
        if not force_refresh:
            cached = self.cache.get(now)
            if cached:
                return cached

        # Fetch and analyze
        context = self.analyzer.analyze(now)

        # Cache with intelligent TTL
        self.cache.set(context)

        return context


# Global instance for convenience
_manager: TemporalContextManager | None = None


def get_temporal_context(force_refresh: bool = False, current_time: datetime | None = None) -> TemporalContext:
    """Get current F1 temporal context.

    This is the primary public API for accessing temporal context.

    Args:
        force_refresh: Force fetch from FastF1 (ignore cache)
        current_time: Override current time (for testing)

    Returns:
        Complete temporal context

    Example:
        >>> context = get_temporal_context()
        >>> print(f"Current season: {context.current_season}")
        >>> if context.current_weekend:
        >>>     print(f"Race weekend: {context.current_weekend.event_name}")
    """
    global _manager
    if _manager is None:
        _manager = TemporalContextManager()
    return _manager.get_context(force_refresh=force_refresh, current_time=current_time)
