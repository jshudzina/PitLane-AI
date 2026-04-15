"""Race outcome probability computation and historical evaluation.

Orchestrates the predict-then-update loop over historical data and
collects predictions for scoring.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pitlane_elo.bayesian.van_kesteren import VanKesterenConfig, VanKesterenModel
from pitlane_elo.data import get_race_entries_range, group_entries_by_race
from pitlane_elo.prediction.scoring import brier_score, log_likelihood, log_wealth_ratio, race_level_comparison
from pitlane_elo.ratings.base import RatingModel

logger = logging.getLogger(__name__)


@dataclass
class RacePrediction:
    """Prediction record for a single race."""

    year: int
    round: int
    driver_ids: list[str] = field(default_factory=list)
    predicted_probs: np.ndarray = field(default_factory=lambda: np.array([]))
    actual_winner_idx: int = -1  # -1 = winner not in prediction set
    actual_winner_id: str = ""
    winner_prob: float = 0.0


def run_historical(
    model: RatingModel,
    start_year: int = 1970,
    end_year: int = 2026,
    *,
    session_type: str = "R",
    per_season_reset: bool = False,
    predict_cap: int | None = None,
) -> list[RacePrediction]:
    """Run a model over historical data, collecting predictions.

    For each race: predict FIRST (using current ratings), then update.
    Season decay is applied at year boundaries.

    Args:
        model: Rating model instance (EndureElo or SpeedElo).
        start_year: First season to process.
        end_year: Last season (inclusive).
        session_type: Filter to this session type ("R" for races).
        per_season_reset: If True, reset all ratings to 0 at each season
            boundary (Powell's approach for the historical comparison).
        predict_cap: If set, only pass the top-N drivers (by current rating)
            to predict_win_probabilities. All drivers still get rating updates.

    Returns:
        List of RacePrediction objects, one per race.
    """
    t_start = time.perf_counter()

    all_entries = get_race_entries_range(start_year, end_year)
    if not all_entries:
        return []

    # Filter to requested session type
    filtered = [e for e in all_entries if e["session_type"] == session_type]
    if not filtered:
        return []

    t_load = time.perf_counter()
    logger.info("Data loaded: %d entries in %.3fs", len(filtered), t_load - t_start)

    races = group_entries_by_race(filtered)
    predictions: list[RacePrediction] = []
    current_year: int | None = None
    predict_total = 0.0
    update_total = 0.0

    for race_entries in races:
        year = race_entries[0]["year"]
        rnd = race_entries[0]["round"]

        # Season boundary handling
        if current_year is not None and year != current_year:
            if per_season_reset:
                model.ratings.clear()
                model.k_factors.clear()
            else:
                model.apply_season_decay(year)
        current_year = year

        # Get driver IDs for this race (in finishing order from group_entries_by_race)
        driver_ids = [e["driver_id"] for e in race_entries]
        if len(driver_ids) < 2:
            continue

        # PREDICT before updating
        t0 = time.perf_counter()

        # Optionally cap the driver set for prediction (top-N by rating)
        if predict_cap is not None and len(driver_ids) > predict_cap:
            ranked = sorted(driver_ids, key=lambda d: model.get_rating(d), reverse=True)
            predict_ids = ranked[:predict_cap]
        else:
            predict_ids = driver_ids

        probs = model.predict_win_probabilities(predict_ids)
        predict_total += time.perf_counter() - t0

        # Determine actual winner (first in finishing order = position 1)
        winner_id = driver_ids[0]
        if winner_id in predict_ids:
            winner_idx = predict_ids.index(winner_id)
            winner_prob = float(probs[winner_idx])
        else:
            # Winner was outside the capped set — sentinel index, zero probability
            winner_idx = -1
            winner_prob = 0.0

        predictions.append(
            RacePrediction(
                year=year,
                round=rnd,
                driver_ids=predict_ids,
                predicted_probs=probs,
                actual_winner_idx=winner_idx,
                actual_winner_id=winner_id,
                winner_prob=winner_prob,
            )
        )

        # THEN update ratings
        t0 = time.perf_counter()
        model.process_race(race_entries)
        update_total += time.perf_counter() - t0

    elapsed = time.perf_counter() - t_start
    logger.info(
        "%s: %d races in %.3fs (predict=%.3fs, update=%.3fs)",
        model.__class__.__name__,
        len(predictions),
        elapsed,
        predict_total,
        update_total,
    )
    return predictions


def run_historical_bayesian(
    config: VanKesterenConfig,
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
    predict_cap: int | None = None,
) -> list[RacePrediction]:
    """Year-lagged evaluation of the VanKesterenModel.

    For each year Y in [start_year+1, end_year]:
      1. Fit VanKesterenModel on year Y-1 (all races)
      2. For each race in year Y: predict win probabilities before seeing result

    Unknown drivers or teams in year Y (not seen in Y-1 training data) receive
    eta=0.0, the prior mean, so their win probability equals 1/n_participants.

    Args:
        config: VanKesterenConfig controlling sampling speed and quality.
        start_year: First training year. Predictions begin at start_year+1.
        end_year: Last evaluation year (inclusive).
        db_path: Override the default database path.
        predict_cap: If set, only predict for the top-N participants by
            posterior mean eta (theta_d + theta_t for their team).

    Returns:
        List of RacePrediction objects, one per race in [start_year+1, end_year].
    """
    predictions: list[RacePrediction] = []

    for year in range(start_year + 1, end_year + 1):
        logger.info("Bayesian eval: fitting on %d, predicting %d", year - 1, year)
        model = VanKesterenModel(config)
        if model.fit_from_db(year - 1, db_path=db_path) is None:
            logger.warning("No data for training year %d, skipping %d", year - 1, year)
            continue

        eval_entries = get_race_entries_range(year, year)
        if not eval_entries:
            logger.warning("No race data for evaluation year %d", year)
            continue

        filtered = [e for e in eval_entries if e["session_type"] == "R"]
        races = group_entries_by_race(filtered)

        # Precompute posterior mean eta per (driver, team) for predict_cap ranking
        driver_means = model.driver_ratings()
        team_means = model.team_ratings()

        for race_entries in races:
            race_year = race_entries[0]["year"]
            rnd = race_entries[0]["round"]
            driver_ids = [e["driver_id"] for e in race_entries]
            team_ids = [e.get("team", "") or "" for e in race_entries]

            if len(driver_ids) < 2:
                continue

            drivers_teams = list(zip(driver_ids, team_ids, strict=True))

            if predict_cap is not None and len(drivers_teams) > predict_cap:
                # Rank by posterior mean eta; unknown driver/team → 0.0
                mean_eta = [driver_means.get(d, 0.0) + team_means.get(t, 0.0) for d, t in drivers_teams]
                ranked_idx = sorted(range(len(drivers_teams)), key=lambda i: mean_eta[i], reverse=True)
                keep = set(ranked_idx[:predict_cap])
                cap_pairs = [drivers_teams[i] for i in range(len(drivers_teams)) if i in keep]
                cap_ids = [driver_ids[i] for i in range(len(driver_ids)) if i in keep]
            else:
                cap_pairs = drivers_teams
                cap_ids = driver_ids

            probs = model.predict_win_probabilities(cap_pairs)

            winner_id = driver_ids[0]
            if winner_id in cap_ids:
                winner_idx = cap_ids.index(winner_id)
                winner_prob = float(probs[winner_idx])
            else:
                winner_idx = -1
                winner_prob = 0.0

            predictions.append(
                RacePrediction(
                    year=race_year,
                    round=rnd,
                    driver_ids=cap_ids,
                    predicted_probs=probs,
                    actual_winner_idx=winner_idx,
                    actual_winner_id=winner_id,
                    winner_prob=winner_prob,
                )
            )

    logger.info("Bayesian eval complete: %d races across %d-%d", len(predictions), start_year + 1, end_year)
    return predictions


def run_sequential_bayesian(
    config: VanKesterenConfig,
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
    predict_cap: int | None = None,
    min_races: int = 3,
) -> list[RacePrediction]:
    """Sequential within-season evaluation of VanKesterenModel.

    For each year Y in [start_year, end_year]:
      For each race N where N > min_races:
        1. Fit VanKesterenModel on races 1..(N-1) of year Y
        2. Predict win probabilities for race N

    min_races controls how many completed races are required before the first
    prediction (default 3). Races 1..min_races are skipped — too few data
    points for reliable MCMC convergence.

    Args:
        config: VanKesterenConfig controlling sampling speed and quality.
        start_year: First season to evaluate.
        end_year: Last evaluation year (inclusive).
        db_path: Override the default database path.
        predict_cap: If set, only predict for the top-N participants by
            posterior mean eta (theta_d + theta_t for their team).
        min_races: Number of completed races required before first prediction.

    Returns:
        List of RacePrediction objects.
    """
    predictions: list[RacePrediction] = []

    for year in range(start_year, end_year + 1):
        logger.info("Sequential Bayesian eval: year %d", year)
        all_entries = get_race_entries_range(year, year, db_path=db_path)
        if not all_entries:
            logger.warning("No race data for year %d", year)
            continue
        filtered = [e for e in all_entries if e["session_type"] == "R"]
        races = group_entries_by_race(filtered)

        if len(races) <= min_races:
            logger.warning("Year %d has only %d races, need > %d — skipping", year, len(races), min_races)
            continue

        for race_idx in range(min_races, len(races)):
            training_races = races[:race_idx]
            eval_race = races[race_idx]

            model = VanKesterenModel(config)
            model.fit(training_races)

            race_year = eval_race[0]["year"]
            rnd = eval_race[0]["round"]
            driver_ids = [e["driver_id"] for e in eval_race]
            team_ids = [e.get("team", "") or "" for e in eval_race]
            drivers_teams = list(zip(driver_ids, team_ids, strict=True))

            driver_means = model.driver_ratings()
            team_means = model.team_ratings()

            if predict_cap is not None and len(drivers_teams) > predict_cap:
                mean_eta = [driver_means.get(d, 0.0) + team_means.get(t, 0.0) for d, t in drivers_teams]
                ranked_idx = sorted(range(len(drivers_teams)), key=lambda i: mean_eta[i], reverse=True)
                keep = set(ranked_idx[:predict_cap])
                cap_pairs = [drivers_teams[i] for i in range(len(drivers_teams)) if i in keep]
                cap_ids = [driver_ids[i] for i in range(len(driver_ids)) if i in keep]
            else:
                cap_pairs = drivers_teams
                cap_ids = driver_ids

            probs = model.predict_win_probabilities(cap_pairs)

            winner_id = driver_ids[0]
            if winner_id in cap_ids:
                winner_idx = cap_ids.index(winner_id)
                winner_prob = float(probs[winner_idx])
            else:
                winner_idx = -1
                winner_prob = 0.0

            predictions.append(
                RacePrediction(
                    year=race_year,
                    round=rnd,
                    driver_ids=cap_ids,
                    predicted_probs=probs,
                    actual_winner_idx=winner_idx,
                    actual_winner_id=winner_id,
                    winner_prob=winner_prob,
                )
            )

    logger.info("Sequential Bayesian eval complete: %d races across %d-%d", len(predictions), start_year, end_year)
    return predictions


def evaluate_model(
    predictions: list[RacePrediction],
    eval_start_year: int | None = None,
    eval_end_year: int | None = None,
) -> dict[str, float]:
    """Compute evaluation metrics over a window of predictions.

    Args:
        predictions: Output from :func:`run_historical`.
        eval_start_year: First year to include (None = no lower bound).
        eval_end_year: Last year to include (None = no upper bound).

    Returns:
        Dict with keys: log_likelihood, brier_score, n_races,
        median_winner_prob, mean_winner_prob.
    """
    filtered = predictions
    if eval_start_year is not None:
        filtered = [p for p in filtered if p.year >= eval_start_year]
    if eval_end_year is not None:
        filtered = [p for p in filtered if p.year <= eval_end_year]

    if not filtered:
        return {"log_likelihood": 0.0, "brier_score": 0.0, "n_races": 0}

    winner_probs = np.array([p.winner_prob for p in filtered])
    # Only include races where the winner was in the prediction set for Brier
    brier_inputs = [(p.predicted_probs, p.actual_winner_idx) for p in filtered if p.actual_winner_idx >= 0]

    return {
        "log_likelihood": log_likelihood(winner_probs),
        "brier_score": brier_score(brier_inputs),
        "n_races": len(filtered),
        "median_winner_prob": float(np.median(winner_probs)),
        "mean_winner_prob": float(np.mean(winner_probs)),
    }


def compare_models(
    preds_a: list[RacePrediction],
    preds_b: list[RacePrediction],
    eval_start_year: int | None = None,
    eval_end_year: int | None = None,
) -> dict[str, float]:
    """Compare two models using race-level metrics.

    Args:
        preds_a: Predictions from model A (typically endure-Elo).
        preds_b: Predictions from model B (typically speed-Elo).
        eval_start_year: First year to include.
        eval_end_year: Last year to include.

    Returns:
        Dict with keys: race_level_pct (fraction A > B),
        log_wealth_ratio (Powell's D(q,p)), n_races.
    """

    def _filter(preds: list[RacePrediction]) -> list[RacePrediction]:
        out = preds
        if eval_start_year is not None:
            out = [p for p in out if p.year >= eval_start_year]
        if eval_end_year is not None:
            out = [p for p in out if p.year <= eval_end_year]
        return out

    fa = _filter(preds_a)
    fb = _filter(preds_b)

    if not fa or not fb:
        return {"race_level_pct": 0.5, "log_wealth_ratio": 0.0, "n_races": 0}

    # Align by (year, round)
    key_to_a = {(p.year, p.round): p for p in fa}
    key_to_b = {(p.year, p.round): p for p in fb}
    common_keys = sorted(set(key_to_a) & set(key_to_b))

    if not common_keys:
        return {"race_level_pct": 0.5, "log_wealth_ratio": 0.0, "n_races": 0}

    ll_a = np.array([np.log(max(key_to_a[k].winner_prob, 1e-15)) for k in common_keys])
    ll_b = np.array([np.log(max(key_to_b[k].winner_prob, 1e-15)) for k in common_keys])
    wp_a = np.array([key_to_a[k].winner_prob for k in common_keys])
    wp_b = np.array([key_to_b[k].winner_prob for k in common_keys])

    return {
        "race_level_pct": race_level_comparison(ll_a, ll_b),
        "log_wealth_ratio": log_wealth_ratio(wp_a, wp_b),
        "n_races": len(common_keys),
    }
