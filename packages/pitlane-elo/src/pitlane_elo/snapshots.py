"""ELO snapshot orchestration: pre-race ratings, win/podium probabilities, and actual results.

Captures the state of the EndureElo model immediately before each race update
and stores it to ``elo_snapshots``. Persistence lives in :class:`RatingsStore`;
this module owns only the predict/update orchestration and the read helpers
used by the CLI.

Snapshots are computed only for drivers who **started** the race — i.e. those
with a non-null ``grid_position``. DNS entries are excluded from the win and
podium probability inputs (they still flow to ``model.process_race`` where
``_filter_entries`` handles mechanical DNFs for rating updates).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import click
import duckdb

from pitlane_elo.config import ENDURE_ELO_CALIBRATED
from pitlane_elo.data import (
    RaceEntry,
    get_db_path,
    get_race_entries_range,
    group_entries_by_race,
)
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings_store import RatingsStore

# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------

DEFAULT_STATE_RETENTION_YEARS = 5
"""Drivers with no race_entries within this many years of the checkpoint are
pruned from elo_model_state. Safe for endure-elo because initial_rating=0 and
ratings decay geometrically toward 0, so re-initialization on return is
equivalent to keeping the decayed value."""

_RETENTION_ENV_VAR = "PITLANE_STATE_RETENTION_YEARS"


def _resolve_retention_years(override: int | None) -> int:
    """Explicit arg wins; otherwise env var; otherwise default."""
    if override is not None:
        return override
    env = os.environ.get(_RETENTION_ENV_VAR, "").strip()
    if env:
        return int(env)
    return DEFAULT_STATE_RETENTION_YEARS


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
# Schema management (thin wrapper kept for backward compatibility)
# ---------------------------------------------------------------------------


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create elo_snapshots and elo_model_state tables/indexes. Idempotent."""
    RatingsStore(con, retention_years=DEFAULT_STATE_RETENTION_YEARS).ensure_schema()


# ---------------------------------------------------------------------------
# Core single-race processing
# ---------------------------------------------------------------------------


def _starters(entries: list[RaceEntry]) -> list[RaceEntry]:
    """Entries with a non-null grid_position (drivers who started the race)."""
    return [e for e in entries if e.get("grid_position") is not None]


def predict_snapshot_rows(
    model: EndureElo,
    race_entries: list[RaceEntry],
    session_type: str,
    *,
    current_year: int | None,
) -> tuple[list[tuple], int]:
    """Compute pre-race snapshot rows for one race. Does not update the model.

    Applies season decay when the race crosses a year boundary from
    ``current_year``. Only starters (``grid_position is not None``) are fed to
    ``predict_win_probabilities`` / ``predict_podium_probabilities`` and only
    starters produce snapshot rows. Returns ``([], race_year)`` when fewer
    than two starters are present.
    """
    year = race_entries[0]["year"]

    if current_year is not None and year != current_year:
        model.apply_season_decay(year)

    starters = _starters(race_entries)
    if len(starters) < 2:
        return [], year

    rnd = starters[0]["round"]
    driver_ids = [e["driver_id"] for e in starters]

    for d in driver_ids:
        model.get_rating(d)

    pre_ratings = {d: model.ratings[d] for d in driver_ids}
    pre_ks = {d: model.k_factors[d] for d in driver_ids}

    probs = model.predict_win_probabilities(driver_ids)
    prob_map = dict(zip(driver_ids, probs, strict=True))
    podium_probs = model.predict_podium_probabilities(driver_ids)
    podium_map = dict(zip(driver_ids, podium_probs, strict=True))

    finish_map = {e["driver_id"]: e.get("finish_position") for e in starters}
    dnf_map = {e["driver_id"]: e.get("dnf_category") or "none" for e in starters}

    rows: list[tuple] = [
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
        for driver_id in driver_ids
    ]
    return rows, year


def _race_year_round(race_entries: list[RaceEntry]) -> tuple[int, int]:
    return race_entries[0]["year"], race_entries[0]["round"]


