"""Tests for pitlane_elo.snapshots — persistence layer for ELO pre-race state."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from pitlane_elo.snapshots import (
    EloSnapshot,
    add_race_snapshot,
    build_snapshots,
    catchup_snapshots,
    ensure_schema,
    get_driver_rating_history,
    get_race_snapshot,
)

# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestEnsureSchema:
    def test_creates_table(self, tmp_db: Path) -> None:
        con = duckdb.connect(str(tmp_db))
        try:
            ensure_schema(con)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_snapshots" in tables

    def test_idempotent(self, tmp_db: Path) -> None:
        con = duckdb.connect(str(tmp_db))
        try:
            ensure_schema(con)
            ensure_schema(con)  # second call must not raise
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
        n = build_snapshots(2023, 2024, db_path=multi_race_db)
        assert n == 30

    def test_probabilities_sum_to_one(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            rows = con.execute(
                "SELECT year, round, SUM(win_probability) AS s FROM elo_snapshots GROUP BY year, round"
            ).fetchall()
        finally:
            con.close()
        assert rows, "No rows found"
        for _, _, prob_sum in rows:
            assert abs(prob_sum - 1.0) < 1e-9, f"Prob sum {prob_sum} deviates from 1.0"

    def test_round1_pre_race_ratings_are_initial(self, multi_race_db: Path) -> None:
        # Before any race updates, all drivers start at 0.0
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            rows = con.execute("SELECT pre_race_rating FROM elo_snapshots WHERE year = 2023 AND round = 1").fetchall()
        finally:
            con.close()
        assert rows, "No rows for 2023 R1"
        for (rating,) in rows:
            assert rating == 0.0, f"Expected 0.0 for first race, got {rating}"

    def test_winner_finish_position_captured(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            row = con.execute(
                "SELECT driver_id, finish_position FROM elo_snapshots "
                "WHERE year = 2023 AND round = 1 AND finish_position = 1"
            ).fetchone()
        finally:
            con.close()
        assert row is not None, "No winner row found for 2023 R1"
        assert row[0] == "max_verstappen"

    def test_dnf_category_captured(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            row = con.execute(
                "SELECT driver_id, dnf_category FROM elo_snapshots "
                "WHERE year = 2023 AND round = 2 AND driver_id = 'lewis_hamilton'"
            ).fetchone()
        finally:
            con.close()
        assert row is not None
        assert row[1] == "mechanical"

    def test_upsert_idempotent(self, multi_race_db: Path) -> None:
        n1 = build_snapshots(2023, 2024, db_path=multi_race_db)
        n2 = build_snapshots(2023, 2024, db_path=multi_race_db)
        assert n1 == n2
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            count = con.execute("SELECT COUNT(*) FROM elo_snapshots").fetchone()[0]
        finally:
            con.close()
        assert count == n1

    def test_k_factors_positive(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            min_k = con.execute("SELECT MIN(pre_race_k) FROM elo_snapshots").fetchone()[0]
        finally:
            con.close()
        assert min_k > 0

    def test_podium_probabilities_in_range(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            row = con.execute("SELECT MIN(podium_probability), MAX(podium_probability) FROM elo_snapshots").fetchone()
        finally:
            con.close()
        assert row[0] >= 0.0
        assert row[1] <= 1.0

    def test_podium_probability_gte_win_probability(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            violations = con.execute(
                "SELECT COUNT(*) FROM elo_snapshots WHERE podium_probability < win_probability - 1e-9"
            ).fetchone()[0]
        finally:
            con.close()
        assert violations == 0

    def test_podium_probability_on_snapshot_object(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_race_snapshot(2023, 1, db_path=multi_race_db)
        assert all(hasattr(r, "podium_probability") for r in rows)
        assert all(0.0 <= r.podium_probability <= 1.0 for r in rows)


# ---------------------------------------------------------------------------
# get_race_snapshot tests
# ---------------------------------------------------------------------------


class TestGetRaceSnapshot:
    def test_returns_correct_number_of_drivers(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_race_snapshot(2024, 1, db_path=multi_race_db)
        assert len(rows) == 5

    def test_returns_elo_snapshot_objects(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_race_snapshot(2024, 1, db_path=multi_race_db)
        assert all(isinstance(r, EloSnapshot) for r in rows)

    def test_sorted_by_prob_descending(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_race_snapshot(2023, 1, db_path=multi_race_db)
        probs = [r.win_probability for r in rows]
        assert probs == sorted(probs, reverse=True)

    def test_missing_race_returns_empty(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_race_snapshot(9999, 1, db_path=multi_race_db)
        assert rows == []

    def test_no_table_returns_empty(self, tmp_db: Path) -> None:
        # Table hasn't been created yet — should not raise
        rows = get_race_snapshot(2024, 1, db_path=tmp_db)
        assert rows == []

    def test_correct_year_round_on_rows(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_race_snapshot(2024, 2, db_path=multi_race_db)
        assert all(r.year == 2024 and r.round == 2 for r in rows)


# ---------------------------------------------------------------------------
# get_driver_rating_history tests
# ---------------------------------------------------------------------------


class TestGetDriverRatingHistory:
    def test_returns_chronological_order(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", db_path=multi_race_db)
        years_rounds = [(r.year, r.round) for r in rows]
        assert years_rounds == sorted(years_rounds)

    def test_correct_row_count_for_driver(self, multi_race_db: Path) -> None:
        # max_verstappen appears in all 6 races
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", db_path=multi_race_db)
        assert len(rows) == 6

    def test_start_end_year_filter(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", start_year=2024, end_year=2024, db_path=multi_race_db)
        assert all(r.year == 2024 for r in rows)
        assert len(rows) == 3  # 3 races in 2024

    def test_unknown_driver_returns_empty(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_driver_rating_history("fake_driver_xyz", db_path=multi_race_db)
        assert rows == []

    def test_no_table_returns_empty(self, tmp_db: Path) -> None:
        rows = get_driver_rating_history("max_verstappen", db_path=tmp_db)
        assert rows == []

    def test_ratings_increase_after_wins(self, multi_race_db: Path) -> None:
        # max_verstappen wins 2023 R1 and R2, so rating should be positive after those
        build_snapshots(2023, 2024, db_path=multi_race_db)
        rows = get_driver_rating_history("max_verstappen", start_year=2023, end_year=2023, db_path=multi_race_db)
        # First race pre-race rating is 0.0, subsequent ones should be positive
        assert rows[0].pre_race_rating == 0.0
        assert rows[1].pre_race_rating > 0.0  # won race 1, so rating went up


# ---------------------------------------------------------------------------
# TestEnsureSchema — model-state table
# ---------------------------------------------------------------------------


class TestEnsureSchemaModelState:
    def test_creates_model_state_table(self, tmp_db: Path) -> None:
        con = duckdb.connect(str(tmp_db))
        try:
            ensure_schema(con)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_model_state" in tables

    def test_idempotent_with_model_state(self, tmp_db: Path) -> None:
        con = duckdb.connect(str(tmp_db))
        try:
            ensure_schema(con)
            ensure_schema(con)
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()
        assert "elo_model_state" in tables


# ---------------------------------------------------------------------------
# TestBuildSnapshotsModelState — build_snapshots also populates elo_model_state
# ---------------------------------------------------------------------------


class TestBuildSnapshotsModelState:
    def test_populates_model_state(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            count = con.execute("SELECT COUNT(*) FROM elo_model_state").fetchone()[0]
        finally:
            con.close()
        assert count > 0

    def test_model_state_row_per_race_driver(self, multi_race_db: Path) -> None:
        # 6 races, each race saves state for all ever-seen drivers (grows each race)
        # just check the final race has all 5 drivers
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            count = con.execute("SELECT COUNT(*) FROM elo_model_state WHERE year = 2024 AND round = 3").fetchone()[0]
        finally:
            con.close()
        assert count == 5

    def test_model_state_k_factors_positive(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        con = duckdb.connect(str(multi_race_db), read_only=True)
        try:
            min_k = con.execute("SELECT MIN(k_factor) FROM elo_model_state").fetchone()[0]
        finally:
            con.close()
        assert min_k > 0


# ---------------------------------------------------------------------------
# TestModelStatePruning — inactive drivers excluded from elo_model_state
# ---------------------------------------------------------------------------


class TestModelStatePruning:
    def test_long_retired_driver_pruned(self, tmp_db: Path) -> None:
        """A driver last active in 2000 must not appear in state checkpoints from 2011+."""
        con = duckdb.connect(str(tmp_db))
        try:
            # Seed a "historical" driver racing only in 2000 and current drivers from 2011-2012
            for rnd, finish_map in [
                (1, {"retired_driver": 1, "active_a": 2, "active_b": 3}),
                (2, {"retired_driver": 1, "active_a": 2, "active_b": 3}),
            ]:
                for driver_id, finish in finish_map.items():
                    con.execute(
                        "INSERT INTO race_entries (year, round, session_type, driver_id, team, "
                        "laps_completed, status, dnf_category, is_wet_race, is_street_circuit, finish_position) "
                        "VALUES (2000, ?, 'R', ?, 'Team', 57, 'Finished', 'none', false, false, ?)",
                        [rnd, driver_id, finish],
                    )
            for rnd, finish_map in [
                (1, {"active_a": 1, "active_b": 2}),
                (2, {"active_a": 2, "active_b": 1}),
            ]:
                for driver_id, finish in finish_map.items():
                    for year in (2011, 2012):
                        con.execute(
                            "INSERT INTO race_entries (year, round, session_type, driver_id, team, "
                            "laps_completed, status, dnf_category, is_wet_race, is_street_circuit, finish_position) "
                            "VALUES (?, ?, 'R', ?, 'Team', 57, 'Finished', 'none', false, false, ?)",
                            [year, rnd, driver_id, finish],
                        )
            con.commit()
        finally:
            con.close()

        build_snapshots(2000, 2012, db_path=tmp_db)

        with duckdb.connect(str(tmp_db), read_only=True) as con:
            # retired_driver must appear in 2000 checkpoints (within retention window)
            count_2000 = con.execute(
                "SELECT COUNT(*) FROM elo_model_state WHERE driver_id = 'retired_driver' AND year = 2000"
            ).fetchone()[0]
            # retired_driver must NOT appear in 2011+ checkpoints (11+ years since last race)
            count_2011 = con.execute(
                "SELECT COUNT(*) FROM elo_model_state WHERE driver_id = 'retired_driver' AND year >= 2011"
            ).fetchone()[0]
            # active drivers must still be present in 2012 checkpoints
            count_active_2012 = con.execute(
                "SELECT COUNT(DISTINCT driver_id) FROM elo_model_state WHERE year = 2012 AND round = 2"
            ).fetchone()[0]

        assert count_2000 > 0, "retired_driver should be in 2000 state"
        assert count_2011 == 0, "retired_driver should be pruned from 2011+ state"
        assert count_active_2012 == 2, "active drivers must remain in 2012 state"

    def test_returning_driver_within_retention_window_kept(self, tmp_db: Path) -> None:
        """A driver who returns within 10 years must remain in all checkpoints."""
        con = duckdb.connect(str(tmp_db))
        try:
            # driver_a races in 2014 and 2020 (6 year gap — within 10yr window)
            # driver_b races every year 2014-2020 for continuity
            for year in range(2014, 2021):
                for _rnd in (1,):
                    con.execute(
                        "INSERT INTO race_entries (year, round, session_type, driver_id, team, "
                        "laps_completed, status, dnf_category, is_wet_race, is_street_circuit, finish_position) "
                        "VALUES (?, 1, 'R', 'driver_b', 'Team', 57, 'Finished', 'none', false, false, 1)",
                        [year],
                    )
            for year in (2014, 2020):
                con.execute(
                    "INSERT INTO race_entries (year, round, session_type, driver_id, team, "
                    "laps_completed, status, dnf_category, is_wet_race, is_street_circuit, finish_position) "
                    "VALUES (?, 1, 'R', 'driver_a', 'Team', 57, 'Finished', 'none', false, false, 2)",
                    [year],
                )
            con.commit()
        finally:
            con.close()

        build_snapshots(2014, 2020, db_path=tmp_db)

        with duckdb.connect(str(tmp_db), read_only=True) as con:
            # driver_a raced in 2014; in 2019 checkpoint they are 5 years inactive — still within window
            count_2019 = con.execute(
                "SELECT COUNT(*) FROM elo_model_state WHERE driver_id = 'driver_a' AND year = 2019"
            ).fetchone()[0]
            # driver_a races again in 2020 — must appear in 2020 state
            count_2020 = con.execute(
                "SELECT COUNT(*) FROM elo_model_state WHERE driver_id = 'driver_a' AND year = 2020"
            ).fetchone()[0]

        assert count_2019 > 0, "driver_a should still be in 2019 state (5yr gap < 10yr window)"
        assert count_2020 > 0, "driver_a should be in 2020 state after returning"


# ---------------------------------------------------------------------------
# TestAddRaceSnapshot
# ---------------------------------------------------------------------------


class TestAddRaceSnapshot:
    def test_matches_full_rebuild(self, multi_race_db: Path, tmp_path: Path) -> None:
        # db_a: build 2023 only, then add 2024 R1 incrementally
        db_a = multi_race_db
        build_snapshots(2023, 2023, db_path=db_a)
        add_race_snapshot(2024, 1, db_path=db_a)

        # db_b: full build through 2024
        import shutil

        db_b = tmp_path / "full.duckdb"
        shutil.copy(db_a, db_b)
        # Reset elo_snapshots and elo_model_state on db_b, rebuild from scratch
        with duckdb.connect(str(db_b)) as con:
            con.execute("DELETE FROM elo_snapshots")
            con.execute("DELETE FROM elo_model_state")
            con.commit()
        build_snapshots(2023, 2024, db_path=db_b)

        # Compare 2024 R1 rows from both DBs
        def fetch_r1(db: Path) -> dict[str, tuple]:
            with duckdb.connect(str(db), read_only=True) as con:
                rows = con.execute(
                    "SELECT driver_id, pre_race_rating, pre_race_k, win_probability, podium_probability "
                    "FROM elo_snapshots WHERE year = 2024 AND round = 1 ORDER BY driver_id"
                ).fetchall()
            return {r[0]: r[1:] for r in rows}

        rows_a = fetch_r1(db_a)
        rows_b = fetch_r1(db_b)
        assert set(rows_a) == set(rows_b), "Driver sets differ"
        for driver_id in rows_a:
            for val_a, val_b in zip(rows_a[driver_id], rows_b[driver_id], strict=True):
                assert abs(val_a - val_b) < 1e-10, f"{driver_id}: {val_a} != {val_b}"

    def test_is_idempotent(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2023, db_path=multi_race_db)
        n1 = add_race_snapshot(2024, 1, db_path=multi_race_db)
        n2 = add_race_snapshot(2024, 1, db_path=multi_race_db)
        assert n1 == n2
        with duckdb.connect(str(multi_race_db), read_only=True) as con:
            count = con.execute("SELECT COUNT(*) FROM elo_snapshots WHERE year = 2024 AND round = 1").fetchone()[0]
        assert count == n1

    def test_rejects_race_before_checkpoint(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        import click

        with pytest.raises(click.ClickException):
            add_race_snapshot(2024, 2, db_path=multi_race_db)

    def test_rejects_real_gap(self, multi_race_db: Path) -> None:
        # Checkpoint through 2024 R1; race_entries has R2 and R3; try to add R3
        build_snapshots(2023, 2024, db_path=multi_race_db)
        # Delete state for R2 and R3 so checkpoint stops at R1
        with duckdb.connect(str(multi_race_db)) as con:
            con.execute("DELETE FROM elo_model_state WHERE year = 2024 AND round >= 2")
            con.execute("DELETE FROM elo_snapshots WHERE year = 2024 AND round >= 2")
            con.commit()
        import click

        with pytest.raises(click.ClickException, match="R2"):
            add_race_snapshot(2024, 3, db_path=multi_race_db)

    def test_allows_cancelled_round_gap(self, cancelled_rounds_db: Path) -> None:
        # DB has 2023 R1-R3 and 2024 R1 + 2024 R3 (R2 is cancelled — no entry).
        # After building 2023 + 2024 R1, adding 2024 R3 should succeed because R2 has no entry.
        build_snapshots(2023, 2023, db_path=cancelled_rounds_db)
        add_race_snapshot(2024, 1, db_path=cancelled_rounds_db)
        # R2 is absent from race_entries — add R3 directly
        n = add_race_snapshot(2024, 3, db_path=cancelled_rounds_db)
        assert n == 5  # 5 drivers

    def test_allows_cancelled_matches_full_rebuild(self, cancelled_rounds_db: Path, tmp_path: Path) -> None:
        # Incremental add of R3 (after R2 cancellation) should match full rebuild.
        import shutil

        db_incr = cancelled_rounds_db
        build_snapshots(2023, 2023, db_path=db_incr)
        add_race_snapshot(2024, 1, db_path=db_incr)
        add_race_snapshot(2024, 3, db_path=db_incr)

        db_full = tmp_path / "full.duckdb"
        shutil.copy(db_incr, db_full)
        with duckdb.connect(str(db_full)) as con:
            con.execute("DELETE FROM elo_snapshots")
            con.execute("DELETE FROM elo_model_state")
            con.commit()
        build_snapshots(2023, 2024, db_path=db_full)

        with duckdb.connect(str(db_incr), read_only=True) as con:
            incr_rows = {
                r[0]: r[1:]
                for r in con.execute(
                    "SELECT driver_id, pre_race_rating, win_probability "
                    "FROM elo_snapshots WHERE year = 2024 AND round = 3 ORDER BY driver_id"
                ).fetchall()
            }
        with duckdb.connect(str(db_full), read_only=True) as con:
            full_rows = {
                r[0]: r[1:]
                for r in con.execute(
                    "SELECT driver_id, pre_race_rating, win_probability "
                    "FROM elo_snapshots WHERE year = 2024 AND round = 3 ORDER BY driver_id"
                ).fetchall()
            }
        assert set(incr_rows) == set(full_rows)
        for driver_id in incr_rows:
            for v_i, v_f in zip(incr_rows[driver_id], full_rows[driver_id], strict=True):
                assert abs(v_i - v_f) < 1e-10, f"{driver_id}: {v_i} != {v_f}"

    def test_rejects_no_checkpoint(self, tmp_db: Path) -> None:
        import click

        with pytest.raises(click.ClickException, match="snapshot"):
            add_race_snapshot(2024, 1, db_path=tmp_db)

    def test_crosses_year_boundary(self, multi_race_db: Path, tmp_path: Path) -> None:
        # Incremental add of 2024 R1 after building only 2023 should apply phi_season.
        # Proof: it must match the full rebuild's pre_race_rating for 2024 R1.
        import shutil

        db_incr = multi_race_db
        build_snapshots(2023, 2023, db_path=db_incr)
        add_race_snapshot(2024, 1, db_path=db_incr)

        db_full = tmp_path / "full.duckdb"
        shutil.copy(db_incr, db_full)
        with duckdb.connect(str(db_full)) as con:
            con.execute("DELETE FROM elo_snapshots")
            con.execute("DELETE FROM elo_model_state")
            con.commit()
        build_snapshots(2023, 2024, db_path=db_full)

        with duckdb.connect(str(db_incr), read_only=True) as con:
            incr_rating = con.execute(
                "SELECT pre_race_rating FROM elo_snapshots "
                "WHERE year = 2024 AND round = 1 AND driver_id = 'max_verstappen'"
            ).fetchone()[0]
        with duckdb.connect(str(db_full), read_only=True) as con:
            full_rating = con.execute(
                "SELECT pre_race_rating FROM elo_snapshots "
                "WHERE year = 2024 AND round = 1 AND driver_id = 'max_verstappen'"
            ).fetchone()[0]

        assert abs(incr_rating - full_rating) < 1e-10
        # Sanity: phi_season < 1 means the 2024 rating must be lower than the 2023 R3 post-race rating
        with duckdb.connect(str(db_full), read_only=True) as con:
            r23_r3_pre = con.execute(
                "SELECT pre_race_rating FROM elo_snapshots "
                "WHERE year = 2023 AND round = 3 AND driver_id = 'max_verstappen'"
            ).fetchone()[0]
        # phi_season < 1 so the decayed 2024 rating will differ from the 2023 R3 pre-race value
        assert full_rating != r23_r3_pre


# ---------------------------------------------------------------------------
# TestCatchupSnapshots
# ---------------------------------------------------------------------------


class TestCatchupSnapshots:
    def test_processes_all_missing_races(self, multi_race_db: Path) -> None:
        # Build through 2023 only, then catchup should add 2024 R1-R3
        build_snapshots(2023, 2023, db_path=multi_race_db)
        n = catchup_snapshots(db_path=multi_race_db)
        assert n == 15  # 3 races × 5 drivers

    def test_already_up_to_date_returns_zero(self, multi_race_db: Path) -> None:
        build_snapshots(2023, 2024, db_path=multi_race_db)
        n = catchup_snapshots(db_path=multi_race_db)
        assert n == 0

    def test_catchup_matches_full_rebuild(self, multi_race_db: Path, tmp_path: Path) -> None:
        import shutil

        db_catchup = multi_race_db
        build_snapshots(2023, 2023, db_path=db_catchup)
        catchup_snapshots(db_path=db_catchup)

        db_full = tmp_path / "full.duckdb"
        shutil.copy(db_catchup, db_full)
        with duckdb.connect(str(db_full)) as con:
            con.execute("DELETE FROM elo_snapshots")
            con.execute("DELETE FROM elo_model_state")
            con.commit()
        build_snapshots(2023, 2024, db_path=db_full)

        with duckdb.connect(str(db_catchup), read_only=True) as con:
            catchup_rows = con.execute(
                "SELECT year, round, driver_id, pre_race_rating, win_probability "
                "FROM elo_snapshots WHERE year = 2024 ORDER BY year, round, driver_id"
            ).fetchall()
        with duckdb.connect(str(db_full), read_only=True) as con:
            full_rows = con.execute(
                "SELECT year, round, driver_id, pre_race_rating, win_probability "
                "FROM elo_snapshots WHERE year = 2024 ORDER BY year, round, driver_id"
            ).fetchall()

        assert len(catchup_rows) == len(full_rows)
        for (y_c, r_c, d_c, rat_c, w_c), (y_f, r_f, d_f, rat_f, w_f) in zip(catchup_rows, full_rows, strict=True):
            assert y_c == y_f and r_c == r_f and d_c == d_f
            assert abs(rat_c - rat_f) < 1e-10, f"{d_c} {y_c} R{r_c}: rating {rat_c} != {rat_f}"
            assert abs(w_c - w_f) < 1e-10, f"{d_c} {y_c} R{r_c}: win_prob {w_c} != {w_f}"

    def test_rejects_no_checkpoint(self, tmp_db: Path) -> None:
        import click

        with pytest.raises(click.ClickException, match="snapshot"):
            catchup_snapshots(db_path=tmp_db)
