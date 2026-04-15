"""Tests for pitlane_elo.bayesian.data_prep — all deterministic, no PyMC."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pitlane_elo.bayesian.data_prep import SeasonData, prepare_season, prepare_season_from_db
from pitlane_elo.data import RaceEntry


def _make_entry(
    driver_id: str,
    team: str,
    finish: int | None,
    *,
    round_num: int = 1,
    laps: int = 57,
    dnf_category: str = "none",
    is_wet_race: bool = False,
    is_street_circuit: bool = False,
) -> RaceEntry:
    return {
        "year": 2023,
        "round": round_num,
        "session_type": "R",
        "driver_id": driver_id,
        "team": team,
        "laps_completed": laps,
        "status": "Finished" if dnf_category == "none" else "Retired",
        "dnf_category": dnf_category,
        "is_wet_race": is_wet_race,
        "is_street_circuit": is_street_circuit,
        "finish_position": finish,
    }


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SIMPLE_RACE: list[RaceEntry] = [
    _make_entry("alpha", "TeamA", 1),
    _make_entry("beta", "TeamA", 2),
    _make_entry("gamma", "TeamB", 3),
]

TWO_RACE_SEASON: list[list[RaceEntry]] = [
    SIMPLE_RACE,
    [
        _make_entry("alpha", "TeamA", 2, round_num=2),
        _make_entry("beta", "TeamA", 1, round_num=2),
        _make_entry("gamma", "TeamB", 3, round_num=2),
    ],
]


class TestPrepareSeasonBasicShape:
    def test_n_drivers(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert data.n_drivers == 3

    def test_n_teams(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert data.n_teams == 2

    def test_n_races(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert data.n_races == 2

    def test_race_orders_length(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert len(data.race_orders) == 2
        for order in data.race_orders:
            assert len(order) == 3

    def test_context_flags_shape(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert data.is_wet_race.shape == (2,)
        assert data.is_street_circuit.shape == (2,)

    def test_context_flags_default_false(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert not data.is_wet_race.any()
        assert not data.is_street_circuit.any()


class TestAlphabeticalOrdering:
    def test_driver_ids_sorted(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert data.driver_ids == tuple(sorted(data.driver_ids))

    def test_team_ids_sorted(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        assert data.team_ids == tuple(sorted(data.team_ids))

    def test_deterministic_across_calls(self) -> None:
        d1 = prepare_season(TWO_RACE_SEASON)
        d2 = prepare_season(TWO_RACE_SEASON)
        assert d1.driver_ids == d2.driver_ids
        assert d1.team_ids == d2.team_ids
        np.testing.assert_array_equal(d1.driver_team_idx, d2.driver_team_idx)

    def test_driver_to_idx_reverse_of_driver_ids(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        for i, d in enumerate(data.driver_ids):
            assert data.driver_to_idx[d] == i

    def test_team_to_idx_reverse_of_team_ids(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        for i, t in enumerate(data.team_ids):
            assert data.team_to_idx[t] == i


class TestDriverTeamMapping:
    def test_team_a_drivers_map_to_same_team_idx(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        alpha_team = data.driver_team_idx[data.driver_to_idx["alpha"]]
        beta_team = data.driver_team_idx[data.driver_to_idx["beta"]]
        assert alpha_team == beta_team

    def test_gamma_maps_to_team_b(self) -> None:
        data = prepare_season(TWO_RACE_SEASON)
        gamma_idx = data.driver_to_idx["gamma"]
        team_b_idx = data.team_to_idx["TeamB"]
        assert data.driver_team_idx[gamma_idx] == team_b_idx

    def test_most_common_team_wins_for_switcher(self) -> None:
        # zeta drives TeamA for 3 races, TeamB for 1 — should be assigned TeamA.
        season = [[_make_entry("zeta", "TeamA", 1, round_num=r)] for r in range(1, 4)] + [
            [_make_entry("zeta", "TeamB", 1, round_num=4)]
        ]
        data = prepare_season(season, min_finishers=1)
        zeta_team_idx = data.driver_team_idx[data.driver_to_idx["zeta"]]
        assert data.team_ids[zeta_team_idx] == "TeamA"


class TestDNFHandling:
    """DNF categorisation is not used; any driver without a finish_position is excluded."""

    def test_dnf_excluded_from_ordering(self) -> None:
        race = [
            _make_entry("alpha", "TeamA", 1),
            _make_entry("beta", "TeamA", 2),
            _make_entry("gamma", "TeamB", None, laps=30, dnf_category="mechanical"),
        ]
        data = prepare_season([race])
        assert data.n_races == 1
        # Only 2 classified finishers in the race order.
        assert len(data.race_orders[0]) == 2

    def test_crash_dnf_also_excluded(self) -> None:
        race = [
            _make_entry("alpha", "TeamA", 1),
            _make_entry("beta", "TeamA", 2),
            _make_entry("gamma", "TeamB", None, laps=10, dnf_category="crash"),
        ]
        data = prepare_season([race])
        assert len(data.race_orders[0]) == 2

    def test_dnf_driver_still_in_vocabulary(self) -> None:
        # A driver who DNFs in one race but finishes another is still indexed.
        races = [
            [
                _make_entry("alpha", "TeamA", 1),
                _make_entry("gamma", "TeamB", None, laps=5, dnf_category="mechanical"),
            ],
            [
                _make_entry("alpha", "TeamA", 1, round_num=2),
                _make_entry("gamma", "TeamB", 2, round_num=2),
            ],
        ]
        data = prepare_season(races, min_finishers=1)
        assert "gamma" in data.driver_ids

    def test_dnf_category_field_not_consulted(self) -> None:
        # A driver with finish_position set is always included regardless of dnf_category.
        race = [
            _make_entry("alpha", "TeamA", 1),
            _make_entry("beta", "TeamB", 2, dnf_category="crash"),  # has finish_position
        ]
        data = prepare_season([race])
        assert len(data.race_orders[0]) == 2


class TestMinFinishers:
    def test_race_dropped_when_too_few_finishers(self) -> None:
        # Only 1 classified finisher — below default min_finishers=2.
        race = [
            _make_entry("alpha", "TeamA", 1),
            _make_entry("beta", "TeamA", None, laps=5, dnf_category="mechanical"),
        ]
        data = prepare_season([race], min_finishers=2)
        assert data.n_races == 0

    def test_race_kept_at_exactly_min_finishers(self) -> None:
        race = [
            _make_entry("alpha", "TeamA", 1),
            _make_entry("beta", "TeamB", 2),
        ]
        data = prepare_season([race], min_finishers=2)
        assert data.n_races == 1


class TestContextFlags:
    def test_wet_race_flag_propagates(self) -> None:
        race = [
            _make_entry("alpha", "TeamA", 1, is_wet_race=True),
            _make_entry("beta", "TeamB", 2, is_wet_race=True),
        ]
        data = prepare_season([race])
        assert data.is_wet_race[0]

    def test_street_circuit_flag_propagates(self) -> None:
        race = [
            _make_entry("alpha", "TeamA", 1, is_street_circuit=True),
            _make_entry("beta", "TeamB", 2, is_street_circuit=True),
        ]
        data = prepare_season([race])
        assert data.is_street_circuit[0]


class TestPrepareSeasonFromDb:
    def test_returns_none_for_empty_year(self, tmp_db: Path) -> None:
        result = prepare_season_from_db(1900, db_path=tmp_db)
        assert result is None

    def test_returns_season_data_for_populated_year(self, multi_race_db: Path) -> None:
        result = prepare_season_from_db(2023, db_path=multi_race_db)
        assert isinstance(result, SeasonData)

    def test_correct_driver_count_from_db(self, multi_race_db: Path) -> None:
        result = prepare_season_from_db(2023, db_path=multi_race_db)
        assert result is not None
        # multi_race_db has 5 drivers.
        assert result.n_drivers == 5

    def test_correct_race_count_from_db(self, multi_race_db: Path) -> None:
        result = prepare_season_from_db(2023, db_path=multi_race_db)
        assert result is not None
        # multi_race_db has 3 rounds in 2023; HAM's mechanical DNF in R2
        # means after filtering R2 still has 4 finishers (>= min_finishers=2).
        assert result.n_races == 3