# ---------------------------------------------------------------------------
# Write orchestrators
# ---------------------------------------------------------------------------


def build_snapshots(
    start_year: int = 1970,
    end_year: int = 2026,
    *,
    db_path: Path | None = None,
    session_type: str = "R",
    retention_years: int | None = None,
) -> int:
    """Compute and persist ELO snapshots for every race in ``[start_year, end_year]``.

    Runs the calibrated EndureElo model in a predict-then-update loop. For each
    race captures the pre-race ratings and probabilities *before* updating, then
    upserts a row per starter into elo_snapshots. Post-race model state is
    persisted to elo_model_state, pruned by ``retention_years``.

    Always re-runs from ``start_year`` because ELO ratings at race N depend on
    all prior races. The upsert is idempotent.

    Args:
        start_year: First season to process (warm-up + snapshot start).
        end_year: Last season (inclusive).
        db_path: Override the database path.
        session_type: "R" (race) or "S" (sprint).
        retention_years: Years of history used to decide which drivers to keep
            in checkpoints. Defaults to the ``PITLANE_STATE_RETENTION_YEARS``
            env var, then :data:`DEFAULT_STATE_RETENTION_YEARS`.

    Returns:
        Number of snapshot rows written.
    """
    path = db_path or get_db_path()
    retention = _resolve_retention_years(retention_years)

    all_entries = get_race_entries_range(start_year, end_year, db_path=path)
    if not all_entries:
        return 0

    filtered = [e for e in all_entries if e["session_type"] == session_type]
    if not filtered:
        return 0

    races = group_entries_by_race(filtered)
    model = EndureElo(ENDURE_ELO_CALIBRATED)

    total_rows = 0
    current_year: int | None = None
    active_ids_cache: dict[int, set[str]] = {}

    with duckdb.connect(str(path)) as con:
        store = RatingsStore(con, retention_years=retention)
        store.ensure_schema()

        for race_entries in races:
            rows, race_year = predict_snapshot_rows(model, race_entries, session_type, current_year=current_year)
            current_year = race_year
            model.process_race(race_entries)

            _, rnd = _race_year_round(race_entries)
            if race_year not in active_ids_cache:
                active_ids_cache[race_year] = store.active_driver_ids(race_year, session_type)

            store.write_snapshot_rows(rows)
            store.save_checkpoint(
                model,
                race_year,
                rnd,
                session_type,
                active_driver_ids=active_ids_cache[race_year],
            )
            total_rows += len(rows)

        con.commit()

    return total_rows


def add_race_snapshot(
    year: int,
    round_num: int,
    *,
    session_type: str = "R",
    db_path: Path | None = None,
    retention_years: int | None = None,
) -> int:
    """Incrementally add one race to the snapshot without re-running history.

    Loads the model state saved after the most recent prior race, predicts
    probabilities, updates ratings, and persists both the snapshot rows and
    the updated model state.

    Cancelled races — rounds with no rows in race_entries — are silently
    skipped when checking for gaps.

    Raises:
        click.ClickException: If prerequisites are not met.
    """
    path = db_path or get_db_path()
    retention = _resolve_retention_years(retention_years)

    with duckdb.connect(str(path)) as con:
        store = RatingsStore(con, retention_years=retention)
        store.ensure_schema()

        latest = store.latest_checkpoint(session_type)
        if latest is None:
            raise click.ClickException(
                f"No model state found for session_type={session_type!r}. "
                "Run `pitlane-elo snapshot` first to build the initial state."
            )

        latest_year, latest_round, _ = latest
        if (year, round_num) < (latest_year, latest_round):
            raise click.ClickException(
                f"{year} R{round_num} is before the latest checkpoint "
                f"({latest_year} R{latest_round}). "
                "Use `pitlane-elo snapshot` to replay from scratch."
            )

        prior = store.checkpoint_before(year, round_num, session_type)
        if prior is None:
            cp_year: int | None = None
            cp_round: int | None = None
        else:
            cp_year, cp_round, _ = prior

        if cp_year is not None and cp_round is not None:
            gaps = store.gap_races_between(cp_year, cp_round, year, round_num, session_type)
            if gaps:
                gap_str = ", ".join(f"{y} R{r}" for y, r in gaps)
                raise click.ClickException(
                    f"Cannot add {year} R{round_num}: unprocessed races exist before it: "
                    f"{gap_str}. Add them in order or run `pitlane-elo snapshot-catchup`."
                )

        try:
            race_entries = store.read_race_entries(year, round_num, session_type)
        except duckdb.CatalogException as err:
            raise click.ClickException("race_entries table not found. Check your database path.") from err

        if not race_entries:
            raise click.ClickException(
                f"No race entries found for {year} R{round_num} ({session_type}). "
                "Verify the race exists in race_entries."
            )

        model = EndureElo(ENDURE_ELO_CALIBRATED)
        if cp_year is not None and cp_round is not None:
            ratings, k_factors = store.load_checkpoint(cp_year, cp_round, session_type)
            model.ratings = ratings
            model.k_factors = k_factors

        snapshot_rows, _ = predict_snapshot_rows(model, race_entries, session_type, current_year=cp_year)
        model.process_race(race_entries)

        active_ids = store.active_driver_ids(year, session_type)
        store.write_snapshot_rows(snapshot_rows)
        store.save_checkpoint(
            model,
            year,
            round_num,
            session_type,
            active_driver_ids=active_ids,
        )
        con.commit()

    return len(snapshot_rows)


