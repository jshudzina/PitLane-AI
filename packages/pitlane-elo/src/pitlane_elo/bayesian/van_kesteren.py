"""Van Kesteren & Bergkamp (2023) Bayesian F1 model implemented in PyMC.

Multilevel rank-ordered logit model (Plackett-Luce likelihood) that decomposes
race results into long-term driver skill (theta_d) and constructor advantage
(theta_t). Step 2 adds seasonal form deviations (theta_ds, theta_ts) for
story detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import arviz as az
import pymc as pm
import pytensor.tensor as pt

from pitlane_elo.bayesian.base import BayesianSeasonModel
from pitlane_elo.bayesian.data_prep import SeasonData, prepare_season, prepare_season_from_db
from pitlane_elo.data import RaceEntry


@dataclass(frozen=True)
class VanKesterenConfig:
    """Configuration for the van Kesteren & Bergkamp Bayesian model.

    Attributes:
        name: Human-readable identifier for this configuration.
        model_step: 1 = base model (theta_d, theta_t only).
                    2 = adds seasonal form deviations (theta_ds, theta_ts).
        sigma_d_prior: HalfNormal scale for σ_d (driver skill spread).
        sigma_t_prior: HalfNormal scale for σ_t (constructor advantage spread).
        sigma_ds_prior: HalfNormal scale for σ_ds (seasonal driver form). Step 2 only.
        sigma_ts_prior: HalfNormal scale for σ_ts (seasonal team form). Step 2 only.
        draws: Number of posterior samples per chain.
        tune: Number of tuning steps per chain.
        chains: Number of MCMC chains.
        target_accept: NUTS target acceptance rate.
        random_seed: Seed for reproducibility. None = random.
        min_finishers: Drop races with fewer classified finishers.
    """

    name: str = "van-kesteren-default"
    model_step: int = 1
    sigma_d_prior: float = 1.0
    sigma_t_prior: float = 1.0
    sigma_ds_prior: float = 0.5
    sigma_ts_prior: float = 0.5
    draws: int = 1000
    tune: int = 1000
    chains: int = 4
    target_accept: float = 0.9
    random_seed: int | None = None
    min_finishers: int = 2


VAN_KESTEREN_DEFAULT = VanKesterenConfig()

VAN_KESTEREN_FAST = VanKesterenConfig(
    name="van-kesteren-fast",
    draws=200,
    tune=200,
    chains=2,
    random_seed=42,
)


class VanKesterenModel(BayesianSeasonModel):
    """Van Kesteren & Bergkamp (2023) Bayesian multilevel rank-ordered logit model.

    Fits the Plackett-Luce likelihood to a full season of F1 race results,
    decomposing outcomes into driver skill (theta_d) and constructor advantage
    (theta_t) with proper posterior uncertainty.

    Identifiability: pm.ZeroSumNormal constrains the sum of each parameter
    vector to zero, resolving the additive intercept ambiguity inherent in
    models with both driver and team effects.

    Usage::

        model = VanKesterenModel(VAN_KESTEREN_FAST)
        model.fit_from_db(2019)
        for driver, rating in model.driver_ranking()[:5]:
            print(f"{driver}: {rating:.3f}")
    """

    def __init__(self, config: VanKesterenConfig | None = None) -> None:
        self.config = config or VAN_KESTEREN_DEFAULT
        self._trace: az.InferenceData | None = None
        self._season_data: SeasonData | None = None

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(self, races: list[list[RaceEntry]]) -> az.InferenceData:
        """Fit the Plackett-Luce model to a season's race results.

        Args:
            races: List of races, each a list of RaceEntry dicts.
                Use group_entries_by_race() from data.py to produce this.

        Returns:
            The arviz InferenceData object from MCMC sampling.
        """
        data = prepare_season(
            races,
            min_finishers=self.config.min_finishers,
        )
        model = self._build_model(data)
        with model:
            trace = pm.sample(
                draws=self.config.draws,
                tune=self.config.tune,
                chains=self.config.chains,
                target_accept=self.config.target_accept,
                random_seed=self.config.random_seed,
                return_inferencedata=True,
                progressbar=False,
            )
        self._season_data = data
        self._trace = trace
        return trace

    def fit_from_db(
        self,
        year: int,
        *,
        db_path: Path | None = None,
    ) -> az.InferenceData | None:
        """Convenience: fetch from DB and fit.

        Args:
            year: F1 season year.
            db_path: Override the database path.

        Returns:
            InferenceData, or None if no data exists for the year.
        """
        data = prepare_season_from_db(year, db_path=db_path)
        if data is None:
            return None
        model = self._build_model(data)
        with model:
            trace = pm.sample(
                draws=self.config.draws,
                tune=self.config.tune,
                chains=self.config.chains,
                target_accept=self.config.target_accept,
                random_seed=self.config.random_seed,
                return_inferencedata=True,
                progressbar=False,
            )
        self._season_data = data
        self._trace = trace
        return trace

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def driver_ratings(self) -> dict[str, float]:
        """Posterior means for long-term driver skill (theta_d)."""
        trace, data = self._require_fitted()
        means = trace.posterior["theta_d"].mean(("chain", "draw")).values
        return {d: float(means[i]) for i, d in enumerate(data.driver_ids)}

    def team_ratings(self) -> dict[str, float]:
        """Posterior means for long-term constructor advantage (theta_t)."""
        trace, data = self._require_fitted()
        means = trace.posterior["theta_t"].mean(("chain", "draw")).values
        return {t: float(means[i]) for i, t in enumerate(data.team_ids)}

    def seasonal_driver_ratings(self) -> dict[str, float]:
        """Posterior means for seasonal driver form (theta_ds). Step 2 only.

        Raises:
            RuntimeError: If the model was fitted with model_step=1.
        """
        if self.config.model_step < 2:
            raise RuntimeError("seasonal_driver_ratings() requires model_step >= 2")
        trace, data = self._require_fitted()
        means = trace.posterior["theta_ds"].mean(("chain", "draw")).values
        return {d: float(means[i]) for i, d in enumerate(data.driver_ids)}

    def seasonal_team_ratings(self) -> dict[str, float]:
        """Posterior means for seasonal team form (theta_ts). Step 2 only.

        Raises:
            RuntimeError: If the model was fitted with model_step=1.
        """
        if self.config.model_step < 2:
            raise RuntimeError("seasonal_team_ratings() requires model_step >= 2")
        trace, data = self._require_fitted()
        means = trace.posterior["theta_ts"].mean(("chain", "draw")).values
        return {t: float(means[i]) for i, t in enumerate(data.team_ids)}

    def driver_credible_intervals(
        self, hdi_prob: float = 0.94
    ) -> dict[str, tuple[float, float]]:
        """HDI credible intervals for theta_d per driver."""
        trace, data = self._require_fitted()
        hdi = az.hdi(trace, var_names=["theta_d"], hdi_prob=hdi_prob)["theta_d"].values
        return {d: (float(hdi[i, 0]), float(hdi[i, 1])) for i, d in enumerate(data.driver_ids)}

    def team_credible_intervals(
        self, hdi_prob: float = 0.94
    ) -> dict[str, tuple[float, float]]:
        """HDI credible intervals for theta_t per team."""
        trace, data = self._require_fitted()
        hdi = az.hdi(trace, var_names=["theta_t"], hdi_prob=hdi_prob)["theta_t"].values
        return {t: (float(hdi[i, 0]), float(hdi[i, 1])) for i, t in enumerate(data.team_ids)}

    def driver_ranking(self) -> list[tuple[str, float]]:
        """Drivers sorted by posterior mean theta_d, descending."""
        return sorted(self.driver_ratings().items(), key=lambda x: x[1], reverse=True)

    def team_ranking(self) -> list[tuple[str, float]]:
        """Teams sorted by posterior mean theta_t, descending."""
        return sorted(self.team_ratings().items(), key=lambda x: x[1], reverse=True)

    @property
    def trace(self) -> az.InferenceData:
        """The raw arviz InferenceData. Raises RuntimeError if not fitted."""
        if self._trace is None:
            raise RuntimeError("Model has not been fitted. Call fit() first.")
        return self._trace

    @property
    def season_data(self) -> SeasonData:
        """The SeasonData used for fitting. Raises RuntimeError if not fitted."""
        if self._season_data is None:
            raise RuntimeError("Model has not been fitted. Call fit() first.")
        return self._season_data

    # ------------------------------------------------------------------
    # Model construction
    # ------------------------------------------------------------------

    def _build_model(self, data: SeasonData) -> pm.Model:
        """Construct the PyMC model graph.

        Step 1: theta_d and theta_t only (long-term skill / car advantage).
        Step 2: adds theta_ds and theta_ts (within-season form deviations).

        Non-centered parameterization: raw unit-scale ZeroSumNormal draws are
        multiplied by the scale parameter, decoupling shape from magnitude.
        This avoids Neal's funnel — critical when sigma_d is small relative to
        sigma_t (the typical F1 case where car advantage dominates driver skill).

        ZeroSumNormal enforces the sum-to-zero identifiability constraint;
        scaling a zero-sum vector preserves the constraint.
        """
        with pm.Model() as model:
            sigma_d = pm.HalfNormal("sigma_d", sigma=self.config.sigma_d_prior)
            sigma_t = pm.HalfNormal("sigma_t", sigma=self.config.sigma_t_prior)

            theta_d_raw = pm.ZeroSumNormal("theta_d_raw", sigma=1.0, shape=data.n_drivers)
            theta_t_raw = pm.ZeroSumNormal("theta_t_raw", sigma=1.0, shape=data.n_teams)
            theta_d = pm.Deterministic("theta_d", theta_d_raw * sigma_d)
            theta_t = pm.Deterministic("theta_t", theta_t_raw * sigma_t)

            if self.config.model_step >= 2:
                sigma_ds = pm.HalfNormal("sigma_ds", sigma=self.config.sigma_ds_prior)
                sigma_ts = pm.HalfNormal("sigma_ts", sigma=self.config.sigma_ts_prior)
                theta_ds_raw = pm.ZeroSumNormal("theta_ds_raw", sigma=1.0, shape=data.n_drivers)
                theta_ts_raw = pm.ZeroSumNormal("theta_ts_raw", sigma=1.0, shape=data.n_teams)
                theta_ds = pm.Deterministic("theta_ds", theta_ds_raw * sigma_ds)
                theta_ts = pm.Deterministic("theta_ts", theta_ts_raw * sigma_ts)
                eta = theta_d + theta_t[data.driver_team_idx] + theta_ds + theta_ts[data.driver_team_idx]
            else:
                eta = theta_d + theta_t[data.driver_team_idx]

            # Plackett-Luce log-likelihood via pm.Potential.
            # For a race with finishing order [d_0, ..., d_{m-1}]:
            #   log p(order) = sum_k [ eta[d_k] - logsumexp(eta[d_k:]) ]
            for r, order in enumerate(data.race_orders):
                eta_r = eta[order]
                lse = pt.stack([pt.logsumexp(eta_r[k:], axis=0) for k in range(len(order) - 1)])
                pm.Potential(f"race_{r}", pt.sum(eta_r[:-1] - lse))

        return model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_fitted(self) -> tuple[az.InferenceData, SeasonData]:
        if self._trace is None or self._season_data is None:
            raise RuntimeError("Model has not been fitted. Call fit() first.")
        return self._trace, self._season_data
