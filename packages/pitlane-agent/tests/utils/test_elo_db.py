"""Tests for elo_db utility module using Parquet files."""

import duckdb
from pitlane_agent.utils.elo_db import (
    QualifyingEntry,
    RaceEntry,
    categorize_dnf,
    get_qualifying_entries,
    get_race_entries,
    upsert_qualifying_entries,
    upsert_race_entries,
)

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
    "session_type": "Q",
    "driver_id": "max_verstappen",
    "abbreviation": "VER",
    "team": "Red Bull Racing",
    "q1_time_s": 87.123,
    "q2_time_s": 86.456,
    "q3_time_s": 85.789,
    "best_q_time_s": 85.789,
    "position": 1,
}


def _count_parquet(parquet_path, where: str = "") -> int:
    con = duckdb.connect()
    sql = f"SELECT COUNT(*) FROM read_parquet('{parquet_path}')"
    if where:
        sql += f" WHERE {where}"
    result = con.execute(sql).fetchone()
    con.close()
    return result[0]


def _query_parquet(parquet_path, cols: str, where: str = ""):
    con = duckdb.connect()
    sql = f"SELECT {cols} FROM read_parquet('{parquet_path}')"
    if where:
        sql += f" WHERE {where}"
    result = con.execute(sql).fetchone()
    con.close()
    return result


class TestUpsertRaceEntries:
    """Tests for upsert_race_entries."""

    def test_inserts_single_record(self, tmp_path):
        upsert_race_entries(tmp_path, [_SAMPLE_RACE_ENTRY])

        parquet_path = tmp_path / "race_entries" / "2024.parquet"
        assert parquet_path.exists()
        assert _count_parquet(parquet_path) == 1

    def test_inserts_multiple_records(self, tmp_path):
        records = [
            {**_SAMPLE_RACE_ENTRY, "driver_id": "max_verstappen"},
            {**_SAMPLE_RACE_ENTRY, "driver_id": "hamilton"},
            {**_SAMPLE_RACE_ENTRY, "driver_id": "leclerc"},
        ]
        upsert_race_entries(tmp_path, records)

        parquet_path = tmp_path / "race_entries" / "2024.parquet"
        assert _count_parquet(parquet_path) == 3

    def test_replaces_existing_record(self, tmp_path):
        upsert_race_entries(tmp_path, [_SAMPLE_RACE_ENTRY])
        updated = {**_SAMPLE_RACE_ENTRY, "laps_completed": 42}
        upsert_race_entries(tmp_path, [updated])

        parquet_path = tmp_path / "race_entries" / "2024.parquet"
        result = _query_parquet(
            parquet_path,
            "laps_completed",
            "year = 2024 AND round = 1 AND session_type = 'R' AND driver_id = 'max_verstappen'",
        )
        assert result[0] == 42

    def test_empty_records_is_noop(self, tmp_path):
        upsert_race_entries(tmp_path, [])
        assert not (tmp_path / "race_entries" / "2024.parquet").exists()

    def test_nullable_grid_and_finish_position(self, tmp_path):
        record = {**_SAMPLE_RACE_ENTRY, "grid_position": None, "finish_position": None}
        upsert_race_entries(tmp_path, [record])

        parquet_path = tmp_path / "race_entries" / "2024.parquet"
        result = _query_parquet(parquet_path, "grid_position, finish_position", "driver_id = 'max_verstappen'")
        assert result[0] is None
        assert result[1] is None

    def test_sprint_and_race_coexist(self, tmp_path):
        race = {**_SAMPLE_RACE_ENTRY, "session_type": "R"}
        sprint = {**_SAMPLE_RACE_ENTRY, "session_type": "S"}
        upsert_race_entries(tmp_path, [race, sprint])

        parquet_path = tmp_path / "race_entries" / "2024.parquet"
        assert _count_parquet(parquet_path, "driver_id = 'max_verstappen'") == 2

    def test_nullable_abbreviation(self, tmp_path):
        record = {**_SAMPLE_RACE_ENTRY, "driver_id": "farina", "abbreviation": None}
        upsert_race_entries(tmp_path, [record])

        parquet_path = tmp_path / "race_entries" / "2024.parquet"
        result = _query_parquet(parquet_path, "abbreviation", "driver_id = 'farina'")
        assert result[0] is None

    def test_year_partitioned_files(self, tmp_path):
        records = [
            {**_SAMPLE_RACE_ENTRY, "year": 2023},
            {**_SAMPLE_RACE_ENTRY, "year": 2024},
        ]
        upsert_race_entries(tmp_path, records)

        assert (tmp_path / "race_entries" / "2023.parquet").exists()
        assert (tmp_path / "race_entries" / "2024.parquet").exists()


