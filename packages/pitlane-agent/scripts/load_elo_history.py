#!/usr/bin/env python3
"""Load ELO input data for all seasons from 1970 to 2025.

Iterates over each year in the range and delegates to update_elo_data.py,
which handles session loading, extraction, and DuckDB upserts. Already-
processed rounds are skipped automatically unless --force is passed.

Usage:
    python scripts/load_elo_history.py
    python scripts/load_elo_history.py --start-year 1990
    python scripts/load_elo_history.py --start-year 2020 --end-year 2025
    python scripts/load_elo_history.py --force
    python scripts/load_elo_history.py --db-path /custom/path.duckdb
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click


@click.command()
@click.option("--start-year", default=1970, type=int, show_default=True, help="First season to load.")
@click.option("--end-year", default=2025, type=int, show_default=True, help="Last season to load (inclusive).")
@click.option(
    "--db-path",
    "db_path_str",
    default=None,
    type=str,
    help="Path to DuckDB file (default: bundled pitlane.duckdb).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-fetch and overwrite rounds already in DB.",
)
def load_elo_history(
    start_year: int,
    end_year: int,
    db_path_str: str | None,
    force: bool,
) -> None:
    """Load ELO input data for all seasons from START_YEAR to END_YEAR."""
    if start_year > end_year:
        raise click.UsageError(f"--start-year ({start_year}) must be <= --end-year ({end_year})")

    update_script = Path(__file__).parent / "update_elo_data.py"
    if not update_script.exists():
        raise click.ClickException(f"update_elo_data.py not found at {update_script}")

    years = list(range(start_year, end_year + 1))
    click.echo(f"Loading ELO data for {len(years)} seasons: {start_year}–{end_year}", err=True)

    failed_years: list[int] = []

    for year in years:
        click.echo(f"\n{'=' * 60}", err=True)
        click.echo(f"Season {year}", err=True)
        click.echo(f"{'=' * 60}", err=True)

        cmd = [sys.executable, str(update_script), "--year", str(year)]
        if db_path_str:
            cmd += ["--db-path", db_path_str]
        if force:
            cmd.append("--force")

        result = subprocess.run(cmd)

        if result.returncode != 0:
            click.echo(f"  FAILED: season {year} exited with code {result.returncode}", err=True)
            failed_years.append(year)

    click.echo(f"\n{'=' * 60}", err=True)
    total = len(years)
    succeeded = total - len(failed_years)
    click.echo(f"Done. {succeeded}/{total} seasons succeeded.", err=True)

    if failed_years:
        click.echo(f"Failed years: {failed_years}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    load_elo_history()
