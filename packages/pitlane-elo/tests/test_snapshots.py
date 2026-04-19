"""Tests for pitlane_elo.snapshots — persistence layer for ELO pre-race state."""

from __future__ import annotations

from pathlib import Path

import duckdb
from pitlane_elo.snapshots import (
    EloSnapshot,
    build_snapshots,
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
                "SELECT year, round, SUM(win_probability) AS s "
                "FROM elo_snapshots GROUP BY year, round"
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
            rows = con.execute(
                "SELECT pre_race_rating FROM elo_snapshots WHERE year = 2023 AND round = 1"
            ).fetchall()
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
            row = con.execute(
                "SELECT MIN(podium_probability), MAX(podium_probability) FROM elo_snapshots"
            ).fetchone()
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
        rows = get_driver_rating_history(
            "max_verstappen", start_year=2024, end_year=2024, db_path=multi_race_db
        )
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
        rows = get_driver_rating_history(
            "max_verstappen", start_year=2023, end_year=2023, db_path=multi_race_db
        )
        # First race pre-race rating is 0.0, subsequent ones should be positive
        assert rows[0].pre_race_rating == 0.0
        assert rows[1].pre_race_rating > 0.0  # won race 1, so rating went up
