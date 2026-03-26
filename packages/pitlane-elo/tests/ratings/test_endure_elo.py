"""Tests for pitlane_elo.ratings.endure_elo."""

from __future__ import annotations

import pytest
from pitlane_elo.ratings.endure_elo import EndureElo


class TestEndureElo:
    def test_instantiation(self) -> None:
        model = EndureElo()
        assert model.config.name == "endure-elo-default"

    def test_get_rating_initializes(self) -> None:
        model = EndureElo()
        rating = model.get_rating("verstappen")
        assert rating == model.config.initial_rating

    def test_process_race_not_implemented(self) -> None:
        model = EndureElo()
        with pytest.raises(NotImplementedError):
            model.process_race([])
