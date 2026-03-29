"""Hyperparameter calibration for ELO rating models.

Implements a two-phase search strategy:
  1. Random search over (k_max, phi_race, phi_season) to find a good region.
  2. Nelder-Mead local refinement from the best random-search point.

Temporal split design (anchored to regulation-change years):
  - Warmup  1970–1979: burn ratings in from zero; predictions not scored
  - Calibration 1980–2013: log-likelihood maximized to select params
  - Validation  2014–2021: generalization across 2014 hybrid era
  - Holdout     2022–2025: truly unseen; reported only after param selection

References:
  Powell (2023) Section 3.4 — specifying hyperparameters
  Bergstra & Bengio (2012) — random search beats grid search
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Type

import numpy as np
from scipy.optimize import minimize

from pitlane_elo.config import EloConfig
from pitlane_elo.prediction.forecast import evaluate_model, run_historical
from pitlane_elo.ratings.base import RatingModel

# Default search bounds
BOUNDS: dict[str, tuple[float, float]] = {
    "k_max": (0.05, 1.5),       # log-uniform; asymptotic variance / new-entrant k
    "phi_race": (0.90, 0.999),  # within-season AR(1) decay, per race
    "phi_season": (0.60, 0.99), # between-season decay, per year boundary
}


@dataclass
class CalibrationResult:
    """Output of a calibration run."""

    best_config: EloConfig
    cal_log_likelihood: float   # on calibration window
    val_log_likelihood: float   # on validation window
    n_cal_races: int
    n_val_races: int
    random_results: list[dict]  # all random-search trials, sorted by log_likelihood desc


def _score(
    k_max: float,
    phi_race: float,
    phi_season: float,
    *,
    model_class: Type[RatingModel],
    base_config: EloConfig,
    warmup_start: int,
    cal_start: int,
    cal_end: int,
) -> float:
    """Return calibration-window log-likelihood for a given parameter set."""
    config = dataclasses.replace(
        base_config,
        name="calibrating",
        k_max=float(k_max),
        phi_race=float(phi_race),
        phi_season=float(phi_season),
    )
    model = model_class(config)
    preds = run_historical(model, warmup_start, cal_end)
    return evaluate_model(preds, cal_start, cal_end)["log_likelihood"]


def random_search(
    model_class: Type[RatingModel],
    base_config: EloConfig,
    warmup_start: int,
    cal_start: int,
    cal_end: int,
    *,
    n_trials: int = 100,
    seed: int | None = None,
) -> list[dict]:
    """Random search over (k_max, phi_race, phi_season).

    k_max is sampled log-uniformly (spans an order of magnitude).
    phi values are sampled uniformly over their bounded ranges.

    Returns:
        List of dicts with keys k_max, phi_race, phi_season, log_likelihood,
        sorted by log_likelihood descending.
    """
    rng = np.random.default_rng(seed)
    results = []
    for _ in range(n_trials):
        k_max = float(np.exp(rng.uniform(np.log(BOUNDS["k_max"][0]), np.log(BOUNDS["k_max"][1]))))
        phi_race = float(rng.uniform(*BOUNDS["phi_race"]))
        phi_season = float(rng.uniform(*BOUNDS["phi_season"]))
        ll = _score(
            k_max, phi_race, phi_season,
            model_class=model_class,
            base_config=base_config,
            warmup_start=warmup_start,
            cal_start=cal_start,
            cal_end=cal_end,
        )
        results.append({"k_max": k_max, "phi_race": phi_race, "phi_season": phi_season, "log_likelihood": ll})
    return sorted(results, key=lambda r: r["log_likelihood"], reverse=True)


def calibrate(
    model_class: Type[RatingModel],
    base_config: EloConfig,
    warmup_start: int,
    cal_start: int,
    cal_end: int,
    val_start: int,
    val_end: int,
    *,
    n_trials: int = 100,
    seed: int | None = None,
) -> CalibrationResult:
    """Random search + Nelder-Mead refinement, then score on validation window.

    Args:
        model_class: EndureElo or SpeedElo class (not instance).
        base_config: Config whose non-calibrated fields are inherited.
        warmup_start: First year to process (ratings burn-in; not scored).
        cal_start: First year scored during calibration (param selection).
        cal_end: Last year scored during calibration.
        val_start: First year of validation window (generalization check).
        val_end: Last year of validation window.
        n_trials: Number of random-search evaluations.
        seed: RNG seed for reproducibility.

    Returns:
        CalibrationResult with best_config, calibration LL, validation LL,
        race counts, and the full sorted random-search trial list.
    """
    rand_results = random_search(
        model_class, base_config,
        warmup_start, cal_start, cal_end,
        n_trials=n_trials,
        seed=seed,
    )
    best = rand_results[0]

    def neg_ll(x: list[float]) -> float:
        k_max, phi_race, phi_season = x
        # Penalty for out-of-bounds (Nelder-Mead doesn't respect constraints)
        if not (0.01 <= k_max <= 2.0 and 0.5 <= phi_race < 1.0 and 0.5 <= phi_season < 1.0):
            return 1e9
        return -_score(
            k_max, phi_race, phi_season,
            model_class=model_class,
            base_config=base_config,
            warmup_start=warmup_start,
            cal_start=cal_start,
            cal_end=cal_end,
        )

    x0 = [best["k_max"], best["phi_race"], best["phi_season"]]
    res = minimize(neg_ll, x0, method="Nelder-Mead", options={"maxiter": 300, "xatol": 1e-4, "fatol": 0.1})
    k_max, phi_race, phi_season = res.x

    best_config = dataclasses.replace(
        base_config,
        name=f"{base_config.name}-calibrated",
        k_max=float(k_max),
        phi_race=float(phi_race),
        phi_season=float(phi_season),
    )

    # Single run covers both calibration and validation windows
    model = model_class(best_config)
    preds = run_historical(model, warmup_start, val_end)
    cal_metrics = evaluate_model(preds, cal_start, cal_end)
    val_metrics = evaluate_model(preds, val_start, val_end)

    return CalibrationResult(
        best_config=best_config,
        cal_log_likelihood=cal_metrics["log_likelihood"],
        val_log_likelihood=val_metrics["log_likelihood"],
        n_cal_races=cal_metrics["n_races"],
        n_val_races=val_metrics["n_races"],
        random_results=rand_results,
    )
