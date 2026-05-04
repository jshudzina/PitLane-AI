"""Public studio API for pitlane-elo.

Stable boundary consumed by pitlane-studio (and integration tests).
Wraps pitlane_elo.stories.signals.detect_stories with the studio-facing
signature (year, round) — mapping the public `round` parameter to the
internal `round_num` via positional call.

Per CONTEXT.md D-01: returns the existing StorySignal dataclass as-is.
Phase 2's AngleService is responsible for any boundary-type transformation.
"""

from __future__ import annotations

from pitlane_elo.stories.signals import StorySignal
from pitlane_elo.stories.signals import detect_stories as _detect_stories


def detect_stories(year: int, round: int) -> list[StorySignal]:  # noqa: A002
    """Detect story signals for a completed race.

    Args:
        year: Season year (e.g. 2026).
        round: Round number within the season (e.g. 5).

    Returns:
        List of StorySignal instances, sorted by |value| descending.
        Empty list if no ELO snapshots have been built for this race
        (this is a data condition, not an error condition).
    """
    # Positional call — internal parameter is `round_num`, do NOT pass round=
    return _detect_stories(year, round)


__all__ = ["StorySignal", "detect_stories"]
