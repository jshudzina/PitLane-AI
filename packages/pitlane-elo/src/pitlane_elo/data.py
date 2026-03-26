"""Read-only access to the pitlane DuckDB database.

Provides TypedDicts and query functions for race and qualifying entries.
Adapted from pitlane_agent.utils.elo_db — only the read-only subset is
included here so that pitlane-elo has no dependency on pitlane-agent.
"""

from __future__ import annotations

import itertools
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
# Explicit column lists (used in SELECT to avoid fragility from schema changes)
# ---------------------------------------------------------------------------

_RACE_COLS = (
    "year, round, session_type, driver_id, abbreviation, team, "
    "grid_position, finish_position, laps_completed, status, "
    "dnf_category, is_wet_race, is_street_circuit"
)

_QUALIFYING_COLS = (
    "year, round, session_type, driver_id, abbreviation, team, q1_time_s, q2_time_s, q3_time_s, best_q_time_s, position"
)


# ---------------------------------------------------------------------------
# Read-only query helpers
# ---------------------------------------------------------------------------


def _query(
    path: Path,
    sql: str,
    params: list[object],
) -> list[dict[str, object]] | None:
    """Execute a read-only query and return a list of row dicts, or None."""
    if not path.exists():
        return None
    with duckdb.connect(str(path), read_only=True) as con:
        cursor = con.execute(sql, params)
        rows = cursor.fetchall()
        if not rows:
            return None
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]


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
    if session_type is not None:
        sql = f"SELECT {_RACE_COLS} FROM race_entries WHERE year = ? AND session_type = ? ORDER BY round, driver_id"
        result = _query(path, sql, [year, session_type])
    else:
        sql = f"SELECT {_RACE_COLS} FROM race_entries WHERE year = ? ORDER BY round, driver_id"
        result = _query(path, sql, [year])
    return cast(list[RaceEntry], result) if result else None


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
    if session_type is not None:
        sql = (
            f"SELECT {_QUALIFYING_COLS} FROM qualifying_entries"
            " WHERE year = ? AND session_type = ? ORDER BY round, driver_id"
        )
        result = _query(path, sql, [year, session_type])
    else:
        sql = f"SELECT {_QUALIFYING_COLS} FROM qualifying_entries WHERE year = ? ORDER BY round, driver_id"
        result = _query(path, sql, [year])
    return cast(list[QualifyingEntry], result) if result else None


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
    sql = f"SELECT {_RACE_COLS} FROM race_entries WHERE year BETWEEN ? AND ? ORDER BY year, round, driver_id"
    result = _query(path, sql, [start_year, end_year])
    return cast(list[RaceEntry], result) if result else None


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
    sql = (
        f"SELECT {_QUALIFYING_COLS} FROM qualifying_entries WHERE year BETWEEN ? AND ? ORDER BY year, round, driver_id"
    )
    result = _query(path, sql, [start_year, end_year])
    return cast(list[QualifyingEntry], result) if result else None


# ---------------------------------------------------------------------------
# Data shaping helpers
# ---------------------------------------------------------------------------


def _finish_sort_key(entry: RaceEntry) -> tuple[int, int]:
    """Sort key that puts finishers first (by position), then DNFs (by laps desc)."""
    fp = entry.get("finish_position")
    if fp is not None:
        return (0, fp)
    # DNFs without finish_position: rank by laps completed (more laps = better)
    return (1, -(entry.get("laps_completed", 0) or 0))


def order_race_entries(entries: list[RaceEntry]) -> list[RaceEntry]:
    """Sort race entries into finishing order (best first).

    Finishers are sorted by ``finish_position``. DNFs without a finish position
    are appended after finishers, ordered by ``laps_completed`` descending
    (more laps = retired later = higher implied position).
    """
    return sorted(entries, key=_finish_sort_key)


def group_entries_by_race(entries: list[RaceEntry]) -> list[list[RaceEntry]]:
    """Group a flat list of race entries into per-race lists in finishing order.

    Entries are grouped by ``(year, round, session_type)`` and each group is
    sorted via :func:`order_race_entries`.  The groups themselves are returned
    in chronological order.
    """
    key_fn = lambda e: (e["year"], e["round"], e["session_type"])
    sorted_entries = sorted(entries, key=key_fn)
    return [order_race_entries(list(group)) for _, group in itertools.groupby(sorted_entries, key=key_fn)]


__all__ = [
    "RaceEntry",
    "QualifyingEntry",
    "get_db_path",
    "get_race_entries",
    "get_qualifying_entries",
    "get_race_entries_range",
    "get_qualifying_entries_range",
    "order_race_entries",
    "group_entries_by_race",
]
