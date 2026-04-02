"""Empirical estimation of the constructor-adjustment weight alpha.

Implements a grid search to find the alpha that maximises the log-likelihood
of race winners when driver ratings are adjusted by:

    adjusted_i = R_driver_i - alpha * R_constructor_i

where R_constructor is produced by a parallel ConstructorElo track.

NOTE — Circularity: ConstructorElo is trained on raw driver finish positions,
not on alpha-adjusted positions. This means the two models are not jointly
optimised. The estimated alpha will be a first-order approximation; the
literature value (van Kesteren & Bergkamp 2023) is ~7.3.  Joint optimisation
(alternating updates until convergence) is a future refinement.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import numpy as np

from pitlane_elo.data import get_race_entries_range, group_entries_by_race
from pitlane_elo.ratings.constructor_elo import ConstructorElo
from pitlane_elo.ratings.endure_elo import EndureElo, _inclusion_exclusion


class _RaceObs(TypedDict):
    """Per-driver observation for one race, used in grid search scoring."""

    driver_id: str
    driver_rating: float
    constructor_rating: float
    is_winner: bool


def estimate_alpha(
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
    alpha_bounds: tuple[float, float] = (0.0, 15.0),
    n_steps: int = 30,
    on_step: Callable[[int, int, float, float, float], None] | None = None,
) -> float:
    """Estimate the constructor-adjustment weight alpha via grid search.

    Runs :class:`~pitlane_elo.ratings.endure_elo.EndureElo` and
    :class:`~pitlane_elo.ratings.constructor_elo.ConstructorElo` in parallel
    over ``[start_year, end_year]``.  After each race both models are updated
    and per-driver ``(driver_rating, constructor_rating)`` pairs are recorded.

    Alpha is then fit by a uniform grid search over ``alpha_bounds`` with
    ``n_steps`` candidate values.  For each candidate the adjusted driver
    ratings ``R_driver - alpha * R_constructor`` are passed through the
    inclusion-exclusion win probability formula and the sum of
    ``log P(winner)`` over all races is computed.  The alpha with the
    highest log-likelihood is returned.

    Returns ``alpha_bounds[0]`` if there is no data for the requested range.

    Args:
        start_year: First season to process (used for warm-up and estimation).
        end_year: Last season (inclusive).
        db_path: Override the database path.
        alpha_bounds: ``(lo, hi)`` range for the grid search.
        n_steps: Number of evenly-spaced candidate alpha values.
        on_step: Optional callback invoked after each grid-search step with
            ``(step, total, alpha, log_likelihood, best_ll_so_far)``.

    Returns:
        Estimated alpha value in ``[alpha_bounds[0], alpha_bounds[1]]``.
    """
    all_entries = get_race_entries_range(start_year, end_year, db_path=db_path)
    if not all_entries:
        return alpha_bounds[0]

    filtered = [e for e in all_entries if e["session_type"] == "R"]
    if not filtered:
        return alpha_bounds[0]

    races = group_entries_by_race(filtered)
    driver_model = EndureElo()
    constructor_model = ConstructorElo()

    # Per-race observation lists for the grid search
    race_observations: list[list[_RaceObs]] = []

    current_year: int | None = None

    for race_entries in races:
        year = race_entries[0]["year"]

        # Season boundary: apply decay to both models
        if current_year is not None and year != current_year:
            driver_model.apply_season_decay(year)
            constructor_model.apply_season_decay(year)
        current_year = year

        # Update both models
        driver_model.process_race(race_entries)
        constructor_model.process_race(race_entries)

        # Determine winner (first entry in finishing order)
        ordered_ids = [e["driver_id"] for e in race_entries]
        winner_id = ordered_ids[0]

        obs: list[_RaceObs] = []
        for e in race_entries:
            driver_id = e["driver_id"]
            team = e["team"]
            # Both models initialise unseen entities on first get_rating call
            obs.append(
                _RaceObs(
                    driver_id=driver_id,
                    driver_rating=driver_model.get_rating(driver_id),
                    constructor_rating=constructor_model.get_rating(team),
                    is_winner=(driver_id == winner_id),
                )
            )
        race_observations.append(obs)

    if not race_observations:
        return alpha_bounds[0]

    # Grid search over alpha candidates
    candidates = np.linspace(alpha_bounds[0], alpha_bounds[1], max(n_steps, 1))
    best_alpha = candidates[0]
    best_ll = float("-inf")
    total_steps = len(candidates)

    for step, alpha in enumerate(candidates, 1):
        total_ll = 0.0
        for race_obs in race_observations:
            if not race_obs:
                continue

            adjusted = np.array([o["driver_rating"] - alpha * o["constructor_rating"] for o in race_obs])
            lambdas = np.exp(-adjusted)
            probs = _inclusion_exclusion(lambdas)
            probs = np.clip(probs, 1e-15, 1.0)
            total = probs.sum()
            if total > 0:
                probs = probs / total

            winner_idx = next((i for i, o in enumerate(race_obs) if o["is_winner"]), None)
            if winner_idx is None:
                continue
            total_ll += float(np.log(max(probs[winner_idx], 1e-15)))

        if total_ll > best_ll:
            best_ll = total_ll
            best_alpha = float(alpha)

        if on_step is not None:
            on_step(step, total_steps, float(alpha), total_ll, best_ll)

    return best_alpha


__all__ = ["estimate_alpha"]
