"""Read-only access to the pitlane DuckDB database.

Provides TypedDicts and query functions for race and qualifying entries.
Adapted from pitlane_agent.utils.elo_db — only the read-only subset is
included here so that pitlane-elo has no dependency on pitlane-agent.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict, cast

import duckdb

# ---------------------------------------------------------------------------
# TypedDicts — mirrors of the pitlane-agent schema
# ---------------------------------------------------------------------------


class _RaceEntryRequired(TypedDict):
    year: int
    round: int
    session_type: str  # "R" or "S" (sprint)
    driver_id: str  # Ergast driverId slug, e.g. "hamilton"
    team: str
    laps_completed: int
    status: str  # raw FastF1 status string
    dnf_category: str  # "none", "mechanical", or "crash"
    is_wet_race: bool
    is_street_circuit: bool


class RaceEntry(_RaceEntryRequired, total=False):
    """Per-driver result for a race or sprint session."""

    abbreviation: str | None
    grid_position: int | None
    finish_position: int | None


class _QualifyingEntryRequired(TypedDict):
    year: int
    round: int
    session_type: str  # "Q" or "SQ"
    driver_id: str
    team: str
    position: int


class QualifyingEntry(_QualifyingEntryRequired, total=False):
    """Per-driver result for a qualifying session."""

    abbreviation: str | None
    q1_time_s: float | None
    q2_time_s: float | None
    q3_time_s: float | None
    best_q_time_s: float | None


# ---------------------------------------------------------------------------
# DB path resolution
# ---------------------------------------------------------------------------

_DEFAULT_RELATIVE_DB = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "pitlane-agent"
    / "src"
    / "pitlane_agent"
    / "data"
    / "pitlane.duckdb"
)


def get_db_path() -> Path:
    """Resolve the path to the pitlane DuckDB database.

    Resolution order:
    1. ``PITLANE_DB_PATH`` environment variable (if set and non-empty).
    2. Default: ``packages/pitlane-agent/src/pitlane_agent/data/pitlane.duckdb``
       relative to the pitlane-elo package location.
    """
    env = os.environ.get("PITLANE_DB_PATH", "").strip()
    if env:
        return Path(env)
    return _DEFAULT_RELATIVE_DB


# ---------------------------------------------------------------------------
# Column tuples (for dict construction from rows)
# ---------------------------------------------------------------------------

_RACE_COLUMNS = (
    "year",
    "round",
    "session_type",
    "driver_id",
    "abbreviation",
    "team",
    "grid_position",
    "finish_position",
    "laps_completed",
    "status",
    "dnf_category",
    "is_wet_race",
    "is_street_circuit",
)

_QUALIFYING_COLUMNS = (
    "year",
    "round",
    "session_type",
    "driver_id",
    "abbreviation",
    "team",
    "q1_time_s",
    "q2_time_s",
    "q3_time_s",
    "best_q_time_s",
    "position",
)


# ---------------------------------------------------------------------------
# Read-only query functions
# ---------------------------------------------------------------------------


def get_race_entries(
    year: int,
    *,
    db_path: Path | None = None,
    session_type: str | None = None,
) -> list[RaceEntry] | None:
    """Fetch race entries for a season, optionally filtered by session type.

    Args:
        year: The F1 season year to query.
        db_path: Override the database path. Defaults to :func:`get_db_path`.
        session_type: If provided, filter to this session type ("R" or "S").

    Returns:
        List of RaceEntry dicts, or None if the database does not exist or
        no rows match.
    """
    path = db_path or get_db_path()
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        if session_type is not None:
            cursor = con.execute(
                "SELECT * FROM race_entries WHERE year = ? AND session_type = ? ORDER BY round, driver_id",
                [year, session_type],
            )
        else:
            cursor = con.execute(
                "SELECT * FROM race_entries WHERE year = ? ORDER BY round, driver_id",
                [year],
            )
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
    finally:
        con.close()
    return [cast(RaceEntry, dict(zip(columns, row, strict=True))) for row in rows]


def get_qualifying_entries(
    year: int,
    *,
    db_path: Path | None = None,
    session_type: str | None = None,
) -> list[QualifyingEntry] | None:
    """Fetch qualifying entries for a season, optionally filtered by session type.

    Args:
        year: The F1 season year to query.
        db_path: Override the database path. Defaults to :func:`get_db_path`.
        session_type: If provided, filter to this session type ("Q" or "SQ").

    Returns:
        List of QualifyingEntry dicts, or None if the database does not exist
        or no rows match.
    """
    path = db_path or get_db_path()
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        if session_type is not None:
            cursor = con.execute(
                "SELECT * FROM qualifying_entries WHERE year = ? AND session_type = ? ORDER BY round, driver_id",
                [year, session_type],
            )
        else:
            cursor = con.execute(
                "SELECT * FROM qualifying_entries WHERE year = ? ORDER BY round, driver_id",
                [year],
            )
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
    finally:
        con.close()
    return [cast(QualifyingEntry, dict(zip(columns, row, strict=True))) for row in rows]


def get_race_entries_range(
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
) -> list[RaceEntry] | None:
    """Fetch race entries across a range of seasons (inclusive).

    Args:
        start_year: First season year.
        end_year: Last season year (inclusive).
        db_path: Override the database path.

    Returns:
        List of RaceEntry dicts, or None if no rows match.
    """
    path = db_path or get_db_path()
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        cursor = con.execute(
            "SELECT * FROM race_entries WHERE year BETWEEN ? AND ? ORDER BY year, round, driver_id",
            [start_year, end_year],
        )
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
    finally:
        con.close()
    return [cast(RaceEntry, dict(zip(columns, row, strict=True))) for row in rows]


def get_qualifying_entries_range(
    start_year: int,
    end_year: int,
    *,
    db_path: Path | None = None,
) -> list[QualifyingEntry] | None:
    """Fetch qualifying entries across a range of seasons (inclusive).

    Args:
        start_year: First season year.
        end_year: Last season year (inclusive).
        db_path: Override the database path.

    Returns:
        List of QualifyingEntry dicts, or None if no rows match.
    """
    path = db_path or get_db_path()
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        cursor = con.execute(
            "SELECT * FROM qualifying_entries WHERE year BETWEEN ? AND ? ORDER BY year, round, driver_id",
            [start_year, end_year],
        )
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
    finally:
        con.close()
    return [cast(QualifyingEntry, dict(zip(columns, row, strict=True))) for row in rows]


__all__ = [
    "RaceEntry",
    "QualifyingEntry",
    "get_db_path",
    "get_race_entries",
    "get_qualifying_entries",
    "get_race_entries_range",
    "get_qualifying_entries_range",
]