def catchup_snapshots(
    *,
    session_type: str = "R",
    db_path: Path | None = None,
    retention_years: int | None = None,
) -> int:
    """Add every race in race_entries that has no model-state checkpoint yet.

    Finds the latest checkpoint in elo_model_state, then processes all
    subsequent races in chronological order. Cancelled rounds (no entries in
    race_entries) are naturally skipped.

    Raises:
        click.ClickException: If no prior checkpoint exists.
    """
    path = db_path or get_db_path()
    retention = _resolve_retention_years(retention_years)
    total_rows = 0

    with duckdb.connect(str(path)) as con:
        store = RatingsStore(con, retention_years=retention)
        store.ensure_schema()

        checkpoint = store.latest_checkpoint(session_type)
        if checkpoint is None:
            raise click.ClickException(
                f"No model state found for session_type={session_type!r}. "
                "Run `pitlane-elo snapshot` first to build the initial state."
            )

        cp_year, cp_round, _ = checkpoint

        try:
            pending = store.pending_races_after_checkpoint(cp_year, cp_round, session_type)
        except duckdb.CatalogException as err:
            raise click.ClickException("race_entries table not found. Check your database path.") from err

        if not pending:
            return 0

        ratings, k_factors = store.load_checkpoint(cp_year, cp_round, session_type)
        model = EndureElo(ENDURE_ELO_CALIBRATED)
        model.ratings = ratings
        model.k_factors = k_factors

        current_year: int = cp_year
        active_ids_cache: dict[int, set[str]] = {}

        for race_year, race_round in pending:
            race_entries = store.read_race_entries(race_year, race_round, session_type)
            if not race_entries:
                continue

            snapshot_rows, current_year = predict_snapshot_rows(
                model,
                race_entries,
                session_type,
                current_year=current_year,
            )
            model.process_race(race_entries)

            if race_year not in active_ids_cache:
                active_ids_cache[race_year] = store.active_driver_ids(race_year, session_type)

            store.write_snapshot_rows(snapshot_rows)
            store.save_checkpoint(
                model,
                race_year,
                race_round,
                session_type,
                active_driver_ids=active_ids_cache[race_year],
            )
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
    """All driver snapshots for one race, sorted by win_probability DESC."""
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
    """All snapshot rows for one driver in chronological order."""
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
    "DEFAULT_STATE_RETENTION_YEARS",
    "EloSnapshot",
    "add_race_snapshot",
    "build_snapshots",
    "catchup_snapshots",
    "ensure_schema",
    "get_driver_rating_history",
    "get_race_snapshot",
    "predict_snapshot_rows",
]
