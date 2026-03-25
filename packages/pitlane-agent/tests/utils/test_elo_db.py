"""Tests for elo_db utility module using in-memory DuckDB."""

from pathlib import Path

import duckdb
from pitlane_agent.utils.elo_db import (
    QualifyingEntry,
    RaceEntry,
    categorize_dnf,
    get_qualifying_entries,
    get_race_entries,
    init_elo_tables,
    upsert_qualifying_entries,
    upsert_race_entries,
)
from pitlane_agent.utils.stats_db import init_db


_SAMPLE_RACE_ENTRY: RaceEntry = {
    "year": 2024,
    "round": 1,
    "session_type": "R",
    "driver_id": "max_verstappen",
    "abbreviation": "VER",
    "team": "Red Bull Racing",
    "grid_position": 1,
    "finish_position": 1,
    "laps_completed": 57,
    "status": "Finished",
    "dnf_category": "none",
    "is_wet_race": False,
    "is_street_circuit": False,
}

_SAMPLE_QUALIFYING_ENTRY: QualifyingEntry = {
    "year": 2024,
    "round": 1,
    "driver_id": "max_verstappen",
    "abbreviation": "VER",
    "team": "Red Bull Racing",
    "q1_time_s": 87.123,
    "q2_time_s": 86.456,
    "q3_time_s": 85.789,
    "best_q_time_s": 85.789,
    "position": 1,
}


