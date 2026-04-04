"""Driver/constructor rating separation.

Isolates driver skill from constructor advantage using:
- Teammate normalisation (within-team delta)
- Car-adjusted driver score (R_driver - alpha * R_constructor)
- Driver transfer calibration events

Based on van Kesteren & Bergkamp's finding that ~88% of F1 race result
variance is explained by the constructor, ~12% by driver skill.
"""

from __future__ import annotations

from typing import TypedDict

from pitlane_elo.data import RaceEntry


class TeammateData(TypedDict):
    """Within-team rating delta for a single driver in a single race."""

    year: int
    round: int
    driver_id: str
    teammate_id: str
    driver_rating: float
    teammate_rating: float
    delta: float  # driver_rating - teammate_rating; positive = driver is higher rated


class TeammateNormaliser:
    """Accumulates within-team rating deltas across a driver's career.

    Call :meth:`record` immediately *after* the driver ELO model has processed
    each race so that ``ratings`` reflect post-update values.

    Both directions are stored (A→B and B→A), making per-driver queries
    straightforward without joining.
    """

    def __init__(self) -> None:
        self.history: dict[str, list[TeammateData]] = {}

    def record(
        self,
        entries: list[RaceEntry],
        ratings: dict[str, float],
    ) -> list[TeammateData]:
        """Record within-team rating deltas after a race has been processed.

        Args:
            entries: All driver entries for the race (any order).
            ratings: Current driver ratings from the ELO model (post-update).

        Returns:
            List of :class:`TeammateData` recorded for this race.
            Empty if no team has two valid finishers present in ``ratings``.
        """
        if not entries:
            return []

        year = entries[0]["year"]
        rnd = entries[0]["round"]

        # Collect valid finishers that also appear in ratings
        valid: list[RaceEntry] = [
            e for e in entries if e.get("finish_position") is not None and e["driver_id"] in ratings
        ]

        # Group by team
        by_team: dict[str, list[RaceEntry]] = {}
        for e in valid:
            by_team.setdefault(e["team"], []).append(e)

        new_records: list[TeammateData] = []

        for team_entries in by_team.values():
            if len(team_entries) < 2:
                continue

            # For 3+-car teams (rare, pre-1980): use the two with lowest finish_position
            sorted_entries = sorted(team_entries, key=lambda e: e["finish_position"])  # type: ignore[arg-type]
            a, b = sorted_entries[0], sorted_entries[1]

            r_a = ratings[a["driver_id"]]
            r_b = ratings[b["driver_id"]]

            record_a = TeammateData(
                year=year,
                round=rnd,
                driver_id=a["driver_id"],
                teammate_id=b["driver_id"],
                driver_rating=r_a,
                teammate_rating=r_b,
                delta=r_a - r_b,
            )
            record_b = TeammateData(
                year=year,
                round=rnd,
                driver_id=b["driver_id"],
                teammate_id=a["driver_id"],
                driver_rating=r_b,
                teammate_rating=r_a,
                delta=r_b - r_a,
            )

            self.history.setdefault(a["driver_id"], []).append(record_a)
            self.history.setdefault(b["driver_id"], []).append(record_b)
            new_records.extend([record_a, record_b])

        return new_records


__all__ = ["TeammateData", "TeammateNormaliser"]
