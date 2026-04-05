"""Abstract base class for batch-fit Bayesian season models."""

from __future__ import annotations

from abc import ABC, abstractmethod

import arviz as az

from pitlane_elo.data import RaceEntry


class BayesianSeasonModel(ABC):
    """Interface for models that fit an entire season at once via MCMC.

    Distinct from RatingModel (which updates sequentially per race). Implementations
    receive a full season's grouped race results, fit a posterior, and expose
    driver/team ratings as posterior means with credible intervals.
    """

    @abstractmethod
    def fit(self, races: list[list[RaceEntry]]) -> az.InferenceData:
        """Fit the model to a season's race results.

        Args:
            races: List of races, each a list of RaceEntry dicts in finishing
                order (best first). Use group_entries_by_race() from data.py
                to produce this from a flat list of entries.

        Returns:
            The arviz InferenceData object from MCMC sampling.
        """

    @abstractmethod
    def driver_ratings(self) -> dict[str, float]:
        """Posterior means for long-term driver skill (θ_d).

        Returns:
            Mapping from driver_id to posterior mean rating.

        Raises:
            RuntimeError: If fit() has not been called.
        """

    @abstractmethod
    def team_ratings(self) -> dict[str, float]:
        """Posterior means for long-term constructor advantage (θ_t).

        Returns:
            Mapping from team name to posterior mean rating.

        Raises:
            RuntimeError: If fit() has not been called.
        """

    @abstractmethod
    def driver_credible_intervals(
        self, hdi_prob: float = 0.94
    ) -> dict[str, tuple[float, float]]:
        """HDI credible intervals for θ_d per driver.

        Args:
            hdi_prob: Highest density interval probability mass (default 0.94).

        Returns:
            Mapping from driver_id to (lower, upper) HDI bounds.

        Raises:
            RuntimeError: If fit() has not been called.
        """

    @abstractmethod
    def team_credible_intervals(
        self, hdi_prob: float = 0.94
    ) -> dict[str, tuple[float, float]]:
        """HDI credible intervals for θ_t per team.

        Args:
            hdi_prob: Highest density interval probability mass (default 0.94).

        Returns:
            Mapping from team name to (lower, upper) HDI bounds.

        Raises:
            RuntimeError: If fit() has not been called.
        """

    @abstractmethod
    def driver_ranking(self) -> list[tuple[str, float]]:
        """Drivers sorted by posterior mean θ_d, descending.

        Returns:
            List of (driver_id, posterior_mean) tuples, highest rated first.

        Raises:
            RuntimeError: If fit() has not been called.
        """

    @abstractmethod
    def team_ranking(self) -> list[tuple[str, float]]:
        """Teams sorted by posterior mean θ_t, descending.

        Returns:
            List of (team_name, posterior_mean) tuples, highest rated first.

        Raises:
            RuntimeError: If fit() has not been called.
        """
