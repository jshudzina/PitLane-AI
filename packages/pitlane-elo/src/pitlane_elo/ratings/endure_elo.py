"""Endure-Elo: Powell's sequential knock-out rating model.

Decomposes each race into m-1 sequential rounds, eliminating the worst
finisher each round. Based on the Plackett-Luce model with exponential
failure times. Demonstrated to beat speed-Elo 76.3% of the time over
873 F1 races (Powell, 2023).
"""

from __future__ import annotations

import numpy as np

from pitlane_elo.config import EloConfig
from pitlane_elo.data import RaceEntry
from pitlane_elo.ratings.base import RatingModel


class EndureElo(RatingModel):
    """Powell's endure-Elo with sequential knock-out rounds."""

    def __init__(self, config: EloConfig | None = None) -> None:
        from pitlane_elo.config import ENDURE_ELO_DEFAULT

        super().__init__(config or ENDURE_ELO_DEFAULT)

    def process_race(self, entries: list[RaceEntry]) -> None:
        raise NotImplementedError

    def predict_win_probabilities(self, driver_ids: list[str]) -> np.ndarray:
        raise NotImplementedError
