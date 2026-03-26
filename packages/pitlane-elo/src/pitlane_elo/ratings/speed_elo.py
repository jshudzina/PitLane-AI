"""Speed-Elo: standard round-robin pairwise ELO (baseline model).

Treats each race as n(n-1)/2 pairwise comparisons. This is the approach
used by Xun and most traditional F1 Elo implementations. Serves as the
baseline against which endure-Elo is benchmarked.
"""

from __future__ import annotations

import numpy as np

from pitlane_elo.config import EloConfig
from pitlane_elo.data import RaceEntry
from pitlane_elo.ratings.base import RatingModel


class SpeedElo(RatingModel):
    """Round-robin pairwise Elo rating model."""

    def __init__(self, config: EloConfig | None = None) -> None:
        from pitlane_elo.config import SPEED_ELO_DEFAULT

        super().__init__(config or SPEED_ELO_DEFAULT)

    def process_race(self, entries: list[RaceEntry]) -> None:
        raise NotImplementedError

    def predict_win_probabilities(self, driver_ids: list[str]) -> np.ndarray:
        raise NotImplementedError
