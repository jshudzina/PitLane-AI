"""Tests for pitlane_elo.snapshots — persistence layer for ELO pre-race state."""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb
import pytest
from pitlane_elo.snapshots import (
    DEFAULT_STATE_RETENTION_YEARS,
    EloSnapshot,
    _resolve_retention_years,
    add_race_snapshot,
    build_snapshots,
    catchup_snapshots,
    ensure_schema,
    get_driver_rating_history,
    get_race_snapshot,
)

# ---------------------------------------------------------------------------
# Write helper (mirrors conftest._write_race_parquet for inline data)
# ---------------------------------------------------------------------------

_RACE_DDL = """
    year INTEGER NOT NULL, round INTEGER NOT NULL, session_type VARCHAR NOT NULL,
    driver_id VARCHAR NOT NULL, abbreviation VARCHAR, team VARCHAR NOT NULL,
    grid_position INTEGER, finish_position INTEGER,
    laps_completed INTEGER NOT NULL, status VARCHAR NOT NULL,
    dnf_category VARCHAR NOT NULL, is_wet_race BOOLEAN NOT NULL,
    is_street_circuit BOOLEAN NOT NULL
"""


def _write_race_parquet(data_dir: Path, rows: list[tuple]) -> None:
    from collections import defaultdict

    by_year: dict[int, list[tuple]] = defaultdict(list)
    for row in rows:
        by_year[row[0]].append(row)
    for year, year_rows in by_year.items():
        parquet_path = data_dir / f"race_entries_{year}.parquet"
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE race_entries ({_RACE_DDL})")
            for row in year_rows:
                con.execute("INSERT INTO race_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", list(row))
            con.execute(f"COPY race_entries TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        finally:
            con.close()


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def _read_snapshots(data_dir: Path, sql_suffix: str = "", params: list | None = None) -> list[tuple]:
    """Query elo_snapshots Parquet files and return rows."""
    glob_pattern = str(data_dir / "elo_snapshots_*.parquet")
    if not list(data_dir.glob("elo_snapshots_*.parquet")):
        return []
    con = duckdb.connect()
    try:
        full_sql = f"SELECT * FROM read_parquet('{glob_pattern}')" + (f" {sql_suffix}" if sql_suffix else "")
        return con.execute(full_sql, params or []).fetchall()
    finally:
        con.close()


def _read_model_state(data_dir: Path, sql_suffix: str = "", params: list | None = None) -> list[tuple]:
    """Query elo_model_state Parquet file and return rows."""
    model_state_path = data_dir / "elo_model_state.parquet"
    if not model_state_path.exists():
        return []
    con = duckdb.connect()
    try:
        full_sql = f"SELECT * FROM read_parquet('{model_state_path}')" + (f" {sql_suffix}" if sql_suffix else "")
        return con.execute(full_sql, params or []).fetchall()
    finally:
        con.close()


def _reset_elo_parquet(data_dir: Path) -> None:
    """Delete all ELO Parquet files from data_dir (resets snapshot state)."""
    for f in data_dir.glob("elo_snapshots_*.parquet"):
        f.unlink()
    model_state = data_dir / "elo_model_state.parquet"
    if model_state.exists():
        model_state.unlink()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestEnsureSchema:
    def test_creates_table(self, tmp_db: Path) -> None:
        con = duckdb.connect()
        try:
            ensure_schema(con, tmp_db)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_snapshots" in tables

    def test_idempotent(self, tmp_db: Path) -> None:
        con = duckdb.connect()
        try:
            ensure_schema(con, tmp_db)
            ensure_schema(con, tmp_db)  # second call must not raise
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_snapshots" in tables


# ---------------------------------------------------------------------------
# build_snapshots tests
# ---------------------------------------------------------------------------


class TestBuildSnapshots:
    def test_row_count(self, multi_race_db: Path) -> None:
        # 6 races × 5 drivers = 30 rows
        n = build_snapshots(2023, 2024, data_dir=multi_race_db)
        assert n == 30

    def test_probabilities_sum_to_one(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            rows = con.execute(
                f"SELECT year, round, SUM(win_probability) AS s "
                f"FROM read_parquet('{glob_pattern}') GROUP BY year, round"
            ).fetchall()
        finally:
            con.close()
        assert rows, "No rows found"
        for _, _, prob_sum in rows:
            assert abs(prob_sum - 1.0) < 1e-9, f"Prob sum {prob_sum} deviates from 1.0"

    def test_round1_pre_race_ratings_are_initial(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            rows = con.execute(
                f"SELECT pre_race_rating FROM read_parquet('{glob_pattern}') WHERE year = 2023 AND round = 1"
            ).fetchall()
        finally:
            con.close()
        assert rows, "No rows for 2023 R1"
        for (rating,) in rows:
            assert rating == 0.0, f"Expected 0.0 for first race, got {rating}"

    def test_winner_finish_position_captured(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            row = con.execute(
                f"SELECT driver_id, finish_position FROM read_parquet('{glob_pattern}') "
                "WHERE year = 2023 AND round = 1 AND finish_position = 1"
            ).fetchone()
        finally:
            con.close()
        assert row is not None, "No winner row found for 2023 R1"
        assert row[0] == "max_verstappen"

    def test_dnf_category_captured(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            row = con.execute(
                f"SELECT driver_id, dnf_category FROM read_parquet('{glob_pattern}') "
                "WHERE year = 2023 AND round = 2 AND driver_id = 'lewis_hamilton'"
            ).fetchone()
        finally:
            con.close()
        assert row is not None
        assert row[1] == "mechanical"

    def test_upsert_idempotent(self, multi_race_db: Path) -> None:
        n1 = build_snapshots(2023, 2024, data_dir=multi_race_db)
        n2 = build_snapshots(2023, 2024, data_dir=multi_race_db)
        assert n1 == n2
        rows = _read_snapshots(multi_race_db)
        assert len(rows) == n1

    def test_k_factors_positive(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            min_k = con.execute(f"SELECT MIN(pre_race_k) FROM read_parquet('{glob_pattern}')").fetchone()[0]
        finally:
            con.close()
        assert min_k > 0

    def test_podium_probabilities_in_range(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            row = con.execute(
                f"SELECT MIN(podium_probability), MAX(podium_probability) FROM read_parquet('{glob_pattern}')"
            ).fetchone()
        finally:
            con.close()
        assert row[0] >= 0.0
        assert row[1] <= 1.0

    def test_podium_probability_gte_win_probability(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            violations = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{glob_pattern}') WHERE podium_probability < win_probability - 1e-9"
            ).fetchone()[0]
        finally:
            con.close()
        assert violations == 0

    def test_podium_probability_on_snapshot_object(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_race_snapshot(2023, 1, data_dir=multi_race_db)
        assert all(hasattr(r, "podium_probability") for r in rows)
        assert all(0.0 <= r.podium_probability <= 1.0 for r in rows)


# ---------------------------------------------------------------------------
# get_race_snapshot tests
# ---------------------------------------------------------------------------


class TestGetRaceSnapshot:
    def test_returns_correct_number_of_drivers(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_race_snapshot(2024, 1, data_dir=multi_race_db)
        assert len(rows) == 5

    def test_returns_elo_snapshot_objects(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_race_snapshot(2024, 1, data_dir=multi_race_db)
        assert all(isinstance(r, EloSnapshot) for r in rows)

    def test_sorted_by_prob_descending(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_race_snapshot(2023, 1, data_dir=multi_race_db)
        probs = [r.win_probability for r in rows]
        assert probs == sorted(probs, reverse=True)

    def test_missing_race_returns_empty(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_race_snapshot(9999, 1, data_dir=multi_race_db)
        assert rows == []

    def test_no_parquet_returns_empty(self, tmp_db: Path) -> None:
        rows = get_race_snapshot(2024, 1, data_dir=tmp_db)
        assert rows == []

    def test_correct_year_round_on_rows(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_race_snapshot(2024, 2, data_dir=multi_race_db)
        assert all(r.year == 2024 and r.round == 2 for r in rows)


# ---------------------------------------------------------------------------
# get_driver_rating_history tests
# ---------------------------------------------------------------------------


class TestGetDriverRatingHistory:
    def test_returns_chronological_order(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", data_dir=multi_race_db)
        years_rounds = [(r.year, r.round) for r in rows]
        assert years_rounds == sorted(years_rounds)

    def test_correct_row_count_for_driver(self, multi_race_db: Path) -> None:
        # max_verstappen appears in all 6 races
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", data_dir=multi_race_db)
        assert len(rows) == 6

    def test_start_end_year_filter(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", start_year=2024, end_year=2024, data_dir=multi_race_db)
        assert all(r.year == 2024 for r in rows)
        assert len(rows) == 3  # 3 races in 2024

    def test_unknown_driver_returns_empty(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_driver_rating_history("fake_driver_xyz", data_dir=multi_race_db)
        assert rows == []

    def test_no_parquet_returns_empty(self, tmp_db: Path) -> None:
        rows = get_driver_rating_history("max_verstappen", data_dir=tmp_db)
        assert rows == []

    def test_ratings_increase_after_wins(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", start_year=2023, end_year=2023, data_dir=multi_race_db)
        assert rows[0].pre_race_rating == 0.0
        assert rows[1].pre_race_rating > 0.0


# ---------------------------------------------------------------------------
# TestEnsureSchema — model-state table
# ---------------------------------------------------------------------------


class TestEnsureSchemaModelState:
    def test_creates_model_state_table(self, tmp_db: Path) -> None:
        con = duckdb.connect()
        try:
            ensure_schema(con, tmp_db)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_model_state" in tables

    def test_idempotent_with_model_state(self, tmp_db: Path) -> None:
        con = duckdb.connect()
        try:
            ensure_schema(con, tmp_db)
            ensure_schema(con, tmp_db)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_model_state" in tables


# ---------------------------------------------------------------------------
# TestBuildSnapshotsModelState
# ---------------------------------------------------------------------------


class TestBuildSnapshotsModelState:
    def test_populates_model_state(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        rows = _read_model_state(multi_race_db)
        assert len(rows) > 0

    def test_model_state_row_per_race_driver(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        model_state_path = multi_race_db / "elo_model_state.parquet"
        con = duckdb.connect()
        try:
            count = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') WHERE year = 2024 AND round = 3"
            ).fetchone()[0]
        finally:
            con.close()
        assert count == 5

    def test_model_state_k_factors_positive(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        model_state_path = multi_race_db / "elo_model_state.parquet"
        con = duckdb.connect()
        try:
            min_k = con.execute(f"SELECT MIN(k_factor) FROM read_parquet('{model_state_path}')").fetchone()[0]
        finally:
            con.close()
        assert min_k > 0


# ---------------------------------------------------------------------------
# TestModelStatePruning — inactive drivers excluded from elo_model_state
# ---------------------------------------------------------------------------


class TestModelStatePruning:
    def test_long_retired_driver_pruned(self, tmp_db: Path) -> None:
        """A driver last active in 2000 must not appear in state checkpoints from 2011+."""
        # Seed a "historical" driver racing only in 2000 and current drivers from 2011-2012
        rows_2000 = []
        for rnd, finish_map in [
            (1, {"retired_driver": 1, "active_a": 2, "active_b": 3}),
            (2, {"retired_driver": 1, "active_a": 2, "active_b": 3}),
        ]:
            for driver_id, finish in finish_map.items():
                rows_2000.append(
                    (2000, rnd, "R", driver_id, None, "Team", finish, finish, 57, "Finished", "none", False, False)
                )

        rows_active = []
        for rnd, finish_map in [
            (1, {"active_a": 1, "active_b": 2}),
            (2, {"active_a": 2, "active_b": 1}),
        ]:
            for driver_id, finish in finish_map.items():
                for year in (2011, 2012):
                    rows_active.append(
                        (year, rnd, "R", driver_id, None, "Team", finish, finish, 57, "Finished", "none", False, False)
                    )

        _write_race_parquet(tmp_db, rows_2000 + rows_active)

        build_snapshots(2000, 2012, data_dir=tmp_db, retention_years=10)

        model_state_path = tmp_db / "elo_model_state.parquet"
        con = duckdb.connect()
        try:
            count_2000 = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') "
                "WHERE driver_id = 'retired_driver' AND year = 2000"
            ).fetchone()[0]
            count_2011 = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') "
                "WHERE driver_id = 'retired_driver' AND year >= 2011"
            ).fetchone()[0]
            count_active_2012 = con.execute(
                f"SELECT COUNT(DISTINCT driver_id) FROM read_parquet('{model_state_path}') "
                "WHERE year = 2012 AND round = 2"
            ).fetchone()[0]
        finally:
            con.close()

        assert count_2000 > 0, "retired_driver should be in 2000 state"
        assert count_2011 == 0, "retired_driver should be pruned from 2011+ state"
        assert count_active_2012 == 2, "active drivers must remain in 2012 state"

    def test_returning_driver_within_retention_window_kept(self, tmp_db: Path) -> None:
        """A driver who returns within 10 years must remain in all checkpoints."""
        rows: list[tuple] = []
        # driver_b races every year 2014-2020 for continuity
        for year in range(2014, 2021):
            rows.append((year, 1, "R", "driver_b", None, "Team", 1, 1, 57, "Finished", "none", False, False))
        # driver_a races only in 2014 and 2020 (6-year gap — within 10yr window)
        for year in (2014, 2020):
            rows.append((year, 1, "R", "driver_a", None, "Team", 2, 2, 57, "Finished", "none", False, False))

        _write_race_parquet(tmp_db, rows)

        build_snapshots(2014, 2020, data_dir=tmp_db, retention_years=10)

        model_state_path = tmp_db / "elo_model_state.parquet"
        con = duckdb.connect()
        try:
            count_2019 = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') WHERE driver_id = 'driver_a' AND year = 2019"
            ).fetchone()[0]
            count_2020 = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') WHERE driver_id = 'driver_a' AND year = 2020"
            ).fetchone()[0]
        finally:
            con.close()

        assert count_2019 > 0, "driver_a should still be in 2019 state (5yr gap < 10yr window)"
        assert count_2020 > 0, "driver_a should be in 2020 state after returning"


# ---------------------------------------------------------------------------
# TestAddRaceSnapshot
# ---------------------------------------------------------------------------


class TestAddRaceSnapshot:
    def test_matches_full_rebuild(self, multi_race_db: Path, tmp_path: Path) -> None:
        db_a = multi_race_db
        build_snapshots(2023, 2023, data_dir=db_a)
        add_race_snapshot(2024, 1, data_dir=db_a)

        db_b = tmp_path / "full_data"
        shutil.copytree(db_a, db_b)
        _reset_elo_parquet(db_b)
        build_snapshots(2023, 2024, data_dir=db_b)

        def fetch_r1(d: Path) -> dict[str, tuple]:
            glob_pattern = str(d / "elo_snapshots_*.parquet")
            con = duckdb.connect()
            try:
                rows = con.execute(
                    f"SELECT driver_id, pre_race_rating, pre_race_k, win_probability, podium_probability "
                    f"FROM read_parquet('{glob_pattern}') WHERE year = 2024 AND round = 1 ORDER BY driver_id"
                ).fetchall()
            finally:
                con.close()
            return {r[0]: r[1:] for r in rows}

        rows_a = fetch_r1(db_a)
        rows_b = fetch_r1(db_b)
        assert set(rows_a) == set(rows_b), "Driver sets differ"
        for driver_id in rows_a:
            for val_a, val_b in zip(rows_a[driver_id], rows_b[driver_id], strict=True):
                assert abs(val_a - val_b) < 1e-10, f"{driver_id}: {val_a} != {val_b}"

    def test_is_idempotent(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2023, data_dir=multi_race_db)
        n1 = add_race_snapshot(2024, 1, data_dir=multi_race_db)
        n2 = add_race_snapshot(2024, 1, data_dir=multi_race_db)
        assert n1 == n2
        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            count = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{glob_pattern}') WHERE year = 2024 AND round = 1"
            ).fetchone()[0]
        finally:
            con.close()
        assert count == n1

    def test_rejects_race_before_checkpoint(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        import click

        with pytest.raises(click.ClickException):
            add_race_snapshot(2024, 2, data_dir=multi_race_db)

    def test_rejects_real_gap(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        # Delete state for R2 and R3 so checkpoint stops at R1
        model_state_path = multi_race_db / "elo_model_state.parquet"
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE ms AS SELECT * FROM read_parquet('{model_state_path}')")
            con.execute("DELETE FROM ms WHERE year = 2024 AND round >= 2")
            con.execute(f"COPY ms TO '{model_state_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        finally:
            con.close()

        glob_pattern = str(multi_race_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            # Rebuild snapshot Parquet without R2/R3
            years = {r[0] for r in con.execute(f"SELECT DISTINCT year FROM read_parquet('{glob_pattern}')").fetchall()}
            for year in years:
                snap_path = multi_race_db / f"elo_snapshots_{year}.parquet"
                con.execute(
                    f"COPY (SELECT * FROM read_parquet('{glob_pattern}') "
                    f"WHERE year = {year} AND NOT (year = 2024 AND round >= 2)) "
                    f"TO '{snap_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
                )
        finally:
            con.close()

        import click

        with pytest.raises(click.ClickException, match="R2"):
            add_race_snapshot(2024, 3, data_dir=multi_race_db)

    def test_allows_cancelled_round_gap(self, cancelled_rounds_db: Path) -> None:
        build_snapshots(2023, 2023, data_dir=cancelled_rounds_db)
        add_race_snapshot(2024, 1, data_dir=cancelled_rounds_db)
        n = add_race_snapshot(2024, 3, data_dir=cancelled_rounds_db)
        assert n == 5  # 5 drivers

    def test_allows_cancelled_matches_full_rebuild(self, cancelled_rounds_db: Path, tmp_path: Path) -> None:
        db_incr = cancelled_rounds_db
        build_snapshots(2023, 2023, data_dir=db_incr)
        add_race_snapshot(2024, 1, data_dir=db_incr)
        add_race_snapshot(2024, 3, data_dir=db_incr)

        db_full = tmp_path / "full_data"
        shutil.copytree(db_incr, db_full)
        _reset_elo_parquet(db_full)
        build_snapshots(2023, 2024, data_dir=db_full)

        def fetch_r3(d: Path) -> dict[str, tuple]:
            glob_pattern = str(d / "elo_snapshots_*.parquet")
            con = duckdb.connect()
            try:
                rows = con.execute(
                    f"SELECT driver_id, pre_race_rating, win_probability "
                    f"FROM read_parquet('{glob_pattern}') WHERE year = 2024 AND round = 3 ORDER BY driver_id"
                ).fetchall()
            finally:
                con.close()
            return {r[0]: r[1:] for r in rows}

        incr_rows = fetch_r3(db_incr)
        full_rows = fetch_r3(db_full)
        assert set(incr_rows) == set(full_rows)
        for driver_id in incr_rows:
            for v_i, v_f in zip(incr_rows[driver_id], full_rows[driver_id], strict=True):
                assert abs(v_i - v_f) < 1e-10, f"{driver_id}: {v_i} != {v_f}"

    def test_rejects_no_checkpoint(self, tmp_db: Path) -> None:
        import click

        with pytest.raises(click.ClickException, match="snapshot"):
            add_race_snapshot(2024, 1, data_dir=tmp_db)

    def test_crosses_year_boundary(self, multi_race_db: Path, tmp_path: Path) -> None:
        db_incr = multi_race_db
        build_snapshots(2023, 2023, data_dir=db_incr)
        add_race_snapshot(2024, 1, data_dir=db_incr)

        db_full = tmp_path / "full_data"
        shutil.copytree(db_incr, db_full)
        _reset_elo_parquet(db_full)
        build_snapshots(2023, 2024, data_dir=db_full)

        def fetch_rating(d: Path) -> float:
            glob_pattern = str(d / "elo_snapshots_*.parquet")
            con = duckdb.connect()
            try:
                return con.execute(
                    f"SELECT pre_race_rating FROM read_parquet('{glob_pattern}') "
                    "WHERE year = 2024 AND round = 1 AND driver_id = 'max_verstappen'"
                ).fetchone()[0]
            finally:
                con.close()

        incr_rating = fetch_rating(db_incr)
        full_rating = fetch_rating(db_full)
        assert abs(incr_rating - full_rating) < 1e-10

        # Sanity: phi_season < 1 means 2024 rating must differ from 2023 R3 pre-race rating
        glob_full = str(db_full / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            r23_r3_pre = con.execute(
                f"SELECT pre_race_rating FROM read_parquet('{glob_full}') "
                "WHERE year = 2023 AND round = 3 AND driver_id = 'max_verstappen'"
            ).fetchone()[0]
        finally:
            con.close()
        assert full_rating != r23_r3_pre


# ---------------------------------------------------------------------------
# TestCatchupSnapshots
# ---------------------------------------------------------------------------


class TestCatchupSnapshots:
    def test_processes_all_missing_races(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2023, data_dir=multi_race_db)
        n = catchup_snapshots(data_dir=multi_race_db)
        assert n == 15  # 3 races × 5 drivers

    def test_already_up_to_date_returns_zero(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, data_dir=multi_race_db)
        n = catchup_snapshots(data_dir=multi_race_db)
        assert n == 0

    def test_catchup_matches_full_rebuild(self, multi_race_db: Path, tmp_path: Path) -> None:
        db_catchup = multi_race_db
        build_snapshots(2023, 2023, data_dir=db_catchup)
        catchup_snapshots(data_dir=db_catchup)

        db_full = tmp_path / "full_data"
        shutil.copytree(db_catchup, db_full)
        _reset_elo_parquet(db_full)
        build_snapshots(2023, 2024, data_dir=db_full)

        def fetch_2024(d: Path) -> list[tuple]:
            glob_pattern = str(d / "elo_snapshots_*.parquet")
            con = duckdb.connect()
            try:
                return con.execute(
                    f"SELECT year, round, driver_id, pre_race_rating, win_probability "
                    f"FROM read_parquet('{glob_pattern}') WHERE year = 2024 ORDER BY year, round, driver_id"
                ).fetchall()
            finally:
                con.close()

        catchup_rows = fetch_2024(db_catchup)
        full_rows = fetch_2024(db_full)

        assert len(catchup_rows) == len(full_rows)
        for (y_c, r_c, d_c, rat_c, w_c), (y_f, r_f, d_f, rat_f, w_f) in zip(catchup_rows, full_rows, strict=True):
            assert y_c == y_f and r_c == r_f and d_c == d_f
            assert abs(rat_c - rat_f) < 1e-10, f"{d_c} {y_c} R{r_c}: rating {rat_c} != {rat_f}"
            assert abs(w_c - w_f) < 1e-10, f"{d_c} {y_c} R{r_c}: win_prob {w_c} != {w_f}"

    def test_rejects_no_checkpoint(self, tmp_db: Path) -> None:
        import click

        with pytest.raises(click.ClickException, match="snapshot"):
            catchup_snapshots(data_dir=tmp_db)


# ---------------------------------------------------------------------------
# TestStarterFilter — only drivers who started appear in snapshot rows
# ---------------------------------------------------------------------------


class TestStarterFilter:
    def test_dns_drivers_excluded_from_snapshots(self, tmp_db: Path) -> None:
        rows = [
            (2024, 1, "R", "driver_a", None, "T", 1, 1, 57, "Finished", "none", False, False),
            (2024, 1, "R", "driver_b", None, "T", 2, 2, 57, "Finished", "none", False, False),
            (2024, 1, "R", "driver_c", None, "T", 3, 3, 57, "Finished", "none", False, False),
            (2024, 1, "R", "dns_driver", None, "T", None, None, 57, "Finished", "none", False, False),
        ]
        _write_race_parquet(tmp_db, rows)

        n = build_snapshots(2024, 2024, data_dir=tmp_db, retention_years=10)

        assert n == 3, "DNS driver must not produce a snapshot row"
        glob_pattern = str(tmp_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            ids = {row[0] for row in con.execute(f"SELECT driver_id FROM read_parquet('{glob_pattern}')").fetchall()}
        finally:
            con.close()
        assert ids == {"driver_a", "driver_b", "driver_c"}
        assert "dns_driver" not in ids

    def test_probabilities_sum_to_one_with_dns_present(self, tmp_db: Path) -> None:
        rows = [
            (2024, 1, "R", "driver_a", None, "T", 1, 1, 57, "Finished", "none", False, False),
            (2024, 1, "R", "driver_b", None, "T", 2, 2, 57, "Finished", "none", False, False),
            (2024, 1, "R", "driver_c", None, "T", 3, 3, 57, "Finished", "none", False, False),
            (2024, 1, "R", "dns_driver", None, "T", None, None, 57, "Finished", "none", False, False),
        ]
        _write_race_parquet(tmp_db, rows)

        build_snapshots(2024, 2024, data_dir=tmp_db, retention_years=10)
        glob_pattern = str(tmp_db / "elo_snapshots_*.parquet")
        con = duckdb.connect()
        try:
            total = con.execute(f"SELECT SUM(win_probability) FROM read_parquet('{glob_pattern}')").fetchone()[0]
        finally:
            con.close()
        assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# TestRetentionResolution — explicit arg > env var > default
# ---------------------------------------------------------------------------


class TestRetentionResolution:
    def test_default_is_five(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PITLANE_STATE_RETENTION_YEARS", raising=False)
        assert DEFAULT_STATE_RETENTION_YEARS == 5
        assert _resolve_retention_years(None) == 5

    def test_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PITLANE_STATE_RETENTION_YEARS", "7")
        assert _resolve_retention_years(None) == 7

    def test_explicit_arg_beats_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PITLANE_STATE_RETENTION_YEARS", "7")
        assert _resolve_retention_years(3) == 3

    def test_retention_param_prunes_state(self, tmp_db: Path) -> None:
        """With retention_years=3, a driver inactive for >3 years must be pruned."""
        rows: list[tuple] = []
        # old_driver races only in 2020; active drivers race every year
        for driver_id, grid, finish in [("old_driver", 1, 1), ("active_a", 2, 2), ("active_b", 3, 3)]:
            rows.append((2020, 1, "R", driver_id, None, "T", grid, finish, 57, "Finished", "none", False, False))
        for year in (2021, 2022, 2023, 2024, 2025):
            for driver_id, grid, finish in [("active_a", 1, 1), ("active_b", 2, 2)]:
                rows.append((year, 1, "R", driver_id, None, "T", grid, finish, 57, "Finished", "none", False, False))
        _write_race_parquet(tmp_db, rows)

        build_snapshots(2020, 2025, data_dir=tmp_db, retention_years=3)

        model_state_path = tmp_db / "elo_model_state.parquet"
        con = duckdb.connect()
        try:
            count_2025 = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') "
                "WHERE driver_id = 'old_driver' AND year = 2025"
            ).fetchone()[0]
            count_2022 = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{model_state_path}') "
                "WHERE driver_id = 'old_driver' AND year = 2022"
            ).fetchone()[0]
        finally:
            con.close()
        assert count_2025 == 0, "old_driver must be pruned by 2025 with retention=3"
        assert count_2022 > 0, "old_driver must remain in 2022 with retention=3"
