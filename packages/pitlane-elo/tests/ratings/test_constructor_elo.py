"""Tests for pitlane_elo.ratings.constructor_elo."""

from __future__ import annotations

import numpy as np
import pytest
from pitlane_elo.config import EloConfig
from pitlane_elo.data import RaceEntry
from pitlane_elo.ratings.constructor_elo import ConstructorElo

from tests.conftest import make_race_entry


# ---------------------------------------------------------------------------
# Helper: make_race_entry with a real team name
# ---------------------------------------------------------------------------


def _make(driver_id: str, team: str, finish: int | None, laps: int = 57) -> RaceEntry:
    e = make_race_entry(driver_id, finish, laps=laps)
    return {**e, "team": team}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConstructorElo:
    def test_instantiation(self) -> None:
        model = ConstructorElo()
        assert model.config is not None
        assert isinstance(model.ratings, dict)

    def test_winner_rating_increases(self) -> None:
        """After one race the winning constructor's rating should rise."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", 3),
            _make("B2", "TeamB", 4),
            _make("C1", "TeamC", 5),
            _make("C2", "TeamC", 6),
        ]
        model.process_race(entries)
        assert model.ratings["TeamA"] > 0.0
        assert model.ratings["TeamC"] < 0.0

    def test_repeated_races_diverge_ratings(self) -> None:
        """After many races where TeamA dominates, ratings diverge in order."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", 3),
            _make("B2", "TeamB", 4),
            _make("C1", "TeamC", 5),
            _make("C2", "TeamC", 6),
        ]
        for _ in range(20):
            model.process_race(entries)
        assert model.ratings["TeamA"] > model.ratings["TeamB"] > model.ratings["TeamC"]

    def test_probabilities_sum_to_one(self) -> None:
        """predict_win_probabilities should return values summing to 1.0."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", 3),
            _make("B2", "TeamB", 4),
        ]
        for _ in range(5):
            model.process_race(entries)

        probs = model.predict_win_probabilities(["TeamA", "TeamB"])
        assert probs.shape == (2,)
        assert abs(probs.sum() - 1.0) < 1e-10

    def test_higher_rated_constructor_has_higher_win_prob(self) -> None:
        """After training, the dominant constructor should have higher win prob."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", 3),
            _make("B2", "TeamB", 4),
        ]
        for _ in range(10):
            model.process_race(entries)

        probs = model.predict_win_probabilities(["TeamA", "TeamB"])
        assert probs[0] > probs[1]

    def test_solo_finisher_uses_that_position(self) -> None:
        """If one driver DNFs (no finish_position), the team still participates."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", None, laps=10),  # DNF
            _make("B1", "TeamB", 2),
            _make("B2", "TeamB", 3),
        ]
        # Should process without error
        model.process_race(entries)
        assert "TeamA" in model.ratings
        assert "TeamB" in model.ratings

    def test_both_dnf_team_ranked_last(self) -> None:
        """A team where both drivers DNF is ranked after all finishers."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", None, laps=5),
            _make("B2", "TeamB", None, laps=3),
        ]
        model.process_race(entries)
        # TeamA (finishers) should have higher rating than TeamB (both DNF)
        assert model.ratings["TeamA"] > model.ratings["TeamB"]

    def test_k_factor_decreases_with_more_data(self) -> None:
        """K-factor should decrease (Glicko-style) as more data accumulates."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", 3),
            _make("B2", "TeamB", 4),
        ]
        model.process_race(entries)
        k_after_1 = model.k_factors["TeamA"]
        for _ in range(19):
            model.process_race(entries)
        k_after_20 = model.k_factors["TeamA"]
        assert k_after_20 < k_after_1

    def test_season_decay_reduces_ratings(self) -> None:
        """apply_season_decay (inherited) should reduce ratings toward zero."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
            _make("B1", "TeamB", 3),
            _make("B2", "TeamB", 4),
        ]
        for _ in range(5):
            model.process_race(entries)

        rating_before = model.ratings["TeamA"]
        model.apply_season_decay(2025)
        rating_after = model.ratings["TeamA"]

        assert abs(rating_after) < abs(rating_before)

    def test_too_few_constructors_skipped(self) -> None:
        """A race with only one constructor produces no rating update."""
        model = ConstructorElo()
        entries = [
            _make("A1", "TeamA", 1),
            _make("A2", "TeamA", 2),
        ]
        model.process_race(entries)
        # No ratings should be populated (single-constructor race is skipped)
        assert model.ratings == {}

    def test_custom_config(self) -> None:
        """ConstructorElo accepts a custom EloConfig."""
        config = EloConfig(name="test-constructor", k_max=0.1)
        model = ConstructorElo(config)
        assert model.config.k_max == 0.1
