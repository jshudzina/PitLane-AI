"""Endure-Elo: Powell's sequential knock-out rating model.

Decomposes each race into m-1 sequential rounds, eliminating the worst
finisher each round. Based on the Plackett-Luce model with exponential
failure times. Demonstrated to beat speed-Elo 76.3% of the time over
873 F1 races (Powell, 2023).

Key equations (from the paper):
  Elimination probability (eq 3):
    P(i eliminated) = exp(-R̂_i) / Σ exp(-R̂_j)
  K-factor update (eq 5):
    k_i^{-1} ← k_i^{-1} + P(survive) * (1 - P(survive))
  Rating update (eq 6):
    R̂_i ← R̂_i + k_i * [I(survived) - P(survived)]
  Win probability (eq 60, inclusion-exclusion):
    P(j wins) = Σ (-1)^|C_r| * λ_j / (λ_j + Σ_{k∈C_r} λ_k)
"""

from __future__ import annotations

import numpy as np

from pitlane_elo.config import ENDURE_ELO_DEFAULT, EloConfig
from pitlane_elo.data import RaceEntry, order_race_entries
from pitlane_elo.ratings.base import RatingModel


class EndureElo(RatingModel):
    """Powell's endure-Elo with sequential knock-out rounds."""

    def __init__(self, config: EloConfig | None = None) -> None:
        super().__init__(config or ENDURE_ELO_DEFAULT)

    def process_race(self, entries: list[RaceEntry]) -> None:
        """Update ratings from a single race using sequential elimination.

        The race is decomposed into m-1 knock-out rounds. In each round the
        last-place finisher is eliminated and all participants' ratings are
        updated according to the gradient of the Plackett-Luce log-likelihood.
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

        # Apply between-race decay (eq 8: R̂ ← φ · R̂)
        for d in driver_ids:
            self.ratings[d] *= self.config.phi_race

        # Sequential elimination: m-1 rounds, eliminating last place first
        remaining = list(driver_ids)  # in finishing order (best first)

        for _ in range(m - 1):
            # The driver eliminated this round is the last in the remaining set
            eliminated = remaining[-1]

            # Compute elimination probabilities (eq 3)
            # P(i eliminated) = exp(-R_i) / Σ exp(-R_j)
            neg_ratings = np.array([-self.ratings[d] for d in remaining])
            neg_ratings_shifted = neg_ratings - neg_ratings.max()  # numerical stability
            exp_neg = np.exp(neg_ratings_shifted)
            elim_probs = exp_neg / exp_neg.sum()
            survive_probs = 1.0 - elim_probs

            # K-factor (precision) update FIRST (eq 5)
            # k_i^{-1} ← k_i^{-1} + P(survive) * (1 - P(survive))
            for idx, d in enumerate(remaining):
                p_s = survive_probs[idx]
                k_inv = 1.0 / self.k_factors[d] + p_s * (1.0 - p_s)
                self.k_factors[d] = max(self.config.k_min, min(1.0 / k_inv, self.config.k_max))

            # Rating update (eq 6)
            # R̂_i ← R̂_i + k_i * [I(survived) - P(survived)]
            for idx, d in enumerate(remaining):
                survived = 1.0 if d != eliminated else 0.0
                self.ratings[d] += self.k_factors[d] * (survived - survive_probs[idx])

            # Remove eliminated driver from remaining set
            remaining.pop()

    def predict_win_probabilities(self, driver_ids: list[str]) -> np.ndarray:
        """Compute win probability using the inclusion-exclusion formula (eq 60).

        P(j wins) = Σ_{r=0}^{2^{n-1}-1} (-1)^|C_r| * λ_j / (λ_j + Σ_{k∈C_r} λ_k)

        where λ_i = exp(-R̂_i) and C_r are elements of the power set of
        competitors excluding j.

        Uses the recursive denominator-building approach from Powell's R code
        (Appendix A.1.3) for efficiency.
        """
        n = len(driver_ids)
        if n == 0:
            return np.array([])
        if n == 1:
            return np.array([1.0])

        lambdas = np.array([np.exp(-self.get_rating(d)) for d in driver_ids])
        probs = np.zeros(n)

        for i in range(n):
            lambda_i = lambdas[i]
            # Build denominators and signs recursively over rivals
            # Start with just lambda_i as the sole denominator, sign +1
            others = np.delete(lambdas, i)
            denominators = np.array([lambda_i])
            signs = np.array([1.0])

            for k in range(n - 1):
                # Each existing denominator spawns a copy with others[k] added
                # and the sign flipped
                denominators = np.concatenate([denominators, denominators + others[k]])
                signs = np.concatenate([signs, -signs])

            probs[i] = np.sum(lambda_i / denominators * signs)

        # Clamp small numerical errors
        probs = np.clip(probs, 0.0, 1.0)
        total = probs.sum()
        if total > 0:
            probs /= total
        return probs
