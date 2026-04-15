"""Convert RaceEntry lists into arrays suitable for the van Kesteren PyMC model."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pitlane_elo.data import RaceEntry, get_race_entries, group_entries_by_race


@dataclass(frozen=True)
class SeasonData:
    """Model-ready arrays derived from one season's race entries.

    All driver and team vocabularies are sorted alphabetically, so the same
    dataset always produces the same integer index assignment.
    """

    driver_ids: tuple[str, ...]
    team_ids: tuple[str, ...]
    # driver_team_idx[d] = team index for driver d (most common team that season)
    driver_team_idx: np.ndarray  # shape (n_drivers,), int
    # Each element: 1-D int array of driver indices in finishing order (best first)
    race_orders: list[np.ndarray]
    is_wet_race: np.ndarray  # shape (n_races,), bool
    is_street_circuit: np.ndarray  # shape (n_races,), bool
    driver_to_idx: dict[str, int]
    team_to_idx: dict[str, int]

    @property
    def n_drivers(self) -> int:
        return len(self.driver_ids)

    @property
    def n_teams(self) -> int:
        return len(self.team_ids)

    @property
    def n_races(self) -> int:
        return len(self.race_orders)


def prepare_season(
    races: list[list[RaceEntry]],
    *,
    min_finishers: int = 2,
) -> SeasonData:
    """Convert grouped race entries for one season into model-ready arrays.

    DNF handling: any driver without a finish_position is excluded from that
    race's Plackett-Luce ordering. DNF categorisation (mechanical vs crash) is
    not used — the data is unreliable and the model does not need it. Drivers
    who DNF in some races still appear in the parameter vocabulary and receive
    ratings from the races they complete.

    Args:
        races: List of races, each a list of RaceEntry dicts. Each sub-list
            should cover a single (year, round, session_type) combination.
            Use group_entries_by_race() from data.py to produce this.
        min_finishers: Races with fewer classified finishers are dropped
            entirely (Plackett-Luce is undefined for a single-entry ordering).

    Returns:
        SeasonData with deterministically indexed arrays ready for PyMC.
    """
    # Collect all drivers and their team counts across the season.
    driver_team_counts: dict[str, Counter[str]] = {}
    for race in races:
        for entry in race:
            d = entry["driver_id"]
            t = entry["team"]
            if d not in driver_team_counts:
                driver_team_counts[d] = Counter()
            driver_team_counts[d][t] += 1

    # Alphabetical ordering for determinism.
    driver_ids = tuple(sorted(driver_team_counts))
    # Each driver's primary team: most common team that season.
    driver_primary_team = {d: counts.most_common(1)[0][0] for d, counts in driver_team_counts.items()}
    team_ids = tuple(sorted(set(driver_primary_team.values())))

    driver_to_idx = {d: i for i, d in enumerate(driver_ids)}
    team_to_idx = {t: i for i, t in enumerate(team_ids)}

    driver_team_idx = np.array([team_to_idx[driver_primary_team[d]] for d in driver_ids], dtype=np.intp)

    race_orders: list[np.ndarray] = []
    wet_flags: list[bool] = []
    street_flags: list[bool] = []

    for race in races:
        # Only classified finishers (those with a finish_position) contribute
        # to the Plackett-Luce ordering. DNFs of any kind are excluded.
        finishers = sorted(
            (e for e in race if e.get("finish_position") is not None),
            key=lambda e: e["finish_position"],  # type: ignore[arg-type]
        )

        if len(finishers) < min_finishers:
            continue

        order_idx = np.array([driver_to_idx[e["driver_id"]] for e in finishers], dtype=np.intp)
        race_orders.append(order_idx)

        # All entries in the same race share the same context flags.
        wet_flags.append(bool(race[0]["is_wet_race"]))
        street_flags.append(bool(race[0]["is_street_circuit"]))

    return SeasonData(
        driver_ids=driver_ids,
        team_ids=team_ids,
        driver_team_idx=driver_team_idx,
        race_orders=race_orders,
        is_wet_race=np.array(wet_flags, dtype=bool),
        is_street_circuit=np.array(street_flags, dtype=bool),
        driver_to_idx=driver_to_idx,
        team_to_idx=team_to_idx,
    )


def prepare_season_from_db(
    year: int,
    *,
    db_path: Path | None = None,
) -> SeasonData | None:
    """Convenience wrapper: fetch race entries from DB, group, and prepare.

    Fetches only session_type='R' (full race, not sprint) entries.

    Args:
        year: F1 season year.
        db_path: Override the database path. Defaults to get_db_path().

    Returns:
        SeasonData, or None if the database has no entries for the year.
    """
    entries = get_race_entries(year, db_path=db_path, session_type="R")
    if not entries:
        return None
    races = group_entries_by_race(entries)
    return prepare_season(races)
