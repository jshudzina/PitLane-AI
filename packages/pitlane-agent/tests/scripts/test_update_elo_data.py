"""Tests for update_elo_data script helpers."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

# Import the script module directly since it lives outside the package src tree.
_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "update_elo_data.py"
_spec = importlib.util.spec_from_file_location("update_elo_data", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("update_elo_data", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_classify_retired_via_rcm = _mod._classify_retired_via_rcm


def _make_rcm(*rows: dict) -> pd.DataFrame:
    """Build a minimal race_control_messages DataFrame from dicts."""
    cols = ["Lap", "Message", "Flag", "Scope", "RacingNumber"]
    base = {"Lap": 0, "Message": "", "Flag": None, "Scope": None, "RacingNumber": None}
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([{**base, **r} for r in rows])


class TestClassifyRetiredViaRcm:
    def test_collision_keyword_returns_crash(self):
        rcm = _make_rcm({"Lap": 5, "Message": "CAR 18 (STR) COLLISION AT TURN 22"})
        assert _classify_retired_via_rcm(rcm, "18", 5) == "crash"

    def test_accident_keyword_returns_crash(self):
        rcm = _make_rcm({"Lap": 3, "Message": "CAR 14 (ALO) ACCIDENT AT TURN 5"})
        assert _classify_retired_via_rcm(rcm, "14", 3) == "crash"

    def test_cars_prefix_multi_car_message_returns_crash(self):
        # "CARS N (ABR)" — leading space + number + space + paren is the distinguishing pattern
        rcm = _make_rcm({"Lap": 2, "Message": "CARS 18 (STR) AND 44 (HAM) COLLISION AT TURN 1"})
        assert _classify_retired_via_rcm(rcm, "18", 2) == "crash"

    def test_incident_keyword_returns_crash(self):
        rcm = _make_rcm(
            {"Lap": 1, "Message": "INCIDENT INVOLVING CARS 3 (RIC) AND 23 (ALB) CAUSING A COLLISION"}
        )
        assert _classify_retired_via_rcm(rcm, "3", 1) == "crash"

    def test_stopped_only_no_crash_keyword_returns_mechanical(self):
        # Single-car wall crash: "STOPPED" message but no collision keyword — v1 known gap
        rcm = _make_rcm({"Lap": 7, "Message": "CAR 18 (STR) STOPPED AT TURN 23"})
        assert _classify_retired_via_rcm(rcm, "18", 7) == "mechanical"

    def test_no_messages_for_car_returns_mechanical(self):
        rcm = _make_rcm(
            {"Lap": 5, "Message": "CAR 44 (HAM) COLLISION AT TURN 1"},
        )
        assert _classify_retired_via_rcm(rcm, "18", 5) == "mechanical"

    def test_empty_rcm_returns_mechanical(self):
        rcm = _make_rcm()
        assert _classify_retired_via_rcm(rcm, "77", 15) == "mechanical"

    def test_message_outside_window_ignored(self):
        rcm = _make_rcm({"Lap": 20, "Message": "CAR 18 (STR) COLLISION AT TURN 5"})
        # retirement_lap=5, window=3 → range [2, 8]; lap 20 is outside
        assert _classify_retired_via_rcm(rcm, "18", 5) == "mechanical"

    def test_message_at_window_boundary_included(self):
        rcm = _make_rcm({"Lap": 8, "Message": "CAR 18 (STR) COLLISION AT TURN 5"})
        # retirement_lap=5, window=3 → range [2, 8]; lap 8 is on boundary
        assert _classify_retired_via_rcm(rcm, "18", 5) == "crash"

    def test_retirement_lap_zero_does_not_go_negative(self):
        rcm = _make_rcm({"Lap": 1, "Message": "CAR 6 (HAD) INCIDENT AT TURN 11"})
        assert _classify_retired_via_rcm(rcm, "6", 0) == "crash"

    def test_case_insensitive_car_pattern_via_upper(self):
        # Messages are uppercased internally; lowercase input should still match
        rcm = _make_rcm({"Lap": 5, "Message": "car 18 (str) collision at turn 22"})
        assert _classify_retired_via_rcm(rcm, "18", 5) == "crash"

    def test_multi_car_incident_both_cars_classified_crash(self):
        rcm = _make_rcm(
            {"Lap": 1, "Message": "INCIDENT INVOLVING CARS 3 (RIC) AND 23 (ALB) CAUSING A COLLISION"}
        )
        assert _classify_retired_via_rcm(rcm, "3", 1) == "crash"
        assert _classify_retired_via_rcm(rcm, "23", 1) == "crash"