class TestUpsertQualifyingEntries:
    """Tests for upsert_qualifying_entries."""

    def test_inserts_single_record(self, tmp_path):
        upsert_qualifying_entries(tmp_path, [_SAMPLE_QUALIFYING_ENTRY])

        parquet_path = tmp_path / "qualifying_entries" / "2024.parquet"
        assert parquet_path.exists()
        assert _count_parquet(parquet_path) == 1

    def test_inserts_multiple_records(self, tmp_path):
        records = [
            {**_SAMPLE_QUALIFYING_ENTRY, "driver_id": "max_verstappen", "position": 1},
            {**_SAMPLE_QUALIFYING_ENTRY, "driver_id": "hamilton", "position": 2},
            {**_SAMPLE_QUALIFYING_ENTRY, "driver_id": "leclerc", "position": 3},
        ]
        upsert_qualifying_entries(tmp_path, records)

        parquet_path = tmp_path / "qualifying_entries" / "2024.parquet"
        assert _count_parquet(parquet_path) == 3

    def test_replaces_existing_record(self, tmp_path):
        upsert_qualifying_entries(tmp_path, [_SAMPLE_QUALIFYING_ENTRY])
        updated = {**_SAMPLE_QUALIFYING_ENTRY, "best_q_time_s": 84.999}
        upsert_qualifying_entries(tmp_path, [updated])

        parquet_path = tmp_path / "qualifying_entries" / "2024.parquet"
        result = _query_parquet(parquet_path, "best_q_time_s", "driver_id = 'max_verstappen' AND session_type = 'Q'")
        assert result[0] == 84.999

    def test_empty_records_is_noop(self, tmp_path):
        upsert_qualifying_entries(tmp_path, [])
        assert not (tmp_path / "qualifying_entries" / "2024.parquet").exists()

    def test_nullable_q2_and_q3_times(self, tmp_path):
        record = {
            **_SAMPLE_QUALIFYING_ENTRY,
            "driver_id": "bottas",
            "q2_time_s": None,
            "q3_time_s": None,
            "best_q_time_s": 87.123,
            "position": 16,
        }
        upsert_qualifying_entries(tmp_path, [record])

        parquet_path = tmp_path / "qualifying_entries" / "2024.parquet"
        result = _query_parquet(parquet_path, "q2_time_s, q3_time_s", "driver_id = 'bottas'")
        assert result[0] is None
        assert result[1] is None

    def test_q_and_sq_coexist_for_same_round(self, tmp_path):
        q_entry = {**_SAMPLE_QUALIFYING_ENTRY, "session_type": "Q"}
        sq_entry = {**_SAMPLE_QUALIFYING_ENTRY, "session_type": "SQ"}
        upsert_qualifying_entries(tmp_path, [q_entry, sq_entry])

        parquet_path = tmp_path / "qualifying_entries" / "2024.parquet"
        assert _count_parquet(parquet_path, "driver_id = 'max_verstappen'") == 2

    def test_all_q_times_null_pre2006(self, tmp_path):
        record: QualifyingEntry = {
            "year": 1995,
            "round": 1,
            "session_type": "Q",
            "driver_id": "schumacher",
            "abbreviation": None,
            "team": "Benetton",
            "q1_time_s": None,
            "q2_time_s": None,
            "q3_time_s": None,
            "best_q_time_s": None,
            "position": 1,
        }
        upsert_qualifying_entries(tmp_path, [record])

        parquet_path = tmp_path / "qualifying_entries" / "1995.parquet"
        result = _query_parquet(
            parquet_path,
            "q1_time_s, q2_time_s, q3_time_s, best_q_time_s",
            "driver_id = 'schumacher'",
        )
        assert all(v is None for v in result)


