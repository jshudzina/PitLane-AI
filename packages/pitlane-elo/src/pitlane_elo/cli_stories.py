"""CLI subcommands for story angle detection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from pitlane_elo.stories.signals import detect_stories


@click.group()
def stories() -> None:
    """Detect and surface F1 narrative story angles from ELO signals."""


@stories.command()
@click.option("--year", type=int, required=True, help="Season year.")
@click.option("--round", "round_num", type=int, required=True, help="Race round number.")
@click.option("--session-type", type=click.Choice(["R", "S"]), default="R", show_default=True)
@click.option("--trend-lookback", type=int, default=3, show_default=True,
              help="Number of prior races for momentum delta.")
@click.option("--db-path", type=click.Path(), default=None,
              help="Override data directory (must contain elo_snapshots/).")
def detect(year: int, round_num: int, session_type: str, trend_lookback: int, db_path: str | None) -> None:
    """Detect story signals for one race and print as JSON.

    \b
    Requires snapshots to be built first:
      pitlane-elo snapshot --start-year 1970 --end-year <year>

    \b
    Example:
      pitlane-elo stories detect --year 2026 --round 3
    """
    data_dir = Path(db_path) if db_path else None
    signals = detect_stories(
        year, round_num,
        session_type=session_type,
        data_dir=data_dir,
        trend_lookback=trend_lookback,
    )

    if not signals:
        click.echo(
            json.dumps({
                "year": year,
                "round": round_num,
                "session_type": session_type,
                "story_count": 0,
                "signals": [],
                "message": "No story signals detected — snapshots may not exist for this race.",
            }, indent=2),
            err=False,
        )
        return

    click.echo(json.dumps({
        "year": year,
        "round": round_num,
        "session_type": session_type,
        "story_count": len(signals),
        "signals": [s.to_dict() for s in signals],
    }, indent=2))


@stories.command()
@click.option("--year", type=int, required=True, help="Season year.")
@click.option("--session-type", type=click.Choice(["R", "S"]), default="R", show_default=True)
@click.option("--trend-lookback", type=int, default=3, show_default=True)
@click.option("--db-path", type=click.Path(), default=None, help="Override data directory.")
def season(year: int, session_type: str, trend_lookback: int, db_path: str | None) -> None:
    """Detect story signals across all races in a season.

    \b
    Example:
      pitlane-elo stories season --year 2025
    """
    from pitlane_elo.data import get_data_dir, get_race_entries, group_entries_by_race

    data_dir = Path(db_path) if db_path else get_data_dir()
    entries = get_race_entries(year, data_dir=data_dir, session_type=session_type)
    if not entries:
        click.echo(
            json.dumps({"error": f"No race entries found for {year} ({session_type})."}),
            err=True,
        )
        sys.exit(1)

    races = group_entries_by_race(entries)
    all_results = []

    for race in races:
        r_year = race[0]["year"]
        r_round = race[0]["round"]
        signals = detect_stories(
            r_year, r_round,
            session_type=session_type,
            data_dir=data_dir,
            trend_lookback=trend_lookback,
        )
        all_results.append({
            "year": r_year,
            "round": r_round,
            "story_count": len(signals),
            "signals": [s.to_dict() for s in signals],
        })

    click.echo(json.dumps({
        "year": year,
        "session_type": session_type,
        "total_races": len(all_results),
        "races": all_results,
    }, indent=2))
