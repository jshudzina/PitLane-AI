"""Unit tests for pitlane_elo.cli_stories (pitlane-elo stories subcommands)."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
from click.testing import CliRunner
from pitlane_elo.cli_stories import stories

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SNAPSHOT_DDL = """
    year INTEGER NOT NULL,
    round INTEGER NOT NULL,
    session_type VARCHAR NOT NULL,
    driver_id VARCHAR NOT NULL,
    pre_race_rating DOUBLE NOT NULL,
    pre_race_k DOUBLE NOT NULL,
    win_probability DOUBLE NOT NULL,
    podium_probability DOUBLE NOT NULL,
    finish_position INTEGER,
    dnf_category VARCHAR NOT NULL
"""

_RACE_DDL = """
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
    is_wet_race       BOOLEAN NOT NULL,
    is_street_circuit BOOLEAN NOT NULL
"""


def _write_snapshot_parquet(data_dir: Path, rows: list[tuple]) -> None:
    snapshots_dir = data_dir / "elo_snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = snapshots_dir / "snapshots.parquet"
    con = duckdb.connect()
    try:
        con.execute(f"CREATE TABLE snaps ({_SNAPSHOT_DDL})")
        for row in rows:
            con.execute("INSERT INTO snaps VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", list(row))
        con.execute(f"COPY snaps TO '{parquet_path}' (FORMAT PARQUET)")
    finally:
        con.close()


def _write_race_parquet(data_dir: Path, rows: list[tuple]) -> None:
    """Write race entry tuples (year, round, session_type, driver_id, abbr, team,
    grid, finish, laps, status, dnf, is_wet, is_street) to parquet."""
    by_year: dict[int, list[tuple]] = {}
    for row in rows:
        by_year.setdefault(row[0], []).append(row)
    for year, year_rows in by_year.items():
        parquet_path = data_dir / "race_entries" / f"{year}.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE race_entries ({_RACE_DDL})")
            for row in year_rows:
                con.execute(
                    "INSERT INTO race_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    list(row),
                )
            con.execute(f"COPY race_entries TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        finally:
            con.close()


def _minimal_snapshots(year: int, round_num: int, n_drivers: int = 5) -> list[tuple]:
    """Minimal snapshot rows with no surprise or trend signals (finish == expected rank)."""
    return [(year, round_num, "R", f"D{i}", float(i), 0.1, 1.0 / (i + 1), 0.5, i + 1, "none") for i in range(n_drivers)]


def _minimal_race_rows(year: int, round_num: int, n_drivers: int = 5) -> list[tuple]:
    return [
        (year, round_num, "R", f"D{i}", None, "Team", i + 1, i + 1, 50, "Finished", "none", False, False)
        for i in range(n_drivers)
    ]


# ---------------------------------------------------------------------------
# detect — help and argument validation
# ---------------------------------------------------------------------------


class TestDetectHelp:
    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--help"])
        assert result.exit_code == 0

    def test_help_documents_year_and_round(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--help"])
        assert "--year" in result.output
        assert "--round" in result.output

    def test_help_documents_session_type_and_lookback(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--help"])
        assert "--session-type" in result.output
        assert "--trend-lookback" in result.output

    def test_help_documents_db_path(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--help"])
        assert "--db-path" in result.output


class TestDetectRequiredArgs:
    def test_missing_year_fails(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--round", "3"])
        assert result.exit_code != 0

    def test_missing_round_fails(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024"])
        assert result.exit_code != 0

    def test_invalid_session_type_fails(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--session-type", "Q"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# detect — output shape and content
# ---------------------------------------------------------------------------


class TestDetectOutput:
    def test_no_snapshots_exits_zero_with_empty_signals(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["story_count"] == 0
        assert data["signals"] == []

    def test_no_snapshots_output_contains_year_and_round(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["year"] == 2024
        assert data["round"] == 3

    def test_no_snapshots_includes_message(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert "message" in data

    def test_with_snapshots_output_is_valid_json(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)  # must not raise
        assert isinstance(data, dict)

    def test_with_snapshots_output_has_required_keys(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert {"year", "round", "session_type", "story_count", "signals"} <= set(data)

    def test_with_snapshots_year_round_echoed(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 7))
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "7", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["year"] == 2024
        assert data["round"] == 7

    def test_with_snapshots_session_type_echoed(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(
            stories,
            ["detect", "--year", "2024", "--round", "3", "--session-type", "R", "--db-path", str(tmp_path)],
        )
        data = json.loads(result.output)
        assert data["session_type"] == "R"

    def test_signals_is_list(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert isinstance(data["signals"], list)

    def test_story_count_matches_signals_length(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["story_count"] == len(data["signals"])

    def test_surprise_signal_present_in_output(self, tmp_path):
        # VER expected P20 (lowest win_prob), finishes P1 → surprise_over
        rows = [(2024, 3, "R", f"D{i}", float(i), 0.0, 1.0 / (i + 1), 0.5, i + 1, "none") for i in range(19)]
        rows.append((2024, 3, "R", "VER", 1.0, 0.0, 0.001, 0.01, 1, "none"))
        _write_snapshot_parquet(tmp_path, rows)
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["story_count"] > 0
        signal_types = {s["signal_type"] for s in data["signals"]}
        assert "surprise_over" in signal_types

    def test_each_signal_has_required_keys(self, tmp_path):
        rows = [(2024, 3, "R", f"D{i}", float(i), 0.0, 1.0 / (i + 1), 0.5, i + 1, "none") for i in range(19)]
        rows.append((2024, 3, "R", "VER", 1.0, 0.0, 0.001, 0.01, 1, "none"))
        _write_snapshot_parquet(tmp_path, rows)
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "3", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        required = {"signal_type", "driver_id", "year", "round", "value", "threshold", "narrative", "context"}
        for signal in data["signals"]:
            assert required <= set(signal), f"Signal missing keys: {required - set(signal)}"

    def test_trend_lookback_flag_accepted(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(
            stories,
            ["detect", "--year", "2024", "--round", "3", "--trend-lookback", "6", "--db-path", str(tmp_path)],
        )
        assert result.exit_code == 0

    def test_sprint_session_type_accepted(self, tmp_path):
        snap_rows = [(2024, 3, "S", f"D{i}", float(i), 0.1, 1.0 / (i + 1), 0.5, i + 1, "none") for i in range(5)]
        _write_snapshot_parquet(tmp_path, snap_rows)
        runner = CliRunner()
        result = runner.invoke(
            stories,
            ["detect", "--year", "2024", "--round", "3", "--session-type", "S", "--db-path", str(tmp_path)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["session_type"] == "S"

    def test_wrong_year_returns_empty_signals(self, tmp_path):
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["detect", "--year", "2025", "--round", "3", "--db-path", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["story_count"] == 0

    def test_exception_exits_1_with_error_json(self):
        from unittest.mock import patch

        with patch("pitlane_elo.cli_stories.detect_stories", side_effect=RuntimeError("snapshot missing")):
            runner = CliRunner()
            result = runner.invoke(stories, ["detect", "--year", "2024", "--round", "5"])
        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err
        assert "snapshot missing" in err["error"]


# ---------------------------------------------------------------------------
# season — help and argument validation
# ---------------------------------------------------------------------------


class TestSeasonHelp:
    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--help"])
        assert result.exit_code == 0

    def test_help_documents_year(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--help"])
        assert "--year" in result.output

    def test_missing_year_fails(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["season"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# season — output shape and content
# ---------------------------------------------------------------------------


class TestSeasonOutput:
    def test_no_race_entries_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_with_race_entries_and_snapshots_exits_zero(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_output_is_valid_json(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_output_has_required_keys(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert {"year", "session_type", "total_races", "races"} <= set(data)

    def test_year_echoed_in_output(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["year"] == 2024

    def test_total_races_matches_races_list(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["total_races"] == len(data["races"])

    def test_each_race_entry_has_required_keys(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        for race in data["races"]:
            assert {"year", "round", "story_count", "signals"} <= set(race)

    def test_story_count_matches_signals_per_race(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        for race in data["races"]:
            assert race["story_count"] == len(race["signals"])

    def test_multiple_rounds_all_present(self, tmp_path):
        race_rows = _minimal_race_rows(2024, 1) + _minimal_race_rows(2024, 2) + _minimal_race_rows(2024, 3)
        snap_rows = _minimal_snapshots(2024, 1) + _minimal_snapshots(2024, 2) + _minimal_snapshots(2024, 3)
        _write_race_parquet(tmp_path, race_rows)
        _write_snapshot_parquet(tmp_path, snap_rows)
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["total_races"] == 3
        rounds = {r["round"] for r in data["races"]}
        assert rounds == {1, 2, 3}

    def test_season_type_echoed(self, tmp_path):
        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--session-type", "R", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        assert data["session_type"] == "R"

    def test_surprise_signal_surfaced_in_season(self, tmp_path):
        # One race with an obvious surprise (expected last, finished first)
        snap_rows = [(2024, 1, "R", f"D{i}", float(i), 0.0, 1.0 / (i + 1), 0.5, i + 1, "none") for i in range(19)]
        snap_rows.append((2024, 1, "R", "VER", 1.0, 0.0, 0.001, 0.01, 1, "none"))
        race_rows = [
            (2024, 1, "R", f"D{i}", None, "Team", i + 1, i + 1, 50, "Finished", "none", False, False) for i in range(19)
        ]
        race_rows.append((2024, 1, "R", "VER", None, "Team", 20, 1, 50, "Finished", "none", False, False))
        _write_snapshot_parquet(tmp_path, snap_rows)
        _write_race_parquet(tmp_path, race_rows)
        runner = CliRunner()
        result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        data = json.loads(result.output)
        r1 = next(r for r in data["races"] if r["round"] == 1)
        assert r1["story_count"] > 0

    def test_exception_exits_1_with_error_json(self, tmp_path):
        from unittest.mock import patch

        _write_race_parquet(tmp_path, _minimal_race_rows(2024, 3))
        _write_snapshot_parquet(tmp_path, _minimal_snapshots(2024, 3))
        with patch("pitlane_elo.cli_stories.detect_stories", side_effect=RuntimeError("duckdb error")):
            runner = CliRunner()
            result = runner.invoke(stories, ["season", "--year", "2024", "--db-path", str(tmp_path)])
        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err
        assert "duckdb error" in err["error"]


# ---------------------------------------------------------------------------
# stories group — top-level help
# ---------------------------------------------------------------------------


class TestStoriesGroupHelp:
    def test_group_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["--help"])
        assert result.exit_code == 0

    def test_group_help_lists_detect_and_season(self):
        runner = CliRunner()
        result = runner.invoke(stories, ["--help"])
        assert "detect" in result.output
        assert "season" in result.output
