"""CLI entry point for pitlane-elo model training and evaluation."""

from __future__ import annotations

import click

from pitlane_elo.prediction.forecast import compare_models, evaluate_model, run_historical
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings.speed_elo import SpeedElo


def _make_model(name: str) -> EndureElo | SpeedElo:
    if name == "endure-elo":
        return EndureElo()
    return SpeedElo()


@click.group()
def main() -> None:
    """PitLane ELO — F1 rating models and story detection."""


@main.command()
@click.option("--start-year", type=int, default=1970, help="First season to process.")
@click.option("--end-year", type=int, default=2026, help="Last season to process (inclusive).")
@click.option("--model", "model_name", type=click.Choice(["endure-elo", "speed-elo"]), default="endure-elo")
@click.option("--per-season-reset", is_flag=True, help="Reset ratings each season (Powell baseline).")
def run(start_year: int, end_year: int, model_name: str, per_season_reset: bool) -> None:
    """Compute ratings across a range of seasons."""
    click.echo(f"Running {model_name} from {start_year} to {end_year}...")
    model = _make_model(model_name)
    preds = run_historical(model, start_year=start_year, end_year=end_year, per_season_reset=per_season_reset)
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
@click.option("--start-year", type=int, default=1970, help="First season to process.")
@click.option("--end-year", type=int, default=2026, help="Last season to process (inclusive).")
@click.option("--eval-start", type=int, default=2015, help="First year of evaluation window.")
@click.option("--eval-end", type=int, default=2021, help="Last year of evaluation window.")
@click.option("--per-season-reset", is_flag=True, help="Reset ratings each season (Powell baseline).")
def evaluate(start_year: int, end_year: int, eval_start: int, eval_end: int, per_season_reset: bool) -> None:
    """Evaluate endure-Elo vs speed-Elo on historical data."""
    click.echo(f"Training both models {start_year}–{end_year}, evaluating {eval_start}–{eval_end}...")

    endure = EndureElo()
    speed = SpeedElo()
    preds_e = run_historical(endure, start_year=start_year, end_year=end_year, per_season_reset=per_season_reset)
    preds_s = run_historical(speed, start_year=start_year, end_year=end_year, per_season_reset=per_season_reset)

    metrics_e = evaluate_model(preds_e, eval_start_year=eval_start, eval_end_year=eval_end)
    metrics_s = evaluate_model(preds_s, eval_start_year=eval_start, eval_end_year=eval_end)
    comparison = compare_models(preds_e, preds_s, eval_start_year=eval_start, eval_end_year=eval_end)

    click.echo(f"\n{'Metric':<25} {'Endure-Elo':>12} {'Speed-Elo':>12}")
    click.echo("-" * 51)
    click.echo(f"{'Races evaluated':<25} {metrics_e['n_races']:>12} {metrics_s['n_races']:>12}")
    click.echo(f"{'Log-likelihood':<25} {metrics_e['log_likelihood']:>12.2f} {metrics_s['log_likelihood']:>12.2f}")
    click.echo(f"{'Brier score':<25} {metrics_e['brier_score']:>12.4f} {metrics_s['brier_score']:>12.4f}")
    click.echo(f"{'Mean winner prob':<25} {metrics_e['mean_winner_prob']:>12.4f} {metrics_s['mean_winner_prob']:>12.4f}")
    click.echo(f"{'Median winner prob':<25} {metrics_e['median_winner_prob']:>12.4f} {metrics_s['median_winner_prob']:>12.4f}")

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
