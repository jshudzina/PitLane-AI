"""Tests for TeammateNormaliser in pitlane_elo.separation.decompose."""

from __future__ import annotations

from pitlane_elo.data import RaceEntry
from pitlane_elo.separation.decompose import TeammateData, TeammateNormaliser


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _entry(
    driver_id: str,
    team: str,
    finish: int | None,
    laps: int = 57,
) -> RaceEntry:
    return {
        "year": 2024,
        "round": 1,
        "session_type": "R",
        "driver_id": driver_id,
        "team": team,
        "laps_completed": laps,
        "status": "Finished" if finish is not None else "Retired",
        "dnf_category": "none",
        "is_wet_race": False,
        "is_street_circuit": False,
        "finish_position": finish,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTeammateNormaliser:
    def test_empty_entries_returns_empty(self) -> None:
        norm = TeammateNormaliser()
        result = norm.record([], {})
        assert result == []
        assert norm.history == {}

    def test_single_driver_per_team_skipped(self) -> None:
        """One driver per team → no teammate pair → no records."""
        entries = [
            _entry("A", "TeamA", 1),
            _entry("B", "TeamB", 2),
        ]
        ratings = {"A": 1.0, "B": -0.5}
        norm = TeammateNormaliser()
        result = norm.record(entries, ratings)
        assert result == []
        assert norm.history == {}

    def test_two_teams_standard_case(self) -> None:
        """Standard 4-driver, 2-team race produces 4 records (bidirectional)."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", 2),
            _entry("B1", "TeamB", 3),
            _entry("B2", "TeamB", 4),
        ]
        ratings = {"A1": 2.0, "A2": 1.0, "B1": -0.5, "B2": -1.5}
        norm = TeammateNormaliser()
        result = norm.record(entries, ratings)

        assert len(result) == 4
        assert len(norm.history["A1"]) == 1
        assert len(norm.history["A2"]) == 1
        assert len(norm.history["B1"]) == 1
        assert len(norm.history["B2"]) == 1

    def test_delta_values_correct(self) -> None:
        """Delta = driver_rating - teammate_rating."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", 2),
        ]
        ratings = {"A1": 3.0, "A2": 1.0}
        norm = TeammateNormaliser()
        norm.record(entries, ratings)

        rec_a1 = norm.history["A1"][0]
        assert rec_a1["driver_rating"] == 3.0
        assert rec_a1["teammate_rating"] == 1.0
        assert rec_a1["delta"] == 2.0

    def test_delta_sign_symmetric(self) -> None:
        """A→B and B→A records have opposite-sign deltas."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", 2),
        ]
        ratings = {"A1": 3.0, "A2": 1.0}
        norm = TeammateNormaliser()
        norm.record(entries, ratings)

        assert norm.history["A1"][0]["delta"] == -norm.history["A2"][0]["delta"]

    def test_dnf_driver_excluded(self) -> None:
        """Driver with finish_position=None → their team has ≤1 valid finisher → no records."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", None),  # DNF, no finish_position
            _entry("B1", "TeamB", 3),
            _entry("B2", "TeamB", 4),
        ]
        ratings = {"A1": 1.0, "A2": 0.5, "B1": -0.5, "B2": -1.0}
        norm = TeammateNormaliser()
        result = norm.record(entries, ratings)

        # TeamA produces no records (only A1 has finish_position)
        assert "A1" not in norm.history
        assert "A2" not in norm.history
        # TeamB still produces 2 records
        assert len(result) == 2

    def test_both_dnf_team_skipped(self) -> None:
        """Both drivers with no finish_position → team skipped entirely."""
        entries = [
            _entry("A1", "TeamA", None),
            _entry("A2", "TeamA", None),
        ]
        ratings = {"A1": 1.0, "A2": 0.5}
        norm = TeammateNormaliser()
        result = norm.record(entries, ratings)
        assert result == []

    def test_history_accumulates_across_races(self) -> None:
        """Calling record() twice grows history length to 2 per driver."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", 2),
        ]
        ratings = {"A1": 1.0, "A2": -1.0}
        norm = TeammateNormaliser()
        norm.record(entries, ratings)
        norm.record(entries, ratings)

        assert len(norm.history["A1"]) == 2
        assert len(norm.history["A2"]) == 2

    def test_driver_missing_from_ratings_skipped(self) -> None:
        """Driver not present in ratings dict → their team is skipped."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", 2),
        ]
        # A2 missing from ratings
        ratings = {"A1": 1.0}
        norm = TeammateNormaliser()
        result = norm.record(entries, ratings)
        assert result == []

    def test_three_car_team_uses_two_best(self) -> None:
        """3-car team: only the two drivers with lowest finish_position are used."""
        entries = [
            _entry("A1", "TeamA", 1),
            _entry("A2", "TeamA", 3),
            _entry("A3", "TeamA", 5),  # third car — should be ignored
        ]
        ratings = {"A1": 3.0, "A2": 1.0, "A3": -2.0}
        norm = TeammateNormaliser()
        result = norm.record(entries, ratings)

        assert len(result) == 2
        driver_ids = {r["driver_id"] for r in result}
        assert driver_ids == {"A1", "A2"}
        assert "A3" not in norm.history

    def test_year_round_preserved_in_record(self) -> None:
        """TeammateData carries year and round from the entries."""
        entries = [
            {**_entry("A1", "TeamA", 1), "year": 2023, "round": 5},
            {**_entry("A2", "TeamA", 2), "year": 2023, "round": 5},
        ]
        ratings = {"A1": 1.0, "A2": 0.5}
        norm = TeammateNormaliser()
        norm.record(entries, ratings)

        rec = norm.history["A1"][0]
        assert rec["year"] == 2023
        assert rec["round"] == 5
