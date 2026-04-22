"""Shared test fixtures for pitlane-elo."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import duckdb
import pytest
from pitlane_elo.data import QualifyingEntry, RaceEntry

# ---------------------------------------------------------------------------
# Reusable test helpers
# ---------------------------------------------------------------------------


def make_race_entry(
    driver_id: str,
    finish: int | None,
    *,
    dnf_category: str = "none",
    laps: int = 57,
) -> RaceEntry:
    """Build a minimal RaceEntry dict for unit tests."""
    return {
        "year": 2024,
        "round": 1,
        "session_type": "R",
        "driver_id": driver_id,
        "team": "Team",
        "laps_completed": laps,
        "status": "Finished" if dnf_category == "none" else "Retired",
        "dnf_category": dnf_category,
        "is_wet_race": False,
        "is_street_circuit": False,
        "finish_position": finish,
    }


# ---------------------------------------------------------------------------
# Sample data matching the pitlane-agent schema
# ---------------------------------------------------------------------------

SAMPLE_RACE_ENTRY: RaceEntry = {
    "year": 2024,
    "round": 1,
    "session_type": "R",
    "driver_id": "max_verstappen",
    "abbreviation": "VER",
    "team": "Red Bull Racing",
    "grid_position": 1,
    "finish_position": 1,
    "laps_completed": 57,
    "status": "Finished",
    "dnf_category": "none",
    "is_wet_race": False,
    "is_street_circuit": False,
}

SAMPLE_QUALIFYING_ENTRY: QualifyingEntry = {
    "year": 2024,
    "round": 1,
    "session_type": "Q",
    "driver_id": "max_verstappen",
    "abbreviation": "VER",
    "team": "Red Bull Racing",
    "q1_time_s": 88.123,
    "q2_time_s": 87.456,
    "q3_time_s": 86.789,
    "best_q_time_s": 86.789,
    "position": 1,
}


# ---------------------------------------------------------------------------
# Parquet helpers (self-contained — no pitlane-agent dependency)
# ---------------------------------------------------------------------------

_RACE_DDL = """
    year              INTEGER NOT NULL,
    round             INTEGER NOT NULL,
    session_type      VARCHAR NOT NULL,
    driver_id         VARCHAR NOT NULL,
    abbreviation      VARCHAR,
    team              VARCHAR NOT NULL,
    grid_position     INTEGER,
    finish_position   INTEGER,
    laps_completed    INTEGER NOT NULL,
    status            VARCHAR NOT NULL,
    dnf_category      VARCHAR NOT NULL,
    is_wet_race       BOOLEAN NOT NULL,
    is_street_circuit BOOLEAN NOT NULL
"""

_QUAL_DDL = """
    year          INTEGER NOT NULL,
    round         INTEGER NOT NULL,
    session_type  VARCHAR NOT NULL,
    driver_id     VARCHAR NOT NULL,
    abbreviation  VARCHAR,
    team          VARCHAR NOT NULL,
    q1_time_s     DOUBLE,
    q2_time_s     DOUBLE,
    q3_time_s     DOUBLE,
    best_q_time_s DOUBLE,
    position      INTEGER NOT NULL
"""


def _write_race_parquet(data_dir: Path, rows: list[tuple]) -> None:
    """Write race entry tuples to year-partitioned Parquet files.

    Each row must be: (year, round, session_type, driver_id, abbreviation, team,
    grid_position, finish_position, laps_completed, status, dnf_category,
    is_wet_race, is_street_circuit).
    """
    by_year: dict[int, list[tuple]] = defaultdict(list)
    for row in rows:
        by_year[row[0]].append(row)
    for year, year_rows in by_year.items():
        parquet_path = data_dir / "race_entries" / f"{year}.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE race_entries ({_RACE_DDL})")
            for row in year_rows:
                con.execute("INSERT INTO race_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", list(row))
            con.execute(f"COPY race_entries TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        finally:
            con.close()


def _write_qual_parquet(data_dir: Path, rows: list[tuple]) -> None:
    """Write qualifying entry tuples to year-partitioned Parquet files.

    Each row must be: (year, round, session_type, driver_id, abbreviation, team,
    q1_time_s, q2_time_s, q3_time_s, best_q_time_s, position).
    """
    by_year: dict[int, list[tuple]] = defaultdict(list)
    for row in rows:
        by_year[row[0]].append(row)
    for year, year_rows in by_year.items():
        parquet_path = data_dir / "qualifying_entries" / f"{year}.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE qualifying_entries ({_QUAL_DDL})")
            for row in year_rows:
                con.execute("INSERT INTO qualifying_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", list(row))
            con.execute(f"COPY qualifying_entries TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        finally:
            con.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a temporary data directory (no Parquet files yet)."""
    return tmp_path


