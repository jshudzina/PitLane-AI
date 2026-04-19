"""ELO snapshot persistence: pre-race ratings, win/podium probabilities, and actual results.

Captures the state of the EndureElo model immediately before each race update
and stores it to a DuckDB table (elo_snapshots). This allows querying predicted
win/podium probabilities and comparing them to actual results without re-running
from 1970 each time.

Schema: elo_snapshots(year, round, session_type, driver_id, pre_race_rating,
                       pre_race_k, win_probability, podium_probability,
                       finish_position, dnf_category, created_at)
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from pitlane_elo.config import ENDURE_ELO_CALIBRATED
from pitlane_elo.data import get_db_path, get_race_entries_range, group_entries_by_race
from pitlane_elo.ratings.endure_elo import EndureElo

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class EloSnapshot:
    """Pre-race model state and actual result for one driver in one race."""

    year: int
    round: int
    session_type: str
    driver_id: str
    pre_race_rating: float
    pre_race_k: float
    win_probability: float
    podium_probability: float
    finish_position: int | None
    dnf_category: str


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS elo_snapshots (
    year               INTEGER   NOT NULL,
    round              INTEGER   NOT NULL,
    session_type       VARCHAR   NOT NULL,
    driver_id          VARCHAR   NOT NULL,
    pre_race_rating    DOUBLE    NOT NULL,
    pre_race_k         DOUBLE    NOT NULL,
    win_probability    DOUBLE    NOT NULL,
    podium_probability DOUBLE    NOT NULL DEFAULT 0.0,
    finish_position    INTEGER,
    dnf_category       VARCHAR   NOT NULL DEFAULT 'none',
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (year, round, session_type, driver_id)
)
"""

_ADD_PODIUM_COL_SQL = """
ALTER TABLE elo_snapshots
    ADD COLUMN podium_probability DOUBLE DEFAULT 0.0
"""

_CREATE_DRIVER_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_elo_snapshots_driver
    ON elo_snapshots (driver_id, year, round)
"""

_CREATE_RACE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_elo_snapshots_race
    ON elo_snapshots (year, round, session_type)
"""

_UPSERT_SQL = """
INSERT OR REPLACE INTO elo_snapshots
    (year, round, session_type, driver_id, pre_race_rating, pre_race_k,
     win_probability, podium_probability, finish_position, dnf_category, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
"""

# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create elo_snapshots table and indexes if they do not exist. Idempotent."""
    con.execute(_CREATE_TABLE_SQL)
    with contextlib.suppress(Exception):
        con.execute(_ADD_PODIUM_COL_SQL)
    con.execute(_CREATE_DRIVER_INDEX_SQL)
    con.execute(_CREATE_RACE_INDEX_SQL)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def build_snapshots(
    start_year: int = 1970,
    end_year: int = 2026,
    *,
    db_path: Path | None = None,
    session_type: str = "R",
) -> int:
    """Compute and persist ELO snapshots for every race in [start_year, end_year].

    Runs the calibrated EndureElo model in a predict-then-update loop.  For each
    race, captures the pre-race ratings and win probabilities *before* calling
    process_race(), then upserts a row per driver into elo_snapshots.

    Always re-runs from start_year because ELO ratings at race N depend on all
    prior races. A full 1970–2026 run completes in ~3–5 seconds.  The upsert is
    idempotent: running twice produces the same row count.

    Args:
        start_year: First season to process (used as warm-up + snapshot start).
        end_year: Last season (inclusive).
        db_path: Override the database path. Defaults to :func:`~pitlane_elo.data.get_db_path`.
        session_type: Session type to process ("R" for race, "S" for sprint).

    Returns:
        Number of snapshot rows written.
    """
    path = db_path or get_db_path()

    all_entries = get_race_entries_range(start_year, end_year, db_path=path)
    if not all_entries:
        return 0

    filtered = [e for e in all_entries if e["session_type"] == session_type]
    if not filtered:
        return 0

    races = group_entries_by_race(filtered)
    model = EndureElo(ENDURE_ELO_CALIBRATED)

    rows: list[tuple] = []
    current_year: int | None = None

    for race_entries in races:
        year = race_entries[0]["year"]
        rnd = race_entries[0]["round"]

        # Season boundary: apply inter-season decay
        if current_year is not None and year != current_year:
            model.apply_season_decay(year)
        current_year = year

        driver_ids = [e["driver_id"] for e in race_entries]

        # Initialize all drivers so ratings/k_factors are populated before snapshot.
        # get_rating() sets initial_rating and k_max for unseen drivers.
        for d in driver_ids:
            model.get_rating(d)

        # Capture pre-race state (BEFORE predict or update)
        pre_ratings = {d: model.ratings[d] for d in driver_ids}
        pre_ks = {d: model.k_factors[d] for d in driver_ids}

        # Predict win and podium probabilities before updating
        probs = model.predict_win_probabilities(driver_ids)
        prob_map = dict(zip(driver_ids, probs, strict=True))
        podium_probs = model.predict_podium_probabilities(driver_ids)
        podium_map = dict(zip(driver_ids, podium_probs, strict=True))

        # Actual results from the ordered race entries
        finish_map = {e["driver_id"]: e.get("finish_position") for e in race_entries}
        dnf_map = {e["driver_id"]: e.get("dnf_category") or "none" for e in race_entries}

        for driver_id in driver_ids:
            rows.append(
                (
                    year,
                    rnd,
                    session_type,
                    driver_id,
                    pre_ratings[driver_id],
                    pre_ks[driver_id],
                    float(prob_map[driver_id]),
                    float(podium_map[driver_id]),
                    finish_map.get(driver_id),
                    dnf_map.get(driver_id, "none"),
                )
            )

        # Update ratings AFTER snapshot
        model.process_race(race_entries)

    # Bulk upsert
    con = duckdb.connect(str(path))
    try:
        ensure_schema(con)
        con.executemany(_UPSERT_SQL, rows)
        con.commit()
    finally:
        con.close()

    return len(rows)


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

