"""CLI entry point for pitlane-elo model training and evaluation."""

from __future__ import annotations

import dataclasses
import json
import logging
import time
from pathlib import Path

import click
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pitlane_elo.calibration import calibrate as run_calibrate
from pitlane_elo.config import ENDURE_ELO_DEFAULT, SPEED_ELO_DEFAULT
from pitlane_elo.data import get_db_path
from pitlane_elo.prediction.forecast import compare_models, evaluate_model, run_historical
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings.speed_elo import SpeedElo
from pitlane_elo.separation.alpha_estimation import estimate_alpha
from pitlane_elo.snapshots import build_snapshots, get_driver_rating_history, get_race_snapshot


def _make_model(name: str) -> EndureElo | SpeedElo:
    if name == "endure-elo":
        return EndureElo()
    return SpeedElo()


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable timing logs.")
def main(verbose: bool) -> None:
    """PitLane ELO — F1 rating models and story detection."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(name)s %(message)s",
    )


@main.command()
@click.option("--start-year", type=int, default=1970, help="First season to process.")
@click.option("--end-year", type=int, default=2026, help="Last season to process (inclusive).")
@click.option("--model", "model_name", type=click.Choice(["endure-elo", "speed-elo"]), default="endure-elo")
@click.option("--per-season-reset", is_flag=True, help="Reset ratings each season (Powell baseline).")
@click.option("--predict-cap", type=int, default=15, help="Cap prediction to top-N drivers by rating (0=no cap).")
def run(start_year: int, end_year: int, model_name: str, per_season_reset: bool, predict_cap: int) -> None:
    """Run a single model over historical races and print results.

    For each race the model predicts FIRST (from current ratings), then
    updates ratings from the actual result. Metrics are computed over all
    processed races.
    """
    cap = predict_cap or None
    click.echo(f"Running {model_name} from {start_year} to {end_year}...")
    model = _make_model(model_name)
    preds = run_historical(
        model,
        start_year=start_year,
        end_year=end_year,
        per_season_reset=per_season_reset,
        predict_cap=cap,
    )
    click.echo(f"Processed {len(preds)} races.")

    if not preds:
        return

    metrics = evaluate_model(preds)
    click.echo(f"Log-likelihood: {metrics['log_likelihood']:.2f}")
    click.echo(f"Brier score:    {metrics['brier_score']:.4f}")
    click.echo(f"Mean winner P:  {metrics['mean_winner_prob']:.4f}")
    click.echo(f"Median winner P:{metrics['median_winner_prob']:.4f}")

    # Top-10 rated drivers
    top = sorted(model.ratings.items(), key=lambda x: x[1], reverse=True)[:10]
    click.echo("\nTop 10 ratings:")
    for rank, (driver, rating) in enumerate(top, 1):
        click.echo(f"  {rank:>2}. {driver:<25} {rating:>8.2f}")


@main.command()
@click.option("--warmup-start", type=int, default=1970, help="First season for rating warm-up (not evaluated).")
@click.option("--eval-start", type=int, default=2015, help="First year of evaluation window.")
@click.option("--eval-end", type=int, default=2024, help="Last year of evaluation window (inclusive).")
@click.option("--per-season-reset", is_flag=True, help="Reset ratings each season (Powell baseline).")
@click.option("--predict-cap", type=int, default=15, help="Cap prediction to top-N drivers by rating (0=no cap).")
def evaluate(
    warmup_start: int,
    eval_start: int,
    eval_end: int,
    per_season_reset: bool,
    predict_cap: int,
) -> None:
    """Compare endure-Elo vs speed-Elo in two phases.

    \b
    Phase 1 — Warm-up (warmup-start to eval-start-1):
      Races are processed to build up ratings, but predictions are not scored.
    Phase 2 — Evaluation (eval-start to eval-end):
      Predictions are scored. Each race is still predict-then-update, so every
      prediction is out-of-sample (made before seeing the result).
    """
    cap = predict_cap or None
    click.echo(f"Warm-up {warmup_start}–{eval_start - 1}, evaluating {eval_start}–{eval_end}...")

    endure = EndureElo()
    speed = SpeedElo()
    preds_e = run_historical(
        endure,
        start_year=warmup_start,
        end_year=eval_end,
        per_season_reset=per_season_reset,
        predict_cap=cap,
    )
    preds_s = run_historical(
        speed,
        start_year=warmup_start,
        end_year=eval_end,
        per_season_reset=per_season_reset,
        predict_cap=cap,
    )

    metrics_e = evaluate_model(preds_e, eval_start_year=eval_start, eval_end_year=eval_end)
    metrics_s = evaluate_model(preds_s, eval_start_year=eval_start, eval_end_year=eval_end)
    comparison = compare_models(preds_e, preds_s, eval_start_year=eval_start, eval_end_year=eval_end)

    click.echo(f"\n{'Metric':<25} {'Endure-Elo':>12} {'Speed-Elo':>12}")
    click.echo("-" * 51)
    click.echo(f"{'Races evaluated':<25} {metrics_e['n_races']:>12} {metrics_s['n_races']:>12}")
    click.echo(f"{'Log-likelihood':<25} {metrics_e['log_likelihood']:>12.2f} {metrics_s['log_likelihood']:>12.2f}")
    click.echo(f"{'Brier score':<25} {metrics_e['brier_score']:>12.4f} {metrics_s['brier_score']:>12.4f}")
    me, ms = metrics_e, metrics_s
    click.echo(f"{'Mean winner prob':<25} {me['mean_winner_prob']:>12.4f} {ms['mean_winner_prob']:>12.4f}")
    click.echo(f"{'Median winner prob':<25} {me['median_winner_prob']:>12.4f} {ms['median_winner_prob']:>12.4f}")

    click.echo(f"\n{'Comparison (eval window)':<25}")
    click.echo("-" * 51)
    click.echo(f"{'Race-level % (E > S)':<25} {comparison['race_level_pct']:>12.1%}")
    click.echo(f"{'Log-wealth D(E,S)':<25} {comparison['log_wealth_ratio']:>12.2f}")
    click.echo(f"{'Races compared':<25} {comparison['n_races']:>12}")


@main.command()
@click.option("--warmup-start", type=int, default=1970, help="First season to process (burn-in; not scored).")
@click.option("--cal-start", type=int, default=1980, help="First year scored during calibration.")
@click.option("--cal-end", type=int, default=2013, help="Last year scored during calibration.")
@click.option("--val-start", type=int, default=2014, help="First year of validation window.")
@click.option("--val-end", type=int, default=2021, help="Last year of validation window.")
@click.option("--holdout-start", type=int, default=None, help="First holdout year (reported only).")
@click.option("--holdout-end", type=int, default=None, help="Last year of holdout.")
@click.option("--model", "model_name", type=click.Choice(["endure-elo", "speed-elo"]), default="endure-elo")
@click.option("--n-trials", type=int, default=100, help="Number of random-search trials.")
@click.option("--seed", type=int, default=None, help="RNG seed for reproducibility.")
@click.option("--predict-cap", type=int, default=15, help="Cap predictions to top-N drivers by rating (0=no cap).")
@click.option("--top-n", type=int, default=10, help="Show top-N random search results.")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write calibrated config to this JSON file.",
)
def calibrate(
    warmup_start: int,
    cal_start: int,
    cal_end: int,
    val_start: int,
    val_end: int,
    holdout_start: int | None,
    holdout_end: int | None,
    model_name: str,
    n_trials: int,
    seed: int | None,
    predict_cap: int,
    top_n: int,
    output: str | None,
) -> None:
    """Calibrate k_max, phi_race, phi_season via random search + Nelder-Mead.

    \b
    Phase 1 — Random search (n-trials evaluations):
      Samples (k_max, phi_race, phi_season) from their bounds and scores each
      on the calibration window. k_max is sampled log-uniformly.
    Phase 2 — Nelder-Mead refinement:
      Local optimizer starts from the best random-search point.
    Phase 3 — Validation:
      Best config is scored on val-start to val-end (not used for selection).
    Phase 4 — Holdout (optional):
      If --holdout-start/end are given, the final config is scored on that
      window and reported. This is the truly unseen evaluation.

    \b
    Default temporal split (anchored to regulation changes):
      Calibration: 1980–2013  (pre-hybrid era)
      Validation:  2014–2021  (hybrid era, crosses 2014 regulation change)
      Holdout:     2022–2025  (ground-effect era)
    """
    model_class = EndureElo if model_name == "endure-elo" else SpeedElo
    base_config = ENDURE_ELO_DEFAULT if model_name == "endure-elo" else SPEED_ELO_DEFAULT

    click.echo(f"Calibrating {model_name}: warmup {warmup_start}, cal {cal_start}–{cal_end}, val {val_start}–{val_end}")
    seed_suffix = f" (seed={seed})" if seed is not None else ""
    click.echo(f"Random search: {n_trials} trials{seed_suffix}")

    best_ll_so_far: list[float] = []  # mutable cell for closure

    def _on_trial(trial: int, total: int, ll: float) -> None:
        if not best_ll_so_far or ll > best_ll_so_far[0]:
            best_ll_so_far[:] = [ll]
        click.echo(
            f"  [{trial:>{len(str(total))}}/{total}] ll={ll:>10.2f}  best={best_ll_so_far[0]:>10.2f}",
            nl=True,
        )

    nm_best_so_far: list[float] = []

    def _on_nm_iter(iteration: int, ll: float) -> None:
        if not nm_best_so_far or ll > nm_best_so_far[0]:
            nm_best_so_far[:] = [ll]
        click.echo(f"  [NM {iteration:>3}] ll={ll:>10.2f}  best={nm_best_so_far[0]:>10.2f}", nl=True)

    cap = predict_cap or None
    result = run_calibrate(
        model_class,
        base_config,
        warmup_start,
        cal_start,
        cal_end,
        val_start,
        val_end,
        n_trials=n_trials,
        seed=seed,
        predict_cap=cap,
        on_trial=_on_trial,
        on_nm_iter=_on_nm_iter,
    )
    click.echo("Nelder-Mead done.")

    # Top-N random search results
    click.echo(f"\nTop {min(top_n, len(result.random_results))} random search results:")
    click.echo(f"  {'k_max':>8}  {'phi_race':>10}  {'phi_season':>10}  {'cal_ll':>10}")
    click.echo("  " + "-" * 44)
    for r in result.random_results[:top_n]:
        click.echo(
            f"  {r['k_max']:>8.4f}  {r['phi_race']:>10.4f}  {r['phi_season']:>10.4f}  {r['log_likelihood']:>10.2f}"
        )

    # Best config after refinement
    cfg = result.best_config
    click.echo("\nBest config (after Nelder-Mead refinement):")
    click.echo(f"  k_max      = {cfg.k_max:.4f}")
    click.echo(f"  phi_race   = {cfg.phi_race:.4f}")
    click.echo(f"  phi_season = {cfg.phi_season:.4f}")

    # Calibration / validation summary
    click.echo(f"\n{'Window':<20} {'Log-likelihood':>15} {'Races':>8}")
    click.echo("-" * 45)
    click.echo(f"{'Calibration':<20} {result.cal_log_likelihood:>15.2f} {result.n_cal_races:>8}")
    click.echo(f"{'Validation':<20} {result.val_log_likelihood:>15.2f} {result.n_val_races:>8}")

    # Optional holdout
    if holdout_start is not None and holdout_end is not None:
        click.echo(f"\nRunning holdout {holdout_start}–{holdout_end}...")
        model = model_class(result.best_config)
        preds = run_historical(model, warmup_start, holdout_end, predict_cap=cap)
        holdout_metrics = evaluate_model(preds, holdout_start, holdout_end)
        click.echo(f"{'Holdout':<20} {holdout_metrics['log_likelihood']:>15.2f} {holdout_metrics['n_races']:>8}")

    if output is not None:
        payload = dataclasses.asdict(result.best_config)
        payload = {k: round(v, 4) if isinstance(v, float) else v for k, v in payload.items()}
        Path(output).write_text(json.dumps(payload, indent=2))
        click.echo(f"\nConfig written to {output}")


@main.command("estimate-alpha")
@click.option("--start-year", type=int, default=1970, help="First season to process (warm-up and estimation).")
@click.option("--end-year", type=int, default=2024, help="Last season (inclusive).")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write result to JSON: {alpha: <float>}.",
)
def estimate_alpha_cmd(start_year: int, end_year: int, output: str | None) -> None:
    """Estimate the constructor-adjustment weight alpha via OLS variance decomposition.

    \b
    Runs EndureElo (driver) and ConstructorElo (constructor) in parallel over
    [start-year, end-year].  Before each race, records the current pre-race
    (R_driver, R_constructor) pair for each entry.

    Alpha is estimated as:

        alpha = Cov(driver_ratings, constructor_ratings) / Var(constructor_ratings)

    Expected result: alpha ~= 0.77 over the hybrid era (2014–2024).
    """
    click.echo(f"Estimating alpha over {start_year}–{end_year} (OLS)...")
    alpha = estimate_alpha(start_year, end_year)
    click.echo(f"Estimated alpha: {alpha:.4f}")
    if output is not None:
        Path(output).write_text(json.dumps({"alpha": round(alpha, 4)}, indent=2))
        click.echo(f"Written to {output}")


@main.command("van-kesteren")
@click.option("--year", type=int, required=True, help="Season to fit.")
@click.option("--step", type=click.Choice(["1", "2"]), default="1", help="Model step (1=base, 2=seasonal form).")
@click.option("--fast", is_flag=True, help="Use fast sampling preset (200 draws, 2 chains) for a quick check.")
def van_kesteren_cmd(year: int, step: str, fast: bool) -> None:
    """Fit the van Kesteren Bayesian model to one season and print rankings.

    \b
    Prints driver ratings (theta_d) and team ratings (theta_t) with 94% HDI
    credible intervals, sorted from highest to lowest.

    \b
    Example:
      pitlane-elo van-kesteren --year 2019 --fast
    """
    from pitlane_elo.bayesian import VanKesterenModel
    from pitlane_elo.bayesian.van_kesteren import VAN_KESTEREN_DEFAULT, VAN_KESTEREN_FAST, VanKesterenConfig

    if fast:
        config = VanKesterenConfig(
            name=VAN_KESTEREN_FAST.name,
            model_step=int(step),
            draws=VAN_KESTEREN_FAST.draws,
            tune=VAN_KESTEREN_FAST.tune,
            chains=VAN_KESTEREN_FAST.chains,
            random_seed=VAN_KESTEREN_FAST.random_seed,
        )
    else:
        config = VanKesterenConfig(
            name=VAN_KESTEREN_DEFAULT.name,
            model_step=int(step),
        )

    click.echo(f"Fitting van Kesteren model (step {step}) on {year}...")
    model = VanKesterenModel(config)
    result = model.fit_from_db(year)

    if result is None:
        click.echo(f"No race data found for {year}.", err=True)
        raise SystemExit(1)

    driver_cis = model.driver_credible_intervals()
    click.echo(f"\nDriver ratings — theta_d ({year}):")
    click.echo(f"  {'Driver':<25} {'Rating':>8}  {'94% HDI':>20}")
    click.echo("  " + "-" * 57)
    for driver, rating in model.driver_ranking():
        lo, hi = driver_cis[driver]
        click.echo(f"  {driver:<25} {rating:>+8.3f}  [{lo:>+7.3f}, {hi:>+7.3f}]")

    team_cis = model.team_credible_intervals()
    click.echo(f"\nTeam ratings — theta_t ({year}):")
    click.echo(f"  {'Team':<25} {'Rating':>8}  {'94% HDI':>20}")
    click.echo("  " + "-" * 57)
    for team, rating in model.team_ranking():
        lo, hi = team_cis[team]
        click.echo(f"  {team:<25} {rating:>+8.3f}  [{lo:>+7.3f}, {hi:>+7.3f}]")


@main.command("evaluate-van-kesteren")
@click.option(
    "--start-year",
    default=2018,
    show_default=True,
    help="First training year (predictions start at start_year+1).",
)
@click.option("--end-year", default=2024, show_default=True, help="Last evaluation year (inclusive).")
@click.option(
    "--step",
    type=click.Choice(["1", "2"]),
    default="1",
    show_default=True,
    help="Model step (1=base, 2=seasonal form).",
)
@click.option("--fast", is_flag=True, help="Use fast sampling preset (200 draws, 2 chains).")
@click.option("--predict-cap", default=None, type=int, help="Cap prediction to top-N drivers by posterior mean eta.")
@click.option(
    "--surprise-threshold",
    default=0.05,
    show_default=True,
    help="Print races where winner_prob < threshold.",
)
@click.option("--sequential", is_flag=True, help="Refit after every race within each season instead of year-lagged.")
@click.option("--min-races", default=3, show_default=True, help="Races required before first sequential prediction.")
def evaluate_van_kesteren_cmd(
    start_year: int,
    end_year: int,
    step: str,
    fast: bool,
    predict_cap: int | None,
    surprise_threshold: float,
    sequential: bool,
    min_races: int,
) -> None:
    """Evaluate the van Kesteren model with ELO-style metrics.

    \b
    Year-lagged mode (default): for each year Y in [start_year+1, end_year]:
      1. Fits the Bayesian model on season Y-1
      2. Predicts win probabilities for every race in season Y

    \b
    Sequential mode (--sequential): for each year Y in [start_year, end_year]:
      For each race N > min_races:
        1. Fits the Bayesian model on races 1..(N-1) of season Y
        2. Predicts win probabilities for race N

    \b
    Metrics match pitlane-elo run/evaluate: log-likelihood, Brier score,
    mean and median winner probability. Surprising results (actual winner
    had low predicted probability) are listed below the summary.

    \b
    Example:
      pitlane-elo evaluate-van-kesteren --start-year 2018 --end-year 2024 --fast
      pitlane-elo evaluate-van-kesteren --start-year 2019 --end-year 2024 --fast --sequential
    """
    from pitlane_elo.bayesian.van_kesteren import VAN_KESTEREN_DEFAULT, VAN_KESTEREN_FAST, VanKesterenConfig
    from pitlane_elo.prediction.forecast import evaluate_model, run_historical_bayesian, run_sequential_bayesian

    if fast:
        config = VanKesterenConfig(
            name=VAN_KESTEREN_FAST.name,
            model_step=int(step),
            draws=VAN_KESTEREN_FAST.draws,
            tune=VAN_KESTEREN_FAST.tune,
            chains=VAN_KESTEREN_FAST.chains,
            random_seed=VAN_KESTEREN_FAST.random_seed,
        )
    else:
        config = VanKesterenConfig(
            name=VAN_KESTEREN_DEFAULT.name,
            model_step=int(step),
        )

    if sequential:
        click.echo(f"Van Kesteren model — sequential within-season ({start_year}–{end_year})")
        click.echo(f"  Fitting on races 1..N-1, predicting race N  |  step={step}  fast={fast}  min_races={min_races}")
        click.echo()
        predictions = run_sequential_bayesian(
            config,
            start_year=start_year,
            end_year=end_year,
            predict_cap=predict_cap,
            min_races=min_races,
        )
    else:
        click.echo(f"Van Kesteren model — year-lagged evaluation ({start_year + 1}–{end_year})")
        click.echo(f"  Training: season Y-1 → predicting season Y  |  step={step}  fast={fast}")
        click.echo()
        predictions = run_historical_bayesian(
            config,
            start_year=start_year,
            end_year=end_year,
            predict_cap=predict_cap,
        )

    if not predictions:
        click.echo("No predictions generated. Check that data exists for the requested years.", err=True)
        raise SystemExit(1)

    metrics = evaluate_model(predictions)
    click.echo(f"  Races evaluated:   {metrics['n_races']:>6}")
    click.echo(f"  Log-likelihood:    {metrics['log_likelihood']:>10.2f}")
    click.echo(f"  Brier score:       {metrics['brier_score']:>10.4f}")
    click.echo(f"  Mean winner P:     {metrics['mean_winner_prob']:>10.4f}")
    click.echo(f"  Median winner P:   {metrics['median_winner_prob']:>10.4f}")

    surprises = [p for p in predictions if p.winner_prob < surprise_threshold]
    if surprises:
        click.echo(f"\nSurprising results (winner_prob < {surprise_threshold:.0%}):")
        click.echo(f"  {'Year':>4}  {'Rnd':>3}  {'Winner':<25}  {'Predicted':>9}")
        click.echo("  " + "-" * 48)
        for p in sorted(surprises, key=lambda x: x.winner_prob):
            click.echo(f"  {p.year:>4}  {p.round:>3}  {p.actual_winner_id:<25}  {p.winner_prob:>8.1%}")


@main.command()
@click.option("--start-year", type=int, default=1970, help="First season to process.")
@click.option("--end-year", type=int, default=2026, help="Last season (inclusive).")
@click.option("--session-type", type=click.Choice(["R", "S"]), default="R", help="Session type to snapshot.")
@click.option("--db-path", type=click.Path(), default=None, help="Override database path.")
def snapshot(start_year: int, end_year: int, session_type: str, db_path: str | None) -> None:
    """Compute and persist ELO snapshots (pre-race ratings + win probs) for every race.

    Runs the calibrated endure-Elo model in a predict-then-update loop and writes
    one row per driver per race to the elo_snapshots table. Safe to re-run;
    upsert is idempotent.
    """
    path = Path(db_path) if db_path else get_db_path()
    click.echo(f"Running calibrated endure-Elo snapshot ({start_year}–{end_year})...")
    t0 = time.perf_counter()
    n = build_snapshots(start_year, end_year, db_path=path, session_type=session_type)
    elapsed = time.perf_counter() - t0
    click.echo(f"Wrote {n:,} rows in {elapsed:.1f}s.")


@main.command()
@click.option("--year", type=int, required=True, help="Season year.")
@click.option("--round", "round_num", type=int, required=True, help="Race round number.")
@click.option("--session-type", type=click.Choice(["R", "S"]), default="R")
def predict(year: int, round_num: int, session_type: str) -> None:
    """Show pre-race ELO win probabilities vs actual finish for one race.

    Displays a ranked table of drivers by predicted win probability alongside
    their actual finishing position. Run `pitlane-elo snapshot` first.
    """
    rows = get_race_snapshot(year, round_num, session_type=session_type)
    if not rows:
        click.echo(
            f"No snapshot found for {year} R{round_num}. Run `pitlane-elo snapshot` first.",
            err=True,
        )
        raise SystemExit(1)

    click.echo(f"\n{year} Round {round_num} — Pre-race ELO predictions vs actual results")
    click.echo(f"  {'Prob':>4}  {'Driver':<25}  {'Win Prob':>9}  {'Podium Prob':>11}  {'Finish':>7}  {'DNF':<10}")
    click.echo("  " + "─" * 75)

    winner_rank: int | None = None
    winner_prob: float = 0.0
    winner_id: str = ""

    for rank, row in enumerate(rows, 1):
        finish_str = str(row.finish_position) if row.finish_position is not None else "DNF"
        dnf_str = row.dnf_category if row.dnf_category != "none" else "—"

        if row.finish_position == 1:
            winner_rank = rank
            winner_prob = row.win_probability
            winner_id = row.driver_id

        click.echo(
            f"  {rank:>4}  {row.driver_id:<25}  {row.win_probability:>8.1%}"
            f"  {row.podium_probability:>10.1%}  {finish_str:>7}  {dnf_str:<10}"
        )

    click.echo("")
    if winner_rank is not None:
        click.echo(f"Winner ({winner_id}) was prob-ranked #{winner_rank} (predicted: {winner_prob:.1%})")
    else:
        # No finish_position=1 found (e.g. all DNFs or missing data)
        click.echo("Winner could not be determined from snapshot data.")


@main.command("plot-ratings")
@click.option("--driver", "driver_id", required=True, help="Driver ID slug (e.g. max_verstappen).")
@click.option("--start-year", type=int, default=1970, help="First season to include.")
@click.option("--end-year", type=int, default=2026, help="Last season (inclusive).")
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="Output PNG path. Defaults to <driver_id>_ratings.png in the current directory.",
)
def plot_ratings(driver_id: str, start_year: int, end_year: int, output: str | None) -> None:
    """Plot a driver's ELO rating history to a PNG file.

    Run `pitlane-elo snapshot` first to populate the data.
    """
    rows = get_driver_rating_history(driver_id, start_year=start_year, end_year=end_year)
    if not rows:
        click.echo(
            f"No snapshots found for '{driver_id}'. Run `pitlane-elo snapshot` first.",
            err=True,
        )
        raise SystemExit(1)

    out_path = output or f"{driver_id}_ratings.png"

    x = list(range(1, len(rows) + 1))
    ratings = [r.pre_race_rating for r in rows]
    ks = [r.pre_race_k for r in rows]

    # Identify season boundaries for tick labels and dividers
    boundary_indices: list[int] = []
    boundary_labels: list[str] = []
    seen_years: set[int] = set()
    for i, row in enumerate(rows):
        if row.year not in seen_years:
            seen_years.add(row.year)
            boundary_indices.append(i + 1)
            boundary_labels.append(str(row.year))

    fig, ax = plt.subplots(figsize=(14, 5))

    # Uncertainty band: rating ± k_factor
    upper = [r + k for r, k in zip(ratings, ks, strict=True)]
    lower = [r - k for r, k in zip(ratings, ks, strict=True)]
    ax.fill_between(x, lower, upper, alpha=0.15, color="steelblue", label="±k-factor band")

    # Rating line
    ax.plot(x, ratings, color="steelblue", linewidth=1.5, label="Pre-race rating")
    ax.axhline(0, color="gray", linewidth=0.6, linestyle="--", alpha=0.5)

    # Season boundary dividers
    for idx in boundary_indices[1:]:
        ax.axvline(idx, color="gray", linewidth=0.5, linestyle=":", alpha=0.6)

    ax.set_xticks(boundary_indices)
    ax.set_xticklabels(boundary_labels, fontsize=8)
    ax.set_xlabel("Race (season boundaries marked)")
    ax.set_ylabel("Pre-race ELO rating")
    ax.set_title(f"ELO Rating History — {driver_id} ({start_year}–{end_year})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    click.echo(f"Chart saved to {out_path}")


@main.command()
@click.argument("model_name")
def promote(model_name: str) -> None:
    """Promote a trained model artifact to pitlane-agent's data directory."""
    click.echo(f"Promoting {model_name}...")
    click.echo("Not yet implemented.")


if __name__ == "__main__":
    main()
