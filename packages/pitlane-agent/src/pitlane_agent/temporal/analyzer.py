"""Temporal analysis logic for determining F1 season/race/session state."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import fastf1
import pandas as pd

from pitlane_agent.temporal.context import (
    F1Season,
    RaceWeekendContext,
    RaceWeekendPhase,
    SessionContext,
    TemporalContext,
)


class TemporalAnalyzer:
    """Analyzes F1 schedule to determine current temporal state."""

    def __init__(self):
        """Initialize analyzer with FastF1 cache."""
        cache_dir = Path.home() / ".pitlane" / "cache" / "fastf1"
        fastf1.Cache.enable_cache(str(cache_dir))

    def analyze(self, current_time: datetime) -> TemporalContext:
        """Analyze schedule and determine current temporal state.

        Args:
            current_time: Current time (UTC)

        Returns:
            Complete temporal context
        """
        # Ensure timezone awareness
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)

        # Determine season year
        current_season = self._determine_season_year(current_time)

        # Fetch schedule
        try:
            schedule = fastf1.get_event_schedule(current_season, include_testing=False)
        except (ValueError, KeyError, AttributeError, ImportError):
            # If current season schedule isn't available, try previous year
            current_season = current_time.year - 1
            schedule = fastf1.get_event_schedule(current_season, include_testing=False)

        # Convert schedule to list of events
        events = self._parse_schedule(schedule)

        # Analyze temporal state
        season_phase = self._determine_season_phase(current_time, events)
        current_weekend = self._find_current_weekend(current_time, events)
        last_completed = self._find_last_completed_race(current_time, events)
        next_race = self._find_next_race(current_time, events)

        # Calculate stats
        races_completed = sum(1 for e in events if self._is_race_completed(e, current_time))
        races_remaining = len(events) - races_completed

        days_until_next = None
        if next_race and next_race.event_date:
            delta = next_race.event_date - current_time
            days_until_next = delta.days

        # Calculate TTL
        ttl = self._compute_ttl(season_phase, current_weekend)

        return TemporalContext(
            current_time_utc=current_time,
            current_season=current_season,
            season_phase=season_phase,
            current_weekend=current_weekend,
            last_completed_race=last_completed,
            next_race=next_race,
            races_completed=races_completed,
            races_remaining=races_remaining,
            days_until_next_race=days_until_next,
            cache_timestamp=current_time,
            ttl_seconds=ttl,
        )

    def _determine_season_year(self, current_time: datetime) -> int:
        """Determine which F1 season year to query.

        Args:
            current_time: Current time (UTC)

        Returns:
            Season year
        """
        year = current_time.year

        # If it's January or February, we might be in off-season
        # Use previous year if current year schedule isn't available yet
        if current_time.month <= 2:
            try:
                # Try current year first
                fastf1.get_event_schedule(year, include_testing=False)
                return year
            except (ValueError, KeyError, AttributeError, ImportError):
                # FastF1 schedule not available for current year yet
                # Fall back to previous year
                return year - 1

        return year

    def _parse_schedule(self, schedule: pd.DataFrame) -> list[dict]:
        """Parse FastF1 schedule DataFrame into list of event dicts.

        Args:
            schedule: FastF1 event schedule DataFrame

        Returns:
            List of parsed event dictionaries
        """
        events = []
        for _, event in schedule.iterrows():
            # Parse sessions
            sessions = []
            for i in range(1, 6):
                session_name = event.get(f"Session{i}")
                session_date = event.get(f"Session{i}Date")
                session_date_utc = event.get(f"Session{i}DateUtc")

                if session_name and pd.notna(session_date):
                    sessions.append(
                        {
                            "name": session_name,
                            "date_local": session_date,
                            "date_utc": session_date_utc,
                        }
                    )

            events.append(
                {
                    "round": int(event["RoundNumber"]) if pd.notna(event["RoundNumber"]) else 0,
                    "event_name": event["EventName"],
                    "country": event["Country"],
                    "location": event["Location"],
                    "event_date": event["EventDate"],
                    "event_format": event["EventFormat"],
                    "sessions": sessions,
                }
            )

        return events

    def _determine_season_phase(self, current_time: datetime, events: list[dict]) -> F1Season:
        """Determine current F1 season phase.

        Args:
            current_time: Current time (UTC)
            events: List of race events

        Returns:
            Season phase
        """
        if not events:
            return F1Season.OFF_SEASON

        # Get first and last race dates
        first_race_date = events[0]["event_date"]
        last_race_date = events[-1]["event_date"]

        # Convert to datetime if needed
        if isinstance(first_race_date, pd.Timestamp):
            first_race_date = first_race_date.to_pydatetime()
        if isinstance(last_race_date, pd.Timestamp):
            last_race_date = last_race_date.to_pydatetime()

        # Ensure timezone awareness
        if first_race_date.tzinfo is None:
            first_race_date = first_race_date.replace(tzinfo=UTC)
        if last_race_date.tzinfo is None:
            last_race_date = last_race_date.replace(tzinfo=UTC)

        # Pre-season: More than 2 weeks before first race
        if current_time < first_race_date - timedelta(days=14):
            return F1Season.PRE_SEASON

        # Post-season: Within 4 weeks after last race
        if current_time > last_race_date and current_time < last_race_date + timedelta(days=28):
            return F1Season.POST_SEASON

        # Off-season: More than 4 weeks after last race
        if current_time > last_race_date + timedelta(days=28):
            return F1Season.OFF_SEASON

        # In-season: Between first and last race
        return F1Season.IN_SEASON

    def _find_current_weekend(self, current_time: datetime, events: list[dict]) -> RaceWeekendContext | None:
        """Find active race weekend if any.

        A weekend is considered "current" from Thursday 48h before first session
        until 6 hours after the race.

        Args:
            current_time: Current time (UTC)
            events: List of race events

        Returns:
            Current race weekend context or None
        """
        for event in events:
            sessions = event["sessions"]
            if not sessions:
                continue

            # Parse session dates
            parsed_sessions = []
            for session in sessions:
                date_utc = session["date_utc"]
                date_local = session["date_local"]

                if isinstance(date_utc, pd.Timestamp):
                    date_utc = date_utc.to_pydatetime()
                if isinstance(date_local, pd.Timestamp):
                    date_local = date_local.to_pydatetime()

                # Ensure UTC times have timezone info
                if date_utc.tzinfo is None:
                    date_utc = date_utc.replace(tzinfo=UTC)

                # Keep local times as naive datetimes (no timezone)
                # They represent the local time at the circuit
                if date_local.tzinfo is not None:
                    date_local = date_local.replace(tzinfo=None)

                parsed_sessions.append(
                    {
                        "name": session["name"],
                        "date_utc": date_utc,
                        "date_local": date_local,
                    }
                )

            # Check if we're within the race weekend window
            first_session_date = parsed_sessions[0]["date_utc"]
            last_session_date = parsed_sessions[-1]["date_utc"]

            weekend_start = first_session_date - timedelta(hours=48)
            weekend_end = last_session_date + timedelta(hours=6)

            if weekend_start <= current_time <= weekend_end:
                # We're in this race weekend
                return self._build_race_weekend_context(event, parsed_sessions, current_time)

        return None

    def _find_last_completed_race(self, current_time: datetime, events: list[dict]) -> RaceWeekendContext | None:
        """Find most recently completed race.

        Args:
            current_time: Current time (UTC)
            events: List of race events

        Returns:
            Last completed race context or None
        """
        completed_events = []

        for event in events:
            if self._is_race_completed(event, current_time):
                completed_events.append(event)

        if not completed_events:
            return None

        # Get the most recent one
        last_event = completed_events[-1]
        sessions = self._parse_event_sessions(last_event)
        return self._build_race_weekend_context(last_event, sessions, current_time, completed=True)

    def _find_next_race(self, current_time: datetime, events: list[dict]) -> RaceWeekendContext | None:
        """Find next upcoming race weekend.

        Args:
            current_time: Current time (UTC)
            events: List of race events

        Returns:
            Next race context or None
        """
        for event in events:
            event_date = event["event_date"]
            if isinstance(event_date, pd.Timestamp):
                event_date = event_date.to_pydatetime()
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=UTC)

            if event_date > current_time:
                sessions = self._parse_event_sessions(event)
                return self._build_race_weekend_context(event, sessions, current_time)

        return None

    def _is_race_completed(self, event: dict, current_time: datetime) -> bool:
        """Check if a race is completed.

        Args:
            event: Event dictionary
            current_time: Current time (UTC)

        Returns:
            True if race is completed
        """
        # Find the race session (last session)
        sessions = event.get("sessions", [])
        if not sessions:
            return False

        last_session = sessions[-1]
        race_date = last_session["date_utc"]

        if isinstance(race_date, pd.Timestamp):
            race_date = race_date.to_pydatetime()
        if race_date.tzinfo is None:
            race_date = race_date.replace(tzinfo=UTC)

        # Race is completed if it's more than 4 hours in the past
        # Extended from 3 to 4 hours to handle edge cases:
        # - Red-flagged races (e.g., Belgium 2021, Monaco 2011)
        # - Very long races with multiple safety car periods
        # - Post-race ceremonies and interviews
        return current_time > race_date + timedelta(hours=4)

    def _parse_event_sessions(self, event: dict) -> list[dict]:
        """Parse sessions for an event with timezone handling.

        Args:
            event: Event dictionary

        Returns:
            List of parsed session dictionaries
        """
        parsed_sessions = []
        for session in event.get("sessions", []):
            date_utc = session["date_utc"]
            date_local = session["date_local"]

            if isinstance(date_utc, pd.Timestamp):
                date_utc = date_utc.to_pydatetime()
            if isinstance(date_local, pd.Timestamp):
                date_local = date_local.to_pydatetime()

            # Ensure UTC times have timezone info
            if date_utc.tzinfo is None:
                date_utc = date_utc.replace(tzinfo=UTC)

            # Keep local times as naive datetimes (no timezone)
            # They represent the local time at the circuit
            if date_local.tzinfo is not None:
                date_local = date_local.replace(tzinfo=None)

            parsed_sessions.append(
                {
                    "name": session["name"],
                    "date_utc": date_utc,
                    "date_local": date_local,
                }
            )

        return parsed_sessions

    def _build_race_weekend_context(
        self, event: dict, sessions: list[dict], current_time: datetime, completed: bool = False
    ) -> RaceWeekendContext:
        """Build race weekend context from event data.

        Args:
            event: Event dictionary
            sessions: Parsed sessions
            current_time: Current time (UTC)
            completed: Whether the race is completed

        Returns:
            Race weekend context
        """
        # Determine session type mapping
        session_type_map = {
            "Practice 1": "FP1",
            "Practice 2": "FP2",
            "Practice 3": "FP3",
            "Qualifying": "Q",
            "Sprint Qualifying": "SQ",
            "Sprint": "S",
            "Race": "R",
        }

        # Build session contexts
        session_contexts = []
        current_session = None
        next_session = None

        for session in sessions:
            session_type = session_type_map.get(session["name"], "UNKNOWN")

            # Calculate time deltas
            time_delta = (session["date_utc"] - current_time).total_seconds() / 60

            # Session-type aware live detection windows
            # Format: (pre-session minutes, post-session minutes)
            session_windows = {
                "FP1": (-30, 90),  # 60 min session + 30 min buffer
                "FP2": (-30, 90),  # 60 min session + 30 min buffer
                "FP3": (-30, 90),  # 60 min session + 30 min buffer
                "Q": (-30, 90),  # ~60 min session + 30 min buffer
                "SQ": (-30, 60),  # Sprint Qualifying ~45 min
                "S": (-30, 60),  # Sprint ~30 min + 30 min buffer
                "R": (-30, 150),  # Race ~120 min + 30 min buffer
            }
            pre_window, post_window = session_windows.get(session_type, (-30, 120))
            is_live = pre_window <= time_delta <= post_window
            is_recent = -1440 <= time_delta <= 0  # Recent if within last 24h

            minutes_until = int(time_delta) if time_delta > 0 else None
            minutes_since = int(-time_delta) if time_delta < 0 else None

            session_ctx = SessionContext(
                name=session["name"],
                session_type=session_type,
                date_utc=session["date_utc"],
                date_local=session["date_local"],
                is_live=is_live,
                is_recent=is_recent,
                minutes_until=minutes_until,
                minutes_since=minutes_since,
            )

            session_contexts.append(session_ctx)

            # Track current and next sessions
            if is_live and current_session is None:
                current_session = session_ctx
            elif time_delta > 0 and next_session is None:
                next_session = session_ctx

        # Determine weekend phase
        phase = self._determine_weekend_phase(session_contexts, current_time, completed)

        # Check if sprint weekend
        is_sprint = any("Sprint" in s["name"] for s in sessions)

        # Parse event date
        event_date = event["event_date"]
        if isinstance(event_date, pd.Timestamp):
            event_date = event_date.to_pydatetime()
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=UTC)

        return RaceWeekendContext(
            round_number=event["round"],
            event_name=event["event_name"],
            country=event["country"],
            location=event["location"],
            event_date=event_date,
            phase=phase,
            current_session=current_session,
            next_session=next_session,
            all_sessions=session_contexts,
            is_sprint_weekend=is_sprint,
        )

    def _determine_weekend_phase(
        self, sessions: list[SessionContext], current_time: datetime, completed: bool
    ) -> RaceWeekendPhase:
        """Determine current phase of the race weekend.

        Args:
            sessions: List of session contexts
            current_time: Current time (UTC)
            completed: Whether the race is completed

        Returns:
            Race weekend phase
        """
        if completed:
            return RaceWeekendPhase.POST_RACE

        # Check for live or recent sessions
        for session in sessions:
            if session.is_live:
                if "Sprint" in session.name:
                    return RaceWeekendPhase.SPRINT
                elif "Qualifying" in session.name:
                    return RaceWeekendPhase.QUALIFYING
                elif "Race" in session.name:
                    return RaceWeekendPhase.RACE
                elif "Practice" in session.name:
                    return RaceWeekendPhase.PRACTICE

        # Check if race has completed
        race_sessions = [s for s in sessions if s.name == "Race"]
        if (
            race_sessions
            and race_sessions[0].is_recent
            and race_sessions[0].minutes_since
            and race_sessions[0].minutes_since > 120
        ):  # More than 2 hours after race
            return RaceWeekendPhase.POST_RACE

        # Otherwise, we're before or between sessions
        return RaceWeekendPhase.BEFORE_WEEKEND

    def _compute_ttl(self, season_phase: F1Season, current_weekend: RaceWeekendContext | None) -> int:
        """Compute cache TTL based on temporal state.

        Args:
            season_phase: Current season phase
            current_weekend: Current race weekend (if any)

        Returns:
            TTL in seconds
        """
        # Off-season: 7 days
        if season_phase == F1Season.OFF_SEASON:
            return 7 * 24 * 60 * 60

        # Pre-season: 3 days
        if season_phase == F1Season.PRE_SEASON:
            return 3 * 24 * 60 * 60

        # Post-season: 5 days
        if season_phase == F1Season.POST_SEASON:
            return 5 * 24 * 60 * 60

        # During race weekend
        if current_weekend:
            # Check if any session is live
            if current_weekend.current_session and current_weekend.current_session.is_live:
                return 5 * 60  # 5 minutes during live session

            # Check if next session is soon (within 2 hours)
            if (
                current_weekend.next_session
                and current_weekend.next_session.minutes_until
                and current_weekend.next_session.minutes_until < 120
            ):
                return 15 * 60  # 15 minutes when session approaching

            # Otherwise during race weekend
            return 60 * 60  # 1 hour

        # Between weekends during season
        return 12 * 60 * 60  # 12 hours
