"""ELO snapshot persistence: pre-race ratings, win/podium probabilities, and actual results.

Captures the state of the EndureElo model immediately before each race update
and stores it to a DuckDB table (elo_snapshots). This allows querying predicted
win/podium probabilities and comparing them to actual results without re-running
from 1970 each time.

Schema: elo_snapshots(year, round, session_type, driver_id, pre_race_rating,
                       pre_race_k, win_probability, podium_probability,
                       finish_position, dnf_category, created_at)

Schema: elo_model_state(year, round, session_type, driver_id, rating, k_factor)
        Full post-race model state enabling incremental snapshot additions.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from pitlane_elo.config import ENDURE_ELO_CALIBRATED
from pitlane_elo.data import (
    _RACE_COLS,
    RaceEntry,
    get_db_path,
    get_race_entries_range,
    group_entries_by_race,
    order_race_entries,
)
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
# Schema management
# ---------------------------------------------------------------------------


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create elo_snapshots and elo_model_state tables/indexes if they do not exist. Idempotent."""
    con.execute(_CREATE_TABLE_SQL)
    with contextlib.suppress(duckdb.CatalogException):
        con.execute(_ADD_PODIUM_COL_SQL)
    con.execute(_CREATE_DRIVER_INDEX_SQL)
    con.execute(_CREATE_RACE_INDEX_SQL)
    con.execute(_CREATE_MODEL_STATE_SQL)
    con.execute(_CREATE_MODEL_STATE_INDEX_SQL)


# ---------------------------------------------------------------------------
# Model-state helpers
# ---------------------------------------------------------------------------


def _save_model_state(
    con: duckdb.DuckDBPyConnection,
    model: EndureElo,
    year: int,
    round_num: int,
    session_type: str,
) -> None:
    """Persist the full model state (all drivers) after processing a race."""
    rows = [
        (year, round_num, session_type, driver_id, rating, model.k_factors[driver_id])
        for driver_id, rating in model.ratings.items()
    ]
    con.executemany(_UPSERT_STATE_SQL, rows)


def _load_model_state(
    con: duckdb.DuckDBPyConnection,
    year: int,
    round_num: int,
    session_type: str,
) -> tuple[dict[str, float], dict[str, float]]:
    """Load (ratings, k_factors) saved after the given race. Returns empty dicts if not found."""
    cursor = con.execute(
        "SELECT driver_id, rating, k_factor FROM elo_model_state WHERE year = ? AND round = ? AND session_type = ?",
        [year, round_num, session_type],
    )
    rows = cursor.fetchall()
    ratings: dict[str, float] = {}
    k_factors: dict[str, float] = {}
    for driver_id, rating, k_factor in rows:
        ratings[driver_id] = rating
        k_factors[driver_id] = k_factor
    return ratings, k_factors


