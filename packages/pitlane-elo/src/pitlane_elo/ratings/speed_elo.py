"""Speed-Elo: sequential selection rating model (baseline).

Treats each race as m-1 sequential selection rounds that identify the
best competitors first. This is the conventional Plackett-Luce orientation
that serves as the baseline against which endure-Elo is benchmarked.

Key equations (Powell, 2023):
  Win probability for round a (eq 50):
    E(j wins round a) = exp(R_j) / Σ_{i: u_i >= a} exp(R_i)
  Rating update (eq 49):
    R̂_j += k * [X(j wins round a) - E(j wins round a)]
  Overall win probability (eq 51):
    P(j wins) = exp(R_j) / Σ exp(R_a)
"""

from __future__ import annotations

import numpy as np

from pitlane_elo.config import SPEED_ELO_DEFAULT, EloConfig
from pitlane_elo.data import RaceEntry, order_race_entries
from pitlane_elo.ratings.base import RatingModel


class SpeedElo(RatingModel):
    """Sequential selection Elo rating model (Powell's speed-Elo)."""

    def __init__(self, config: EloConfig | None = None) -> None:
        super().__init__(config or SPEED_ELO_DEFAULT)

    def process_race(self, entries: list[RaceEntry]) -> None:
        """Update ratings from a single race using sequential selection rounds.

        The race is decomposed into m-1 selection rounds. In each round the
        best remaining finisher is selected and all participants' ratings are
        updated according to the gradient of the speed Plackett-Luce
        log-likelihood.
        """
        filtered = self._filter_entries(entries)
        ordered = order_race_entries(filtered)
        m = len(ordered)
        if m < 2:
            return

        driver_ids = [e["driver_id"] for e in ordered]

        # Ensure all drivers are initialized
        for d in driver_ids:
            self.get_rating(d)

        # Apply between-race decay
        for d in driver_ids:
            self.ratings[d] *= self.config.phi_race

        # Sequential selection: m-1 rounds, selecting 1st place first.
        # Iterate by start index to avoid O(n) list.pop(0) each round.
        for start in range(m - 1):
            remaining = driver_ids[start:]
            # The driver selected this round is the best in the remaining set
            selected = remaining[0]

            # Compute win probabilities for this round (eq 50)
            # E(j wins round) = exp(R_j) / Σ exp(R_i)
            ratings_arr = np.array([self.ratings[d] for d in remaining])
            ratings_shifted = ratings_arr - ratings_arr.max()  # numerical stability
            exp_r = np.exp(ratings_shifted)
            win_probs = exp_r / exp_r.sum()

            # K-factor (precision) update FIRST (same Glicko-style as endure-Elo)
            for idx, d in enumerate(remaining):
                p_w = win_probs[idx]
                k_inv = 1.0 / self.k_factors[d] + p_w * (1.0 - p_w)
                self.k_factors[d] = max(self.config.k_min, min(1.0 / k_inv, self.config.k_max))

            # Rating update (eq 49)
            # R̂_j += k_j * [X(j wins round) - E(j wins round)]
            for idx, d in enumerate(remaining):
                won = 1.0 if d == selected else 0.0
                self.ratings[d] += self.k_factors[d] * (won - win_probs[idx])

    def predict_win_probabilities(self, driver_ids: list[str]) -> np.ndarray:
        """Compute win probability using softmax (eq 51).

        P(j wins) = exp(R_j) / Σ exp(R_a)

        For the speed model, the win probability is simply the probability
        of winning the first selection round.
        """
        n = len(driver_ids)
        if n == 0:
            return np.array([])
        if n == 1:
            return np.array([1.0])

        ratings_arr = np.array([self.get_rating(d) for d in driver_ids])
        ratings_shifted = ratings_arr - ratings_arr.max()
        exp_r = np.exp(ratings_shifted)
        return exp_r / exp_r.sum()
