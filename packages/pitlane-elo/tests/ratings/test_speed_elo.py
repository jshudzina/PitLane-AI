"""Tests for pitlane_elo.ratings.speed_elo."""

from __future__ import annotations

import pytest
from pitlane_elo.ratings.speed_elo import SpeedElo


class TestSpeedElo:
    def test_instantiation(self) -> None:
        model = SpeedElo()
        assert model.config.name == "speed-elo-default"

    def test_get_rating_initializes(self) -> None:
        model = SpeedElo()
        rating = model.get_rating("hamilton")
        assert rating == model.config.initial_rating

    def test_process_race_not_implemented(self) -> None:
        model = SpeedElo()
        with pytest.raises(NotImplementedError):
            model.process_race([])
