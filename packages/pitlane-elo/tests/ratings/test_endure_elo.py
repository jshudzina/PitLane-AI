"""Tests for pitlane_elo.ratings.endure_elo."""

from __future__ import annotations

import numpy as np
from pitlane_elo.config import EloConfig
from pitlane_elo.ratings.endure_elo import EndureElo
from tests.conftest import make_race_entry


class TestEndureElo:
    def test_instantiation(self) -> None:
        model = EndureElo()
        assert model.config.name == "endure-elo-default"

    def test_get_rating_initializes(self) -> None:
        model = EndureElo()
        rating = model.get_rating("verstappen")
        assert rating == model.config.initial_rating

    def test_three_driver_race(self) -> None:
        """Winner's rating should increase, loser's should decrease."""
        model = EndureElo()
        entries = [make_race_entry("A", 1), make_race_entry("B", 2), make_race_entry("C", 3)]
        model.process_race(entries)

        assert model.ratings["A"] > 0.0, "Winner rating should increase"
        assert model.ratings["C"] < 0.0, "Last place rating should decrease"

    def test_repeated_races_diverge_ratings(self) -> None:
        """After many races where A always beats B, ratings should diverge."""
        model = EndureElo()
        for _ in range(20):
            entries = [make_race_entry("A", 1), make_race_entry("B", 2), make_race_entry("C", 3)]
            model.process_race(entries)

        assert model.ratings["A"] > model.ratings["B"] > model.ratings["C"]

    def test_probabilities_sum_to_one(self) -> None:
        model = EndureElo()
        # Give drivers some history
        for _ in range(5):
            model.process_race([make_race_entry("A", 1), make_race_entry("B", 2), make_race_entry("C", 3)])

        probs = model.predict_win_probabilities(["A", "B", "C"])
        assert probs.shape == (3,)
        assert abs(probs.sum() - 1.0) < 1e-10

    def test_higher_rated_driver_has_higher_win_prob(self) -> None:
        model = EndureElo()
        for _ in range(10):
            model.process_race([make_race_entry("A", 1), make_race_entry("B", 2), make_race_entry("C", 3)])

        probs = model.predict_win_probabilities(["A", "B", "C"])
        assert probs[0] > probs[1] > probs[2]

    def test_k_factor_decreases_with_more_data(self) -> None:
        """K-factor should decrease as more data accumulates (Glicko-style)."""
        model = EndureElo()
        model.get_rating("A")  # triggers init
        k_before = model.k_factors["A"]

        for _ in range(10):
            model.process_race([make_race_entry("A", 1), make_race_entry("B", 2), make_race_entry("C", 3)])

        k_after = model.k_factors["A"]
        assert k_after < k_before, "K-factor should decrease with more observations"

    def test_season_decay_reduces_ratings(self) -> None:
        model = EndureElo()
        for _ in range(5):
            model.process_race([make_race_entry("A", 1), make_race_entry("B", 2)])

        rating_before = model.ratings["A"]
        model.apply_season_decay(2025)  # non-regulation year
        assert model.ratings["A"] < rating_before

    def test_crash_dnf_included(self) -> None:
        """Crash DNFs should be included and ranked by laps completed."""
        model = EndureElo()
        entries = [
            make_race_entry("A", 1),
            make_race_entry("B", 2),
            make_race_entry("C", None, dnf_category="crash", laps=10),
        ]
        model.process_race(entries)
        # C crashed, should have lowest rating
        assert model.ratings["C"] < model.ratings["A"]
        assert model.ratings["C"] < model.ratings["B"]

    def test_mechanical_dnf_excluded_when_configured(self) -> None:
        """Mechanical DNFs should be excluded when config says so."""
        config = EloConfig(name="test", exclude_mechanical_dnf=True)
        model = EndureElo(config)
        entries = [
            make_race_entry("A", 1),
            make_race_entry("B", 2),
            make_race_entry("C", None, dnf_category="mechanical", laps=10),
        ]
        model.process_race(entries)
        # C should not have been processed (no rating change from initial)
        assert "C" not in model.ratings

    def test_single_driver_race_is_noop(self) -> None:
        model = EndureElo()
        model.process_race([make_race_entry("A", 1)])
        assert "A" not in model.ratings  # never initialized since < 2 drivers

    def test_win_probability_equal_ratings(self) -> None:
        """With equal ratings, all drivers should have equal win probability."""
        model = EndureElo()
        probs = model.predict_win_probabilities(["A", "B", "C"])
        np.testing.assert_allclose(probs, [1 / 3, 1 / 3, 1 / 3], atol=1e-10)

    def test_win_probability_two_drivers(self) -> None:
        """Two-driver case should match standard Bradley-Terry."""
        model = EndureElo()
        model.ratings["A"] = 1.0
        model.ratings["B"] = 0.0
        model.k_factors["A"] = 0.5
        model.k_factors["B"] = 0.5

        probs = model.predict_win_probabilities(["A", "B"])
        # For two drivers, endure-Elo win prob = exp(R_A) / (exp(R_A) + exp(R_B))
        expected_a = np.exp(1.0) / (np.exp(1.0) + np.exp(0.0))
        np.testing.assert_allclose(probs[0], expected_a, atol=1e-10)
