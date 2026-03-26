"""CLI entry point for pitlane-elo model training and evaluation."""

from __future__ import annotations

import click


@click.group()
def main() -> None:
    """PitLane ELO — F1 rating models and story detection."""


@main.command()
@click.option("--start-year", type=int, default=1970, help="First season to process.")
@click.option("--end-year", type=int, default=2026, help="Last season to process (inclusive).")
@click.option("--model", type=click.Choice(["endure-elo", "speed-elo"]), default="endure-elo")
def run(start_year: int, end_year: int, model: str) -> None:
    """Compute ratings across a range of seasons."""
    click.echo(f"Running {model} from {start_year} to {end_year}...")
    click.echo("Not yet implemented.")


@main.command()
def evaluate() -> None:
    """Evaluate model predictions against historical results."""
    click.echo("Not yet implemented.")


@main.command()
@click.argument("model_name")
def promote(model_name: str) -> None:
    """Promote a trained model artifact to pitlane-agent's data directory."""
    click.echo(f"Promoting {model_name}...")
    click.echo("Not yet implemented.")


if __name__ == "__main__":
    main()
