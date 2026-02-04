"""Intelligent caching for temporal context."""

import json
from datetime import datetime
from pathlib import Path

from pitlane_agent.temporal.context import (
    F1Season,
    RaceWeekendContext,
    RaceWeekendPhase,
    SessionContext,
    TemporalContext,
)


class TemporalCache:
    """File-based cache for temporal context with intelligent TTL."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize cache.

        Args:
            cache_dir: Cache directory (defaults to ~/.pitlane/cache/temporal)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".pitlane" / "cache" / "temporal"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "context_cache.json"

    def get(self, current_time: datetime) -> TemporalContext | None:
        """Retrieve cached context if valid.

        Args:
            current_time: Current time (UTC, must be timezone-aware)

        Returns:
            Cached context if valid, None otherwise

        Raises:
            ValueError: If current_time is not timezone-aware
        """
        if current_time.tzinfo is None:
            raise ValueError("current_time must be timezone-aware (include tzinfo)")

        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            # Check if cache is expired
            expires_at = datetime.fromisoformat(data["expires_at"])
            if current_time > expires_at:
                return None

            # Deserialize context
            context = self._deserialize_context(data["context"])
            return context

        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid cache file
            return None

    def set(self, context: TemporalContext) -> None:
        """Cache context with TTL.

        Args:
            context: Temporal context to cache
        """
        # Calculate expiration time
        from datetime import timedelta

        expires_at = context.cache_timestamp + timedelta(seconds=context.ttl_seconds)

        # Serialize to JSON
        cache_data = {
            "timestamp": context.cache_timestamp.isoformat(),
            "ttl_seconds": context.ttl_seconds,
            "expires_at": expires_at.isoformat(),
            "context": context.to_dict(),
        }

        # Write to file
        with open(self.cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)

    def clear(self) -> None:
        """Clear all cached data."""
        if self.cache_file.exists():
            self.cache_file.unlink()

    def _deserialize_context(self, data: dict) -> TemporalContext:
        """Deserialize context from dictionary.

        Args:
            data: Serialized context dictionary

        Returns:
            Temporal context
        """
        return TemporalContext(
            current_time_utc=datetime.fromisoformat(data["current_time_utc"]),
            current_season=data["current_season"],
            season_phase=F1Season(data["season_phase"]),
            current_weekend=self._deserialize_weekend(data["current_weekend"]) if data["current_weekend"] else None,
            last_completed_race=(
                self._deserialize_weekend(data["last_completed_race"]) if data["last_completed_race"] else None
            ),
            next_race=self._deserialize_weekend(data["next_race"]) if data["next_race"] else None,
            races_completed=data["races_completed"],
            races_remaining=data["races_remaining"],
            days_until_next_race=data["days_until_next_race"],
            cache_timestamp=datetime.fromisoformat(data["cache_timestamp"]),
            ttl_seconds=data["ttl_seconds"],
        )

    def _deserialize_weekend(self, data: dict) -> RaceWeekendContext:
        """Deserialize race weekend context.

        Args:
            data: Serialized weekend dictionary

        Returns:
            Race weekend context
        """
        return RaceWeekendContext(
            round_number=data["round_number"],
            event_name=data["event_name"],
            country=data["country"],
            location=data["location"],
            event_date=datetime.fromisoformat(data["event_date"]),
            phase=RaceWeekendPhase(data["phase"]),
            current_session=self._deserialize_session(data["current_session"]) if data["current_session"] else None,
            next_session=self._deserialize_session(data["next_session"]) if data["next_session"] else None,
            all_sessions=[self._deserialize_session(s) for s in data["all_sessions"]],
            is_sprint_weekend=data["is_sprint_weekend"],
        )

    def _deserialize_session(self, data: dict) -> SessionContext:
        """Deserialize session context.

        Args:
            data: Serialized session dictionary

        Returns:
            Session context
        """
        return SessionContext(
            name=data["name"],
            session_type=data["session_type"],
            date_utc=datetime.fromisoformat(data["date_utc"]),
            date_local=datetime.fromisoformat(data["date_local"]),
            is_live=data["is_live"],
            is_recent=data["is_recent"],
            minutes_until=data["minutes_until"],
            minutes_since=data["minutes_since"],
        )