class TestGetRaceEntries:
    """Tests for get_race_entries."""

    def test_returns_none_when_parquet_does_not_exist(self, tmp_path):
        result = get_race_entries(tmp_path, 2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path):
        upsert_race_entries(tmp_path, [_SAMPLE_RACE_ENTRY])
        result = get_race_entries(tmp_path, 2023)
        assert result is None

    def test_returns_rows_for_year(self, tmp_path):
        upsert_race_entries(tmp_path, [_SAMPLE_RACE_ENTRY])
        result = get_race_entries(tmp_path, 2024)

        assert result is not None
        assert len(result) == 1
        assert result[0]["driver_id"] == "max_verstappen"

    def test_returns_dicts_with_correct_keys(self, tmp_path):
        upsert_race_entries(tmp_path, [_SAMPLE_RACE_ENTRY])
        result = get_race_entries(tmp_path, 2024)

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
        records = [
            {**_SAMPLE_RACE_ENTRY, "round": 3},
            {**_SAMPLE_RACE_ENTRY, "round": 1},
            {**_SAMPLE_RACE_ENTRY, "round": 2},
        ]
        upsert_race_entries(tmp_path, records)
        result = get_race_entries(tmp_path, 2024)

        assert result is not None
        assert [r["round"] for r in result] == [1, 2, 3]

    def test_isolates_by_year(self, tmp_path):
        records = [
            {**_SAMPLE_RACE_ENTRY, "year": 2023},
            {**_SAMPLE_RACE_ENTRY, "year": 2024},
        ]
        upsert_race_entries(tmp_path, records)

        result_2024 = get_race_entries(tmp_path, 2024)
        result_2023 = get_race_entries(tmp_path, 2023)

        assert result_2024 is not None and len(result_2024) == 1 and result_2024[0]["year"] == 2024
        assert result_2023 is not None and len(result_2023) == 1 and result_2023[0]["year"] == 2023