@pytest.fixture()
def populated_db(tmp_path: Path) -> Path:
    """Temporary data dir pre-populated with a small set of race and qualifying entries."""
    drivers = [
        ("max_verstappen", "VER", "Red Bull Racing", 1),
        ("sergio_perez", "PER", "Red Bull Racing", 2),
        ("lewis_hamilton", "HAM", "Mercedes", 3),
        ("carlos_sainz", "SAI", "Ferrari", 4),
        ("charles_leclerc", "LEC", "Ferrari", 5),
    ]
    race_rows = [
        (2024, 1, "R", driver_id, abbr, team, pos, pos, 57, "Finished", "none", False, False)
        for driver_id, abbr, team, pos in drivers
    ]
    qual_rows = [
        (2024, 1, "Q", driver_id, abbr, team, 90.0 + pos, 89.0 + pos, 88.0 + pos, 88.0 + pos, pos)
        for driver_id, abbr, team, pos in drivers
    ]
    _write_race_parquet(tmp_path, race_rows)
    _write_qual_parquet(tmp_path, qual_rows)
    return tmp_path


@pytest.fixture()
def multi_race_db(tmp_path: Path) -> Path:
    """Data dir with 2 seasons (2023-2024), 3 races each, 5 drivers.

    Includes a mechanical DNF (HAM in 2023 R2) and a crash DNF (LEC in 2024 R1).
    """
    # (year, round, driver_id, abbr, team, grid, finish, laps, status, dnf)
    race_data = [
        # 2023 Round 1
        (2023, 1, "max_verstappen", "VER", "Red Bull Racing", 1, 1, 57, "Finished", "none"),
        (2023, 1, "sergio_perez", "PER", "Red Bull Racing", 3, 2, 57, "Finished", "none"),
        (2023, 1, "lewis_hamilton", "HAM", "Mercedes", 2, 3, 57, "Finished", "none"),
        (2023, 1, "carlos_sainz", "SAI", "Ferrari", 4, 4, 57, "Finished", "none"),
        (2023, 1, "charles_leclerc", "LEC", "Ferrari", 5, 5, 57, "Finished", "none"),
        # 2023 Round 2 — HAM mechanical DNF
        (2023, 2, "max_verstappen", "VER", "Red Bull Racing", 1, 1, 57, "Finished", "none"),
        (2023, 2, "charles_leclerc", "LEC", "Ferrari", 4, 2, 57, "Finished", "none"),
        (2023, 2, "carlos_sainz", "SAI", "Ferrari", 3, 3, 57, "Finished", "none"),
        (2023, 2, "sergio_perez", "PER", "Red Bull Racing", 2, 4, 57, "Finished", "none"),
        (2023, 2, "lewis_hamilton", "HAM", "Mercedes", 5, None, 30, "Engine", "mechanical"),
        # 2023 Round 3
        (2023, 3, "lewis_hamilton", "HAM", "Mercedes", 1, 1, 57, "Finished", "none"),
        (2023, 3, "max_verstappen", "VER", "Red Bull Racing", 2, 2, 57, "Finished", "none"),
        (2023, 3, "charles_leclerc", "LEC", "Ferrari", 3, 3, 57, "Finished", "none"),
        (2023, 3, "sergio_perez", "PER", "Red Bull Racing", 5, 4, 57, "Finished", "none"),
        (2023, 3, "carlos_sainz", "SAI", "Ferrari", 4, 5, 57, "Finished", "none"),
        # 2024 Round 1 — LEC crash DNF
        (2024, 1, "max_verstappen", "VER", "Red Bull Racing", 1, 1, 57, "Finished", "none"),
        (2024, 1, "sergio_perez", "PER", "Red Bull Racing", 2, 2, 57, "Finished", "none"),
        (2024, 1, "lewis_hamilton", "HAM", "Mercedes", 3, 3, 57, "Finished", "none"),
        (2024, 1, "carlos_sainz", "SAI", "Ferrari", 4, 4, 57, "Finished", "none"),
        (2024, 1, "charles_leclerc", "LEC", "Ferrari", 5, None, 10, "Collision", "crash"),
        # 2024 Round 2
        (2024, 2, "charles_leclerc", "LEC", "Ferrari", 1, 1, 57, "Finished", "none"),
        (2024, 2, "max_verstappen", "VER", "Red Bull Racing", 2, 2, 57, "Finished", "none"),
        (2024, 2, "carlos_sainz", "SAI", "Ferrari", 3, 3, 57, "Finished", "none"),
        (2024, 2, "lewis_hamilton", "HAM", "Mercedes", 4, 4, 57, "Finished", "none"),
        (2024, 2, "sergio_perez", "PER", "Red Bull Racing", 5, 5, 57, "Finished", "none"),
        # 2024 Round 3
        (2024, 3, "lewis_hamilton", "HAM", "Mercedes", 2, 1, 57, "Finished", "none"),
        (2024, 3, "charles_leclerc", "LEC", "Ferrari", 1, 2, 57, "Finished", "none"),
        (2024, 3, "max_verstappen", "VER", "Red Bull Racing", 3, 3, 57, "Finished", "none"),
        (2024, 3, "sergio_perez", "PER", "Red Bull Racing", 4, 4, 57, "Finished", "none"),
        (2024, 3, "carlos_sainz", "SAI", "Ferrari", 5, 5, 57, "Finished", "none"),
    ]
    qual_data = [
        # 2023 Round 1
        (2023, 1, "max_verstappen", "VER", "Red Bull Racing", 91.0, 90.0, 89.0, 89.0, 1),
        (2023, 1, "sergio_perez", "PER", "Red Bull Racing", 91.5, 90.5, 89.5, 89.5, 2),
        (2023, 1, "lewis_hamilton", "HAM", "Mercedes", 91.8, 90.8, 89.8, 89.8, 3),
        (2023, 1, "carlos_sainz", "SAI", "Ferrari", 92.0, 91.0, 90.0, 90.0, 4),
        (2023, 1, "charles_leclerc", "LEC", "Ferrari", 92.2, 91.2, 90.2, 90.2, 5),
        # 2023 Round 2
        (2023, 2, "max_verstappen", "VER", "Red Bull Racing", 80.0, 79.0, 78.0, 78.0, 1),
        (2023, 2, "sergio_perez", "PER", "Red Bull Racing", 80.5, 79.5, 78.8, 78.8, 2),
        (2023, 2, "carlos_sainz", "SAI", "Ferrari", 81.0, 80.0, 79.0, 79.0, 3),
        (2023, 2, "charles_leclerc", "LEC", "Ferrari", 81.2, 80.2, 79.2, 79.2, 4),
        (2023, 2, "lewis_hamilton", "HAM", "Mercedes", 81.5, 80.5, 79.5, 79.5, 5),
        # 2023 Round 3
        (2023, 3, "lewis_hamilton", "HAM", "Mercedes", 95.0, 94.0, 93.0, 93.0, 1),
        (2023, 3, "max_verstappen", "VER", "Red Bull Racing", 95.2, 94.2, 93.2, 93.2, 2),
        (2023, 3, "charles_leclerc", "LEC", "Ferrari", 95.5, 94.5, 93.5, 93.5, 3),
        (2023, 3, "sergio_perez", "PER", "Red Bull Racing", 96.0, 95.0, 94.0, 94.0, 4),
        (2023, 3, "carlos_sainz", "SAI", "Ferrari", 96.0, 95.0, 94.0, 94.0, 5),
        # 2024 Round 1
        (2024, 1, "max_verstappen", "VER", "Red Bull Racing", 88.0, 87.0, 86.0, 86.0, 1),
        (2024, 1, "sergio_perez", "PER", "Red Bull Racing", 88.5, 87.5, 86.5, 86.5, 2),
        (2024, 1, "lewis_hamilton", "HAM", "Mercedes", 89.0, 88.0, 87.0, 87.0, 3),
        (2024, 1, "carlos_sainz", "SAI", "Ferrari", 89.5, 88.5, 87.5, 87.5, 4),
        (2024, 1, "charles_leclerc", "LEC", "Ferrari", 89.8, 88.8, 87.8, 87.8, 5),
        # 2024 Round 2
        (2024, 2, "charles_leclerc", "LEC", "Ferrari", 76.0, 75.0, 74.0, 74.0, 1),
        (2024, 2, "max_verstappen", "VER", "Red Bull Racing", 76.2, 75.2, 74.2, 74.2, 2),
        (2024, 2, "carlos_sainz", "SAI", "Ferrari", 76.5, 75.5, 74.5, 74.5, 3),
        (2024, 2, "lewis_hamilton", "HAM", "Mercedes", 77.0, 76.0, 75.0, 75.0, 4),
        (2024, 2, "sergio_perez", "PER", "Red Bull Racing", 77.5, 76.5, 75.5, 75.5, 5),
        # 2024 Round 3
        (2024, 3, "charles_leclerc", "LEC", "Ferrari", 100.0, 99.0, 98.0, 98.0, 1),
        (2024, 3, "lewis_hamilton", "HAM", "Mercedes", 100.2, 99.2, 98.2, 98.2, 2),
        (2024, 3, "max_verstappen", "VER", "Red Bull Racing", 100.5, 99.5, 98.5, 98.5, 3),
        (2024, 3, "sergio_perez", "PER", "Red Bull Racing", 101.0, 100.0, 99.0, 99.0, 4),
        (2024, 3, "carlos_sainz", "SAI", "Ferrari", 101.0, 100.0, 99.0, 99.0, 5),
    ]
    race_rows = [
        (year, rnd, "R", driver_id, abbr, team, grid, finish, laps, status, dnf, False, False)
        for year, rnd, driver_id, abbr, team, grid, finish, laps, status, dnf in race_data
    ]
    qual_rows = [
        (year, rnd, "Q", driver_id, abbr, team, q1, q2, q3, best, pos)
        for year, rnd, driver_id, abbr, team, q1, q2, q3, best, pos in qual_data
    ]
    _write_race_parquet(tmp_path, race_rows)
    _write_qual_parquet(tmp_path, qual_rows)
    return tmp_path