class TestInitEloTables:
    """Tests for init_elo_tables."""

    def test_creates_race_entries_table(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM race_entries").fetchone()
        con.close()

        assert result[0] == 0

    def test_creates_qualifying_entries_table(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM qualifying_entries").fetchone()
        con.close()

        assert result[0] == 0

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dir" / "test.duckdb"
        init_elo_tables(db_path)

        assert db_path.exists()

    def test_idempotent_on_second_call(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        init_elo_tables(db_path)  # should not raise

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM race_entries").fetchone()
        con.close()

        assert result[0] == 0

    def test_additive_with_session_stats(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_db(db_path)       # creates session_stats
        init_elo_tables(db_path)  # adds race_entries and qualifying_entries

        con = duckdb.connect(str(db_path))
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        con.close()

        assert "session_stats" in tables
        assert "race_entries" in tables
        assert "qualifying_entries" in tables


class TestUpsertRaceEntries:
    """Tests for upsert_race_entries."""

    def test_inserts_single_record(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        upsert_race_entries(db_path, [_SAMPLE_RACE_ENTRY])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM race_entries").fetchone()
        con.close()

        assert result[0] == 1

    def test_inserts_multiple_records(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        records = [
            {**_SAMPLE_RACE_ENTRY, "driver_id": "max_verstappen"},
            {**_SAMPLE_RACE_ENTRY, "driver_id": "hamilton"},
            {**_SAMPLE_RACE_ENTRY, "driver_id": "leclerc"},
        ]
        upsert_race_entries(db_path, records)

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM race_entries").fetchone()
        con.close()

        assert result[0] == 3

    def test_replaces_existing_record(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        upsert_race_entries(db_path, [_SAMPLE_RACE_ENTRY])
        updated = {**_SAMPLE_RACE_ENTRY, "laps_completed": 42}
        upsert_race_entries(db_path, [updated])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT laps_completed FROM race_entries "
            "WHERE year = 2024 AND round = 1 AND session_type = 'R' AND driver_id = 'max_verstappen'"
        ).fetchone()
        con.close()

        assert result[0] == 42

    def test_empty_records_is_noop(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        upsert_race_entries(db_path, [])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM race_entries").fetchone()
        con.close()

        assert result[0] == 0

    def test_nullable_grid_and_finish_position(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        record = {**_SAMPLE_RACE_ENTRY, "grid_position": None, "finish_position": None}
        upsert_race_entries(db_path, [record])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT grid_position, finish_position FROM race_entries WHERE driver_id = 'max_verstappen'"
        ).fetchone()
        con.close()

        assert result[0] is None
        assert result[1] is None

    def test_sprint_and_race_coexist(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        race = {**_SAMPLE_RACE_ENTRY, "session_type": "R"}
        sprint = {**_SAMPLE_RACE_ENTRY, "session_type": "S"}
        upsert_race_entries(db_path, [race, sprint])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM race_entries WHERE driver_id = 'max_verstappen'").fetchone()
        con.close()

        assert result[0] == 2

    def test_nullable_abbreviation(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        # Historical driver with no 3-letter code
        record = {**_SAMPLE_RACE_ENTRY, "driver_id": "farina", "abbreviation": None}
        upsert_race_entries(db_path, [record])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT abbreviation FROM race_entries WHERE driver_id = 'farina'"
        ).fetchone()
        con.close()

        assert result[0] is None


class TestUpsertQualifyingEntries:
    """Tests for upsert_qualifying_entries."""

    def test_inserts_single_record(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        upsert_qualifying_entries(db_path, [_SAMPLE_QUALIFYING_ENTRY])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM qualifying_entries").fetchone()
        con.close()

        assert result[0] == 1

    def test_inserts_multiple_records(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        records = [
            {**_SAMPLE_QUALIFYING_ENTRY, "driver_id": "max_verstappen", "position": 1},
            {**_SAMPLE_QUALIFYING_ENTRY, "driver_id": "hamilton", "position": 2},
            {**_SAMPLE_QUALIFYING_ENTRY, "driver_id": "leclerc", "position": 3},
        ]
        upsert_qualifying_entries(db_path, records)

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM qualifying_entries").fetchone()
        con.close()

        assert result[0] == 3

    def test_replaces_existing_record(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        upsert_qualifying_entries(db_path, [_SAMPLE_QUALIFYING_ENTRY])
        updated = {**_SAMPLE_QUALIFYING_ENTRY, "best_q_time_s": 84.999}
        upsert_qualifying_entries(db_path, [updated])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT best_q_time_s FROM qualifying_entries WHERE driver_id = 'max_verstappen'"
        ).fetchone()
        con.close()

        assert result[0] == 84.999

    def test_empty_records_is_noop(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        upsert_qualifying_entries(db_path, [])

        con = duckdb.connect(str(db_path))
        result = con.execute("SELECT COUNT(*) FROM qualifying_entries").fetchone()
        con.close()

        assert result[0] == 0

    def test_nullable_q2_and_q3_times(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        # Driver eliminated in Q1 — no Q2 or Q3 time
        record = {
            **_SAMPLE_QUALIFYING_ENTRY,
            "driver_id": "bottas",
            "q2_time_s": None,
            "q3_time_s": None,
            "best_q_time_s": 87.123,
            "position": 16,
        }
        upsert_qualifying_entries(db_path, [record])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT q2_time_s, q3_time_s FROM qualifying_entries WHERE driver_id = 'bottas'"
        ).fetchone()
        con.close()

        assert result[0] is None
        assert result[1] is None

    def test_all_q_times_null_pre2006(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        # Pre-2006 session: Q1/Q2/Q3 format didn't exist
        record: QualifyingEntry = {
            "year": 1995,
            "round": 1,
            "driver_id": "schumacher",
            "abbreviation": None,
            "team": "Benetton",
            "q1_time_s": None,
            "q2_time_s": None,
            "q3_time_s": None,
            "best_q_time_s": None,
            "position": 1,
        }
        upsert_qualifying_entries(db_path, [record])

        con = duckdb.connect(str(db_path))
        result = con.execute(
            "SELECT q1_time_s, q2_time_s, q3_time_s, best_q_time_s FROM qualifying_entries WHERE driver_id = 'schumacher'"
        ).fetchone()
        con.close()

        assert all(v is None for v in result)


class TestGetRaceEntries:
    """Tests for get_race_entries."""

    def test_returns_none_when_db_does_not_exist(self, tmp_path):
        db_path = tmp_path / "nonexistent.duckdb"
        result = get_race_entries(db_path, 2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        upsert_race_entries(db_path, [_SAMPLE_RACE_ENTRY])

        result = get_race_entries(db_path, 2023)

        assert result is None

    def test_returns_rows_for_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        upsert_race_entries(db_path, [_SAMPLE_RACE_ENTRY])

        result = get_race_entries(db_path, 2024)

        assert result is not None
        assert len(result) == 1
        assert result[0]["driver_id"] == "max_verstappen"

    def test_returns_dicts_with_correct_keys(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        upsert_race_entries(db_path, [_SAMPLE_RACE_ENTRY])

        result = get_race_entries(db_path, 2024)

        assert result is not None
        expected_keys = {
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
        }
        assert set(result[0].keys()) == expected_keys

    def test_results_ordered_by_round(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        records = [
            {**_SAMPLE_RACE_ENTRY, "round": 3},
            {**_SAMPLE_RACE_ENTRY, "round": 1},
            {**_SAMPLE_RACE_ENTRY, "round": 2},
        ]
        upsert_race_entries(db_path, records)

        result = get_race_entries(db_path, 2024)

        assert result is not None
        assert [r["round"] for r in result] == [1, 2, 3]

    def test_isolates_by_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        records = [
            {**_SAMPLE_RACE_ENTRY, "year": 2023},
            {**_SAMPLE_RACE_ENTRY, "year": 2024},
        ]
        upsert_race_entries(db_path, records)

        result_2024 = get_race_entries(db_path, 2024)
        result_2023 = get_race_entries(db_path, 2023)

        assert result_2024 is not None
        assert len(result_2024) == 1
        assert result_2024[0]["year"] == 2024

        assert result_2023 is not None
        assert len(result_2023) == 1
        assert result_2023[0]["year"] == 2023


class TestGetQualifyingEntries:
    """Tests for get_qualifying_entries."""

    def test_returns_none_when_db_does_not_exist(self, tmp_path):
        db_path = tmp_path / "nonexistent.duckdb"
        result = get_qualifying_entries(db_path, 2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        upsert_qualifying_entries(db_path, [_SAMPLE_QUALIFYING_ENTRY])

        result = get_qualifying_entries(db_path, 2023)

        assert result is None

    def test_returns_rows_for_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        upsert_qualifying_entries(db_path, [_SAMPLE_QUALIFYING_ENTRY])

        result = get_qualifying_entries(db_path, 2024)

        assert result is not None
        assert len(result) == 1
        assert result[0]["driver_id"] == "max_verstappen"

    def test_returns_dicts_with_correct_keys(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)
        upsert_qualifying_entries(db_path, [_SAMPLE_QUALIFYING_ENTRY])

        result = get_qualifying_entries(db_path, 2024)

        assert result is not None
        expected_keys = {
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
        }
        assert set(result[0].keys()) == expected_keys

    def test_results_ordered_by_round(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        records = [
            {**_SAMPLE_QUALIFYING_ENTRY, "round": 3},
            {**_SAMPLE_QUALIFYING_ENTRY, "round": 1},
            {**_SAMPLE_QUALIFYING_ENTRY, "round": 2},
        ]
        upsert_qualifying_entries(db_path, records)

        result = get_qualifying_entries(db_path, 2024)

        assert result is not None
        assert [r["round"] for r in result] == [1, 2, 3]

    def test_isolates_by_year(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        init_elo_tables(db_path)

        records = [
            {**_SAMPLE_QUALIFYING_ENTRY, "year": 2023},
            {**_SAMPLE_QUALIFYING_ENTRY, "year": 2024},
        ]
        upsert_qualifying_entries(db_path, records)

        result_2024 = get_qualifying_entries(db_path, 2024)
        result_2023 = get_qualifying_entries(db_path, 2023)

        assert result_2024 is not None
        assert len(result_2024) == 1
        assert result_2024[0]["year"] == 2024

        assert result_2023 is not None
        assert len(result_2023) == 1
        assert result_2023[0]["year"] == 2023


class TestCategorizeDnf:
    """Tests for categorize_dnf."""

    def test_finished_returns_none(self):
        assert categorize_dnf("Finished") == "none"

    def test_lapped_returns_none(self):
        assert categorize_dnf("+1 Lap") == "none"
        assert categorize_dnf("+3 Laps") == "none"
        assert categorize_dnf("Lapped") == "none"

    def test_empty_string_returns_none(self):
        assert categorize_dnf("") == "none"

    def test_mechanical_engine(self):
        assert categorize_dnf("Engine") == "mechanical"

    def test_mechanical_gearbox(self):
        assert categorize_dnf("Gearbox") == "mechanical"

    def test_mechanical_power_unit(self):
        # Tests partial-match path since frozenset has "power unit"
        assert categorize_dnf("Power Unit") == "mechanical"

    def test_mechanical_tyre(self):
        assert categorize_dnf("Tyre") == "mechanical"

    def test_mechanical_hydraulics(self):
        assert categorize_dnf("Hydraulics") == "mechanical"

    def test_mechanical_vibrations(self):
        assert categorize_dnf("Vibrations") == "mechanical"

    def test_mechanical_oil_leak(self):
        assert categorize_dnf("Oil Leak") == "mechanical"

    def test_mechanical_puncture(self):
        assert categorize_dnf("Puncture") == "mechanical"

    def test_non_competitive_withdrew(self):
        assert categorize_dnf("Withdrew") == "mechanical"

    def test_non_competitive_injury(self):
        assert categorize_dnf("Injury") == "mechanical"

    def test_non_competitive_illness(self):
        assert categorize_dnf("Illness") == "mechanical"

    def test_crash_accident(self):
        assert categorize_dnf("Accident") == "crash"

    def test_crash_collision(self):
        assert categorize_dnf("Collision") == "crash"

    def test_crash_spun_off(self):
        assert categorize_dnf("Spun Off") == "crash"

    def test_crash_retired_catchall(self):
        assert categorize_dnf("Retired") == "crash"

    def test_unknown_status_returns_crash(self):
        # Unknown statuses fall through to crash (ambiguous retirement)
        assert categorize_dnf("Disqualified") == "crash"

    def test_case_insensitive(self):
        assert categorize_dnf("ENGINE") == "mechanical"
        assert categorize_dnf("accident") == "crash"
        assert categorize_dnf("FINISHED") == "none"
