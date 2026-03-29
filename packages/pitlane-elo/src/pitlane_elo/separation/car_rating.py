"""Qualifying-based Car Rating (Rc) computation.

Implements Xun's per-Grand-Prix car performance metric:
    Rc = (T_team_avg_qual - T_fastest_qual) / T_fastest_qual

Lower Rc = faster car. Computed per qualifying session, providing a
track-specific signal of raw car pace independent of race outcomes.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import TypedDict

from pitlane_elo.data import (
    QualifyingEntry,
    get_qualifying_entries_range,
    group_qualifying_by_session,
)


class CarRating(TypedDict):
    """Per-team car rating for a single qualifying session."""

    year: int
    round: int
    team: str
    rc: float  # Xun's Rc value (0.0 = fastest car)
    t_team_avg: float  # team's average best qualifying time (seconds)
    t_fastest: float  # session-fastest best qualifying time (seconds)


def compute_session_rc(entries: list[QualifyingEntry]) -> list[CarRating]:
    """Compute Rc for each team from a single qualifying session's entries.

    Args:
        entries: All qualifying entries for one session (same year/round).
                 Drivers missing ``best_q_time_s`` are excluded.

    Returns:
        One :class:`CarRating` per team that has at least one valid time.
        Returns an empty list if no valid times exist.
    """
    if not entries:
        return []

    year = entries[0]["year"]
    rnd = entries[0]["round"]

    # Collect valid times per team
    team_times: dict[str, list[float]] = {}
    all_times: list[float] = []
    for entry in entries:
        t = entry.get("best_q_time_s")
        if t is None:
            continue
        team_times.setdefault(entry["team"], []).append(t)
        all_times.append(t)

    if not all_times:
        return []

    t_fastest = min(all_times)

    results: list[CarRating] = []
    for team in sorted(team_times):
        times = team_times[team]
        t_team_avg = sum(times) / len(times)
        rc = (t_team_avg - t_fastest) / t_fastest
        results.append(
            CarRating(
                year=year,
                round=rnd,
                team=team,
                rc=rc,
                t_team_avg=t_team_avg,
                t_fastest=t_fastest,
            )
        )
    return results


def compute_rc_range(
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
) -> list[CarRating]:
    """Compute Rc for all qualifying sessions across a range of seasons.

    Args:
        start_year: First season year.
        end_year: Last season year (inclusive).
        db_path: Override the database path.

    Returns:
        Flat list of :class:`CarRating` across all sessions, ordered
        chronologically.  Returns an empty list if no qualifying data exists.
    """
    entries = get_qualifying_entries_range(start_year, end_year, db_path=db_path)
    if not entries:
        return []

    sessions = group_qualifying_by_session(entries)
    results: list[CarRating] = []
    for session in sessions:
        results.extend(compute_session_rc(session))
    return results


__all__ = [
    "CarRating",
    "compute_rc_range",
    "compute_session_rc",
]
