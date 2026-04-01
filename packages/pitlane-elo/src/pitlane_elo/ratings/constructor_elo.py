"""Constructor endure-Elo: Powell's sequential knock-out model applied to constructors.

Each constructor's per-race "performance position" is derived from the average
implied finishing rank of its drivers. DNFs without finish_position are ranked
by laps_completed (consistent with order_race_entries). If only one driver has
a valid entry, that driver's implied rank is used directly.

The sequential elimination algorithm is identical to EndureElo but operates
over constructor entities rather than individual drivers.
"""

from __future__ import annotations

import numpy as np

from pitlane_elo.config import ENDURE_ELO_DEFAULT, EloConfig
from pitlane_elo.data import RaceEntry, order_race_entries
from pitlane_elo.ratings.base import RatingModel
from pitlane_elo.ratings.endure_elo import _inclusion_exclusion


class ConstructorElo(RatingModel):
    """Endure-Elo applied to F1 constructors.

    Team names are used as keys in the ``ratings`` and ``k_factors`` dicts
    (matching the ``team`` field on :class:`~pitlane_elo.data.RaceEntry`).

    Per-race constructor position is computed as the average 1-based rank of
    the constructor's drivers in the full field ordering produced by
    :func:`~pitlane_elo.data.order_race_entries`.  This handles DNFs
    consistently without special-casing ``None`` finish positions.
    """

    def __init__(self, config: EloConfig | None = None) -> None:
        super().__init__(config or ENDURE_ELO_DEFAULT)

    def process_race(self, entries: list[RaceEntry]) -> None:
        """Update constructor ratings from a single race.

        Args:
            entries: All driver entries for one race (any order).  Entries
                with ``dnf_category="mechanical"`` are excluded when
                ``config.exclude_mechanical_dnf`` is True.
        """
        filtered = self._filter_entries(entries)
        ordered = order_race_entries(filtered)
        if len(ordered) < 2:
            return

        # Assign each driver a 1-based rank by their index in the ordered list
        driver_rank: dict[str, float] = {e["driver_id"]: float(i + 1) for i, e in enumerate(ordered)}

        # Group by team and compute average rank
        team_ranks: dict[str, list[float]] = {}
        for e in ordered:
            team_ranks.setdefault(e["team"], []).append(driver_rank[e["driver_id"]])

        if len(team_ranks) < 2:
            return

        # Sort constructors by average rank ascending (lower = better)
        constructor_order: list[str] = sorted(team_ranks, key=lambda t: sum(team_ranks[t]) / len(team_ranks[t]))

        # Ensure all constructors are initialized
        for team in constructor_order:
            self.get_rating(team)

        # Apply between-race decay
        for team in constructor_order:
            self.ratings[team] *= self.config.phi_race

        # Sequential elimination: identical algorithm to EndureElo
        remaining = list(constructor_order)  # best-performing constructor first

        for _ in range(len(remaining) - 1):
            eliminated = remaining[-1]

            neg_ratings = np.array([-self.ratings[t] for t in remaining])
            neg_ratings_shifted = neg_ratings - neg_ratings.max()
            exp_neg = np.exp(neg_ratings_shifted)
            elim_probs = exp_neg / exp_neg.sum()
            survive_probs = 1.0 - elim_probs

            # K-factor update
            for idx, team in enumerate(remaining):
                p_s = survive_probs[idx]
                k_inv = 1.0 / self.k_factors[team] + p_s * (1.0 - p_s)
                self.k_factors[team] = max(self.config.k_min, min(1.0 / k_inv, self.config.k_max))

            # Rating update
            for idx, team in enumerate(remaining):
                survived = 1.0 if team != eliminated else 0.0
                self.ratings[team] += self.k_factors[team] * (survived - survive_probs[idx])

            remaining.pop()

    def predict_win_probabilities(self, constructor_ids: list[str]) -> np.ndarray:
        """Compute win probability for each constructor using inclusion-exclusion.

        Args:
            constructor_ids: List of constructor (team) names.

        Returns:
            Array of probabilities summing to 1.0, same order as constructor_ids.
        """
        n = len(constructor_ids)
        if n == 0:
            return np.array([])
        if n == 1:
            return np.array([1.0])

        lambdas = np.array([np.exp(-self.get_rating(t)) for t in constructor_ids])
        probs = _inclusion_exclusion(lambdas)
        probs = np.clip(probs, 0.0, 1.0)
        total = probs.sum()
        if total > 0:
            probs /= total
        return probs


CONSTRUCTOR_ELO_DEFAULT = ENDURE_ELO_DEFAULT

__all__ = ["ConstructorElo", "CONSTRUCTOR_ELO_DEFAULT"]
