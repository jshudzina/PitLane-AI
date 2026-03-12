"""DuckDB-backed stats database for pre-computed session statistics."""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import duckdb

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS session_stats (
    year                    INTEGER NOT NULL,
    round                   INTEGER NOT NULL,
    event_name              VARCHAR NOT NULL,
    country                 VARCHAR NOT NULL,
    date                    VARCHAR,
    session_type            VARCHAR NOT NULL,
    circuit_length_km       DOUBLE,
    total_overtakes         INTEGER,
    total_position_changes  INTEGER,
    average_volatility      DOUBLE,
    mean_pit_stops          DOUBLE,
    total_laps              INTEGER,
    num_safety_cars         INTEGER,
    num_virtual_safety_cars INTEGER,
    num_red_flags           INTEGER,
    podium                  VARCHAR,
    PRIMARY KEY (year, round, session_type)
)
"""

_UPSERT_SQL = """
INSERT OR REPLACE INTO session_stats VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
)
"""


def get_db_path() -> Path:
    """Resolve the bundled .duckdb file path via importlib.resources."""
    ref = importlib.resources.files("pitlane_agent") / "data" / "pitlane.duckdb"
    return Path(str(ref))


def init_db(db_path: Path) -> None:
    """Create the session_stats table if it does not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(_CREATE_TABLE_SQL)
    finally:
        con.close()


def upsert_session_stats(db_path: Path, records: list[dict]) -> None:
    """Insert or replace rows keyed on (year, round, session_type).

    Args:
        db_path: Path to the DuckDB database file.
        records: List of dicts with keys matching the session_stats schema.
    """
    if not records:
        return
    con = duckdb.connect(str(db_path))
    try:
        for record in records:
            con.execute(
                _UPSERT_SQL,
                [
                    record.get("year"),
                    record.get("round"),
                    record.get("event_name"),
                    record.get("country"),
                    record.get("date"),
                    record.get("session_type"),
                    record.get("circuit_length_km"),
                    record.get("total_overtakes"),
                    record.get("total_position_changes"),
                    record.get("average_volatility"),
                    record.get("mean_pit_stops"),
                    record.get("total_laps"),
                    record.get("num_safety_cars"),
                    record.get("num_virtual_safety_cars"),
                    record.get("num_red_flags"),
                    record.get("podium"),
                ],
            )
    finally:
        con.close()


def get_season_stats(db_path: Path, year: int) -> list[dict] | None:
    """Fetch all rows for a season ordered by round.

    Args:
        db_path: Path to the DuckDB database file.
        year: The F1 season year to query.

    Returns:
        List of dicts for each session, or None if the database does not exist
        or no rows are found for the given year.
    """
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        cursor = con.execute(
            "SELECT * FROM session_stats WHERE year = ? ORDER BY round", [year]
        )
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
    finally:
        con.close()
    return [dict(zip(columns, row)) for row in rows]
