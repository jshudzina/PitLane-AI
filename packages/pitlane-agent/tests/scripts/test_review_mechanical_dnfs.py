"""Tests for review_mechanical_dnfs script helpers."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest
from pitlane_agent.utils.elo_db import RaceEntry, init_elo_tables, upsert_race_entries
from pitlane_agent.utils.stats_db import init_db as init_stats_db

# Import the script module directly since it lives outside the package src tree.
_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "review_mechanical_dnfs.py"
_spec = importlib.util.spec_from_file_location("review_mechanical_dnfs", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("review_mechanical_dnfs", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_fetch_mechanical_dnfs = _mod._fetch_mechanical_dnfs
_build_user_prompt = _mod._build_user_prompt
_classify_with_agent = _mod._classify_with_agent
_parse_verdict_from_text = _mod._parse_verdict_from_text
_update_dnf_category = _mod._update_dnf_category
_review_async = _mod._review_async


def _make_entry(**overrides) -> RaceEntry:
    """Build a minimal RaceEntry dict with sensible defaults."""
    base: RaceEntry = {
        "year": 2024,
        "round": 2,
        "session_type": "R",
        "driver_id": "stroll",
        "abbreviation": "STR",
        "team": "Aston Martin",
        "grid_position": 10,
        "finish_position": None,
        "laps_completed": 15,
        "status": "Retired",
        "dnf_category": "mechanical",
        "is_wet_race": False,
        "is_street_circuit": False,
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _make_result_message(structured_output=None):
    """Build a mock ResultMessage with the given structured_output."""
    from claude_agent_sdk.types import ResultMessage

    return ResultMessage(
        subtype="result",
        duration_ms=100,
        duration_api_ms=80,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        structured_output=structured_output,
    )


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    """Create a temporary DuckDB with the race_entries and session_stats tables."""
    db_path = tmp_path / "test.duckdb"
    init_elo_tables(db_path)
    init_stats_db(db_path)
    return db_path


class TestFetchMechanicalDnfs:
    def test_returns_only_mechanical(self, db: Path):
        entries = [
            _make_entry(driver_id="stroll", dnf_category="mechanical"),
            _make_entry(driver_id="hamilton", dnf_category="crash"),
            _make_entry(driver_id="verstappen", dnf_category="none", status="Finished"),
        ]
        upsert_race_entries(db, entries)

        result = _fetch_mechanical_dnfs(db, 2024)
        assert len(result) == 1
        assert result[0]["driver_id"] == "stroll"

    def test_filters_by_year(self, db: Path):
        entries = [
            _make_entry(year=2023, driver_id="stroll", dnf_category="mechanical"),
            _make_entry(year=2024, driver_id="alonso", dnf_category="mechanical"),
        ]
        upsert_race_entries(db, entries)

        result = _fetch_mechanical_dnfs(db, 2024)
        assert len(result) == 1
        assert result[0]["driver_id"] == "alonso"

    def test_filters_by_round(self, db: Path):
        entries = [
            _make_entry(round=1, driver_id="stroll", dnf_category="mechanical"),
            _make_entry(round=2, driver_id="alonso", dnf_category="mechanical"),
        ]
        upsert_race_entries(db, entries)

        result = _fetch_mechanical_dnfs(db, 2024, round_numbers=[2])
        assert len(result) == 1
        assert result[0]["driver_id"] == "alonso"

    def test_empty_result(self, db: Path):
        result = _fetch_mechanical_dnfs(db, 2024)
        assert result == []


class TestBuildUserPrompt:
    def test_includes_driver_and_event_name(self):
        entry = {
            "year": 2024,
            "round": 8,
            "session_type": "R",
            "driver_id": "stroll",
            "abbreviation": "STR",
            "team": "Aston Martin",
            "laps_completed": 15,
            "status": "Retired",
            "event_name": "Monaco Grand Prix",
        }
        prompt = _build_user_prompt(entry)
        assert "STR" in prompt
        assert "Aston Martin" in prompt
        assert "Monaco Grand Prix" in prompt
        assert "2024" in prompt
        assert "Race" in prompt

    def test_falls_back_to_round_when_no_event_name(self):
        entry = {
            "year": 2024,
            "round": 2,
            "session_type": "R",
            "driver_id": "stroll",
            "abbreviation": "STR",
            "team": "Aston Martin",
            "laps_completed": 15,
            "status": "Retired",
            "event_name": None,
        }
        prompt = _build_user_prompt(entry)
        assert "Round 2" in prompt

    def test_sprint_session_label(self):
        entry = {
            "year": 2024,
            "round": 5,
            "session_type": "S",
            "driver_id": "stroll",
            "abbreviation": "STR",
            "team": "Aston Martin",
            "laps_completed": 8,
            "status": "Retired",
            "event_name": "Chinese Grand Prix",
        }
        prompt = _build_user_prompt(entry)
        assert "Sprint" in prompt

    def test_falls_back_to_driver_id_when_no_abbreviation(self):
        entry = {
            "year": 2024,
            "round": 2,
            "session_type": "R",
            "driver_id": "stroll",
            "abbreviation": None,
            "team": "Aston Martin",
            "laps_completed": 15,
            "status": "Retired",
            "event_name": None,
        }
        prompt = _build_user_prompt(entry)
        assert "stroll" in prompt


class TestClassifyWithAgent:
    @pytest.mark.asyncio
    async def test_extracts_crash_verdict(self):
        result_msg = _make_result_message(structured_output={"verdict": "crash", "evidence": "Hit the wall at turn 22"})

        async def mock_query(**kwargs):
            yield result_msg

        with patch.object(_mod, "query", side_effect=mock_query):
            result = await _classify_with_agent(
                {
                    "year": 2024,
                    "round": 2,
                    "session_type": "R",
                    "driver_id": "stroll",
                    "abbreviation": "STR",
                    "team": "Aston Martin",
                    "laps_completed": 15,
                    "status": "Retired",
                },
            )
        assert result == {"verdict": "crash", "evidence": "Hit the wall at turn 22"}

    @pytest.mark.asyncio
    async def test_extracts_mechanical_verdict(self):
        result_msg = _make_result_message(
            structured_output={"verdict": "mechanical", "evidence": "Engine failure confirmed"}
        )

        async def mock_query(**kwargs):
            yield result_msg

        with patch.object(_mod, "query", side_effect=mock_query):
            result = await _classify_with_agent(
                {
                    "year": 2024,
                    "round": 3,
                    "session_type": "R",
                    "driver_id": "alonso",
                    "abbreviation": "ALO",
                    "team": "Aston Martin",
                    "laps_completed": 30,
                    "status": "Retired",
                },
            )
        assert result["verdict"] == "mechanical"

    @pytest.mark.asyncio
    async def test_falls_back_to_text_result_with_crash_keyword(self):
        """When structured_output is None but result text mentions a crash."""
        result_msg = _make_result_message(structured_output=None)
        result_msg.result = "Magnussen crashed into the barrier at Beau Rivage on lap 1."

        async def mock_query(**kwargs):
            yield result_msg

        with patch.object(_mod, "query", side_effect=mock_query):
            result = await _classify_with_agent(
                {
                    "year": 2024,
                    "round": 8,
                    "session_type": "R",
                    "driver_id": "magnussen",
                    "abbreviation": "MAG",
                    "team": "Haas",
                    "laps_completed": 0,
                    "status": "Retired",
                },
            )
        assert result is not None
        assert result["verdict"] == "crash"

    @pytest.mark.asyncio
    async def test_falls_back_to_json_in_text_result(self):
        """When structured_output is None but result text contains JSON."""
        result_msg = _make_result_message(structured_output=None)
        result_msg.result = 'Based on my research: {"verdict": "mechanical", "evidence": "Power unit failure"}'

        async def mock_query(**kwargs):
            yield result_msg

        with patch.object(_mod, "query", side_effect=mock_query):
            result = await _classify_with_agent(
                {
                    "year": 2024,
                    "round": 3,
                    "session_type": "R",
                    "driver_id": "alonso",
                    "abbreviation": "ALO",
                    "team": "Aston Martin",
                    "laps_completed": 30,
                    "status": "Retired",
                },
            )
        assert result == {"verdict": "mechanical", "evidence": "Power unit failure"}

    @pytest.mark.asyncio
    async def test_returns_none_when_no_output_at_all(self):
        result_msg = _make_result_message(structured_output=None)
        # result is also None (default)

        async def mock_query(**kwargs):
            yield result_msg

        with patch.object(_mod, "query", side_effect=mock_query):
            result = await _classify_with_agent(
                {
                    "year": 2024,
                    "round": 2,
                    "session_type": "R",
                    "driver_id": "stroll",
                    "abbreviation": "STR",
                    "team": "Aston Martin",
                    "laps_completed": 15,
                    "status": "Retired",
                },
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_verdict_key(self):
        result_msg = _make_result_message(structured_output={"evidence": "some text but no verdict"})

        async def mock_query(**kwargs):
            yield result_msg

        with patch.object(_mod, "query", side_effect=mock_query):
            result = await _classify_with_agent(
                {
                    "year": 2024,
                    "round": 2,
                    "session_type": "R",
                    "driver_id": "stroll",
                    "abbreviation": "STR",
                    "team": "Aston Martin",
                    "laps_completed": 15,
                    "status": "Retired",
                },
            )
        assert result is None


class TestParseVerdictFromText:
    def test_extracts_json_from_text(self):
        text = 'Here is my analysis: {"verdict": "crash", "evidence": "Wall contact at T22"}'
        result = _parse_verdict_from_text(text)
        assert result == {"verdict": "crash", "evidence": "Wall contact at T22"}

    def test_keyword_fallback_crash(self):
        text = "The driver had a collision with the barrier on lap 5."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "crash"

    def test_keyword_fallback_hit_the_wall(self):
        text = "Stroll hit the wall at turn 22 during the race."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "crash"

    def test_keyword_fallback_spun_out(self):
        text = "Perez spun out at turn 4 and ended up in the gravel trap."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "crash"

    def test_keyword_fallback_beached(self):
        text = "Tsunoda beached his car in the gravel at turn 9."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "crash"

    def test_keyword_fallback_off_track(self):
        text = "Sainz went off track and into the tyre barrier on lap 12."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "crash"

    def test_keyword_fallback_mechanical_engine(self):
        text = "Alonso retired due to a power unit failure on lap 30."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "mechanical"

    def test_keyword_fallback_mechanical_gearbox(self):
        text = "The team confirmed a gearbox issue forced the retirement."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "mechanical"

    def test_keyword_fallback_mechanical_disqualified(self):
        text = "The driver was disqualified after post-race scrutineering."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "mechanical"

    def test_keyword_fallback_mechanical_plank(self):
        text = "Hamilton was excluded due to excessive plank wear found in scrutineering."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "mechanical"

    def test_crash_takes_priority_over_mechanical(self):
        text = "The driver had a collision which caused suspension failure."
        result = _parse_verdict_from_text(text)
        assert result is not None
        assert result["verdict"] == "crash"

    def test_returns_none_for_ambiguous_text(self):
        text = "The driver retired from the race due to an unspecified issue."
        result = _parse_verdict_from_text(text)
        assert result is None

    def test_returns_none_for_empty_text(self):
        result = _parse_verdict_from_text("")
        assert result is None


class TestUpdateDnfCategory:
    def test_updates_mechanical_to_crash(self, db: Path):
        entries = [
            _make_entry(driver_id="stroll", dnf_category="mechanical"),
            _make_entry(driver_id="alonso", dnf_category="mechanical", round=3),
        ]
        upsert_race_entries(db, entries)

        updates = [{"year": 2024, "round": 2, "session_type": "R", "driver_id": "stroll"}]
        count = _update_dnf_category(db, updates)
        assert count == 1

        # Verify the update
        con = duckdb.connect(str(db), read_only=True)
        try:
            row = con.execute(
                "SELECT dnf_category FROM race_entries WHERE year = 2024 AND round = 2 AND driver_id = 'stroll'"
            ).fetchone()
            assert row[0] == "crash"

            # Alonso should remain mechanical
            row2 = con.execute(
                "SELECT dnf_category FROM race_entries WHERE year = 2024 AND round = 3 AND driver_id = 'alonso'"
            ).fetchone()
            assert row2[0] == "mechanical"
        finally:
            con.close()

    def test_empty_updates_returns_zero(self, db: Path):
        count = _update_dnf_category(db, [])
        assert count == 0


class TestReviewAsyncRetry:
    @pytest.mark.asyncio
    async def test_retries_on_none_result(self, db: Path):
        """Agent is called again when first attempt returns no output."""
        entries = [
            _make_entry(driver_id="hulkenberg", abbreviation="HUL"),
        ]
        upsert_race_entries(db, entries)

        call_count = 0

        async def mock_classify(entry, model="haiku"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return {"verdict": "crash", "evidence": "Hit the wall"}

        with patch.object(_mod, "_classify_with_agent", side_effect=mock_classify):
            await _review_async(db, entries, dry_run=True, model="haiku")

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_exception(self, db: Path):
        """Agent is retried when it raises an exception."""
        entries = [
            _make_entry(driver_id="hulkenberg", abbreviation="HUL"),
        ]
        upsert_race_entries(db, entries)

        call_count = 0

        async def mock_classify(entry, model="haiku"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API timeout")
            return {"verdict": "mechanical", "evidence": "Engine failure"}

        with patch.object(_mod, "_classify_with_agent", side_effect=mock_classify):
            await _review_async(db, entries, dry_run=True, model="haiku")

        assert call_count == 2
