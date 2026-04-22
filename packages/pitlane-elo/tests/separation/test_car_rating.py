"""Tests for qualifying-based Car Rating (Rc) computation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pitlane_elo.data import QualifyingEntry, group_qualifying_by_session
from pitlane_elo.separation.car_rating import compute_rc_range, compute_session_rc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_qual_entry(
    driver_id: str,
    team: str,
    best_time: float | None,
    position: int,
    *,
    year: int = 2024,
    rnd: int = 1,
) -> QualifyingEntry:
    return {
        "year": year,
        "round": rnd,
        "session_type": "Q",
        "driver_id": driver_id,
        "team": team,
        "position": position,
        "best_q_time_s": best_time,
    }


# ---------------------------------------------------------------------------
# compute_session_rc unit tests
# ---------------------------------------------------------------------------


class TestComputeSessionRc:
    def test_empty_entries(self) -> None:
        assert compute_session_rc([]) == []

    def test_single_team_fastest(self) -> None:
        """A single team whose avg equals the session fastest gets Rc = 0."""
        entries = [
            _make_qual_entry("A", "TeamA", 90.0, 1),
            _make_qual_entry("B", "TeamA", 90.0, 2),
        ]
        result = compute_session_rc(entries)
        assert len(result) == 1
        assert result[0]["team"] == "TeamA"
        assert result[0]["rc"] == pytest.approx(0.0)
        assert result[0]["t_team_avg"] == pytest.approx(90.0)
        assert result[0]["t_fastest"] == pytest.approx(90.0)

    def test_two_teams(self) -> None:
        """Verify Rc values for two teams with known times."""
        entries = [
            # TeamA: drivers at 89.0 and 89.5 -> avg = 89.25
            _make_qual_entry("A1", "TeamA", 89.0, 1),
            _make_qual_entry("A2", "TeamA", 89.5, 2),
            # TeamB: drivers at 90.0 and 90.2 -> avg = 90.1
            _make_qual_entry("B1", "TeamB", 90.0, 3),
            _make_qual_entry("B2", "TeamB", 90.2, 4),
        ]
        result = compute_session_rc(entries)
        assert len(result) == 2

        # Results are sorted by team name
        rc_a = result[0]
        rc_b = result[1]
        assert rc_a["team"] == "TeamA"
        assert rc_b["team"] == "TeamB"

        # t_fastest = 89.0 (overall fastest)
        assert rc_a["t_fastest"] == pytest.approx(89.0)
        assert rc_b["t_fastest"] == pytest.approx(89.0)

        # TeamA: Rc = (89.25 - 89.0) / 89.0
        assert rc_a["rc"] == pytest.approx((89.25 - 89.0) / 89.0)
        assert rc_a["t_team_avg"] == pytest.approx(89.25)

        # TeamB: Rc = (90.1 - 89.0) / 89.0
        assert rc_b["rc"] == pytest.approx((90.1 - 89.0) / 89.0)
        assert rc_b["t_team_avg"] == pytest.approx(90.1)

        # TeamA should have lower Rc (faster car)
        assert rc_a["rc"] < rc_b["rc"]

    def test_missing_times_skipped(self) -> None:
        """Drivers with None best_q_time_s are excluded from computation."""
        entries = [
            _make_qual_entry("A1", "TeamA", 90.0, 1),
            _make_qual_entry("A2", "TeamA", None, 2),  # no time
            _make_qual_entry("B1", "TeamB", 91.0, 3),
            _make_qual_entry("B2", "TeamB", 92.0, 4),
        ]
        result = compute_session_rc(entries)
        assert len(result) == 2

        rc_a = result[0]
        # TeamA avg should be just the one valid driver
        assert rc_a["t_team_avg"] == pytest.approx(90.0)

    def test_all_times_missing(self) -> None:
        """If no driver has a valid time, return empty."""
        entries = [
            _make_qual_entry("A1", "TeamA", None, 1),
            _make_qual_entry("B1", "TeamB", None, 2),
        ]
        assert compute_session_rc(entries) == []

    def test_single_driver_team(self) -> None:
        """A team with one driver uses that driver's time directly."""
        entries = [
            _make_qual_entry("A1", "TeamA", 88.0, 1),
            _make_qual_entry("A2", "TeamA", 89.0, 2),
            _make_qual_entry("C1", "TeamC", 91.0, 3),  # solo driver
        ]
        result = compute_session_rc(entries)
        rc_c = [r for r in result if r["team"] == "TeamC"][0]
        assert rc_c["t_team_avg"] == pytest.approx(91.0)
        assert rc_c["rc"] == pytest.approx((91.0 - 88.0) / 88.0)

    def test_fastest_team_rc_is_zero(self) -> None:
        """The team whose avg equals the session fastest should get Rc ~ 0."""
        entries = [
            _make_qual_entry("A1", "TeamA", 80.0, 1),
            _make_qual_entry("A2", "TeamA", 80.0, 2),
            _make_qual_entry("B1", "TeamB", 82.0, 3),
            _make_qual_entry("B2", "TeamB", 83.0, 4),
        ]
        result = compute_session_rc(entries)
        rc_a = [r for r in result if r["team"] == "TeamA"][0]
        # avg = 80.0, fastest = 80.0 -> Rc = 0
        assert rc_a["rc"] == pytest.approx(0.0)

    def test_rc_is_nonnegative(self) -> None:
        """Rc should always be >= 0 since no team avg can be below the session fastest."""
        entries = [
            _make_qual_entry("A1", "TeamA", 85.0, 1),
            _make_qual_entry("A2", "TeamA", 86.0, 2),
            _make_qual_entry("B1", "TeamB", 87.0, 3),
            _make_qual_entry("B2", "TeamB", 88.0, 4),
            _make_qual_entry("C1", "TeamC", 90.0, 5),
            _make_qual_entry("C2", "TeamC", 91.0, 6),
        ]
        result = compute_session_rc(entries)
        for cr in result:
            assert cr["rc"] >= 0.0

    def test_year_round_preserved(self) -> None:
        """Output CarRating should carry the year/round from the input entries."""
        entries = [
            _make_qual_entry("A1", "TeamA", 90.0, 1, year=2023, rnd=5),
        ]
        result = compute_session_rc(entries)
        assert result[0]["year"] == 2023
        assert result[0]["round"] == 5


