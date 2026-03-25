#!/usr/bin/env python3
"""Pre-compute per-driver ELO input data and write it to DuckDB.

Loads FastF1 race and qualifying session data for a given year (or specific
round) and upserts per-driver entries into the DuckDB database for use by
the ELO computation pipeline.

Race entries store finishing positions and DNF categories needed for
Powell's endure-Elo. Qualifying entries store Q1/Q2/Q3 lap times needed
for Xun's Car Rating (Rc = team_avg_qual / fastest_qual).

Usage:
    python scripts/update_elo_data.py --year 2024
    python scripts/update_elo_data.py --year 2024 --round 5
    python scripts/update_elo_data.py --year 2024 --force
    python scripts/update_elo_data.py --year 2024 --db-path /custom/path.duckdb
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import backoff
import click
import fastf1
import pandas as pd
from pitlane_agent.utils.elo_db import (
    QualifyingEntry,
    RaceEntry,
    categorize_dnf,
    get_qualifying_entries,
    get_race_entries,
    init_elo_tables,
    upsert_qualifying_entries,
    upsert_race_entries,
)
from pitlane_agent.utils.fastf1_helpers import load_session, setup_fastf1_cache
from pitlane_agent.utils.stats_db import get_db_path
from requests.exceptions import RequestException

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _extract_race_entries(
    session: object,
    year: int,
    round_number: int,
    session_type: str,
) -> list[RaceEntry]:
    """Extract per-driver RaceEntry records from a loaded race session.

    Uses DriverId (Ergast slug) as the primary identifier — stable across all
    of F1 history. Abbreviation is stored as a secondary nullable field.

    Mechanical DNFs have finish_position set to None per Xun's methodology
    (excluding them from ELO computation improves RMSE). Crash DNFs are
    included and ranked at their elimination position.

    is_wet_race and is_street_circuit are Phase 1 stubs — always False.
    Future phases should derive these from session.weather_data and a static
    street circuit lookup respectively.

    Args:
        session: Loaded FastF1 Session object (Race or Sprint).
        year: Season year.
        round_number: Round number.
        session_type: "R" for race, "S" for sprint.

    Returns:
        List of RaceEntry dicts, one per driver row in session.results.
    """
    results = session.results  # type: ignore[union-attr]
    entries: list[RaceEntry] = []

    for _, driver in results.iterrows():
        driver_id = str(driver.get("DriverId", "")).strip()
        if not driver_id:
            logger.warning("Skipping driver row with no DriverId in round %d %s", round_number, session_type)
            continue

        abbr_raw = driver.get("Abbreviation")
        abbr_str = str(abbr_raw).strip() if abbr_raw is not None else ""
        abbreviation: str | None = abbr_str if abbr_str and abbr_str.lower() != "nan" else None

        team_raw = driver.get("TeamName")
        team = str(team_raw) if pd.notna(team_raw) else ""

        status_raw = driver.get("Status")
        status = str(status_raw) if pd.notna(status_raw) else ""

        grid_raw = driver.get("GridPosition")
        grid_position: int | None = (
            int(grid_raw) if pd.notna(grid_raw) and float(grid_raw) > 0 else None
        )

        finish_raw = driver.get("Position")
        finish_position: int | None = int(finish_raw) if pd.notna(finish_raw) else None

        # FastF1 uses "NumberOfLaps" in some versions and "Laps" in others
        laps_raw = driver.get("NumberOfLaps", driver.get("Laps", 0))
        laps_completed = int(laps_raw) if pd.notna(laps_raw) else 0

        dnf_category = categorize_dnf(status)

        # Trust Ergast's stewards' classification as the source of truth.
        # If Ergast gives a finish position (driver was officially classified),
        # keep it even for mechanical dnf_category — e.g. a driver who had
        # handling issues but completed enough laps to be classified.
        # If Ergast already has None (driver was not classified), a mechanical
        # dnf_category signals to the ELO layer to exclude them from ranking.
        # Do not override a non-None finish_position here.

        entries.append(
            RaceEntry(
                year=year,
                round=round_number,
                session_type=session_type,
                driver_id=driver_id,
                abbreviation=abbreviation,
                team=team,
                grid_position=grid_position,
                finish_position=finish_position,
                laps_completed=laps_completed,
                status=status,
                dnf_category=dnf_category,
                # Phase 1 stubs: always False until dedicated detection is implemented.
                # is_wet_race: derive from session.weather_data in a future phase.
                # is_street_circuit: derive from a static location lookup in a future phase.
                is_wet_race=False,
                is_street_circuit=False,
            )
        )

    return entries


def _td_to_seconds(val: object) -> float | None:
    """Convert a pandas Timedelta to float seconds, or None if NaT/missing.

    Q1/Q2/Q3 columns in FastF1 session.results are pd.Timedelta objects.
    Pre-2006 sessions and knocked-out drivers have pd.NaT values.
    """
    if val is None:
        return None
    try:
        if pd.isna(val):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(val.total_seconds())  # type: ignore[union-attr]
    except Exception:
        return None


def _extract_qualifying_entries(
    session: object,
    year: int,
    round_number: int,
) -> list[QualifyingEntry]:
    """Extract per-driver QualifyingEntry records from a loaded qualifying session.

    Q1/Q2/Q3 Timedelta columns are converted to float seconds. pd.NaT values
    (pre-2006 sessions or knocked-out drivers) become None.

    best_q_time_s is the absolute minimum across Q1/Q2/Q3, which is the
    correct input for Xun's Rc = (team_avg_qual - fastest_qual) / fastest_qual.

    Reliable Q1/Q2/Q3 data is only available from 2006 (when F1 introduced
    three-phase knockout qualifying). Pre-2006 sessions store all-None times.

    Args:
        session: Loaded FastF1 Session object (Qualifying).
        year: Season year.
        round_number: Round number.

    Returns:
        List of QualifyingEntry dicts, one per driver.
    """
    results = session.results  # type: ignore[union-attr]
    entries: list[QualifyingEntry] = []

    for _, driver in results.iterrows():
        driver_id = str(driver.get("DriverId", "")).strip()
        if not driver_id:
            logger.warning("Skipping driver row with no DriverId in qualifying round %d", round_number)
            continue

        pos_raw = driver.get("Position")
        if pd.isna(pos_raw):
            continue
        position = int(pos_raw)

        abbr_raw = driver.get("Abbreviation")
        abbr_str = str(abbr_raw).strip() if abbr_raw is not None else ""
        abbreviation: str | None = abbr_str if abbr_str and abbr_str.lower() != "nan" else None

        team_raw = driver.get("TeamName")
        team = str(team_raw) if pd.notna(team_raw) else ""

        q1_s = _td_to_seconds(driver.get("Q1"))
        q2_s = _td_to_seconds(driver.get("Q2"))
        q3_s = _td_to_seconds(driver.get("Q3"))

        available = [t for t in (q1_s, q2_s, q3_s) if t is not None]
        best_q = min(available) if available else None

        entries.append(
            QualifyingEntry(
                year=year,
                round=round_number,
                driver_id=driver_id,
                abbreviation=abbreviation,
                team=team,
                q1_time_s=q1_s,
                q2_time_s=q2_s,
                q3_time_s=q3_s,
                best_q_time_s=best_q,
                position=position,
            )
        )

    return entries


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
    "--db-path",
    "db_path_str",
    default=None,
    type=str,
    help="Path to DuckDB file (default: bundled pitlane.duckdb)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-fetch and overwrite rounds already in DB",
)
def update_elo_data(
    year: int,
    round_number: int | None,
    db_path_str: str | None,
    force: bool,
) -> None:
    """Pre-compute per-driver ELO input data and upsert into DuckDB."""
    db_path = Path(db_path_str) if db_path_str else get_db_path()
    init_elo_tables(db_path)
    click.echo(f"DB: {db_path}", err=True)

    setup_fastf1_cache()

    # Build sets of already-processed keys for skip logic
    existing_race_rounds: set[tuple[int, str]] = set()
    existing_qual_rounds: set[int] = set()
    if not force:
        existing_race = get_race_entries(db_path, year)
        if existing_race:
            existing_race_rounds = {(r["round"], r["session_type"]) for r in existing_race}
        existing_qual = get_qualifying_entries(db_path, year)
        if existing_qual:
            existing_qual_rounds = {r["round"] for r in existing_qual}
        click.echo(
            f"Found {len(existing_race_rounds)} race sessions, "
            f"{len(existing_qual_rounds)} qualifying rounds already in DB for {year}",
            err=True,
        )

    @backoff.on_exception(backoff.expo, RequestException, max_tries=5, jitter=backoff.full_jitter)
    def _get_schedule() -> object:
        return fastf1.get_event_schedule(year, include_testing=False)

    schedule = _get_schedule()

    race_records: list[RaceEntry] = []
    qual_records: list[QualifyingEntry] = []
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
        event_format = event.get("EventFormat", "conventional")

        # Race sessions: regular race + sprint if applicable
        race_session_types = ["R"]
        if event_format in ("sprint", "sprint_shootout", "sprint_qualifying"):
            race_session_types.append("S")

        for st in race_session_types:
            if (rn, st) in existing_race_rounds:
                click.echo(f"  Skipping race round {rn} {st}: {event_name} (already in DB)", err=True)
                skipped += 1
                continue
            click.echo(f"  Processing race round {rn} {st}: {event_name}...", err=True)
            try:
                session = load_session(year, event_name, st)
                entries = _extract_race_entries(session, year, rn, st)
                race_records.extend(entries)
                processed += 1
            except Exception as e:
                click.echo(f"  ERROR race round {rn} {st}: {event_name} — {e}", err=True)
                logger.exception("Failed to process race round %d %s: %s", rn, st, event_name)
                errors += 1

        # Qualifying session (SQ/sprint qualifying deferred to a future phase)
        if rn not in existing_qual_rounds:
            click.echo(f"  Processing qualifying round {rn}: {event_name}...", err=True)
            try:
                session = load_session(year, event_name, "Q")
                entries = _extract_qualifying_entries(session, year, rn)
                qual_records.extend(entries)
                processed += 1
            except Exception as e:
                click.echo(f"  ERROR qualifying round {rn}: {event_name} — {e}", err=True)
                logger.exception("Failed to process qualifying round %d: %s", rn, event_name)
                errors += 1
        else:
            click.echo(f"  Skipping qualifying round {rn}: {event_name} (already in DB)", err=True)
            skipped += 1

    if race_records:
        upsert_race_entries(db_path, race_records)
        click.echo(f"\nUpserted {len(race_records)} race entry records to {db_path}", err=True)

    if qual_records:
        upsert_qualifying_entries(db_path, qual_records)
        click.echo(f"\nUpserted {len(qual_records)} qualifying entry records to {db_path}", err=True)

    click.echo(f"\nDone. Processed: {processed}, Skipped: {skipped}, Errors: {errors}", err=True)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    update_elo_data()
