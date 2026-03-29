"""CLI entry point for pitlane-elo model training and evaluation."""

from __future__ import annotations

import logging

import click

from pitlane_elo.calibration import calibrate as run_calibrate
from pitlane_elo.config import ENDURE_ELO_DEFAULT, SPEED_ELO_DEFAULT
from pitlane_elo.prediction.forecast import compare_models, evaluate_model, run_historical
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings.speed_elo import SpeedElo


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

    click.echo(
        f"Calibrating {model_name}: warmup {warmup_start}, "
        f"cal {cal_start}–{cal_end}, val {val_start}–{val_end}"
    )
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
    )
    click.echo("Random search done. Running Nelder-Mead refinement...")

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
    click.echo(f"  k_max      = {cfg.k_max:.6f}")
    click.echo(f"  phi_race   = {cfg.phi_race:.6f}")
    click.echo(f"  phi_season = {cfg.phi_season:.6f}")

    # Calibration / validation summary
    click.echo(f"\n{'Window':<20} {'Log-likelihood':>15} {'Races':>8}")
    click.echo("-" * 45)
    click.echo(f"{'Calibration':<20} {result.cal_log_likelihood:>15.2f} {result.n_cal_races:>8}")
    click.echo(f"{'Validation':<20} {result.val_log_likelihood:>15.2f} {result.n_val_races:>8}")

    # Optional holdout
    if holdout_start is not None and holdout_end is not None:
        from pitlane_elo.prediction.forecast import evaluate_model, run_historical

        click.echo(f"\nRunning holdout {holdout_start}–{holdout_end}...")
        model = model_class(result.best_config)
        preds = run_historical(model, warmup_start, holdout_end)
        holdout_metrics = evaluate_model(preds, holdout_start, holdout_end)
        click.echo(
            f"{'Holdout':<20} {holdout_metrics['log_likelihood']:>15.2f} {holdout_metrics['n_races']:>8}"
        )


@main.command()
@click.argument("model_name")
def promote(model_name: str) -> None:
    """Promote a trained model artifact to pitlane-agent's data directory."""
    click.echo(f"Promoting {model_name}...")
    click.echo("Not yet implemented.")


if __name__ == "__main__":
    main()
