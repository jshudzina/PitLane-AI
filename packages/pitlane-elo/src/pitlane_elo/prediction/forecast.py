"""Race outcome probability computation and historical evaluation.

Orchestrates the predict-then-update loop over historical data and
collects predictions for scoring.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np

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
    actual_winner_idx: int = 0
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
            # Winner was outside the capped set — record zero probability
            winner_idx = 0
            winner_prob = 0.0

        predictions.append(
            RacePrediction(
                year=year,
                round=rnd,
                driver_ids=predict_ids,
                predicted_probs=probs,
                actual_winner_idx=predict_ids.index(winner_id) if winner_id in predict_ids else 0,
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
    brier_inputs = [(p.predicted_probs, p.actual_winner_idx) for p in filtered]

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
