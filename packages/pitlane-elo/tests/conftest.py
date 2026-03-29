"""Shared test fixtures for pitlane-elo."""

from __future__ import annotations

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

_CREATE_RACE_ENTRIES_SQL = """
CREATE TABLE IF NOT EXISTS race_entries (
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
    is_wet_race       BOOLEAN NOT NULL DEFAULT FALSE,
    is_street_circuit BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (year, round, session_type, driver_id)
)
"""

_CREATE_QUALIFYING_ENTRIES_SQL = """
CREATE TABLE IF NOT EXISTS qualifying_entries (
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
    position      INTEGER NOT NULL,
    PRIMARY KEY (year, round, session_type, driver_id)
)
"""


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Create a temporary DuckDB with race_entries and qualifying_entries tables."""
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute(_CREATE_RACE_ENTRIES_SQL)
        con.execute(_CREATE_QUALIFYING_ENTRIES_SQL)
    finally:
        con.close()
    return db_path


@pytest.fixture()
def populated_db(tmp_db: Path) -> Path:
    """Temporary DB pre-populated with a small set of race and qualifying entries."""
    drivers = [
        ("max_verstappen", "VER", "Red Bull Racing", 1),
        ("sergio_perez", "PER", "Red Bull Racing", 2),
        ("lewis_hamilton", "HAM", "Mercedes", 3),
        ("carlos_sainz", "SAI", "Ferrari", 4),
        ("charles_leclerc", "LEC", "Ferrari", 5),
    ]
    con = duckdb.connect(str(tmp_db))
    try:
        for driver_id, abbr, team, pos in drivers:
            con.execute(
                """INSERT INTO race_entries
                   (year, round, session_type, driver_id, abbreviation, team,
                    grid_position, finish_position, laps_completed, status,
                    dnf_category, is_wet_race, is_street_circuit)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [2024, 1, "R", driver_id, abbr, team, pos, pos, 57, "Finished", "none", False, False],
            )
            con.execute(
                """INSERT INTO qualifying_entries
                   (year, round, session_type, driver_id, abbreviation, team,
                    q1_time_s, q2_time_s, q3_time_s, best_q_time_s, position)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [2024, 1, "Q", driver_id, abbr, team, 90.0 + pos, 89.0 + pos, 88.0 + pos, 88.0 + pos, pos],
            )
    finally:
        con.close()
    return tmp_db


@pytest.fixture()
def multi_race_db(tmp_db: Path) -> Path:
    """DB with 2 seasons (2023-2024), 3 races each, 5 drivers.

    Includes a mechanical DNF (HAM in 2023 R2) and a crash DNF (LEC in 2024 R1).
    Finish positions vary across races to exercise rating updates properly.
    """
    # (year, round, driver_id, abbr, team, grid, finish, laps, status, dnf_cat)
    race_data = [
        # 2023 Round 1 — normal race
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
    # (year, round, driver_id, abbr, team, q1, q2, q3, best, pos)
    qualifying_data = [
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
    con = duckdb.connect(str(tmp_db))
    try:
        for year, rnd, driver_id, abbr, team, grid, finish, laps, status, dnf in race_data:
            con.execute(
                """INSERT INTO race_entries
                   (year, round, session_type, driver_id, abbreviation, team,
                    grid_position, finish_position, laps_completed, status,
                    dnf_category, is_wet_race, is_street_circuit)
                   VALUES (?, ?, 'R', ?, ?, ?, ?, ?, ?, ?, ?, FALSE, FALSE)""",
                [year, rnd, driver_id, abbr, team, grid, finish, laps, status, dnf],
            )
        for year, rnd, driver_id, abbr, team, q1, q2, q3, best, pos in qualifying_data:
            con.execute(
                """INSERT INTO qualifying_entries
                   (year, round, session_type, driver_id, abbreviation, team,
                    q1_time_s, q2_time_s, q3_time_s, best_q_time_s, position)
                   VALUES (?, ?, 'Q', ?, ?, ?, ?, ?, ?, ?, ?)""",
                [year, rnd, driver_id, abbr, team, q1, q2, q3, best, pos],
            )
    finally:
        con.close()
    return tmp_db
