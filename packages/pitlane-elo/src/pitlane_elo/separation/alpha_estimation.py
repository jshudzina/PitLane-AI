"""Empirical estimation of the constructor-adjustment weight alpha.

Implements OLS variance decomposition (van Kesteren & Bergkamp 2023, §7.3):

    alpha = Cov(driver_ratings, constructor_ratings) / Var(constructor_ratings)

This measures the fraction of a driver's ELO explained by their car's ELO.
Ratings are recorded **before** each race update so they are out-of-sample
with respect to that race.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import stats

from pitlane_elo.data import get_race_entries_range, group_entries_by_race
from pitlane_elo.ratings.constructor_elo import ConstructorElo
from pitlane_elo.ratings.endure_elo import EndureElo


def estimate_alpha(
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
) -> float:
    """Estimate the constructor-adjustment weight alpha via OLS variance decomposition.

    Runs :class:`~pitlane_elo.ratings.endure_elo.EndureElo` and
    :class:`~pitlane_elo.ratings.constructor_elo.ConstructorElo` in parallel
    over ``[start_year, end_year]``.  Before each race, the current pre-race
    ``(driver_rating, constructor_rating)`` pair is recorded for each entry.

    Alpha is then estimated as the OLS slope of driver ratings on constructor
    ratings::

        alpha = Cov(driver_ratings, constructor_ratings) / Var(constructor_ratings)

    Returns ``0.0`` if there is no data for the requested range or if all
    constructor ratings are identical (zero variance, OLS undefined).

    Args:
        start_year: First season to process (used for warm-up and estimation).
        end_year: Last season (inclusive).
        db_path: Override the database path.

    Returns:
        Estimated alpha value.
    """
    all_entries = get_race_entries_range(start_year, end_year, db_path=db_path)
    if not all_entries:
        return 0.0

    filtered = [e for e in all_entries if e["session_type"] == "R"]
    if not filtered:
        return 0.0

    races = group_entries_by_race(filtered)
    driver_model = EndureElo()
    constructor_model = ConstructorElo()

    driver_ratings: list[float] = []
    constructor_ratings: list[float] = []

    current_year: int | None = None

    for race_entries in races:
        year = race_entries[0]["year"]

        # Season boundary: apply decay to both models
        if current_year is not None and year != current_year:
            driver_model.apply_season_decay(year)
            constructor_model.apply_season_decay(year)
        current_year = year

        # Record BEFORE update (out-of-sample)
        for e in race_entries:
            driver_ratings.append(driver_model.get_rating(e["driver_id"]))
            constructor_ratings.append(constructor_model.get_rating(e["team"]))

        # Then update both models
        driver_model.process_race(race_entries)
        constructor_model.process_race(race_entries)

    if len(driver_ratings) < 2:
        return 0.0

    x = np.array(constructor_ratings)
    y = np.array(driver_ratings)

    if np.var(x) < 1e-12:
        # All constructor ratings identical — OLS undefined, return safe default
        return 0.0

    return float(stats.linregress(x, y).slope)


__all__ = ["estimate_alpha"]
