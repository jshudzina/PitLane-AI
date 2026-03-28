"""CLI entry point for pitlane-elo model training and evaluation."""

from __future__ import annotations

import logging

import click

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
        model, start_year=start_year, end_year=end_year, per_season_reset=per_season_reset, predict_cap=cap,
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
    warmup_start: int, eval_start: int, eval_end: int, per_season_reset: bool, predict_cap: int,
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
        endure, start_year=warmup_start, end_year=eval_end, per_season_reset=per_season_reset, predict_cap=cap,
    )
    preds_s = run_historical(
        speed, start_year=warmup_start, end_year=eval_end, per_season_reset=per_season_reset, predict_cap=cap,
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
@click.argument("model_name")
def promote(model_name: str) -> None:
    """Promote a trained model artifact to pitlane-agent's data directory."""
    click.echo(f"Promoting {model_name}...")
    click.echo("Not yet implemented.")


if __name__ == "__main__":
    main()