_SNAPSHOT_COLS = (
    "year, round, session_type, driver_id, pre_race_rating, pre_race_k, "
    "win_probability, podium_probability, finish_position, dnf_category"
)


def _rows_to_snapshots(rows: list[tuple], columns: list[str]) -> list[EloSnapshot]:
    result = []
    for row in rows:
        d = dict(zip(columns, row, strict=True))
        result.append(
            EloSnapshot(
                year=d["year"],
                round=d["round"],
                session_type=d["session_type"],
                driver_id=d["driver_id"],
                pre_race_rating=d["pre_race_rating"],
                pre_race_k=d["pre_race_k"],
                win_probability=d["win_probability"],
                podium_probability=d["podium_probability"],
                finish_position=d["finish_position"],
                dnf_category=d["dnf_category"],
            )
        )
    return result


def get_race_snapshot(
    year: int,
    round: int,
    *,
    session_type: str = "R",
    db_path: Path | None = None,
) -> list[EloSnapshot]:
    """Return all driver snapshots for one race, sorted by win_probability DESC.

    Args:
        year: Season year.
        round: Race round number.
        session_type: "R" for race, "S" for sprint.
        db_path: Override the database path.

    Returns:
        List of EloSnapshot objects, or empty list if no data found.
    """
    path = db_path or get_db_path()
    if not path.exists():
        return []

    sql = (
        f"SELECT {_SNAPSHOT_COLS} FROM elo_snapshots "
        "WHERE year = ? AND round = ? AND session_type = ? "
        "ORDER BY win_probability DESC"
    )
    with duckdb.connect(str(path), read_only=True) as con:
        try:
            cursor = con.execute(sql, [year, round, session_type])
        except duckdb.CatalogException:
            # Table doesn't exist yet — user hasn't run snapshot command
            return []
        rows = cursor.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cursor.description]
    return _rows_to_snapshots(rows, columns)


def get_driver_rating_history(
    driver_id: str,
    *,
    start_year: int = 1970,
    end_year: int = 2026,
    session_type: str = "R",
    db_path: Path | None = None,
) -> list[EloSnapshot]:
    """Return all snapshot rows for one driver in chronological order.

    Args:
        driver_id: Ergast driver ID slug (e.g. "max_verstappen").
        start_year: First season to include.
        end_year: Last season (inclusive).
        session_type: "R" for race, "S" for sprint.
        db_path: Override the database path.

    Returns:
        List of EloSnapshot objects in ascending (year, round) order,
        or empty list if no data found.
    """
    path = db_path or get_db_path()
    if not path.exists():
        return []

    sql = (
        f"SELECT {_SNAPSHOT_COLS} FROM elo_snapshots "
        "WHERE driver_id = ? AND year BETWEEN ? AND ? AND session_type = ? "
        "ORDER BY year ASC, round ASC"
    )
    with duckdb.connect(str(path), read_only=True) as con:
        try:
            cursor = con.execute(sql, [driver_id, start_year, end_year, session_type])
        except duckdb.CatalogException:
            return []
        rows = cursor.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cursor.description]
    return _rows_to_snapshots(rows, columns)


__all__ = [
    "EloSnapshot",
    "ensure_schema",
    "build_snapshots",
    "get_race_snapshot",
    "get_driver_rating_history",
]
