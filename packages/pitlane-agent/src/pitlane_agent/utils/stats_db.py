"""Parquet-backed stats database for pre-computed session statistics."""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TypedDict, cast

import duckdb


class SessionStats(TypedDict, total=False):
    year: int
    round: int
    event_name: str
    country: str
    date: str | None
    session_type: str
    circuit_length_km: float | None
    total_overtakes: int | None
    total_position_changes: int | None
    average_volatility: float | None
    mean_pit_stops: float | None
    total_laps: int | None
    num_safety_cars: int | None
    num_virtual_safety_cars: int | None
    num_red_flags: int | None
    podium: str | None


_CREATE_SQL = """
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
INSERT OR REPLACE INTO session_stats (
    year, round, event_name, country, date, session_type,
    circuit_length_km, total_overtakes, total_position_changes,
    average_volatility, mean_pit_stops, total_laps,
    num_safety_cars, num_virtual_safety_cars, num_red_flags, podium
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
)
"""

_COLUMNS = (
    "year",
    "round",
    "event_name",
    "country",
    "date",
    "session_type",
    "circuit_length_km",
    "total_overtakes",
    "total_position_changes",
    "average_volatility",
    "mean_pit_stops",
    "total_laps",
    "num_safety_cars",
    "num_virtual_safety_cars",
    "num_red_flags",
    "podium",
)

_PARQUET_FILE = "session_stats.parquet"


def get_data_dir() -> Path:
    """Resolve the bundled data directory path via importlib.resources."""
    ref = importlib.resources.files("pitlane_agent") / "data"
    return Path(str(ref))


def init_data_dir(data_dir: Path) -> None:
    """Create the data directory if it does not exist."""
    data_dir.mkdir(parents=True, exist_ok=True)


def upsert_session_stats(data_dir: Path, records: list[SessionStats]) -> None:
    """Insert or replace rows keyed on (year, round, session_type).

    Args:
        data_dir: Path to the data directory containing Parquet files.
        records: List of dicts with keys matching the session_stats schema.
    """
    if not records:
        return
    parquet_path = data_dir / _PARQUET_FILE
    rows = [[r.get(col) for col in _COLUMNS] for r in records]
    con = duckdb.connect()
    try:
        con.execute(_CREATE_SQL)
        if parquet_path.exists():
            con.execute(f"INSERT OR REPLACE INTO session_stats SELECT * FROM read_parquet('{parquet_path}')")
        con.executemany(_UPSERT_SQL, rows)
        data_dir.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY session_stats TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    finally:
        con.close()


def get_season_stats(data_dir: Path, year: int) -> list[SessionStats] | None:
    """Fetch all rows for a season ordered by round.

    Args:
        data_dir: Path to the data directory containing Parquet files.
        year: The F1 season year to query.

    Returns:
        List of dicts for each session, or None if the Parquet file does not
        exist or no rows are found for the given year.
    """
    parquet_path = data_dir / _PARQUET_FILE
    if not parquet_path.exists():
        return None
    con = duckdb.connect()
    try:
        cursor = con.execute(
            f"SELECT * FROM read_parquet('{parquet_path}') WHERE year = ? ORDER BY round",
            [year],
        )
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
    finally:
        con.close()
    return [cast(SessionStats, dict(zip(columns, row, strict=True))) for row in rows]
