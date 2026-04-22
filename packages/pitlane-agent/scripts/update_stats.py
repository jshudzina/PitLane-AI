#!/usr/bin/env python3
"""Pre-compute per-session stats and write them to DuckDB.

Loads FastF1 session data for a given year (or specific round) and upserts
the computed stats into the DuckDB database for fast retrieval by the
season-summary command.

Usage:
    python scripts/update_stats.py --year 2024
    python scripts/update_stats.py --year 2024 --round 5
    python scripts/update_stats.py --year 2024 --no-telemetry
    python scripts/update_stats.py --year 2024 --force
    python scripts/update_stats.py --year 2024 --db-path /custom/path.duckdb
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import backoff
import click
import fastf1
import pandas as pd
from pitlane_agent.utils.fastf1_helpers import load_session, setup_fastf1_cache
from pitlane_agent.utils.race_stats import (
    RaceSummaryStats,
    compute_race_summary_stats,
    compute_race_summary_stats_from_results,
    count_track_interruptions,
    get_circuit_length_km,
)
from pitlane_agent.utils.stats_db import (
    SessionStats,
    get_data_dir,
    get_season_stats,
    init_data_dir,
    upsert_session_stats,
)
from requests.exceptions import RequestException

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _extract_podium(session: object) -> list[dict[str, str]]:
    """Extract top-3 podium finishers from session results.

    Returns:
        List of dicts with 'driver' and 'team' keys (up to 3 entries).
        Empty list if results are unavailable.
    """
    podium: list[dict[str, str]] = []
    try:
        results = session.results.sort_values("Position")  # type: ignore[union-attr]
        for _, driver in results.head(3).iterrows():
            if pd.notna(driver["Position"]):
                team_name = driver.get("TeamName")
                abbr = driver.get("Abbreviation", "")
                if pd.isna(abbr) or str(abbr).strip() == "":
                    full_name = driver.get("FullName", "")
                    full_name_str = str(full_name).strip() if pd.notna(full_name) else ""
                    if full_name_str:
                        driver_str = full_name_str
                    else:
                        logger.warning(
                            "Driver at position %s has no Abbreviation or FullName; using 'Unknown'",
                            driver.get("Position"),
                        )
                        driver_str = "Unknown"
                else:
                    driver_str = str(abbr)
                podium.append(
                    {
                        "driver": driver_str,
                        "team": str(team_name) if pd.notna(team_name) else "Unknown",
                    }
                )
    except Exception:
        logger.warning("Could not extract podium from session results", exc_info=True)
    return podium


def _process_session(
    session: object,
    year: int,
    round_number: int,
    event_name: str,
    country: str,
    date_str: str | None,
    session_type: str,
) -> SessionStats:
    """Compute all stats for one session and return a SessionStats dict."""
    race_summary = compute_race_summary_stats(session)  # type: ignore[arg-type]
    if race_summary is None:
        race_summary = compute_race_summary_stats_from_results(session)  # type: ignore[arg-type]
        if race_summary is not None:
            logger.info(
                "Using results-only stats for %s %d: %s — volatility and pit stops unavailable",
                session_type,
                round_number,
                event_name,
            )
        else:
            logger.info(
                "No lap or results data for %s %d: %s, using zeroed stats",
                session_type,
                round_number,
                event_name,
            )
            race_summary = RaceSummaryStats(
                total_overtakes=0,
                total_position_changes=0,
                average_volatility=0.0,
                mean_pit_stops=0.0,
                total_laps=0,
            )

    safety_cars, vscs, red_flags = count_track_interruptions(session)  # type: ignore[arg-type]
    # get_circuit_length_km uses telemetry as Tier 1 and the static Wikipedia
    # table as Tier 2, so calling it is always correct. When with_telemetry=False
    # the session was loaded without telemetry, so Tier 1 will be skipped and
    # Tier 2 (static lookup) still applies.
    circuit_length_km = get_circuit_length_km(session)
    podium = _extract_podium(session)

    return SessionStats(
        year=year,
        round=round_number,
        event_name=event_name,
        country=country,
        date=date_str,
        session_type=session_type,
        circuit_length_km=circuit_length_km,
        total_overtakes=race_summary["total_overtakes"],
        total_position_changes=race_summary["total_position_changes"],
        average_volatility=race_summary["average_volatility"],
        mean_pit_stops=race_summary["mean_pit_stops"],
        total_laps=race_summary["total_laps"],
        num_safety_cars=safety_cars,
        num_virtual_safety_cars=vscs,
        num_red_flags=red_flags,
        podium=json.dumps(podium) if podium else None,
    )


@click.command()
@click.option("--year", required=True, type=int, help="F1 season year (e.g. 2024)")
@click.option(
    "--round",
    "round_number",
    default=None,
    type=int,
    help="Specific round number to update (default: all rounds)",
)
@click.option(
    "--data-dir",
    "data_dir_str",
    default=None,
    type=str,
    help="Path to data directory containing Parquet files (default: bundled data/)",
)
@click.option(
    "--with-telemetry/--no-telemetry",
    "with_telemetry",
    default=True,
    show_default=True,
    help=(
        "Load lap telemetry for precise circuit lengths (2018+). "
        "When disabled, the static Wikipedia lookup table is still used as fallback."
    ),
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-compute and overwrite sessions already in DB",
)
def update_stats(
    year: int,
    round_number: int | None,
    data_dir_str: str | None,
    with_telemetry: bool,
    force: bool,
) -> None:
    """Pre-compute session stats and upsert them into Parquet files."""
    data_dir = Path(data_dir_str) if data_dir_str else get_data_dir()
    init_data_dir(data_dir)
    click.echo(f"Data dir: {data_dir}", err=True)

    setup_fastf1_cache()

    # Build set of already-processed (round, session_type) pairs to skip
    existing: set[tuple[int, str]] = set()
    if not force:
        existing_rows = get_season_stats(data_dir, year)
        if existing_rows:
            existing = {(r["round"], r["session_type"]) for r in existing_rows}
        click.echo(f"Found {len(existing)} sessions already in DB for {year}", err=True)

    @backoff.on_exception(backoff.expo, RequestException, max_tries=5, jitter=backoff.full_jitter)
    def _get_schedule() -> object:
        return fastf1.get_event_schedule(year, include_testing=False)

    @backoff.on_exception(backoff.expo, RequestException, max_tries=5, jitter=backoff.full_jitter)
    def _load_session(event_name: str, st: str, **kwargs: bool) -> object:
        return load_session(year, event_name, st, **kwargs)

    schedule = _get_schedule()

    records: list[SessionStats] = []
    processed = 0
    skipped = 0
    errors = 0

    for _, event in schedule.iterrows():
        rn = int(event["RoundNumber"])
        if rn == 0:
            continue
        if round_number is not None and rn != round_number:
            continue

        event_name = str(event["EventName"])
        country = str(event["Country"])
        event_date = event["EventDate"]
        date_str = event_date.isoformat()[:10] if pd.notna(event_date) else None
        event_format = event.get("EventFormat", "conventional")

        session_types = ["R"]
        if event_format in ("sprint", "sprint_shootout", "sprint_qualifying"):
            session_types.append("S")

        for st in session_types:
            if (rn, st) in existing:
                click.echo(f"  Skipping round {rn} {st}: {event_name} (already in DB)", err=True)
                skipped += 1
                continue

            click.echo(f"  Processing round {rn} {st}: {event_name}...", err=True)
            try:
                session = _load_session(event_name, st, telemetry=with_telemetry)
                record = _process_session(session, year, rn, event_name, country, date_str, st)
                records.append(record)
                processed += 1
                time.sleep(1)
            except Exception as e:
                click.echo(f"  ERROR round {rn} {st}: {event_name} — {e}", err=True)
                logger.exception("Failed to process round %d %s: %s", rn, st, event_name)
                errors += 1

    if records:
        upsert_session_stats(data_dir, records)
        click.echo(f"\nUpserted {len(records)} records to {data_dir}", err=True)

    click.echo(
        f"\nDone. Processed: {processed}, Skipped: {skipped}, Errors: {errors}",
        err=True,
    )

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    update_stats()