@pytest.fixture()
def cancelled_rounds_db(tmp_path: Path) -> Path:
    """Data dir with 2023 R1-R3 and 2024 R1 + R3 (R2 intentionally absent — simulates cancellation)."""
    race_data = [
        # 2023 Round 1
        (2023, 1, "max_verstappen", "VER", "Red Bull Racing", 1, 1, 57, "Finished", "none"),
        (2023, 1, "sergio_perez", "PER", "Red Bull Racing", 3, 2, 57, "Finished", "none"),
        (2023, 1, "lewis_hamilton", "HAM", "Mercedes", 2, 3, 57, "Finished", "none"),
        (2023, 1, "carlos_sainz", "SAI", "Ferrari", 4, 4, 57, "Finished", "none"),
        (2023, 1, "charles_leclerc", "LEC", "Ferrari", 5, 5, 57, "Finished", "none"),
        # 2023 Round 2
        (2023, 2, "max_verstappen", "VER", "Red Bull Racing", 1, 1, 57, "Finished", "none"),
        (2023, 2, "lewis_hamilton", "HAM", "Mercedes", 2, 2, 57, "Finished", "none"),
        (2023, 2, "sergio_perez", "PER", "Red Bull Racing", 3, 3, 57, "Finished", "none"),
        (2023, 2, "carlos_sainz", "SAI", "Ferrari", 4, 4, 57, "Finished", "none"),
        (2023, 2, "charles_leclerc", "LEC", "Ferrari", 5, 5, 57, "Finished", "none"),
        # 2023 Round 3
        (2023, 3, "lewis_hamilton", "HAM", "Mercedes", 1, 1, 57, "Finished", "none"),
        (2023, 3, "max_verstappen", "VER", "Red Bull Racing", 2, 2, 57, "Finished", "none"),
        (2023, 3, "charles_leclerc", "LEC", "Ferrari", 3, 3, 57, "Finished", "none"),
        (2023, 3, "sergio_perez", "PER", "Red Bull Racing", 4, 4, 57, "Finished", "none"),
        (2023, 3, "carlos_sainz", "SAI", "Ferrari", 5, 5, 57, "Finished", "none"),
        # 2024 Round 1 (R2 cancelled — intentionally absent)
        (2024, 1, "max_verstappen", "VER", "Red Bull Racing", 1, 1, 57, "Finished", "none"),
        (2024, 1, "sergio_perez", "PER", "Red Bull Racing", 2, 2, 57, "Finished", "none"),
        (2024, 1, "lewis_hamilton", "HAM", "Mercedes", 3, 3, 57, "Finished", "none"),
        (2024, 1, "carlos_sainz", "SAI", "Ferrari", 4, 4, 57, "Finished", "none"),
        (2024, 1, "charles_leclerc", "LEC", "Ferrari", 5, 5, 57, "Finished", "none"),
        # 2024 Round 3 (R2 skipped — cancelled)
        (2024, 3, "charles_leclerc", "LEC", "Ferrari", 1, 1, 57, "Finished", "none"),
        (2024, 3, "max_verstappen", "VER", "Red Bull Racing", 2, 2, 57, "Finished", "none"),
        (2024, 3, "lewis_hamilton", "HAM", "Mercedes", 3, 3, 57, "Finished", "none"),
        (2024, 3, "sergio_perez", "PER", "Red Bull Racing", 4, 4, 57, "Finished", "none"),
        (2024, 3, "carlos_sainz", "SAI", "Ferrari", 5, 5, 57, "Finished", "none"),
    ]
    race_rows = [
        (year, rnd, "R", driver_id, abbr, team, grid, finish, laps, status, dnf, False, False)
        for year, rnd, driver_id, abbr, team, grid, finish, laps, status, dnf in race_data
    ]
    _write_race_parquet(tmp_path, race_rows)
    return tmp_path
