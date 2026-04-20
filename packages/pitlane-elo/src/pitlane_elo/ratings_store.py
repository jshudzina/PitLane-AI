"""Persistence layer for ELO ratings: snapshots and model-state checkpoints.

Owns every DuckDB interaction previously tangled inside ``snapshots.py``:
schema DDL, snapshot-row upserts, post-race model-state checkpoints, and the
checkpoint-discovery queries used to drive incremental adds.

Callers pass an open connection and a retention policy; the store neither
opens nor closes the connection. ``load_checkpoint`` returns a
:class:`ModelState` so model hydration stays explicit — no method here
mutates a model.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, NamedTuple

import duckdb

from pitlane_elo.data import RACE_COLS, RaceEntry, order_race_entries

if TYPE_CHECKING:
    from pitlane_elo.ratings.endure_elo import EndureElo

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

_UPSERT_SNAPSHOT_SQL = """
INSERT OR REPLACE INTO elo_snapshots
    (year, round, session_type, driver_id, pre_race_rating, pre_race_k,
     win_probability, podium_probability, finish_position, dnf_category, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
"""

_CREATE_MODEL_STATE_SQL = """
CREATE TABLE IF NOT EXISTS elo_model_state (
    year         INTEGER NOT NULL,
    round        INTEGER NOT NULL,
    session_type VARCHAR NOT NULL,
    driver_id    VARCHAR NOT NULL,
    rating       DOUBLE  NOT NULL,
    k_factor     DOUBLE  NOT NULL,
    PRIMARY KEY (year, round, session_type, driver_id)
)
"""

_CREATE_MODEL_STATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_elo_model_state_race
    ON elo_model_state (year, round, session_type)
"""

_UPSERT_STATE_SQL = """
INSERT OR REPLACE INTO elo_model_state
    (year, round, session_type, driver_id, rating, k_factor)
VALUES (?, ?, ?, ?, ?, ?)
"""


# ---------------------------------------------------------------------------
# Typed record shapes
# ---------------------------------------------------------------------------


class Checkpoint(NamedTuple):
    """Identifier for a persisted model-state checkpoint."""

    year: int
    round: int
    session_type: str


class RaceKey(NamedTuple):
    """Primary key fragment identifying a single race within a session type."""

    year: int
    round: int


class ModelState(NamedTuple):
    """Per-driver ratings and k-factors loaded from a checkpoint."""

    ratings: dict[str, float]
    k_factors: dict[str, float]


class SnapshotRow(NamedTuple):
    """One row destined for ``elo_snapshots``. Field order matches the INSERT.

    Declared as a NamedTuple so ``executemany`` treats instances as positional
    parameter tuples while callers get named-field access.
    """

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


class RatingsStore:
    """DuckDB-backed store for ELO snapshot rows and model-state checkpoints."""

    def __init__(self, con: duckdb.DuckDBPyConnection, *, retention_years: int) -> None:
        self.con = con
        self.retention_years = retention_years

    # ----- schema ---------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create tables and indexes if they do not exist. Idempotent."""
        self.con.execute(_CREATE_TABLE_SQL)
        with contextlib.suppress(duckdb.CatalogException):
            self.con.execute(_ADD_PODIUM_COL_SQL)
        self.con.execute(_CREATE_DRIVER_INDEX_SQL)
        self.con.execute(_CREATE_RACE_INDEX_SQL)
        self.con.execute(_CREATE_MODEL_STATE_SQL)
        self.con.execute(_CREATE_MODEL_STATE_INDEX_SQL)

    # ----- active driver pruning ------------------------------------------

    def active_driver_ids(self, year: int, session_type: str) -> set[str]:
        """Driver IDs with at least one entry within ``retention_years`` of ``year``."""
        cursor = self.con.execute(
            "SELECT DISTINCT driver_id FROM race_entries WHERE session_type = ? AND year >= ? AND year <= ?",
            [session_type, year - self.retention_years, year],
        )
        return {row[0] for row in cursor.fetchall()}

    # ----- model-state checkpoints ----------------------------------------

    def save_checkpoint(
        self,
        model: EndureElo,
        year: int,
        round_num: int,
        session_type: str,
        *,
        active_driver_ids: set[str] | None = None,
    ) -> None:
        """Persist (rating, k_factor) for each currently-known driver.

        When ``active_driver_ids`` is supplied, drivers outside that set are
        pruned from the checkpoint so the table does not grow unboundedly.
        """
        rows: list[tuple[int, int, str, str, float, float]] = [
            (year, round_num, session_type, driver_id, rating, model.k_factors[driver_id])
            for driver_id, rating in model.ratings.items()
            if active_driver_ids is None or driver_id in active_driver_ids
        ]
        self.con.executemany(_UPSERT_STATE_SQL, rows)

    def load_checkpoint(
        self,
        year: int,
        round_num: int,
        session_type: str,
    ) -> ModelState:
        """Return ``ModelState`` saved after the given race (empty if missing)."""
        cursor = self.con.execute(
            "SELECT driver_id, rating, k_factor FROM elo_model_state WHERE year = ? AND round = ? AND session_type = ?",
            [year, round_num, session_type],
        )
        ratings: dict[str, float] = {}
        k_factors: dict[str, float] = {}
        for driver_id, rating, k_factor in cursor.fetchall():
            ratings[driver_id] = rating
            k_factors[driver_id] = k_factor
        return ModelState(ratings=ratings, k_factors=k_factors)

    def latest_checkpoint(self, session_type: str) -> Checkpoint | None:
        """Most recently persisted checkpoint for the session type, or None."""
        try:
            cursor = self.con.execute(
                "SELECT year, round, session_type FROM elo_model_state "
                "WHERE session_type = ? "
                "ORDER BY year DESC, round DESC LIMIT 1",
                [session_type],
            )
        except duckdb.CatalogException:
            return None
        row = cursor.fetchone()
        if row is None:
            return None
        return Checkpoint(year=row[0], round=row[1], session_type=row[2])

    def checkpoint_before(
        self,
        year: int,
        round_num: int,
        session_type: str,
    ) -> Checkpoint | None:
        """Most recent checkpoint strictly before ``(year, round_num)``, or None."""
        try:
            cursor = self.con.execute(
                "SELECT year, round, session_type FROM elo_model_state "
                "WHERE session_type = ? "
                "  AND (year < ? OR (year = ? AND round < ?)) "
                "ORDER BY year DESC, round DESC LIMIT 1",
                [session_type, year, year, round_num],
            )
        except duckdb.CatalogException:
            return None
        row = cursor.fetchone()
        if row is None:
            return None
        return Checkpoint(year=row[0], round=row[1], session_type=row[2])

    def gap_races_between(
        self,
        cp_year: int,
        cp_round: int,
        target_year: int,
        target_round: int,
        session_type: str,
    ) -> list[RaceKey]:
        """``RaceKey`` values in race_entries strictly between checkpoint and target."""
        cursor = self.con.execute(
            "SELECT DISTINCT year, round FROM race_entries "
            "WHERE session_type = ? "
            "  AND (year > ? OR (year = ? AND round > ?)) "
            "  AND (year < ? OR (year = ? AND round < ?)) "
            "ORDER BY year, round",
            [session_type, cp_year, cp_year, cp_round, target_year, target_year, target_round],
        )
        return [RaceKey(year=r[0], round=r[1]) for r in cursor.fetchall()]

    # ----- snapshot rows --------------------------------------------------

    def write_snapshot_rows(self, rows: list[SnapshotRow]) -> None:
        """Upsert a batch of snapshot rows. Safe to call with an empty list."""
        if not rows:
            return
        self.con.executemany(_UPSERT_SNAPSHOT_SQL, rows)

    # ----- race-entries read ----------------------------------------------

    def read_race_entries(
        self,
        year: int,
        round_num: int,
        session_type: str,
    ) -> list[RaceEntry]:
        """Load a single race's entries, ordered by finishing position."""
        cursor = self.con.execute(
            f"SELECT {RACE_COLS} FROM race_entries "
            "WHERE year = ? AND round = ? AND session_type = ? "
            "ORDER BY driver_id",
            [year, round_num, session_type],
        )
        entry_rows = cursor.fetchall()
        if not entry_rows:
            return []
        columns = [desc[0] for desc in cursor.description]
        entries: list[RaceEntry] = [
            dict(zip(columns, row, strict=True))  # type: ignore[misc]
            for row in entry_rows
        ]
        return order_race_entries(entries)

    def pending_races_after_checkpoint(
        self,
        cp_year: int,
        cp_round: int,
        session_type: str,
    ) -> list[RaceKey]:
        """``RaceKey`` values in race_entries after the given checkpoint."""
        cursor = self.con.execute(
            "SELECT DISTINCT year, round FROM race_entries "
            "WHERE session_type = ? "
            "  AND (year > ? OR (year = ? AND round > ?)) "
            "ORDER BY year, round",
            [session_type, cp_year, cp_year, cp_round],
        )
        return [RaceKey(year=r[0], round=r[1]) for r in cursor.fetchall()]


__all__ = [
    "Checkpoint",
    "ModelState",
    "RaceKey",
    "RatingsStore",
    "SnapshotRow",
]
