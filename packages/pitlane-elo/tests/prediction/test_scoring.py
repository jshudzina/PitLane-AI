"""Tests for pitlane_elo.prediction.scoring."""

from __future__ import annotations

import numpy as np
import pytest
from pitlane_elo.prediction.scoring import (
    brier_score,
    log_likelihood,
    log_wealth_ratio,
    race_level_comparison,
    rmse_position,
)


class TestLogLikelihood:
    def test_perfect_predictions(self) -> None:
        """All winners predicted with prob 1.0 → LL = 0."""
        probs = np.array([1.0, 1.0, 1.0])
        assert log_likelihood(probs) == pytest.approx(0.0)

    def test_uniform_predictions(self) -> None:
        """Uniform 1/20 for 5 races → LL = 5 * log(1/20)."""
        probs = np.full(5, 1 / 20)
        expected = 5 * np.log(1 / 20)
        assert log_likelihood(probs) == pytest.approx(expected)

    def test_handles_zero_probs(self) -> None:
        """Zero probability should not produce -inf."""
        probs = np.array([0.0, 0.5])
        result = log_likelihood(probs)
        assert np.isfinite(result)


class TestBrierScore:
    def test_perfect_predictions(self) -> None:
        preds = [(np.array([1.0, 0.0, 0.0]), 0)]
        assert brier_score(preds) == pytest.approx(0.0)

    def test_uniform_predictions(self) -> None:
        # With 3 drivers, uniform = 1/3 each, winner at idx 0
        probs = np.array([1 / 3, 1 / 3, 1 / 3])
        preds = [(probs, 0)]
        # BS = (1/3-1)^2 + (1/3-0)^2 + (1/3-0)^2 = 4/9 + 1/9 + 1/9 = 6/9
        assert brier_score(preds) == pytest.approx(6 / 9)

    def test_empty_returns_zero(self) -> None:
        assert brier_score([]) == 0.0


class TestRmsePosition:
    def test_perfect(self) -> None:
        pred = np.array([1.0, 2.0, 3.0])
        actual = np.array([1.0, 2.0, 3.0])
        assert rmse_position(pred, actual) == pytest.approx(0.0)

    def test_known_value(self) -> None:
        pred = np.array([1.0, 2.0])
        actual = np.array([2.0, 1.0])
        # RMSE = sqrt((1+1)/2) = 1.0
        assert rmse_position(pred, actual) == pytest.approx(1.0)


class TestRaceLevelComparison:
    def test_a_always_better(self) -> None:
        ll_a = np.array([1.0, 2.0, 3.0])
        ll_b = np.array([0.0, 0.0, 0.0])
        assert race_level_comparison(ll_a, ll_b) == pytest.approx(1.0)

    def test_split(self) -> None:
        ll_a = np.array([1.0, 0.0, 1.0, 0.0])
        ll_b = np.array([0.0, 1.0, 0.0, 1.0])
        assert race_level_comparison(ll_a, ll_b) == pytest.approx(0.5)


class TestLogWealthRatio:
    def test_equal_models(self) -> None:
        probs = np.array([0.3, 0.5, 0.2])
        assert log_wealth_ratio(probs, probs) == pytest.approx(0.0)

    def test_q_better(self) -> None:
        q = np.array([0.5, 0.5])
        p = np.array([0.1, 0.1])
        # D = 2 * log(0.5/0.1) = 2 * log(5)
        assert log_wealth_ratio(q, p) == pytest.approx(2 * np.log(5))