# ---------------------------------------------------------------------------
# group_qualifying_by_session tests
# ---------------------------------------------------------------------------


class TestGroupQualifyingBySession:
    def test_groups_by_year_round(self) -> None:
        entries = [
            _make_qual_entry("A", "T", 90.0, 1, year=2024, rnd=1),
            _make_qual_entry("B", "T", 91.0, 2, year=2024, rnd=1),
            _make_qual_entry("A", "T", 80.0, 1, year=2024, rnd=2),
        ]
        groups = group_qualifying_by_session(entries)
        assert len(groups) == 2
        assert len(groups[0]) == 2  # round 1
        assert len(groups[1]) == 1  # round 2

    def test_sorted_by_position(self) -> None:
        entries = [
            _make_qual_entry("B", "T", 91.0, 2, year=2024, rnd=1),
            _make_qual_entry("A", "T", 90.0, 1, year=2024, rnd=1),
        ]
        groups = group_qualifying_by_session(entries)
        assert groups[0][0]["driver_id"] == "A"  # position 1 first
        assert groups[0][1]["driver_id"] == "B"


# ---------------------------------------------------------------------------
# compute_rc_range integration tests
# ---------------------------------------------------------------------------


class TestComputeRcRange:
    def test_with_multi_race_db(self, multi_race_db: Path) -> None:
        result = compute_rc_range(2023, 2024, data_dir=multi_race_db)

        # 6 sessions * 3 teams = 18 CarRating entries
        assert len(result) == 18

        # Spot-check: 2023 R1, Red Bull has drivers at 89.0 and 89.5
        # t_team_avg = 89.25, t_fastest = 89.0
        rb_2023_r1 = [r for r in result if r["year"] == 2023 and r["round"] == 1 and r["team"] == "Red Bull Racing"]
        assert len(rb_2023_r1) == 1
        assert rb_2023_r1[0]["rc"] == pytest.approx((89.25 - 89.0) / 89.0)
        assert rb_2023_r1[0]["t_team_avg"] == pytest.approx(89.25)
        assert rb_2023_r1[0]["t_fastest"] == pytest.approx(89.0)

    def test_empty_range(self, multi_race_db: Path) -> None:
        """Year range with no data returns empty list."""
        result = compute_rc_range(1950, 1951, data_dir=multi_race_db)
        assert result == []

    def test_with_populated_db(self, populated_db: Path) -> None:
        """Verify against populated_db fixture (1 session, 2024 R1)."""
        result = compute_rc_range(2024, 2024, data_dir=populated_db)

        # 3 teams: Red Bull, Mercedes, Ferrari
        assert len(result) == 3
        teams = {r["team"]: r for r in result}

        # VER: 89.0, PER: 90.0 -> avg 89.5, fastest = 89.0
        rb = teams["Red Bull Racing"]
        assert rb["rc"] == pytest.approx((89.5 - 89.0) / 89.0)
