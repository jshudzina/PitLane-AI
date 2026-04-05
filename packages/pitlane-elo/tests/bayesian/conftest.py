"""Shared fixtures for van Kesteren Bayesian model tests."""

from __future__ import annotations

import pytest
from pitlane_elo.bayesian.van_kesteren import VAN_KESTEREN_FAST, VanKesterenConfig
from pitlane_elo.data import RaceEntry


def _make_entry(
    driver_id: str,
    team: str,
    finish: int | None,
    *,
    round_num: int = 1,
    laps: int = 57,
    dnf_category: str = "none",
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
        "is_wet_race": False,
        "is_street_circuit": False,
        "finish_position": finish,
    }


@pytest.fixture()
def fast_config() -> VanKesterenConfig:
    """VAN_KESTEREN_FAST config for use in unit tests."""
    return VAN_KESTEREN_FAST


@pytest.fixture()
def fast_config_step2() -> VanKesterenConfig:
    """Fast config with model_step=2 for seasonal form tests."""
    return VanKesterenConfig(
        name="van-kesteren-fast-step2",
        model_step=2,
        draws=200,
        tune=200,
        chains=2,
        random_seed=42,
    )


@pytest.fixture()
def dominant_season() -> list[list[RaceEntry]]:
    """5 races where driver_a always wins, driver_b is second, driver_c is third.

    Two teams: TeamA (driver_a, driver_b) and TeamB (driver_c).
    The clear dominance hierarchy makes rank-ordering tests robust to sampling noise.
    """
    races = []
    for r in range(1, 6):
        races.append([
            _make_entry("driver_a", "TeamA", 1, round_num=r),
            _make_entry("driver_b", "TeamA", 2, round_num=r),
            _make_entry("driver_c", "TeamB", 3, round_num=r),
        ])
    return races
