"""Shared test fixtures for pitlane-elo."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from pitlane_elo.data import QualifyingEntry, RaceEntry

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
