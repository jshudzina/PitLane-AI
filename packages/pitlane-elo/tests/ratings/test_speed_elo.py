"""Tests for pitlane_elo.ratings.speed_elo."""

from __future__ import annotations

import numpy as np
import pytest
from pitlane_elo.data import RaceEntry
from pitlane_elo.ratings.speed_elo import SpeedElo


def _make_entry(driver_id: str, finish: int | None, *, dnf_category: str = "none", laps: int = 57) -> RaceEntry:
    return {
        "year": 2024,
        "round": 1,
        "session_type": "R",
        "driver_id": driver_id,
        "team": "Team",
        "laps_completed": laps,
        "status": "Finished" if dnf_category == "none" else "Retired",
        "dnf_category": dnf_category,
        "is_wet_race": False,
        "is_street_circuit": False,
        "finish_position": finish,
    }


class TestSpeedElo:
    def test_instantiation(self) -> None:
        model = SpeedElo()
        assert model.config.name == "speed-elo-default"

    def test_get_rating_initializes(self) -> None:
        model = SpeedElo()
        rating = model.get_rating("hamilton")
        assert rating == model.config.initial_rating

    def test_three_driver_race(self) -> None:
        """Winner's rating should increase, loser's should decrease."""
        model = SpeedElo()
        entries = [_make_entry("A", 1), _make_entry("B", 2), _make_entry("C", 3)]
        model.process_race(entries)

        assert model.ratings["A"] > 0.0, "Winner rating should increase"
        assert model.ratings["C"] < 0.0, "Last place rating should decrease"

    def test_repeated_races_diverge_ratings(self) -> None:
        model = SpeedElo()
        for _ in range(20):
            entries = [_make_entry("A", 1), _make_entry("B", 2), _make_entry("C", 3)]
            model.process_race(entries)

        assert model.ratings["A"] > model.ratings["B"] > model.ratings["C"]

    def test_probabilities_sum_to_one(self) -> None:
        model = SpeedElo()
        for _ in range(5):
            model.process_race([_make_entry("A", 1), _make_entry("B", 2), _make_entry("C", 3)])

        probs = model.predict_win_probabilities(["A", "B", "C"])
        assert probs.shape == (3,)
        assert abs(probs.sum() - 1.0) < 1e-10

    def test_higher_rated_driver_has_higher_win_prob(self) -> None:
        model = SpeedElo()
        for _ in range(10):
            model.process_race([_make_entry("A", 1), _make_entry("B", 2), _make_entry("C", 3)])

        probs = model.predict_win_probabilities(["A", "B", "C"])
        assert probs[0] > probs[1] > probs[2]

    def test_two_driver_symmetry(self) -> None:
        """For a 2-driver race, rating changes should be equal and opposite."""
        model = SpeedElo()
        entries = [_make_entry("A", 1), _make_entry("B", 2)]
        model.process_race(entries)

        # With equal starting ratings, changes should be symmetric
        assert abs(model.ratings["A"] + model.ratings["B"]) < 1e-10

    def test_win_probability_equal_ratings(self) -> None:
        """With equal ratings, all drivers should have equal win probability."""
        model = SpeedElo()
        probs = model.predict_win_probabilities(["A", "B", "C", "D"])
        np.testing.assert_allclose(probs, [0.25, 0.25, 0.25, 0.25], atol=1e-10)

    def test_k_factor_decreases_with_more_data(self) -> None:
        model = SpeedElo()
        model.get_rating("A")
        k_before = model.k_factors["A"]

        for _ in range(10):
            model.process_race([_make_entry("A", 1), _make_entry("B", 2), _make_entry("C", 3)])

        assert model.k_factors["A"] < k_before
