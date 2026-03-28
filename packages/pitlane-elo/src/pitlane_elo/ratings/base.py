"""Abstract base class for ELO rating models."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from pitlane_elo.config import EloConfig
from pitlane_elo.data import RaceEntry


class RatingModel(ABC):
    """Interface that all ELO variants must implement.

    Subclasses provide the core rating update logic. The shared interface
    enables direct model-vs-model comparison in the prediction layer.
    """

    def __init__(self, config: EloConfig) -> None:
        self.config = config
        # driver_id -> current rating
        self.ratings: dict[str, float] = {}
        # driver_id -> current k-factor (for Glicko-style variable k)
        self.k_factors: dict[str, float] = {}

    def get_rating(self, driver_id: str) -> float:
        """Return the current rating for a driver, initializing if unseen."""
        if driver_id not in self.ratings:
            self.ratings[driver_id] = self.config.initial_rating
            self.k_factors[driver_id] = self.config.k_max
        return self.ratings[driver_id]

    @abstractmethod
    def process_race(self, entries: list[RaceEntry]) -> None:
        """Update ratings based on a single race result.

        Args:
            entries: All driver entries for one race, ordered by finish position.
                     Entries with dnf_category="mechanical" and
                     config.exclude_mechanical_dnf=True should be skipped.
        """

    @abstractmethod
    def predict_win_probabilities(self, driver_ids: list[str]) -> np.ndarray:
        """Compute win probability for each driver in an upcoming race.

        Args:
            driver_ids: List of driver IDs entered in the race.

        Returns:
            Array of probabilities summing to 1.0, same order as driver_ids.
        """

    def _filter_entries(self, entries: list[RaceEntry]) -> list[RaceEntry]:
        """Remove mechanical DNFs when configured to do so."""
        if self.config.exclude_mechanical_dnf:
            return [e for e in entries if e["dnf_category"] != "mechanical"]
        return list(entries)

    def apply_season_decay(self, year: int) -> None:
        """Apply between-season rating decay.

        Uses phi_regulation for major regulation years, phi_season otherwise.
        """
        phi = self.config.phi_regulation if year in self.config.regulation_years else self.config.phi_season
        for driver_id in self.ratings:
            self.ratings[driver_id] *= phi
            # Increase uncertainty (k-factor) between seasons
            self.k_factors[driver_id] = min(
                self.k_factors.get(driver_id, self.config.k_max) * (1.0 / phi),
                self.config.k_max,
            )