class TestGetQualifyingEntries:
    """Tests for get_qualifying_entries."""

    def test_returns_none_when_parquet_does_not_exist(self, tmp_path):
        result = get_qualifying_entries(tmp_path, 2024)
        assert result is None

    def test_returns_none_when_no_rows_for_year(self, tmp_path):
        upsert_qualifying_entries(tmp_path, [_SAMPLE_QUALIFYING_ENTRY])
        result = get_qualifying_entries(tmp_path, 2023)
        assert result is None

    def test_returns_rows_for_year(self, tmp_path):
        upsert_qualifying_entries(tmp_path, [_SAMPLE_QUALIFYING_ENTRY])
        result = get_qualifying_entries(tmp_path, 2024)

        assert result is not None
        assert len(result) == 1
        assert result[0]["driver_id"] == "max_verstappen"

    def test_returns_dicts_with_correct_keys(self, tmp_path):
        upsert_qualifying_entries(tmp_path, [_SAMPLE_QUALIFYING_ENTRY])
        result = get_qualifying_entries(tmp_path, 2024)

        assert result is not None
        expected_keys = {
            "year",
            "round",
            "session_type",
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
        records = [
            {**_SAMPLE_QUALIFYING_ENTRY, "round": 3},
            {**_SAMPLE_QUALIFYING_ENTRY, "round": 1},
            {**_SAMPLE_QUALIFYING_ENTRY, "round": 2},
        ]
        upsert_qualifying_entries(tmp_path, records)
        result = get_qualifying_entries(tmp_path, 2024)

        assert result is not None
        assert [r["round"] for r in result] == [1, 2, 3]

    def test_isolates_by_year(self, tmp_path):
        records = [
            {**_SAMPLE_QUALIFYING_ENTRY, "year": 2023},
            {**_SAMPLE_QUALIFYING_ENTRY, "year": 2024},
        ]
        upsert_qualifying_entries(tmp_path, records)

        result_2024 = get_qualifying_entries(tmp_path, 2024)
        result_2023 = get_qualifying_entries(tmp_path, 2023)

        assert result_2024 is not None and len(result_2024) == 1 and result_2024[0]["year"] == 2024
        assert result_2023 is not None and len(result_2023) == 1 and result_2023[0]["year"] == 2023


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

    def test_mechanical_alternator(self):
        assert categorize_dnf("Alternator") == "mechanical"

    def test_mechanical_halfshaft(self):
        assert categorize_dnf("Halfshaft") == "mechanical"

    def test_mechanical_handling(self):
        assert categorize_dnf("Handling") == "mechanical"

    def test_mechanical_ignition(self):
        assert categorize_dnf("Ignition") == "mechanical"

    def test_mechanical_injection(self):
        assert categorize_dnf("Injection") == "mechanical"

    def test_mechanical_distributor(self):
        assert categorize_dnf("Distributor") == "mechanical"

    def test_mechanical_electronics(self):
        assert categorize_dnf("Electronics") == "mechanical"

    def test_mechanical_spark_plugs(self):
        assert categorize_dnf("Spark plugs") == "mechanical"

    def test_mechanical_axle(self):
        assert categorize_dnf("Axle") == "mechanical"

    def test_mechanical_drivetrain(self):
        assert categorize_dnf("Drivetrain") == "mechanical"

    def test_mechanical_power_loss(self):
        assert categorize_dnf("Power loss") == "mechanical"

    def test_mechanical_stalled(self):
        assert categorize_dnf("Stalled") == "mechanical"

    def test_non_competitive_injury(self):
        assert categorize_dnf("Injury") == "mechanical"

    def test_non_competitive_illness(self):
        assert categorize_dnf("Illness") == "mechanical"

    def test_mechanical_track_rod(self):
        assert categorize_dnf("Track rod") == "mechanical"

    def test_mechanical_generic_mechanical(self):
        assert categorize_dnf("Mechanical") == "mechanical"

    def test_mechanical_technical(self):
        assert categorize_dnf("Technical") == "mechanical"

    def test_non_competitive_driver_unwell(self):
        assert categorize_dnf("Driver unwell") == "mechanical"

    def test_non_competitive_injured(self):
        assert categorize_dnf("Injured") == "mechanical"

    def test_non_competitive_physical(self):
        assert categorize_dnf("Physical") == "mechanical"

    def test_non_competitive_driver_seat(self):
        assert categorize_dnf("Driver Seat") == "mechanical"

    def test_non_competitive_safety_concerns(self):
        assert categorize_dnf("Safety concerns") == "mechanical"

    def test_legality_excluded(self):
        assert categorize_dnf("Excluded") == "mechanical"

    def test_legality_underweight(self):
        assert categorize_dnf("Underweight") == "mechanical"

    def test_non_competitive_withdrew(self):
        assert categorize_dnf("Withdrew") == "mechanical"

    def test_legality_disqualified(self):
        assert categorize_dnf("Disqualified") == "mechanical"

    def test_crash_accident(self):
        assert categorize_dnf("Accident") == "crash"

    def test_crash_collision(self):
        assert categorize_dnf("Collision") == "crash"

    def test_crash_spun_off(self):
        assert categorize_dnf("Spun Off") == "crash"

    def test_crash_retired_catchall(self):
        assert categorize_dnf("Retired") == "crash"

    def test_unknown_status_returns_crash(self):
        assert categorize_dnf("SomeUnknownStatus") == "crash"

    def test_case_insensitive(self):
        assert categorize_dnf("ENGINE") == "mechanical"
        assert categorize_dnf("accident") == "crash"
        assert categorize_dnf("FINISHED") == "none"