def _latest_checkpoint(
    con: duckdb.DuckDBPyConnection,
    session_type: str,
) -> tuple[int, int, str] | None:
    """Return (year, round, session_type) of the most recently persisted model state, or None."""
    try:
        cursor = con.execute(
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
    return (row[0], row[1], row[2])


def _checkpoint_before(
    con: duckdb.DuckDBPyConnection,
    year: int,
    round_num: int,
    session_type: str,
) -> tuple[int, int, str] | None:
    """Return the most recent checkpoint STRICTLY before (year, round_num), or None."""
    try:
        cursor = con.execute(
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
    return (row[0], row[1], row[2])


def _gap_races_between(
    con: duckdb.DuckDBPyConnection,
    cp_year: int,
    cp_round: int,
    target_year: int,
    target_round: int,
    session_type: str,
) -> list[tuple[int, int]]:
    """Return (year, round) pairs in race_entries that fall between checkpoint and target (exclusive).

    Uses race_entries as the source of truth — cancelled rounds that have no
    entries are not returned, so they never block incremental adds.
    """
    cursor = con.execute(
        "SELECT DISTINCT year, round FROM race_entries "
        "WHERE session_type = ? "
        "  AND (year > ? OR (year = ? AND round > ?)) "
        "  AND (year < ? OR (year = ? AND round < ?)) "
        "ORDER BY year, round",
        [session_type, cp_year, cp_year, cp_round, target_year, target_year, target_round],
    )
    return [(r[0], r[1]) for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Core single-race processing (shared between build, add, and catchup)
# ---------------------------------------------------------------------------


def _process_race(
    model: EndureElo,
    race_entries: list[RaceEntry],
    session_type: str,
    *,
    current_year: int | None,
) -> tuple[list[tuple], int]:
    """Predict + update for one race. Returns (snapshot_rows, race_year).

    Applies season decay when the race crosses a year boundary from current_year.
    Does NOT write to the database — caller is responsible for persistence.
    """
    year = race_entries[0]["year"]
    rnd = race_entries[0]["round"]

    if current_year is not None and year != current_year:
        model.apply_season_decay(year)

    driver_ids = [e["driver_id"] for e in race_entries]

    for d in driver_ids:
        model.get_rating(d)

    pre_ratings = {d: model.ratings[d] for d in driver_ids}
    pre_ks = {d: model.k_factors[d] for d in driver_ids}

    probs = model.predict_win_probabilities(driver_ids)
    prob_map = dict(zip(driver_ids, probs, strict=True))
    podium_probs = model.predict_podium_probabilities(driver_ids)
    podium_map = dict(zip(driver_ids, podium_probs, strict=True))

    finish_map = {e["driver_id"]: e.get("finish_position") for e in race_entries}
    dnf_map = {e["driver_id"]: e.get("dnf_category") or "none" for e in race_entries}

    rows: list[tuple] = []
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

    model.process_race(race_entries)
    return rows, year


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

    Also persists the full model state after each race into elo_model_state,
    enabling incremental single-race additions via add_race_snapshot().

    Always re-runs from start_year because ELO ratings at race N depend on all
    prior races. The upsert is idempotent: running twice produces the same row count.

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

    snapshot_rows: list[tuple] = []
    state_rows: list[tuple] = []
    current_year: int | None = None

    with duckdb.connect(str(path)) as con:
        ensure_schema(con)

        for race_entries in races:
            rows, race_year = _process_race(model, race_entries, session_type, current_year=current_year)
            snapshot_rows.extend(rows)
            current_year = race_year

            rnd = race_entries[0]["round"]
            for driver_id, rating in model.ratings.items():
                state_rows.append((race_year, rnd, session_type, driver_id, rating, model.k_factors[driver_id]))

        con.executemany(_UPSERT_SQL, snapshot_rows)
        con.executemany(_UPSERT_STATE_SQL, state_rows)
        con.commit()

    return len(snapshot_rows)


def add_race_snapshot(
    year: int,
    round_num: int,
    *,
    session_type: str = "R",
    db_path: Path | None = None,
) -> int:
    """Incrementally add one race to the snapshot without re-running history.

    Loads the model state saved after the most recent prior race, predicts
    probabilities, updates ratings, and persists both the snapshot rows and
    the updated model state.

    Requires elo_model_state to contain a checkpoint immediately before
    (year, round_num). Raises click.ClickException with actionable guidance
    when the prerequisite state is missing.

    Cancelled races — rounds that have no rows in race_entries — are silently
    skipped when checking for gaps, so adding a race after cancellations works
    without any special flags.

    Args:
        year: Season year of the race to add.
        round_num: Round number of the race to add.
        session_type: Session type ("R" or "S").
        db_path: Override the database path.

    Returns:
        Number of snapshot rows written (one per driver).

    Raises:
        click.ClickException: If prerequisites are not met.
    """
    import click

    path = db_path or get_db_path()

    with duckdb.connect(str(path)) as con:
        ensure_schema(con)

        # Check prerequisites before touching race_entries
        latest = _latest_checkpoint(con, session_type)
        if latest is None:
            raise click.ClickException(
                f"No model state found for session_type={session_type!r}. "
                "Run `pitlane-elo snapshot` first to build the initial state."
            )

        latest_year, latest_round, _ = latest

        # Reject adding a race that is strictly before the latest checkpoint (backwards add)
        if (year, round_num) < (latest_year, latest_round):
            raise click.ClickException(
                f"{year} R{round_num} is before the latest checkpoint "
                f"({latest_year} R{latest_round}). "
                "Use `pitlane-elo snapshot` to replay from scratch."
            )

        # For both a fresh forward add and an idempotent re-add of the latest race,
        # replay from the checkpoint strictly BEFORE the target race.
        prior = _checkpoint_before(con, year, round_num, session_type)
        if prior is None:
            # Target is the very first race ever processed; replay from empty state
            cp_year: int | None = None
            cp_round: int | None = None
        else:
            cp_year, cp_round, _ = prior

        # Reject skipping real (non-cancelled) races between prior checkpoint and target
        if cp_year is not None and cp_round is not None:
            gaps = _gap_races_between(con, cp_year, cp_round, year, round_num, session_type)
            if gaps:
                gap_str = ", ".join(f"{y} R{r}" for y, r in gaps)
                raise click.ClickException(
                    f"Cannot add {year} R{round_num}: unprocessed races exist before it: {gap_str}. "
                    "Add them in order or run `pitlane-elo snapshot-catchup`."
                )

        # Load race entries for the target race
        try:
            cursor = con.execute(
                f"SELECT {_RACE_COLS} FROM race_entries "
                "WHERE year = ? AND round = ? AND session_type = ? "
                "ORDER BY driver_id",
                [year, round_num, session_type],
            )
            entry_rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        except duckdb.CatalogException as err:
            raise click.ClickException("race_entries table not found. Check your database path.") from err

        if not entry_rows:
            raise click.ClickException(
                f"No race entries found for {year} R{round_num} ({session_type}). "
                "Verify the race exists in race_entries."
            )

        race_entries: list[RaceEntry] = [
            dict(zip(columns, row, strict=True))
            for row in entry_rows  # type: ignore[misc]
        ]
        race_entries = order_race_entries(race_entries)

        # Hydrate model from the prior checkpoint (or start empty for the very first race)
        model = EndureElo(ENDURE_ELO_CALIBRATED)
        if cp_year is not None and cp_round is not None:
            ratings, k_factors = _load_model_state(con, cp_year, cp_round, session_type)
            model.ratings = ratings
            model.k_factors = k_factors

        # Process the race
        snapshot_rows, _ = _process_race(model, race_entries, session_type, current_year=cp_year)

        # Persist results
        con.executemany(_UPSERT_SQL, snapshot_rows)
        _save_model_state(con, model, year, round_num, session_type)
        con.commit()

    return len(snapshot_rows)


def catchup_snapshots(
    *,
    session_type: str = "R",
    db_path: Path | None = None,
) -> int:
    """Add every race in race_entries that has no model-state checkpoint yet.

    Finds the latest checkpoint in elo_model_state, then processes all
    subsequent races in race_entries in chronological order. Cancelled
    rounds (no entries in race_entries) are naturally skipped.

    Requires at least one prior checkpoint (i.e. `pitlane-elo snapshot` must
    have been run at least once).

    Args:
        session_type: Session type ("R" or "S").
        db_path: Override the database path.

    Returns:
        Total number of snapshot rows written across all newly added races.

    Raises:
        click.ClickException: If no prior checkpoint exists.
    """
    import click

    path = db_path or get_db_path()
    total_rows = 0

    with duckdb.connect(str(path)) as con:
        ensure_schema(con)

        checkpoint = _latest_checkpoint(con, session_type)
        if checkpoint is None:
            raise click.ClickException(
                f"No model state found for session_type={session_type!r}. "
                "Run `pitlane-elo snapshot` first to build the initial state."
            )

        cp_year, cp_round, _ = checkpoint

        # Find all races in race_entries beyond the checkpoint
        try:
            cursor = con.execute(
                "SELECT DISTINCT year, round FROM race_entries "
                "WHERE session_type = ? "
                "  AND (year > ? OR (year = ? AND round > ?)) "
                "ORDER BY year, round",
                [session_type, cp_year, cp_year, cp_round],
            )
            pending = cursor.fetchall()
        except duckdb.CatalogException as err:
            raise click.ClickException("race_entries table not found. Check your database path.") from err

        if not pending:
            return 0

        # Load model from checkpoint once, then process races sequentially
        ratings, k_factors = _load_model_state(con, cp_year, cp_round, session_type)
        model = EndureElo(ENDURE_ELO_CALIBRATED)
        model.ratings = ratings
        model.k_factors = k_factors

        current_year: int = cp_year

        for race_year, race_round in pending:
            cursor = con.execute(
                f"SELECT {_RACE_COLS} FROM race_entries "
                "WHERE year = ? AND round = ? AND session_type = ? ORDER BY driver_id",
                [race_year, race_round, session_type],
            )
            entry_rows = cursor.fetchall()
            if not entry_rows:
                continue
            columns = [desc[0] for desc in cursor.description]
            race_entries: list[RaceEntry] = [
                dict(zip(columns, row, strict=True))
                for row in entry_rows  # type: ignore[misc]
            ]
            race_entries = order_race_entries(race_entries)

            snapshot_rows, current_year = _process_race(model, race_entries, session_type, current_year=current_year)
            con.executemany(_UPSERT_SQL, snapshot_rows)
            _save_model_state(con, model, race_year, race_round, session_type)
            total_rows += len(snapshot_rows)

        con.commit()

    return total_rows


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
    round_num: int,
    *,
    session_type: str = "R",
    db_path: Path | None = None,
) -> list[EloSnapshot]:
    """Return all driver snapshots for one race, sorted by win_probability DESC.

    Args:
        year: Season year.
        round_num: Race round number.
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
            cursor = con.execute(sql, [year, round_num, session_type])
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
    "add_race_snapshot",
    "catchup_snapshots",
    "get_race_snapshot",
    "get_driver_rating_history",
]
