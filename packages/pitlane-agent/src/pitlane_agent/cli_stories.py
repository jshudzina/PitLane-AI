"""CLI story commands — detect ELO story angles and write them to a workspace."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from pitlane_agent.commands.workspace import get_workspace_path, workspace_exists
from pitlane_agent.utils.cli_helpers import get_workspace_id as _get_workspace_id


@click.group()
def stories() -> None:
    """Detect F1 narrative story angles from ELO signals and save to workspace."""


@stories.command()
@click.option("--year", type=int, required=True, help="Season year.")
@click.option("--round", "round_num", type=int, required=True, help="Race round number.")
@click.option("--session-type", type=click.Choice(["R", "S"]), default="R", show_default=True)
@click.option("--trend-lookback", type=int, default=3, show_default=True,
              help="Number of prior races for momentum delta.")
def detect(year: int, round_num: int, session_type: str, trend_lookback: int) -> None:
    """Detect story signals for one race and save to workspace.

    Reads ELO snapshots from the pitlane data directory and writes detected
    story angles to {workspace}/data/stories_{year}_{round_num}.json.

    \b
    Requires snapshots to be built first:
      pitlane-elo snapshot --start-year 1970 --end-year <year>

    \b
    Example:
      pitlane stories detect --year 2026 --round 3
    """
    from pitlane_elo.stories.signals import detect_stories

    workspace_id = _get_workspace_id()
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        signals = detect_stories(
            year, round_num,
            session_type=session_type,
            trend_lookback=trend_lookback,
        )

        payload = {
            "year": year,
            "round": round_num,
            "session_type": session_type,
            "story_count": len(signals),
            "signals": [s.to_dict() for s in signals],
        }
        if not signals:
            payload["message"] = (
                "No story signals detected. "
                "Run `pitlane-elo snapshot-catchup` to ensure snapshots are up to date."
            )

        data_dir = workspace_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_file = data_dir / f"stories_{year}_{round_num}.json"
        output_file.write_text(json.dumps(payload, indent=2))

        click.echo(json.dumps({
            "data_file": str(output_file),
            "year": year,
            "round": round_num,
            "story_count": len(signals),
        }, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


@stories.command()
@click.option("--year", type=int, required=True, help="Season year.")
@click.option("--session-type", type=click.Choice(["R", "S"]), default="R", show_default=True)
@click.option("--trend-lookback", type=int, default=3, show_default=True)
def season(year: int, session_type: str, trend_lookback: int) -> None:
    """Detect story signals across all races in a season and save to workspace.

    Writes {workspace}/data/stories_{year}_season.json.

    \b
    Example:
      pitlane stories season --year 2025
    """
    from pitlane_elo.data import get_data_dir, get_race_entries, group_entries_by_race
    from pitlane_elo.stories.signals import detect_stories

    workspace_id = _get_workspace_id()
    if not workspace_exists(workspace_id):
        click.echo(
            json.dumps({"error": f"Workspace does not exist: {workspace_id}"}),
            err=True,
        )
        sys.exit(1)

    workspace_path = get_workspace_path(workspace_id)

    try:
        data_dir = get_data_dir()
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

        payload = {
            "year": year,
            "session_type": session_type,
            "total_races": len(all_results),
            "races": all_results,
        }

        out_dir = workspace_path / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_file = out_dir / f"stories_{year}_season.json"
        output_file.write_text(json.dumps(payload, indent=2))

        total_signals = sum(r["story_count"] for r in all_results)
        click.echo(json.dumps({
            "data_file": str(output_file),
            "year": year,
            "total_races": len(all_results),
            "total_signals": total_signals,
        }, indent=2))

    except Exception as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
