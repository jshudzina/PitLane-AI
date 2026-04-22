"""Year-lagged and sequential Bayesian race outcome evaluation."""

from __future__ import annotations

import logging
from pathlib import Path

from pitlane_elo.bayesian.van_kesteren import VanKesterenConfig, VanKesterenModel
from pitlane_elo.data import get_race_entries_range, group_entries_by_race
from pitlane_elo.prediction.forecast import RacePrediction

logger = logging.getLogger(__name__)


def run_historical_bayesian(
    config: VanKesterenConfig,
    start_year: int,
    end_year: int,
    *,
    data_dir: Path | None = None,
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
        data_dir: Override the default data directory.
        predict_cap: If set, only predict for the top-N participants by
            posterior mean eta (theta_d + theta_t for their team).

    Returns:
        List of RacePrediction objects, one per race in [start_year+1, end_year].
    """
    predictions: list[RacePrediction] = []

    for year in range(start_year + 1, end_year + 1):
        logger.info("Bayesian eval: fitting on %d, predicting %d", year - 1, year)
        model = VanKesterenModel(config)
        if model.fit_from_db(year - 1, data_dir=data_dir) is None:
            logger.warning("No data for training year %d, skipping %d", year - 1, year)
            continue

        eval_entries = get_race_entries_range(year, year)
        if not eval_entries:
            logger.warning("No race data for evaluation year %d", year)
            continue

        filtered = [e for e in eval_entries if e["session_type"] == "R"]
        races = group_entries_by_race(filtered)

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
    data_dir: Path | None = None,
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
        data_dir: Override the default data directory.
        predict_cap: If set, only predict for the top-N participants by
            posterior mean eta (theta_d + theta_t for their team).
        min_races: Number of completed races required before first prediction.

    Returns:
        List of RacePrediction objects.
    """
    predictions: list[RacePrediction] = []

    for year in range(start_year, end_year + 1):
        logger.info("Sequential Bayesian eval: year %d", year)
        all_entries = get_race_entries_range(year, year, data_dir=data_dir)
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
