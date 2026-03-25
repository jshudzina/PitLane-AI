"""DuckDB-backed ELO data store for per-driver race and qualifying entries."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast

import duckdb

from pitlane_agent.utils.stats_db import get_db_path


class RaceEntry(TypedDict, total=False):
    """Per-driver result for a race or sprint session.

    driver_id is the stable Ergast driverId slug (e.g. "hamilton",
    "max_verstappen") and is the primary identifier. It is reliable across all
    of F1 history. abbreviation is the 3-letter display code (e.g. "HAM") but
    is unreliable for pre-1994 historical drivers.

    is_wet_race and is_street_circuit are Phase 1 stubs — both are always
    stored as False. Future phases should derive is_wet_race from
    session.weather_data and is_street_circuit from a static location lookup.
    """

    year: int
    round: int
    session_type: str  # "R" or "S" (sprint)
    driver_id: str  # Ergast driverId slug, e.g. "hamilton" — stable across all history
    abbreviation: str | None  # 3-letter code; None for pre-1994 historical drivers
    team: str
    grid_position: int | None  # None = pit lane start
    finish_position: int | None  # None = mechanical DNF (Xun's approach)
    laps_completed: int
    status: str  # raw FastF1 status string, e.g. "Finished", "Engine", "Accident"
    dnf_category: str  # "none", "mechanical", or "crash"
    # Phase 1 stubs: always False until dedicated detection is implemented.
    # is_wet_race: derive from session.weather_data in a future phase.
    # is_street_circuit: derive from a static location lookup in a future phase.
    is_wet_race: bool
    is_street_circuit: bool


class QualifyingEntry(TypedDict, total=False):
    """Per-driver result for a qualifying session.

    Used to compute Xun's Car Rating (Rc = team_avg_qual / fastest_qual).
    best_q_time_s is the absolute fastest lap across Q1/Q2/Q3, which is
    the correct input for Rc computation.

    Q1/Q2/Q3 columns are present in all FastF1 sessions but contain pd.NaT
    for pre-2006 seasons (before F1's three-phase knockout qualifying format
    was introduced). For pre-2006 sessions all time columns are None/NULL.
    Reliable data starts from 2006.
    """

    year: int
    round: int
    driver_id: str  # Ergast driverId slug — same identifier as RaceEntry
    abbreviation: str | None  # 3-letter code; None for pre-1994 historical drivers
    team: str
    q1_time_s: float | None  # None if driver did not set a time or pre-2006
    q2_time_s: float | None  # None if eliminated in Q1 or pre-2006
    q3_time_s: float | None  # None if eliminated in Q2 or pre-2006
    best_q_time_s: float | None  # min() of available times; None if no times recorded
    position: int  # classified qualifying position


# Schema version 1. No migration path — if columns change, drop and recreate
# the database file (it is a regenerable cache, not a source of truth).
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
    -- Phase 1 stubs: always FALSE until wet/street detection is implemented
    is_wet_race       BOOLEAN NOT NULL DEFAULT FALSE,
    is_street_circuit BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (year, round, session_type, driver_id)
)
"""

_CREATE_QUALIFYING_ENTRIES_SQL = """
CREATE TABLE IF NOT EXISTS qualifying_entries (
    year          INTEGER NOT NULL,
    round         INTEGER NOT NULL,
    driver_id     VARCHAR NOT NULL,
    abbreviation  VARCHAR,
    team          VARCHAR NOT NULL,
    -- Q1/Q2/Q3 data is only reliable from 2006 (knockout qualifying format).
    -- Pre-2006 sessions have NaT values in FastF1, stored as NULL here.
    q1_time_s     DOUBLE,
    q2_time_s     DOUBLE,
    q3_time_s     DOUBLE,
    best_q_time_s DOUBLE,
    position      INTEGER NOT NULL,
    PRIMARY KEY (year, round, driver_id)
)
"""

_UPSERT_RACE_ENTRY_SQL = """
INSERT OR REPLACE INTO race_entries (
    year, round, session_type, driver_id, abbreviation, team,
    grid_position, finish_position, laps_completed,
    status, dnf_category, is_wet_race, is_street_circuit
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPSERT_QUALIFYING_ENTRY_SQL = """
INSERT OR REPLACE INTO qualifying_entries (
    year, round, driver_id, abbreviation, team,
    q1_time_s, q2_time_s, q3_time_s, best_q_time_s, position
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

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
    "driver_id",
    "abbreviation",
    "team",
    "q1_time_s",
    "q2_time_s",
    "q3_time_s",
    "best_q_time_s",
    "position",
)

_MECHANICAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "engine",
        "gearbox",
        "power unit",
        "hydraulics",
        "electrical",
        "brakes",
        "suspension",
        "overheating",
        "transmission",
        "turbo",
        "oil pressure",
        "fuel",
        "wheel",
        "tyre",
        "throttle",
        "clutch",
    }
)

_CRASH_KEYWORDS: frozenset[str] = frozenset(
    {
        "accident",
        "collision",
        "spun off",
        "damage",
        "retired",
    }
)


def categorize_dnf(status: str) -> str:
    """Derive DNF category from a raw FastF1 status string.

    Returns "none" for classified finishers and lapped drivers, "mechanical"
    for power-unit and reliability failures, and "crash" as the catch-all for
    on-track incidents and ambiguous retirements.

    Following Xun's methodology: mechanical DNFs are excluded from ELO
    computation (the caller sets finish_position=None for these). Crash DNFs
    are included, ranked at their elimination position.

    Args:
        status: Raw status string from session.results["Status"].

    Returns:
        One of "none", "mechanical", or "crash".
    """
    if not status:
        return "none"
    lower = status.lower().strip()
    if lower in ("finished", "lapped") or lower.startswith("+"):
        return "none"
    # Exact-match check (O(1) frozenset lookup)
    if lower in _MECHANICAL_KEYWORDS:
        return "mechanical"
    if lower in _CRASH_KEYWORDS:
        return "crash"
    # Partial-match fallback for multi-word statuses (e.g. "Power Unit")
    for kw in _MECHANICAL_KEYWORDS:
        if kw in lower:
            return "mechanical"
    for kw in _CRASH_KEYWORDS:
        if kw in lower:
            return "crash"
    # Unknown status treated as crash (ambiguous retirement)
    return "crash"


def init_elo_tables(db_path: Path) -> None:
    """Create race_entries and qualifying_entries tables if they do not exist.

    Safe to call on an existing DB that already has a session_stats table —
    uses CREATE TABLE IF NOT EXISTS for both tables. Creates parent directories.

    Args:
        db_path: Path to the DuckDB database file.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(_CREATE_RACE_ENTRIES_SQL)
        con.execute(_CREATE_QUALIFYING_ENTRIES_SQL)
    finally:
        con.close()


def upsert_race_entries(db_path: Path, records: list[RaceEntry]) -> None:
    """Insert or replace race entry rows keyed on (year, round, session_type, driver_id).

    The database must already be initialised via :func:`init_elo_tables` before
    calling this function; the race_entries table must exist.

    Args:
        db_path: Path to the DuckDB database file.
        records: List of RaceEntry dicts with keys matching the schema.
    """
    if not records:
        return
    rows = [[r.get(col) for col in _RACE_COLUMNS] for r in records]
    con = duckdb.connect(str(db_path))
    try:
        con.executemany(_UPSERT_RACE_ENTRY_SQL, rows)
    finally:
        con.close()


def upsert_qualifying_entries(db_path: Path, records: list[QualifyingEntry]) -> None:
    """Insert or replace qualifying entry rows keyed on (year, round, driver_id).

    The database must already be initialised via :func:`init_elo_tables` before
    calling this function; the qualifying_entries table must exist.

    Args:
        db_path: Path to the DuckDB database file.
        records: List of QualifyingEntry dicts with keys matching the schema.
    """
    if not records:
        return
    rows = [[r.get(col) for col in _QUALIFYING_COLUMNS] for r in records]
    con = duckdb.connect(str(db_path))
    try:
        con.executemany(_UPSERT_QUALIFYING_ENTRY_SQL, rows)
    finally:
        con.close()


def get_race_entries(db_path: Path, year: int) -> list[RaceEntry] | None:
    """Fetch all race entries for a season ordered by round then driver.

    Args:
        db_path: Path to the DuckDB database file.
        year: The F1 season year to query.

    Returns:
        List of RaceEntry dicts, or None if the database does not exist or no
        rows are found for the given year.
    """
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path), read_only=True)
    try:
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


def get_qualifying_entries(db_path: Path, year: int) -> list[QualifyingEntry] | None:
    """Fetch all qualifying entries for a season ordered by round then driver.

    Args:
        db_path: Path to the DuckDB database file.
        year: The F1 season year to query.

    Returns:
        List of QualifyingEntry dicts, or None if the database does not exist
        or no rows are found for the given year.
    """
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path), read_only=True)
    try:
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


__all__ = [
    "RaceEntry",
    "QualifyingEntry",
    "categorize_dnf",
    "get_db_path",
    "init_elo_tables",
    "upsert_race_entries",
    "upsert_qualifying_entries",
    "get_race_entries",
    "get_qualifying_entries",
]
