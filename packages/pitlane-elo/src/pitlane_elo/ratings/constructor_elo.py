"""Constructor endure-Elo: Powell's sequential knock-out model applied to constructors.

Each constructor's per-race performance is measured by the sum of F1 championship
points earned by its drivers (using the current 25-18-15-12-10-8-6-4-2-1 scale).
Constructors are ordered by descending points total — the same criterion used
in the actual F1 constructor standings. DNFs and positions outside the top 10
contribute 0 points, consistent with F1 rules.

The sequential elimination algorithm is identical to EndureElo but operates
over constructor entities rather than individual drivers.
"""

from __future__ import annotations

import numpy as np

from pitlane_elo.config import CONSTRUCTOR_ELO_DEFAULT, EloConfig
from pitlane_elo.data import RaceEntry, order_race_entries
from pitlane_elo.ratings.base import RatingModel
from pitlane_elo.ratings.endure_elo import _inclusion_exclusion

# F1 championship points by finishing position (current scale, applied universally).
# Positions outside the top 10 and DNFs contribute 0 points.
_F1_POINTS: dict[int, int] = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}


def _race_points(rank: int) -> int:
    """Return F1 championship points for a given 1-based implied finishing rank."""
    return _F1_POINTS.get(rank, 0)


class ConstructorElo(RatingModel):
    """Endure-Elo applied to F1 constructors.

    Team names are used as keys in the ``ratings`` and ``k_factors`` dicts
    (matching the ``team`` field on :class:`~pitlane_elo.data.RaceEntry`).

    Constructors are ordered each race by their total F1 championship points
    (sum across both drivers), matching the criterion used in the actual F1
    constructor standings. This correctly ranks 1st+4th (37 pts) above
    2nd+3rd (33 pts), and 2nd+3rd above 1st+20th (25 pts).
    """

    def __init__(self, config: EloConfig | None = None) -> None:
        super().__init__(config or CONSTRUCTOR_ELO_DEFAULT)

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

        # Assign each driver a 1-based rank and F1 championship points.
        driver_rank: dict[str, int] = {e["driver_id"]: i + 1 for i, e in enumerate(ordered)}
        driver_points: dict[str, int] = {d: _race_points(r) for d, r in driver_rank.items()}

        # Group by team: accumulate total points and track best (lowest) rank.
        team_points: dict[str, int] = {}
        team_best_rank: dict[str, int] = {}
        for e in ordered:
            did = e["driver_id"]
            team = e["team"]
            team_points[team] = team_points.get(team, 0) + driver_points[did]
            team_best_rank[team] = min(team_best_rank.get(team, 999), driver_rank[did])

        if len(team_points) < 2:
            return

        # Sort constructors best-first.
        # Primary key: descending F1 points (correctly orders top-10 finishers).
        # Tiebreaker: ascending best finishing rank (resolves ties in the 0-point
        # zone, P11 and below, where all teams would otherwise score 0).
        constructor_order: list[str] = sorted(
            team_points,
            key=lambda t: (-team_points[t], team_best_rank[t]),
        )

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

    def predict_win_probabilities(self, driver_ids: list[str]) -> np.ndarray:
        """Compute win probability for each constructor using inclusion-exclusion.

        Args:
            driver_ids: List of constructor (team) names. The parameter name
                matches the base class interface; for ConstructorElo the values
                are team name strings rather than driver ID slugs.

        Returns:
            Array of probabilities summing to 1.0, same order as driver_ids.
        """
        n = len(driver_ids)
        if n == 0:
            return np.array([])
        if n == 1:
            return np.array([1.0])

        lambdas = np.array([np.exp(-self.get_rating(t)) for t in driver_ids])
        probs = _inclusion_exclusion(lambdas)
        probs = np.clip(probs, 0.0, 1.0)
        total = probs.sum()
        if total > 0:
            probs /= total
        return probs



__all__ = ["ConstructorElo", "CONSTRUCTOR_ELO_DEFAULT"]
