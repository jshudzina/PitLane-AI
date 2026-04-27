"""Unit tests for pitlane_elo.stories.signals."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from pitlane_elo.snapshots import EloSnapshot
from pitlane_elo.stories.signals import (
    StorySignal,
    _expected_positions,
    _rows_to_snapshots,
    _sigma_position,
    detect_stories,
    detect_surprise_signals,
    detect_teammate_delta,
    detect_trend_signals,
)

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


def _make_snap(
    driver_id: str,
    *,
    rating: float = 1.0,
    k: float = 0.1,
    win_prob: float = 0.2,
    podium_prob: float = 0.5,
    finish_position: int | None = 1,
    year: int = 2024,
    round_num: int = 5,
    session_type: str = "R",
    dnf_category: str = "none",
) -> EloSnapshot:
    return EloSnapshot(
        year=year,
        round=round_num,
        session_type=session_type,
        driver_id=driver_id,
        pre_race_rating=rating,
        pre_race_k=k,
        win_probability=win_prob,
        podium_probability=podium_prob,
        finish_position=finish_position,
        dnf_category=dnf_category,
    )


def _write_snapshot_parquet(data_dir: Path, rows: list[tuple]) -> None:
    """Write snapshot tuples to elo_snapshots/snapshots.parquet.

    Each row: (year, round, session_type, driver_id, pre_race_rating, pre_race_k,
               win_probability, podium_probability, finish_position, dnf_category)
    """
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


def _make_entry(driver_id: str, team: str, *, year: int = 2024, round_num: int = 5) -> dict:
    return {
        "year": year,
        "round": round_num,
        "session_type": "R",
        "driver_id": driver_id,
        "team": team,
    }


# ---------------------------------------------------------------------------
# StorySignal
# ---------------------------------------------------------------------------


class TestStorySignal:
    def test_to_dict_rounds_value(self):
        sig = StorySignal(
            signal_type="hot_streak",
            driver_id="VER",
            year=2024,
            round=5,
            value=0.123456789,
            threshold=0.5,
            narrative="test",
            context={"foo": "bar"},
        )
        d = sig.to_dict()
        assert d["value"] == round(0.123456789, 4)

    def test_to_dict_contains_all_fields(self):
        sig = StorySignal("slump", "HAM", 2024, 5, -0.7, -0.5, "narrative", {})
        d = sig.to_dict()
        assert set(d) == {
            "signal_type",
            "driver_id",
            "year",
            "round",
            "value",
            "threshold",
            "narrative",
            "context",
        }

    def test_to_dict_preserves_context(self):
        ctx = {"team": "Ferrari", "lookback_races": 3}
        sig = StorySignal("teammate_shift", "LEC", 2024, 5, 0.3, 0.1, "text", ctx)
        assert sig.to_dict()["context"] == ctx


# ---------------------------------------------------------------------------
# _sigma_position
# ---------------------------------------------------------------------------


class TestSigmaPosition:
    def test_floor_at_zero_k(self):
        assert _sigma_position(0.0) == 3.0

    def test_scales_linearly_with_k(self):
        assert _sigma_position(1.0) == pytest.approx(8.0)
        assert _sigma_position(0.5) == pytest.approx(5.5)

    def test_floor_dominates_negative_k(self):
        assert _sigma_position(-1.0) == 3.0


# ---------------------------------------------------------------------------
# _expected_positions
# ---------------------------------------------------------------------------


class TestExpectedPositions:
    def test_ranked_by_win_probability_descending(self):
        snaps = [
            _make_snap("VER", win_prob=0.5),
            _make_snap("HAM", win_prob=0.3),
            _make_snap("SAI", win_prob=0.1),
        ]
        positions = _expected_positions(snaps)
        assert positions == {"VER": 1, "HAM": 2, "SAI": 3}

    def test_single_driver(self):
        assert _expected_positions([_make_snap("VER", win_prob=0.9)]) == {"VER": 1}

    def test_all_drivers_assigned(self):
        snaps = [_make_snap(f"D{i}", win_prob=0.1) for i in range(5)]
        positions = _expected_positions(snaps)
        assert set(positions.values()) == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# _rows_to_snapshots
# ---------------------------------------------------------------------------


class TestRowsToSnapshots:
    _COLS = [
        "year",
        "round",
        "session_type",
        "driver_id",
        "pre_race_rating",
        "pre_race_k",
        "win_probability",
        "podium_probability",
        "finish_position",
        "dnf_category",
    ]

    def test_maps_columns_to_dataclass(self):
        rows = [(2024, 5, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none")]
        snaps = _rows_to_snapshots(rows, self._COLS)
        assert len(snaps) == 1
        s = snaps[0]
        assert s.driver_id == "VER"
        assert s.pre_race_rating == 1.0
        assert s.finish_position == 1

    def test_none_finish_position_preserved(self):
        rows = [(2024, 5, "R", "DNF", 1.0, 0.1, 0.5, 0.8, None, "mechanical")]
        snaps = _rows_to_snapshots(rows, self._COLS)
        assert snaps[0].finish_position is None

    def test_empty_rows(self):
        assert _rows_to_snapshots([], []) == []

    def test_multiple_rows(self):
        rows = [(2024, 5, "R", f"D{i}", float(i), 0.1, 0.1, 0.3, i + 1, "none") for i in range(3)]
        snaps = _rows_to_snapshots(rows, self._COLS)
        assert len(snaps) == 3
        assert [s.driver_id for s in snaps] == ["D0", "D1", "D2"]


# ---------------------------------------------------------------------------
# detect_surprise_signals
# ---------------------------------------------------------------------------


def _big_field_overperformer() -> list[EloSnapshot]:
    """20-driver field where VER (lowest win_prob) finishes P1.

    Expected position for VER = 20. sigma = 3.0 (k=0).
    SurpriseScore = (1 - 20) / 3.0 = -6.33 → surprise_over.
    """
    others = [_make_snap(f"D{i}", win_prob=1.0 / (i + 1), k=0.0, finish_position=i + 1) for i in range(19)]
    ver = _make_snap("VER", win_prob=0.001, k=0.0, finish_position=1)
    return others + [ver]


def _big_field_underperformer() -> list[EloSnapshot]:
    """20-driver field where VER (highest win_prob) finishes last.

    Expected position for VER = 1. sigma = 3.0 (k=0).
    SurpriseScore = (20 - 1) / 3.0 = 6.33 → surprise_under.
    """
    others = [_make_snap(f"D{i}", win_prob=1.0 / (i + 2), k=0.0, finish_position=i + 2) for i in range(19)]
    ver = _make_snap("VER", win_prob=1.0, k=0.0, finish_position=20)
    return others + [ver]


class TestDetectSurpriseSignals:
    def test_empty_snapshots_returns_empty(self):
        assert detect_surprise_signals([], 2024, 5) == []

    def test_none_finish_position_skipped(self):
        snaps = [_make_snap("VER", finish_position=None)]
        assert detect_surprise_signals(snaps, 2024, 5) == []

    def test_surprise_over_detected(self):
        snaps = _big_field_overperformer()
        signals = detect_surprise_signals(snaps, 2024, 5)
        over = [s for s in signals if s.signal_type == "surprise_over" and s.driver_id == "VER"]
        assert len(over) == 1
        assert over[0].value < -2.0

    def test_surprise_under_detected(self):
        snaps = _big_field_underperformer()
        signals = detect_surprise_signals(snaps, 2024, 5)
        under = [s for s in signals if s.signal_type == "surprise_under" and s.driver_id == "VER"]
        assert len(under) == 1
        assert under[0].value > 2.0

    def test_no_surprise_within_threshold(self):
        # 3 drivers, each finishes as expected → |score| << 2.0
        snaps = [
            _make_snap("VER", win_prob=0.5, k=0.0, finish_position=1),
            _make_snap("HAM", win_prob=0.3, k=0.0, finish_position=2),
            _make_snap("SAI", win_prob=0.1, k=0.0, finish_position=3),
        ]
        assert detect_surprise_signals(snaps, 2024, 5) == []

    def test_year_and_round_propagated(self):
        snaps = _big_field_overperformer()
        signals = detect_surprise_signals(snaps, 2023, 10)
        ver_signal = next(s for s in signals if s.driver_id == "VER")
        assert ver_signal.year == 2023
        assert ver_signal.round == 10

    def test_surprise_over_narrative(self):
        snaps = _big_field_overperformer()
        signals = detect_surprise_signals(snaps, 2024, 5)
        ver_signal = next(s for s in signals if s.driver_id == "VER")
        assert "overperformed" in ver_signal.narrative
        assert "VER" in ver_signal.narrative

    def test_surprise_under_narrative(self):
        snaps = _big_field_underperformer()
        signals = detect_surprise_signals(snaps, 2024, 5)
        ver_signal = next(s for s in signals if s.driver_id == "VER")
        assert "underperformed" in ver_signal.narrative

    def test_higher_k_dampens_score(self):
        # Same position delta but high k → larger sigma → smaller |score|
        snaps_low_k = [
            _make_snap("VER", win_prob=0.001, k=0.0, finish_position=1),
            *[_make_snap(f"D{i}", win_prob=1.0 / (i + 1), k=0.0, finish_position=i + 1) for i in range(19)],
        ]
        snaps_high_k = [
            _make_snap("VER", win_prob=0.001, k=2.0, finish_position=1),
            *[_make_snap(f"D{i}", win_prob=1.0 / (i + 1), k=2.0, finish_position=i + 1) for i in range(19)],
        ]
        signals_low = detect_surprise_signals(snaps_low_k, 2024, 5)
        signals_high = detect_surprise_signals(snaps_high_k, 2024, 5)
        ver_low = next(s for s in signals_low if s.driver_id == "VER")
        ver_high = [s for s in signals_high if s.driver_id == "VER"]
        # High k inflates sigma so score may not cross threshold at all, or is smaller magnitude
        assert abs(ver_low.value) > abs(ver_high[0].value) if ver_high else True

    def test_context_contains_expected_fields(self):
        snaps = _big_field_overperformer()
        signals = detect_surprise_signals(snaps, 2024, 5)
        ver_signal = next(s for s in signals if s.driver_id == "VER")
        ctx = ver_signal.context
        assert "expected_position" in ctx
        assert "actual_position" in ctx
        assert ctx["actual_position"] == 1


# ---------------------------------------------------------------------------
# detect_trend_signals
# ---------------------------------------------------------------------------


class TestDetectTrendSignals:
    def test_no_history_directory_returns_empty(self, tmp_path):
        snaps = [_make_snap("VER", rating=1.5)]
        assert detect_trend_signals(snaps, 2024, 5, data_dir=tmp_path) == []

    def test_insufficient_history_skips_driver(self, tmp_path):
        # Only 2 historical races; n=3 requires 3 → driver skipped
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 3, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "VER", 1.2, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [_make_snap("VER", rating=1.5)]
        assert detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path) == []

    def test_hot_streak_detected(self, tmp_path):
        # delta = 1.5 − 0.7 = 0.8 > 0.5 threshold
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "VER", 0.7, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "VER", 1.2, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [_make_snap("VER", rating=1.5)]
        signals = detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path)
        hot = [s for s in signals if s.signal_type == "hot_streak"]
        assert len(hot) == 1
        assert hot[0].driver_id == "VER"
        assert hot[0].value == pytest.approx(0.8)

    def test_slump_detected(self, tmp_path):
        # delta = 0.8 − 1.5 = -0.7 < -0.5 threshold
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "HAM", 1.5, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "HAM", 1.3, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "HAM", 1.1, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [_make_snap("HAM", rating=0.8)]
        signals = detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path)
        slump = [s for s in signals if s.signal_type == "slump"]
        assert len(slump) == 1
        assert slump[0].driver_id == "HAM"
        assert slump[0].value == pytest.approx(-0.7)

    def test_delta_below_threshold_no_signal(self, tmp_path):
        # delta = 1.0 − 0.9 = 0.1 < 0.5 threshold → no signal
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "SAI", 0.9, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "SAI", 0.95, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [_make_snap("SAI", rating=1.0)]
        assert detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path) == []

    def test_hot_and_slump_in_same_field(self, tmp_path):
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "VER", 0.7, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "VER", 1.2, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 2, "R", "HAM", 1.5, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "HAM", 1.3, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "HAM", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 2, "R", "SAI", 0.9, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "SAI", 0.95, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [
            _make_snap("VER", rating=1.5),
            _make_snap("HAM", rating=0.8),
            _make_snap("SAI", rating=1.0),
        ]
        signals = detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path)
        types = {s.signal_type for s in signals}
        assert "hot_streak" in types
        assert "slump" in types
        hot = next(s for s in signals if s.signal_type == "hot_streak")
        slump = next(s for s in signals if s.signal_type == "slump")
        assert hot.driver_id == "VER"
        assert slump.driver_id == "HAM"

    def test_history_excludes_current_race(self, tmp_path):
        # Round 5 itself must not count as history
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 3, "R", "VER", 0.7, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 5, "R", "VER", 1.2, 0.1, 0.5, 0.8, 1, "none"),  # same race → excluded
            ],
        )
        snaps = [_make_snap("VER", rating=1.5)]
        # Only 2 valid history rows (rounds 3,4) for n=3 → insufficient → no signal
        assert detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path) == []

    def test_path_with_single_quote_returns_signals(self, tmp_path):
        # Paths containing single quotes (e.g. /Users/O'Brien/) must not break
        # the DuckDB query via quote injection in the read_parquet() f-string.
        normal_dir = tmp_path / "normal"
        _write_snapshot_parquet(
            normal_dir,
            [
                (2024, 2, "R", "VER", 0.7, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "VER", 1.2, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        import shutil

        quoted_dir = tmp_path / "O'Brien"
        quoted_snapshots = quoted_dir / "elo_snapshots"
        quoted_snapshots.mkdir(parents=True)
        shutil.copy(
            normal_dir / "elo_snapshots" / "snapshots.parquet",
            quoted_snapshots / "snapshots.parquet",
        )
        snaps = [_make_snap("VER", rating=1.5)]
        signals = detect_trend_signals(snaps, 2024, 5, n=3, data_dir=quoted_dir)
        hot = [s for s in signals if s.signal_type == "hot_streak"]
        assert len(hot) == 1

    def test_context_includes_lookback_and_rating(self, tmp_path):
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "VER", 0.7, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "VER", 1.0, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "VER", 1.2, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [_make_snap("VER", rating=1.5)]
        signals = detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path)
        assert signals[0].context["lookback_races"] == 3
        assert signals[0].context["current_rating"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# detect_teammate_delta
# ---------------------------------------------------------------------------


class TestDetectTeammateDelta:
    def test_single_driver_per_team_no_signal(self, tmp_path):
        snaps = [_make_snap("VER", rating=1.5)]
        entries = [_make_entry("VER", "Red Bull Racing")]
        assert detect_teammate_delta(snaps, entries, 2024, 5, data_dir=tmp_path) == []

    def test_consistent_leader_signal(self, tmp_path):
        # LEC consistently ahead of SAI in history and now
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 2, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 3, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
            ],
        )
        snaps = [_make_snap("LEC", rating=1.3), _make_snap("SAI", rating=1.0)]
        entries = [_make_entry("LEC", "Ferrari"), _make_entry("SAI", "Ferrari")]
        signals = detect_teammate_delta(snaps, entries, 2024, 5, data_dir=tmp_path)
        assert len(signals) == 1
        s = signals[0]
        assert s.signal_type == "teammate_shift"
        assert s.driver_id == "LEC"
        assert "LEC" in s.narrative and "SAI" in s.narrative

    def test_gap_flip_signal(self, tmp_path):
        # HAM historically behind RUS; now HAM ahead → flip
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "HAM", 0.9, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 3, "R", "HAM", 0.9, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 4, "R", "HAM", 0.9, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 2, "R", "RUS", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "RUS", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "RUS", 1.1, 0.1, 0.5, 0.8, 1, "none"),
            ],
        )
        snaps = [_make_snap("HAM", rating=1.2), _make_snap("RUS", rating=1.0)]
        entries = [_make_entry("HAM", "Mercedes"), _make_entry("RUS", "Mercedes")]
        signals = detect_teammate_delta(snaps, entries, 2024, 5, data_dir=tmp_path)
        assert len(signals) == 1
        s = signals[0]
        assert s.driver_id == "HAM"
        assert "reversed" in s.narrative

    def test_insufficient_common_races_skipped(self, tmp_path):
        # Only 2 common races; lookback=3 → skipped
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 3, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "LEC", 1.2, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
            ],
        )
        snaps = [_make_snap("LEC", rating=1.3), _make_snap("SAI", rating=1.0)]
        entries = [_make_entry("LEC", "Ferrari"), _make_entry("SAI", "Ferrari")]
        signals = detect_teammate_delta(snaps, entries, 2024, 5, lookback=3, data_dir=tmp_path)
        assert signals == []

    def test_gap_below_minimum_no_signal(self, tmp_path):
        # Consistent leader but gap 0.05 < _TEAMMATE_GAP_MIN=0.1
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "LEC", 1.03, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "LEC", 1.03, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "LEC", 1.03, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 2, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 3, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
            ],
        )
        snaps = [_make_snap("LEC", rating=1.05), _make_snap("SAI", rating=1.0)]
        entries = [_make_entry("LEC", "Ferrari"), _make_entry("SAI", "Ferrari")]
        signals = detect_teammate_delta(snaps, entries, 2024, 5, lookback=3, data_dir=tmp_path)
        assert signals == []

    def test_missing_driver_in_snapshots_skipped(self, tmp_path):
        # SAI has history but not in current race_snapshots → team pair skipped
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 2, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 3, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
            ],
        )
        snaps = [_make_snap("LEC", rating=1.3)]  # SAI absent from current snapshots
        entries = [_make_entry("LEC", "Ferrari"), _make_entry("SAI", "Ferrari")]
        signals = detect_teammate_delta(snaps, entries, 2024, 5, data_dir=tmp_path)
        assert signals == []

    def test_context_includes_team_and_teammate(self, tmp_path):
        _write_snapshot_parquet(
            tmp_path,
            [
                (2024, 2, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 3, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 4, "R", "LEC", 1.1, 0.1, 0.5, 0.8, 1, "none"),
                (2024, 2, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 3, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
                (2024, 4, "R", "SAI", 1.0, 0.1, 0.5, 0.8, 2, "none"),
            ],
        )
        snaps = [_make_snap("LEC", rating=1.3), _make_snap("SAI", rating=1.0)]
        entries = [_make_entry("LEC", "Ferrari"), _make_entry("SAI", "Ferrari")]
        signals = detect_teammate_delta(snaps, entries, 2024, 5, data_dir=tmp_path)
        ctx = signals[0].context
        assert ctx["team"] == "Ferrari"
        assert ctx["teammate"] == "SAI"
        assert "historical_deltas" in ctx


# ---------------------------------------------------------------------------
# detect_stories (integration smoke tests)
# ---------------------------------------------------------------------------


class TestDetectStories:
    def test_no_snapshots_returns_empty(self, tmp_path):
        assert detect_stories(2024, 5, data_dir=tmp_path) == []

    def test_returns_list_of_story_signals(self, tmp_path):
        # Set up a race with one clear surprise
        rows = [(2024, 5, "R", f"D{i}", float(i), 0.0, 1.0 / (i + 1), 0.5, i + 1, "none") for i in range(19)]
        # VER expected last (win_prob=0.001), finishes P1 → surprise_over
        rows.append((2024, 5, "R", "VER", 1.0, 0.0, 0.001, 0.01, 1, "none"))
        _write_snapshot_parquet(tmp_path, rows)
        signals = detect_stories(2024, 5, data_dir=tmp_path)
        assert isinstance(signals, list)
        assert all(isinstance(s, StorySignal) for s in signals)

    def test_signals_sorted_by_abs_value_descending(self, tmp_path):
        # VER massive overperformance (|score|≈6.33) + HAM moderate underperformance
        # HAM expected P1 (win_prob=0.9), finishes P5 → score=(5-1)/3.0=1.33 → no signal
        # Use engineered values to get 2 detectable signals
        rows = []
        # 20-driver field; D0 highest win_prob … VER lowest
        for i in range(18):
            rows.append((2024, 5, "R", f"D{i}", float(i), 0.0, 1.0 / (i + 2), 0.5, i + 3, "none"))
        # HAM: expected P1 (win_prob=1.0), finishes P20 → score=(20-1)/3.0=6.33 → surprise_under
        rows.append((2024, 5, "R", "HAM", 2.0, 0.0, 1.0, 0.9, 20, "none"))
        # VER: expected P20 (win_prob=0.001), finishes P1 → score=(1-20)/3.0=-6.33 → surprise_over
        rows.append((2024, 5, "R", "VER", 1.0, 0.0, 0.001, 0.01, 1, "none"))
        _write_snapshot_parquet(tmp_path, rows)
        signals = detect_stories(2024, 5, data_dir=tmp_path)
        abs_values = [abs(s.value) for s in signals]
        assert abs_values == sorted(abs_values, reverse=True)

    def test_single_duckdb_connection_for_multiple_drivers(self, tmp_path):
        # detect_trend_signals must open exactly one DuckDB connection regardless of driver
        # count. Currently _get_recent_snapshots opens a new connection per driver call.
        from unittest.mock import patch

        import duckdb as real_duckdb

        rows = []
        for driver in ("VER", "HAM", "SAI"):
            for rnd in (2, 3, 4):
                rows.append((2024, rnd, "R", driver, 1.0, 0.1, 0.5, 0.8, 1, "none"))
        _write_snapshot_parquet(tmp_path, rows)

        snaps = [_make_snap(d, rating=1.5) for d in ("VER", "HAM", "SAI")]
        connect_calls = []
        original_connect = real_duckdb.connect

        def counting_connect(*args, **kwargs):
            connect_calls.append(1)
            return original_connect(*args, **kwargs)

        with patch("pitlane_elo.stories.signals.duckdb.connect", side_effect=counting_connect):
            detect_trend_signals(snaps, 2024, 5, n=3, data_dir=tmp_path)

        assert len(connect_calls) == 1, (
            f"Expected 1 DuckDB connection for 3 drivers; got {len(connect_calls)}. "
            "_get_recent_snapshots is opening a new connection per driver call."
        )
