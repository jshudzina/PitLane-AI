"""Prediction assessment metrics.

Pure functions operating on (predicted, actual) arrays:
- Log-likelihood of race winner
- Brier score (win probability calibration)
- RMSE on finishing position
- Race-level comparison (fraction where model A beats model B)
- Log-wealth ratio (Powell's D(q,p), eq 53)
"""

from __future__ import annotations

import numpy as np


def log_likelihood(winner_probs: np.ndarray) -> float:
    """Total log-likelihood across races.

    Args:
        winner_probs: 1-D array where element i is the model's predicted
            probability for the actual winner of race i.

    Returns:
        Sum of log(p) across races. Higher is better.
    """
    clipped = np.clip(winner_probs, 1e-15, 1.0)
    return float(np.sum(np.log(clipped)))


def brier_score(race_predictions: list[tuple[np.ndarray, int]]) -> float:
    """Mean Brier score across races.

    Args:
        race_predictions: List of (probability_vector, actual_winner_index)
            tuples. Each probability_vector sums to 1.0 and the index
            identifies which driver actually won.

    Returns:
        Mean Brier score. Lower is better. 0.0 = perfect, higher = worse.
    """
    if not race_predictions:
        return 0.0
    total = 0.0
    for probs, winner_idx in race_predictions:
        actual = np.zeros_like(probs)
        actual[winner_idx] = 1.0
        total += float(np.sum((probs - actual) ** 2))
    return total / len(race_predictions)


def rmse_position(predicted_positions: np.ndarray, actual_positions: np.ndarray) -> float:
    """RMSE between predicted and actual finishing positions.

    Args:
        predicted_positions: Predicted positions (1-indexed).
        actual_positions: Actual positions (1-indexed).

    Returns:
        Root mean squared error. Lower is better.
    """
    return float(np.sqrt(np.mean((predicted_positions - actual_positions) ** 2)))


def race_level_comparison(ll_a: np.ndarray, ll_b: np.ndarray) -> float:
    """Fraction of races where model A has higher log-likelihood than model B.

    Args:
        ll_a: Per-race log-likelihoods for model A.
        ll_b: Per-race log-likelihoods for model B.

    Returns:
        Fraction in [0, 1]. Values > 0.5 favour model A.
    """
    if len(ll_a) == 0:
        return 0.5
    return float(np.mean(ll_a > ll_b))


def log_wealth_ratio(q_winner_probs: np.ndarray, p_winner_probs: np.ndarray) -> float:
    """Powell's D(q,p) log-wealth ratio (eq 53).

    D(q,p) = Σ log(q_i / p_i)

    where q_i and p_i are the probabilities assigned to the actual winner
    of race i by models q and p respectively.

    Args:
        q_winner_probs: Winner probabilities from model q (endure-Elo).
        p_winner_probs: Winner probabilities from model p (speed-Elo).

    Returns:
        Total log-wealth ratio. Positive = model q is better.
        Powell reports D = 592 over 873 races.
    """
    q_clipped = np.clip(q_winner_probs, 1e-15, 1.0)
    p_clipped = np.clip(p_winner_probs, 1e-15, 1.0)
    return float(np.sum(np.log(q_clipped / p_clipped)))
