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

import numba as nb
import numpy as np

from pitlane_elo.config import ENDURE_ELO_DEFAULT, EloConfig
from pitlane_elo.data import RaceEntry, order_race_entries
from pitlane_elo.ratings.base import RatingModel


@nb.njit(cache=True, parallel=True)
def _inclusion_exclusion(lambdas: np.ndarray) -> np.ndarray:
    """Compute win probabilities via inclusion-exclusion (eq 60).

    JIT-compiled to native ARM with parallel driver iteration.
    """
    n = len(lambdas)
    probs = np.zeros(n)
    for i in nb.prange(n):
        lambda_i = lambdas[i]
        # Build the "others" array excluding driver i
        others = np.empty(n - 1)
        idx = 0
        for j in range(n):
            if j != i:
                others[idx] = lambdas[j]
                idx += 1
        m = n - 1
        total = 0.0
        for bits in range(1 << m):
            denom = lambda_i
            sign = 1.0
            for k in range(m):
                if bits & (1 << k):
                    denom += others[k]
                    sign = -sign
            total += sign * lambda_i / denom
        probs[i] = total
    return probs


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

    def predict_podium_probabilities(self, driver_ids: list[str], *, n_samples: int = 100_000) -> np.ndarray:
        """Compute probability each driver finishes in the top 3 (podium).

        Uses the competitive exponential representation of the Plackett-Luce model:
        draw T_i ~ Exp(λ_i) independently; the top-3 finishers are the 3 drivers
        with the largest T values. With 100_000 samples, standard error is < 0.2%.
        """
        n = len(driver_ids)
        if n == 0:
            return np.array([])
        if n <= 3:
            return np.ones(n)

        lambdas = np.array([np.exp(-self.get_rating(d)) for d in driver_ids])
        rng = np.random.default_rng()
        # T[i, s] ~ Exp(rate=λ_i): survival time for driver i in sample s.
        # Drivers with the 3 largest T values finish on the podium.
        t_samples = rng.exponential(size=(n, n_samples)) / lambdas[:, None]
        top3_threshold = np.partition(t_samples, kth=n - 3, axis=0)[n - 3]
        return np.clip((t_samples >= top3_threshold).mean(axis=1), 0.0, 1.0)

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
        probs = _inclusion_exclusion(lambdas)

        # Clamp small numerical errors
        probs = np.clip(probs, 0.0, 1.0)
        total = probs.sum()
        if total > 0:
            probs /= total
        return probs
